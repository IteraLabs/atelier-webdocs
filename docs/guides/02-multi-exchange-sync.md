---
source_example: atelier-connect/examples/multi_sync/multi_sync_workers.rs
source_manifest: atelier-connect/examples/multi_sync/cross_exchange_solusdt.toml
sdk_version: "0.0.10"
sdk_commit: "(record this before cutover)"
---

# Multi-exchange synchronized collection

The "real" usage pattern: collect the same underlying asset across
multiple exchanges concurrently, with a shared synchronizer cadence
and per-exchange output. This is the shape you want when you're
running cross-exchange analyses (basis, lead-lag, arbitrage signal
research).

This tutorial uses a single TOML manifest with `[defaults]` shared
across workers, so per-`[[workers]]` blocks stay terse.

!!! note "Source"
    Code adapted from
    [`atelier-connect/examples/multi_sync/multi_sync_workers.rs`](https://github.com/IteraLabs/atelier-sdk/tree/main/atelier-connect/examples/multi_sync)
    plus the runner pattern from
    [`atelier-connect/examples/md_worker/run_market_worker.rs`](https://github.com/IteraLabs/atelier-sdk/tree/main/atelier-connect/examples/md_worker)
    in atelier-sdk. Manifest is `cross_exchange_solusdt.toml`.

## What you'll build

A single command that:

- Connects simultaneously to Bybit (`SOLUSDT`), Coinbase (`SOL-USD`),
  and Kraken (`SOL/USD`).
- Synchronizes each exchange onto its own 100 ms grid, driven by
  trade timestamps (`sync_mode = "on_trade"`).
- Writes per-exchange Parquet files to
  `datasets/collected/{exchange}/`.
- Runs for 8 hours then shuts down on its own.

## 1. Project setup

Same dependencies as
[Tutorial 1](01-bybit-to-parquet.md#1-project-setup). If you already
have that crate, you can reuse it; just point the runner at this
manifest instead.

## 2. The TOML manifest

**`cross_exchange_solusdt.toml`**

```toml
# ═══════════════════════════════════════════════════════════════════
#  Cross-exchange — same underlying asset (SOL) across 3 venues
# ═══════════════════════════════════════════════════════════════════

# ── Shared defaults ─────────────────────────────────────────────────
# Pulled in by every [[workers]] entry below unless explicitly
# overridden. Keeps per-worker blocks small.

[defaults]
sync_mode       = "on_trade"
flush_threshold = 36000

[defaults.update_frequency]
value = 100
unit  = "Millis"

[defaults.datatypes.orderbook]
enabled = true
depth   = 50

[defaults.datatypes.trades]
enabled = true

[defaults.logs]
n_orderbooks     = 1000
n_trades         =  500
n_liquidations   =    0
n_fundings       =    0
n_open_interests =    0

# ── Per-exchange workers ────────────────────────────────────────────
# Same underlying asset, different exchange-native symbol formats.

[[workers]]
exchange = "bybit"
symbol   = "SOLUSDT"

[[workers]]
exchange = "coinbase"
symbol   = "SOL-USD"

[[workers]]
exchange = "kraken"
symbol   = "SOL/USD"

# ── Output ──────────────────────────────────────────────────────────
# Per-exchange directories under base_dir.

[output]
base_dir = "datasets/collected"

# ── Session ─────────────────────────────────────────────────────────

[session]
duration_hours = 8
```

Three things worth highlighting:

- **`[defaults]` block.** Pulled into every worker that doesn't
  override the field. The cross-exchange manifest is short because
  most fields are identical across workers.
- **`sync_mode = "on_trade"`.** Trade-driven synchronizer
  ([`TradeDriven`](../sdk/connect/index.md#synchronizer-clock-modes))
  ticks the grid on every trade rather than at fixed intervals.
  Useful when you want the grid to reflect actual market activity
  rather than a wall-clock cadence.
- **Symbol-format heterogeneity.** Bybit uses `SOLUSDT`, Coinbase
  uses `SOL-USD`, Kraken uses `SOL/USD`. Each exchange's native
  format passes through unchanged; the SDK handles the mapping
  internally and sanitizes filenames where needed (`SOL/USD` becomes
  `SOL-USD` in the filename, while the Parquet data retains the
  original symbol string).

## 3. The runner

The runner is identical to the one in
[Tutorial 1](01-bybit-to-parquet.md#3-the-runner) — a single
`MarketWorkerManifest` parsed from TOML, one `MarketWorker` per
`[[workers]]` entry, all draining into a `JoinSet`. The manifest
shape changed; the runtime didn't.

If you wired up Tutorial 1, just swap the `--config` path:

```bash
cargo run --release -- --config cross_exchange_solusdt.toml
```

If you're starting fresh, the `src/main.rs` from Tutorial 1 is what
you want — copy it verbatim.

## 4. What happens at runtime

Three concurrent worker tasks. Each:

- Owns its own WebSocket connection (with reconnect / backoff).
- Owns its own `MarketSynchronizer` ticking on trade timestamps.
- Writes to its own Parquet directory under `datasets/collected/`.

There's no cross-worker synchronization. Each exchange runs at its
own cadence; if Coinbase has 10× the trade rate of Kraken at some
moment, Coinbase's grid will tick 10× as often. That's by design —
the synchronizer's job is to align *within* a feed onto a regular
grid, not to align *across* feeds. Cross-exchange alignment is
something you do offline at analysis time, by joining the resulting
Parquet files on a shared timestamp column.

## 5. Expected directory layout

After the 8 hours elapse:

```
datasets/collected/
├── bybit/
│   ├── orderbooks/SOLUSDT_ob_sync_20260430_120000.000.parquet
│   ├── orderbooks/SOLUSDT_ob_sync_20260430_130000.000.parquet
│   ├── …
│   └── trades/SOLUSDT_trades_sync_20260430_120000.000.parquet
│   │   …
├── coinbase/
│   ├── orderbooks/SOL-USD_ob_sync_20260430_120000.000.parquet
│   │   …
│   └── trades/SOL-USD_trades_sync_20260430_120000.000.parquet
│   │   …
└── kraken/
    ├── orderbooks/SOL-USD_ob_sync_20260430_120000.000.parquet
    │   …
    └── trades/SOL-USD_trades_sync_20260430_120000.000.parquet
        …
```

`flush_threshold = 36000` × 100 ms grid = ~1 hour of data per
Parquet file, so 8 hours yields ~8 files per (exchange, datatype)
pair.

## 6. Reading it back, joined

To do anything cross-exchange, you join the per-exchange Parquet
files on the synchronized grid timestamp. A skeleton with `polars`:

```rust
use polars::prelude::*;

let bybit = LazyFrame::scan_parquet(
    "datasets/collected/bybit/trades/*.parquet",
    Default::default(),
)?;

let coinbase = LazyFrame::scan_parquet(
    "datasets/collected/coinbase/trades/*.parquet",
    Default::default(),
)?;

// Join on the bin (grid timestamp) column with an asof join.
let joined = bybit
    .join_builder()
    .with(coinbase)
    .left_on([col("timestamp")])
    .right_on([col("timestamp")])
    .how(JoinType::AsOf(AsOfOptions {
        strategy: AsofStrategy::Backward,
        tolerance: Some(AnyValue::Duration(100, TimeUnit::Milliseconds)),
        ..Default::default()
    }))
    .finish();

let df = joined.collect()?;
```

The `AsOfOptions::tolerance = 100ms` matches the manifest's grid
period — a Bybit trade in bin `t` is matched with the Coinbase
trade in bin `[t, t + 100ms]`.

## Where to go next

- [Tutorial 3: fit a Hawkes process](03-hawkes-on-arrivals.md) —
  the natural follow-up: model the arrival process per exchange,
  compare excitation parameters across venues.
- [`atelier-connect`](../sdk/connect/index.md) — full reference,
  including the four clock modes and the connection-management
  internals.
- [`atelier-types`](../sdk/types/index.md) — the synchronizer types
  this tutorial relies on.
