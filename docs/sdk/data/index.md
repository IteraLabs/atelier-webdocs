# `atelier-data`

Market data infrastructure for the Atelier SDK. Connects to
cryptocurrency exchanges, normalizes their heterogeneous WebSocket
feeds into a common data model, synchronizes events onto a uniform
time grid, and persists the result to Apache Parquet.

!!! note "Crate version"
    `atelier-data` is currently published at version `0.0.15`,
    independent of the workspace marker `0.0.10` carried by other
    crates. Treat it as the most rapidly-evolving member of the SDK.

In practice, `atelier-data` overlaps significantly with
[`atelier-connect`](../connect/index.md) — both crates contain
worker, synchronizer, and output-sink machinery. The dual existence
is a transition state: the medium-term plan is for `atelier-connect`
to consolidate the connectivity layer while `atelier-data` becomes
the Arrow-backed columnar pipeline. For now, the crates ship
side-by-side.

This page documents what `atelier-data` exposes today.

## Core data types

The same canonical types from [`atelier-types`](../types/index.md),
re-exported and used directly:

| Type             | Description                                                  |
|------------------|--------------------------------------------------------------|
| `Orderbook`      | Full-depth limit order book snapshot                         |
| `OrderbookDelta` | Incremental order book updates                                |
| `Trade`          | Public trade execution                                        |
| `Liquidation`    | Forced liquidation event                                      |
| `FundingRate`    | Perpetual funding rate observation                            |
| `OpenInterest`   | Aggregate open interest snapshot                              |
| `MarketSnapshot` | Time-aligned bundle for one grid period                       |
| `MarketAggregate`| 15-scalar feature vector derived from a `MarketSnapshot`     |

All core types use the builder pattern for validated construction
and implement `Debug`, `Clone`, and `Serialize` / `Deserialize`
where applicable.

## Exchange sources

| Source   | Kind | API                | Order books | Trades | Liquidations | Funding | OI  |
|----------|------|--------------------|-------------|--------|--------------|---------|-----|
| Bybit    | CEX  | WSS v5 (linear)    | yes         | yes    | yes          | yes     | yes |
| Coinbase | CEX  | WSS (Adv Trade)    | yes         | yes    | —            | —       | —   |
| Kraken   | CEX  | WSS v2 (spot)      | yes         | yes    | —            | —       | —   |
| Binance  | CEX  | WSS + REST (spot)  | yes         | yes    | —            | —       | —   |

Each source ships with a typed `WssDecoder` impl, a response model,
and an event classifier that maps raw frames into `ExchangeEvent`.
Binance includes a REST client used by the `BookInitializer`
pipeline stage to seed orderbook state from a snapshot.

## Client layer

Generic transport and lifecycle management shared across all
exchanges:

| Component             | Purpose                                                                              |
|-----------------------|--------------------------------------------------------------------------------------|
| `WssClient<D>`        | Parameterised WebSocket client over a `WssDecoder`                                    |
| `WssClientBuilder`    | Fluent construction                                                                  |
| `HttpClient`          | Rate-limited HTTP, per-exchange base URL, timeout                                     |
| `ConnectionManager`   | Stateful lifecycle tracker — state transitions with timestamps                        |
| `ReconnectPolicy`     | Jittered exponential backoff (100 ms → 10 s) with circuit breaker                     |
| `DisconnectReason`    | Classifies errors as retryable vs non-retryable                                       |

## Workers

`DataWorker` and `MarketWorker` mirror the same names in
[`atelier-connect`](../connect/index.md); both share `IngestionCore`,
which manages the full connection lifecycle including stale-
connection detection, per-topic gap tracking
(`GapDetector` / `GapDetectorSet`), and health monitoring.

## Event pipeline

Composable transform stages between `IngestionCore` and the workers:

| Pipeline                | Exchange      | Purpose                                                                              |
|-------------------------|---------------|--------------------------------------------------------------------------------------|
| `PassthroughPipeline`   | All (default) | Identity — forwards events unmodified                                                 |
| `BookInitializer`       | Binance       | Fetches REST depth snapshot, reconciles WSS deltas, injects synthetic `DepthSnapshot` |

