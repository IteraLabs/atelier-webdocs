# `atelier-io`

Persistence for the Atelier SDK: Parquet, CSV, and JSON readers and
writers for every top-level type. Designed for both
**online persistence** (a worker streaming live data straight to
Parquet) and **offline analysis** (loading Parquet datasets into a
research notebook).

The crate is intentionally narrow. It does not transform data, does
not synchronize, and does not subscribe to anything. It moves bytes
between in-memory `atelier-types` and on-disk files.

## File format support

### Parquet — columnar, the canonical format

| Data type        | Writer                                  | Reader                          |
|------------------|------------------------------------------|---------------------------------|
| Order books      | `write_ob_parquet`                       | `read_ob_parquet`                |
| Trades           | `write_trades_parquet_timestamped`       | `read_trades_parquet`            |
| Funding rates    | `write_funding_parquet_timestamped`      | `read_funding_parquet`           |
| Liquidations     | `write_liquidations_parquet_timestamped` | `read_liquidations_parquet`      |
| Open interest    | `write_oi_parquet_timestamped`           | `read_oi_parquet`                |
| Market snapshots | aggregate writers                        | aggregate readers                |

Recommended for any non-trivial dataset.

### CSV & JSON — human-readable, narrower scope

Currently supported only for orderbooks (`write_csv` / `read_csv`,
`write_json` / `read_json`). Trades and the remaining types return
`UnsupportedFormat`; extending them to text formats is a roadmap item.

## Core traits

| Trait                       | Purpose                                                     |
|-----------------------------|-------------------------------------------------------------|
| `FlushToParquet`            | Single-shot write for any supported type                    |
| `FlushObSyncToParquet`      | Specialized sink for orderbook synchronizer output, batched |
| `FlushAggregateToParquet`   | Optimized path for `MarketAggregate` snapshots              |

`FlushObSyncToParquet` and `FlushAggregateToParquet` are gated
behind the `parquet` and `connect` features.

## Filename convention

All timestamped writers produce files in this shape:

```
{SYMBOL}_{DATATYPE}_{MODE}_{TIMESTAMP}.parquet
```

`MODE` is `sync` for grid-aligned data or `raw` for unprocessed
captures. Symbols containing `/` (e.g. Kraken's `BTC/USDT`) are
sanitized to `-` in the filename (`BTC-USDT`) while the Parquet data
retains the original symbol string.

Examples:

```
BTCUSDT_ob_sync_20260226_153000.123.parquet
ETHUSDT_trades_raw_20260226_160000.456.parquet
BTC-USDT_ob_sync_20260226_153000.123.parquet
```

Files are organized into per-datatype subdirectories: `orderbooks/`,
`trades/`, `liquidations/`, `fundings/`, `open_interests/`.

## Quick start — write & read an orderbook

```rust
use atelier_types::orderbook::Orderbook;
use atelier_io::parquet::FlushToParquet;

let mut ob = Orderbook::new("BTCUSD".to_string());
// ... populate orderbook ...

// Write to Parquet
let path = ob.flush_to_parquet("./data/orderbooks")?;
println!("Wrote orderbook to {}", path.display());

// Read back via polars (or the crate's own readers)
let df = polars::io::parquet::read_parquet(path)?;
println!("Loaded {} rows", df.height());
```

## Quick start — write a `MarketSnapshot`

```rust
use atelier_types::snapshot::MarketSnapshot;
use atelier_io::parquet::FlushToParquet;

let snapshot = MarketSnapshot {
    timestamp: chrono::Utc::now(),
    symbol: "BTCUSD".to_string(),
    orderbook: ob,
    trades: vec![trade1, trade2],
    funding_rate: Some(funding),
    liquidations: vec![],
    open_interest: Some(oi),
};

snapshot.flush_to_parquet("./snapshots")?;
```

## Quick start — batch many snapshots

```rust
use atelier_io::batch::BatchWriter;

let mut writer = BatchWriter::new("./data/snapshots")?;

for snapshot in snapshots {
    writer.push(snapshot)?;
}

writer.flush()?;
```

## Quick start — load trades for analysis

```rust
use atelier_io::parquet::load_trades_from_parquet;

let trades = load_trades_from_parquet(
    "data/trades.parquet",
    Some(vec!["price".to_string(), "quantity".to_string()])
)?;

for trade in trades {
    println!("{} @ {}", trade.quantity, trade.price);
}
```

The `Some(columns)` parameter is column projection — pull only the
columns you need to keep memory bounded.

## Feature flags

| Flag       | Effect                                                                              |
|------------|-------------------------------------------------------------------------------------|
| `parquet`  | Enable Arrow / Parquet I/O. Pulls in `arrow` and `parquet` crates                   |
| `connect`  | Enable integration with `atelier-connect` workers (channel-to-Parquet sinks)        |
| `torch`    | Experimental — PyTorch tensor export, requires a host libtorch installation         |

`parquet` is the one most users want. `connect` is the bridge between
`atelier-connect`'s `OutputSinkSet` and this crate. `torch` is gated
because docs.rs cannot build it without libtorch.

## Integration patterns

**Online → Parquet** — live workers persisting straight to disk:

```
atelier-connect Worker
    │
    ▼
OutputSinkSet::Parquet (atelier-connect, with `parquet` feature)
    │
    ▼
Parquet files
    │
    ▼
atelier-io loaders (offline)
```

**Batch processing** — research notebooks consuming archived data:

```
Raw data files
    │
    ▼
atelier-io loaders
    │
    ▼
Data frames / iterators
    │
    ▼
Analytics / backtesting / model fitting
```

## Where to go next

- [API reference for `atelier-io`](../api/atelier-io/index.md)
- [Tutorial: Bybit → Parquet](../../guides/01-bybit-to-parquet.md) — end-to-end use of `ParquetSink`.
- [`atelier-connect`](../connect/index.md) — what produces the data this crate persists.
- [`atelier-types`](../types/index.md) — the schema all writers serialize.
