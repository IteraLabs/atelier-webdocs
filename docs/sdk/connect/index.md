# `atelier-connect`

Real-time exchange connectivity for the Atelier SDK. Manages
WebSocket connections to four cryptocurrency exchanges, decodes
exchange-native frames into typed `ExchangeEvent`s, runs them through
configurable worker loops, and emits the result via pluggable
output sinks.

If `atelier-types` is the schema, `atelier-connect` is the engine
that fills the schema with live data. It is the SDK's single largest
crate by both surface area and complexity.

## Supported exchanges

| Exchange | API                | Order books     | Trades        | Liquidations | Funding | Open interest |
|----------|--------------------|-----------------|---------------|--------------|---------|---------------|
| Bybit    | WSS v5 (linear)    | yes             | yes           | yes          | yes     | yes           |
| Binance  | WSS + REST (spot)  | yes             | yes           | —            | —       | —             |
| Coinbase | WSS (Adv. Trade)   | yes             | yes           | —            | —       | —             |
| Kraken   | WSS v2 (spot)      | yes             | yes           | —            | —       | —             |

Dashes indicate the exchange does not expose that data type on its
current WebSocket endpoint. Bybit currently has the most complete
coverage; expanding the others to perpetual / futures endpoints is a
roadmap item.

Each exchange ships with a typed decoder (`WssDecoder` impl), a
response model deserialized via `serde::Deserialize`, and an event
classifier that maps raw frames into the unified `ExchangeEvent`
enum. Binance additionally has a REST client used by the
`BookInitializer` pipeline stage to seed orderbook state.

## The data path

```
Exchange WebSocket
    │
    ▼
Exchange client (WssClient<D>) ─── reconnect, backoff, health check
    │
    ▼
WssDecoder ─── exchange-native JSON → typed ExchangeEvent
    │
    ▼
Event pipeline (PassthroughPipeline | BookInitializer | …)
    │
    ▼
Worker (DataWorker | MarketWorker)
    │
    ▼
OutputSinkSet ─── ChannelSink, TerminalSink, ParquetSink (fan-out)
```

## Connection management

| Component             | Purpose                                                                                                 |
|-----------------------|---------------------------------------------------------------------------------------------------------|
| `WssClient<D>`        | Generic WebSocket client over a `WssDecoder`                                                            |
| `WssClientBuilder`    | Fluent construction with URL, headers, decoder                                                          |
| `HttpClient`          | Rate-limited HTTP, per-exchange base URL, timeout                                                        |
| `ConnectionManager`   | Lifecycle tracker — state transitions and timestamps for every connection                               |
| `ReconnectPolicy`     | Jittered exponential backoff (100 ms → 10 s) with circuit breaker                                       |
| `DisconnectReason`    | Classifies low-level errors as retryable vs non-retryable so transient TCP resets don't kill the worker  |

The disconnect classifier is the load-bearing piece for production
reliability — it distinguishes "the network blinked" from "the
exchange rejected us," ensuring the former triggers backoff-and-retry
while the latter surfaces as an error.

## Workers

Two worker types do end-to-end data collection. Both are built on a
shared `IngestionCore` that handles the connection lifecycle, stale-
connection detection, per-topic gap tracking via `GapDetector` /
`GapDetectorSet`, and health monitoring.

### `DataWorker` — raw event ingestion

Lightweight option for collecting raw feed data with minimal
processing. Decodes exchange messages into typed events and delivers
them through a pluggable `OutputSink` pipeline. TOML-driven
configuration via `DataWorkerManifest`. Reconnection, backoff, and
gap detection are automatic.

Use when: you want the raw event stream and will do your own
synchronization downstream.

### `MarketWorker` — synchronized snapshots

Extends `DataWorker`'s ingestion with a `MarketSynchronizer` that
bins heterogeneous events onto a uniform nanosecond grid, producing
`MarketSnapshot` objects at each tick. Snapshots flow through the
same `OutputSink` pipeline and can be flushed to Parquet
automatically.

Use when: you want time-aligned snapshots ready for downstream
analytics or model fitting.

### `ObSynchronizer`

Time-grid sampler specifically for orderbook snapshots. Reduces data
volume via configurable snapshot intervals and handles missing data
points gracefully. Useful when you only care about orderbook state
on a regular cadence rather than every delta.

## Synchronizer clock modes

`MarketSynchronizer` supports four ways of advancing the grid clock:

| Mode                | Grid driven by                                |
|---------------------|-----------------------------------------------|
| `OrderbookDriven`   | Orderbook timestamp crossings (default)        |
| `TradeDriven`       | Trade timestamps                              |
| `LiquidationDriven` | Liquidation timestamps                        |
| `ExternalClock`     | Explicit nanosecond `on_time()` calls         |

State-based feeds (orderbook, funding rate, open interest) carry their
latest value forward across grid ticks. Event-based feeds (trades,
liquidations) collect all events that fell within each grid period.

## Output sinks

The `OutputSink` trait defines where worker output goes. Multiple
sinks run simultaneously via `OutputSinkSet` (fan-out):

| Sink           | What it does                                                                |
|----------------|-----------------------------------------------------------------------------|
| `ChannelSink`  | Wraps `TopicRegistry` broadcast channels for in-process pub/sub              |
| `TerminalSink` | Tracing-formatted terminal output for debugging                              |
| `ParquetSink`  | Buffers `MarketSnapshot`s, decomposes them, flushes per-datatype Parquet files |

`ParquetSink` is feature-gated behind the `parquet` feature.

## Quick start — Bybit MarketWorker

```rust
use atelier_connect::clients::bybit::BybitWssClient;
use atelier_connect::workers::{MarketWorker, MarketWorkerConfig};
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Create Bybit client and connect
    let client = BybitWssClient::builder()
        .subscribe_orderbook("BTCUSDT", 1)
        .subscribe_trades("BTCUSDT")
        .build()?;

    tokio::spawn(async move {
        client.run().await.ok();
    });

    // Configure market worker to emit snapshots every 100ms
    let (tx, mut rx) = mpsc::channel(1000);
    let config = MarketWorkerConfig::default()
        .with_interval_ms(100);

    let mut worker = MarketWorker::new(config, tx);

    while let Some(snapshot) = rx.recv().await {
        println!("Snapshot at {}: {} levels",
            snapshot.timestamp,
            snapshot.orderbook.len());
    }

    Ok(())
}
```

For the full runnable version see the
[Bybit → Parquet tutorial](../../guides/01-bybit-to-parquet.md).

## Quick start — multi-exchange via `ConnectionManager`

```rust
use atelier_connect::clients::{BybitWssClient, CoinbaseWssClient};
use atelier_connect::connection::ConnectionManager;

let manager = ConnectionManager::new();

manager.add_source("bybit",    BybitWssClient::builder().build()?)?;
manager.add_source("coinbase", CoinbaseWssClient::builder().build()?)?;

manager.run_with_health_check().await?;
```

For the synchronized multi-exchange pattern, see the
[Multi-exchange sync tutorial](../../guides/02-multi-exchange-sync.md).

## Features

- `parquet` (optional) — enables `ParquetSink` for high-volume persistence.
- All exchange clients and in-process workers are available without features.

## Where to go next

- [Tutorial: Bybit → Parquet](../../guides/01-bybit-to-parquet.md)
- [Tutorial: multi-exchange sync](../../guides/02-multi-exchange-sync.md)
- [API reference for `atelier-connect`](../api/atelier-connect/index.md)
- [`atelier-types`](../types/index.md) — the wire types this crate emits.
- [`atelier-io`](../io/index.md) — what `ParquetSink` writes to.