`build_pipeline()` selects the appropriate pipeline based on
exchange and configuration.

## Synchronization

`MarketSynchronizer` aligns heterogeneous event streams onto a
uniform nanosecond time grid. Four clock modes are available:

| Mode                | Grid driven by                              |
|---------------------|---------------------------------------------|
| `OrderbookDriven`   | Orderbook timestamp crossings (default)      |
| `TradeDriven`       | Trade timestamps                            |
| `LiquidationDriven` | Liquidation timestamps                       |
| `ExternalClock`     | Explicit nanosecond `on_time()` calls        |

State-based feeds (orderbook, funding, open interest) carry their
latest value forward. Event-based feeds (trades, liquidations)
collect events within each grid period.

## Output sinks

| Sink           | Status   | Description                                                                              |
|----------------|----------|------------------------------------------------------------------------------------------|
| `ChannelSink`  | Working  | `TopicRegistry`-backed broadcast channels for pub/sub                                     |
| `TerminalSink` | Working  | Debug / tracing terminal output                                                          |
| `ParquetSink`  | Working  | Buffers `MarketSnapshot`s, decomposes them, flushes per-datatype Parquet files            |

## Configuration

Workers are configured via TOML manifests. Per-datatype collection
flags live under `[collect.datatypes.*]`:

```toml
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
```

Connection parameters (exchange, symbol, channel capacity, gap
threshold) are shared through `CommonWorkerFields`. Output sinks
are selected via `OutputSinkConfig` (channel / terminal / parquet
with directory).

## Feature flags

| Flag       | Effect                                                                              |
|------------|-------------------------------------------------------------------------------------|
| `parquet`  | Enable Apache Parquet I/O (adds `arrow` + `parquet` deps)                           |
| `torch`    | Enable `tch`-based tensor conversion in the `datasets` module                        |

## Examples

| Example               | Description                                          |
|-----------------------|------------------------------------------------------|
| `run_data_worker`     | Raw event ingestion via DataWorker                   |
| `run_market_worker`   | Synchronized snapshots to Parquet via MarketWorker   |
| `read_market_worker`  | Read Parquet files and print per-symbol stats        |
| `bybit_markets`       | Bybit market snapshot collection (standalone)        |
| `coinbase_markets`    | Coinbase market snapshot collection                   |
| `kraken_markets`      | Kraken market snapshot collection                    |
| `market_load`         | Load and verify most recent Parquet files            |
| `market_fetch`        | Multi-exchange raw stream collector                  |
| `multi_sync_workers`  | Multi-worker manifest parser                          |

All ship in `atelier-data/examples/` and are runnable via
`cargo run -p atelier_data --example <name>`.

## Roadmap

The current shape of the crate is interim. Tracked items:

- **Exchange coverage expansion.** Coinbase (INTX), Kraken (Futures),
  and Binance (perpetual / futures) currently only support orderbooks
  and trades through their spot / linear APIs. Adding perpetual
  contract endpoints unlocks liquidations, funding, and open interest
  for these exchanges.
- **Trades CSV / JSON I/O.** Orderbooks support text format
  round-trips; trades and remaining types return
  `UnsupportedFormat`. Extending the existing patterns from
  `orderbooks/io/` is straightforward.
- **`torch` feature on docs.rs.** docs.rs builds in a sandbox without
  libtorch, so `torch`-gated items don't appear there. A stub-type
  strategy for the `docsrs` build is under consideration.
- **`TerminalSink` enhancements.** Currently emits one-line tracing
  summaries. Planned: configurable verbosity, pretty-printed orderbook
  depth, formatted trade tapes.
- **Dedicated snapshots topic.** `ParquetSink` decomposes snapshots
  into per-datatype files. A dedicated snapshots topic for downstream
  consumers is planned.
- **Orderbook validation hardening.** TODO markers in
  `orderbooks/core.rs` track order ID validation, hash-based integrity
  checks, and refactoring of level manipulation logic.

## Where to go next

- [API reference for `atelier-data`](../api/atelier-data/index.md)
- [`atelier-connect`](../connect/index.md) — overlapping connectivity layer.
- [Architecture](../architecture.md) — the cross-crate picture.
