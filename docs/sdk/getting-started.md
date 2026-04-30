# Getting started

The shortest path through the Atelier SDK. By the end of this page
you will have a Rust project that connects to Bybit, streams a few
minutes of live order-book and trade data, and writes a small
Parquet file you can read back in any analytics tool.

If you want the full runnable variant with logging, error handling,
and a TOML manifest, jump to
[Tutorial 1: Bybit → Parquet](../guides/01-bybit-to-parquet.md).

## Prerequisites

- **Rust** 1.85+ (the workspace uses edition 2024).
- **A Bybit account** is **not** required — we'll use the public
  WebSocket endpoint, which doesn't need authentication for market
  data.

## 1. Create a new crate

```bash
cargo new --bin atelier-quickstart
cd atelier-quickstart
```

## 2. Add `atelier-sdk` to `Cargo.toml`

```toml
[package]
name = "atelier-quickstart"
version = "0.1.0"
edition = "2024"

[dependencies]
atelier-sdk = { version = "0.0.10", features = ["parquet"] }
tokio       = { version = "1", features = ["full"] }
anyhow      = "1"
tracing-subscriber = "0.3"
```

`atelier-sdk` is a facade crate — adding it pulls in the workspace
crates you'll touch (`atelier-types`, `atelier-connect`, `atelier-io`,
etc.) so you don't have to list each one.

The `parquet` feature opts into the Parquet sink and the Parquet
reader/writer functions in `atelier-io`.

## 3. The minimum viable worker

```rust
use atelier_sdk::atelier_connect::{
    clients::bybit::BybitWssClient,
    workers::{MarketWorker, MarketWorkerConfig},
};
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    // 1. Build a Bybit client subscribed to BTCUSDT order book + trades.
    let client = BybitWssClient::builder()
        .subscribe_orderbook("BTCUSDT", 1)
        .subscribe_trades("BTCUSDT")
        .build()?;

    // 2. Run the connection in a background task.
    tokio::spawn(async move {
        if let Err(e) = client.run().await {
            eprintln!("client error: {e}");
        }
    });

    // 3. Configure a MarketWorker that emits a snapshot every 100 ms.
    let (tx, mut rx) = mpsc::channel(1024);
    let config = MarketWorkerConfig::default()
        .with_interval_ms(100);
    let mut worker = MarketWorker::new(config, tx);

    // 4. Drain snapshots until you stop the program.
    while let Some(snapshot) = rx.recv().await {
        println!(
            "{}  {} levels  {} trades",
            snapshot.timestamp,
            snapshot.orderbook.len(),
            snapshot.trades.len(),
        );
    }

    Ok(())
}
```

Run it:

```bash
cargo run
```

You should see one line per 100 ms with a level count and a trade
count. Press Ctrl-C to stop.

## 4. Persist to Parquet

Replace the `while let` block with a Parquet sink. `atelier-connect`
ships `OutputSinkSet` so you can fan out to multiple destinations at
once — channel + Parquet is a common pattern for "give me snapshots
in process AND on disk":

```rust
use atelier_sdk::atelier_connect::sinks::{OutputSinkSet, ParquetSink};

let parquet = ParquetSink::new("./data/snapshots")?;
let sinks   = OutputSinkSet::new()
    .with_parquet(parquet)
    .with_channel(tx);
```

Wire `sinks` into the worker instead of just `tx`. After running
for a few minutes you'll have a tree like:

```
data/snapshots/
├── orderbooks/BTCUSDT_ob_sync_20260430_120000.000.parquet
└── trades/BTCUSDT_trades_sync_20260430_120000.000.parquet
```

The filename convention (`{symbol}_{datatype}_{mode}_{ts}`) is
documented on the [`atelier-io`](io/index.md#filename-convention)
page.

## 5. Read it back

```rust
use atelier_sdk::atelier_io::parquet::load_trades_from_parquet;

let trades = load_trades_from_parquet(
    "data/snapshots/trades/BTCUSDT_trades_sync_20260430_120000.000.parquet",
    None,  // load all columns
)?;

for trade in trades.iter().take(10) {
    println!("{}  {} {} @ {}",
        trade.timestamp, trade.side, trade.quantity, trade.price);
}
```

Drop `Some(vec!["price".into(), "quantity".into()])` in for `None`
to project only those columns.

## What you just learned

| Concept                               | Where it lives                                                      |
|---------------------------------------|---------------------------------------------------------------------|
| Exchange clients with reconnect       | [`atelier-connect`](connect/index.md)                                |
| Workers that synchronize feeds        | [`atelier-connect`](connect/index.md) `MarketWorker`                |
| Output sinks (channel, terminal, parquet) | [`atelier-connect`](connect/index.md) `OutputSinkSet`            |
| Parquet readers / writers             | [`atelier-io`](io/index.md)                                         |
| The data types this all flows through | [`atelier-types`](types/index.md)                                    |

## Where to go next

- [Tutorial 1: Bybit → Parquet](../guides/01-bybit-to-parquet.md) —
  the same flow with TOML manifests, proper error handling, and
  graceful shutdown.
- [Tutorial 2: multi-exchange sync](../guides/02-multi-exchange-sync.md) —
  fanning out across Bybit, Coinbase, Binance, Kraken with a single
  synchronizer.
- [Tutorial 3: Hawkes on arrivals](../guides/03-hawkes-on-arrivals.md) —
  fitting a quantitative model on the data you just collected.
- [Architecture](architecture.md) — how the crates fit together.
