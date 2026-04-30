---
source_example: atelier-connect/examples/md_worker/run_market_worker.rs
source_manifest: atelier-connect/examples/md_worker/md_worker_bybit.toml
sdk_version: "0.0.10"
sdk_commit: "(record this before cutover)"
---

# Bybit → Parquet

The simplest end-to-end path through the SDK. Connect to Bybit's
public WebSocket, synchronize the order-book and trade feeds onto a
200 ms grid, and write the result to Parquet — three symbols, two
data types, hands-off shutdown via Ctrl-C or a configured timer.

This tutorial uses a **TOML manifest** to drive the worker rather
than wiring everything in Rust. A manifest is the production pattern:
the same binary can target any exchange and any symbol set without
recompiling.

!!! note "Source"
    Code lifted from
    [`atelier-connect/examples/md_worker/run_market_worker.rs`](https://github.com/IteraLabs/atelier-sdk/tree/main/atelier-connect/examples/md_worker)
    in atelier-sdk. The manifest is `md_worker_bybit.toml` from the
    same directory.

## What you'll build

By the end:

- A `cargo run` command that streams BTCUSDT, ETHUSDT, and SOLUSDT
  order books and trades from Bybit.
- A `datasets/collected/bybit/` directory full of Parquet files,
  grouped by data type (`orderbooks/`, `trades/`).
- Terminal output for live visibility while the worker runs.

## 1. Project setup

```toml
# Cargo.toml
[package]
name = "bybit-to-parquet"
version = "0.1.0"
edition = "2024"

[dependencies]
atelier-connect    = { version = "0.0.10", features = ["parquet"] }
anyhow             = "1"
clap               = { version = "4", features = ["derive"] }
tokio              = { version = "1", features = ["full"] }
tracing            = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

The `parquet` feature on `atelier-connect` opts into `ParquetSink`.

## 2. The TOML manifest

**`md_worker_bybit.toml`**

```toml
# Bybit MarketWorker — synchronised snapshots to Parquet.

[collect]
exchange = "bybit"
gap_threshold_secs = 30

[collect.datatypes.orderbook]
enabled = true
depth = 50

[collect.datatypes.trades]
enabled = true

[collect.datatypes.liquidations]
enabled = false

[collect.datatypes.funding_rates]
enabled = false

[collect.datatypes.open_interest]
enabled = false

[collect.sync]
sync_mode = "on_time"
flush_threshold = 3000  # snapshots per Parquet flush (3000 × 200ms = 10 min)

[collect.sync.update_frequency]
value = 200
unit = "Millis"

# Dual output: Parquet for persistence + Terminal for visibility.
[[collect.output]]
type = "parquet"
dir  = "datasets/collected/bybit/"

[[collect.output]]
type = "terminal"

# ── Workers ─────────────────────────────────────────────────────────────

[[workers]]
symbol = "BTCUSDT"

[[workers]]
symbol = "ETHUSDT"

[[workers]]
symbol = "SOLUSDT"

# ── Session ─────────────────────────────────────────────────────────────

# Optional: run for N hours then shut down gracefully.
# Otherwise runs until Ctrl-C.
# [session]
# duration_hours = 0.5
```

A few things worth pointing at:

- **`[collect.datatypes.*]`** — the per-datatype enable flags. Bybit
  exposes liquidations, funding rates, and open interest, but for a
  beta walkthrough we keep it to orderbook + trades.
- **`[collect.sync] sync_mode = "on_time"`** — uses `ExternalClock`
  mode, ticking the grid every `update_frequency` regardless of what
  events arrived. Predictable cadence regardless of market activity.
- **`flush_threshold = 3000`** — 3000 snapshots × 200 ms = 10 minutes
  of data per Parquet file. Tunable for your I/O budget.
- **Dual output** — Parquet for persistence, Terminal for live
  visibility. The `OutputSinkSet` fans out to both.
- **`[[workers]]`** — three symbols, three independent workers. Each
  gets its own connection, its own synchronizer, its own files.

## 3. The runner

**`src/main.rs`**

```rust
//! MarketWorker example — synchronised market snapshots to Parquet.

use clap::Parser;
use std::{path::PathBuf, time::Duration};
use tokio::{sync::watch, task::JoinSet};
use tracing_subscriber::EnvFilter;

use atelier_connect::{
    config::workers::MarketWorkerManifest,
    workers::market_worker::MarketWorker,
};

#[derive(Parser, Debug)]
#[command(name = "bybit-to-parquet", version, about)]
struct Cli {
    /// Path to a TOML worker manifest file.
    #[arg(short, long)]
    config: PathBuf,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .with_target(true)
        .init();

    let cli = Cli::parse();
    let manifest = MarketWorkerManifest::from_toml(&cli.config)?;
    let configs = manifest.resolve_all();

    if configs.is_empty() {
        anyhow::bail!("manifest is empty");
    }

    tracing::info!(
        workers = configs.len(),
        config = %cli.config.display(),
        "examples.market_worker.starting"
    );

    // ── shutdown signalling ─────────────────────────────────────────
    let (shutdown_tx, shutdown_rx) = watch::channel(false);
    let shutdown_tx_clone = shutdown_tx.clone();

    tokio::spawn(async move {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
        tracing::info!("shutdown_requested");
        let _ = shutdown_tx_clone.send(true);
    });

    if let Some(dur_secs) = manifest.duration_secs() {
        let shutdown_tx_clone = shutdown_tx.clone();
        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_secs_f64(dur_secs)).await;
            tracing::info!(duration_secs = dur_secs, "session_elapsed");
            let _ = shutdown_tx_clone.send(true);
        });
    }

    // ── spawn workers ────────────────────────────────────────────────
    let mut join_set = JoinSet::new();

    for (i, cfg) in configs.into_iter().enumerate() {
        let rx = shutdown_rx.clone();
        let label = format!("{}:{}", cfg.common.exchange, cfg.common.symbol);

        let worker = MarketWorker::from_config(cfg)?;
        tracing::info!(worker = i, label = %label, "spawning");

        // Stagger the connections so we don't burst all sockets at t=0.
        if i > 0 {
            tokio::time::sleep(Duration::from_millis(250)).await;
        }
        join_set.spawn(async move { worker.run(rx).await });
    }

    // ── await results ────────────────────────────────────────────────
    let mut total_snapshots: u64 = 0;
    while let Some(result) = join_set.join_next().await {
        match result {
            Ok(Ok(report)) => {
                tracing::info!(
                    exchange = %report.ingestion.exchange,
                    symbol = %report.ingestion.symbol,
                    total_events = report.ingestion.total_events,
                    snapshots = report.snapshots_produced,
                    flushes = report.flushes,
                    elapsed = format!("{:.1}s", report.ingestion.elapsed_secs),
                    reconnects = report.ingestion.reconnect_count,
                    "finished"
                );
                total_snapshots += report.snapshots_produced;
            }
            Ok(Err(e)) => tracing::error!(error = %e, "worker_error"),
            Err(e) => tracing::error!(error = %e, "worker_panic"),
        }
    }

    tracing::info!(total_snapshots, "all_done");
    Ok(())
}
```

The structure is worth noting:

- **One manifest, many workers.** `MarketWorkerManifest::resolve_all()`
  returns one `MarketWorkerConfig` per `[[workers]]` entry. Each gets
  its own `MarketWorker` and its own task in the `JoinSet`.
- **Two shutdown sources.** Ctrl-C and the optional `duration_hours`
  timer both flip the same `watch::channel`, which all workers
  observe via the cloned `rx`.
- **Connection stagger.** A 250 ms sleep between worker spawns
  prevents bursting N sockets simultaneously, which some exchanges
  rate-limit.
- **Per-worker reports.** When a worker exits cleanly, it returns an
  `IngestionReport` with event counts, snapshot counts, reconnects,
  and elapsed time. We log those; they're handy for offline auditing.

## 4. Run it

```bash
cargo run --release -- --config md_worker_bybit.toml
```

Expected console output (heavily abbreviated):

```
INFO  bybit-to-parquet: examples.market_worker.starting workers=3 config=md_worker_bybit.toml
INFO  bybit-to-parquet: spawning worker=0 label=bybit:BTCUSDT
INFO  bybit-to-parquet: spawning worker=1 label=bybit:ETHUSDT
INFO  bybit-to-parquet: spawning worker=2 label=bybit:SOLUSDT
INFO  atelier_connect::workers: ingestion.connected exchange=bybit symbol=BTCUSDT
INFO  atelier_connect::workers: ingestion.connected exchange=bybit symbol=ETHUSDT
INFO  atelier_connect::workers: ingestion.connected exchange=bybit symbol=SOLUSDT
…
INFO  atelier_connect::sinks::parquet: flush.complete file=datasets/collected/bybit/orderbooks/BTCUSDT_ob_sync_20260430_120000.000.parquet rows=3000
…
^C
INFO  bybit-to-parquet: shutdown_requested
INFO  bybit-to-parquet: finished exchange=bybit symbol=BTCUSDT total_events=128744 snapshots=3000 flushes=1 elapsed=600.2s reconnects=0
INFO  bybit-to-parquet: all_done total_snapshots=9000
```

## 5. What you got on disk

```
datasets/collected/bybit/
├── orderbooks/
│   ├── BTCUSDT_ob_sync_20260430_120000.000.parquet
│   ├── ETHUSDT_ob_sync_20260430_120000.000.parquet
│   └── SOLUSDT_ob_sync_20260430_120000.000.parquet
└── trades/
    ├── BTCUSDT_trades_sync_20260430_120000.000.parquet
    ├── ETHUSDT_trades_sync_20260430_120000.000.parquet
    └── SOLUSDT_trades_sync_20260430_120000.000.parquet
```

The filename pattern is documented on the
[`atelier-io`](../sdk/io/index.md#filename-convention) page.

## Where to go next

- [Tutorial 2: multi-exchange synchronized collection](02-multi-exchange-sync.md) —
  fan the same flow out across Bybit, Coinbase, and Kraken.
- [Tutorial 3: fit a Hawkes process](03-hawkes-on-arrivals.md) —
  consume the Parquet files you just wrote.
- [`atelier-connect`](../sdk/connect/index.md) — full conceptual reference.
- [`atelier-io`](../sdk/io/index.md) — readers for the files this tutorial wrote.
