---
description: The microstructure datasets the Atelier platform collects — exchanges, symbols, schema, naming convention, and how to read them.
---

# Dataset catalog

The Atelier platform collects normalized market-microstructure data — trades and Level-2
orderbook snapshots — from multiple cryptocurrency exchanges into a single, exchange-agnostic
schema. This page documents what the seed corpus covers, the on-disk convention, the record
schema, and how to read it with the SDK. The same data feeds the
[research notes](../research/index.md).

!!! info "Format, not a download"
    This catalog documents the **schema and collection convention**, not a hosted download.
    You produce your own corpus by running a collector — see
    [Tutorial 1: Bybit → Parquet](../guides/01-bybit-to-parquet.md) — and read it back with
    the functions below. Everything here is reproducible from the SDK.

## Coverage (seed corpus)

A snapshot of the current collected corpus — **407 Parquet files, ~3.8 MB**, gathered early
June 2026 in synchronized (`sync`) mode:

| Exchange   | Datatype            | Files | Notes |
|------------|---------------------|------:|-------|
| **Binance**  | Orderbook snapshots | 362 | The bulk of the corpus — L2 books across five symbols |
| **Coinbase** | Orderbook snapshots |  43 | Second-venue coverage for cross-exchange work |
| **Binance**  | Trades              |   1 | Sample trade stream |
| **Bybit**    | Trades              |   1 | Sample trade stream (used by the Hawkes tutorial) |

**Symbols:** `BTC-USDT`, `ETH-USDT`, `SOL-USDT`, `ALGO-USDT`, `LINK-USDT`.

This is a **seed corpus**, deliberately skewed toward Binance L2 books; it is enough to
develop and reproduce the published analyses, not a balanced multi-venue panel. Collect more
with the SDK as needed.

## File naming

Every file follows one convention, which downstream tools parse to locate the right data for
a symbol and time range:

```
{exchange}_{symbol}_{datatype}_{mode}_{YYYYMMDD}_{HHMMSS.mmm}.parquet
```

Real examples from the corpus:

```text
binance_BTC-USDT_trades_sync_20260602_044413.927.parquet
coinbase_BTC-USDT_ob_sync_20260601_195024.176.parquet
bybit_BTC-USDT_trades_sync_20260602_044412.022.parquet
```

- `datatype` is `trades` or `ob` (orderbook).
- `mode` is `sync` for grid-aligned, synchronized collection.
- The trailing timestamp is the collection start (millisecond precision).

## Schema

Records use the SDK's exchange-agnostic types — exchange wire formats are normalized into
these by the per-exchange decoders. The authoritative definitions live in
[`atelier-types`](../sdk/types/index.md); the logical shapes are:

=== "Trade"

    | Field | Type | Meaning |
    |-------|------|---------|
    | `trade_ts` | `u64` | Trade timestamp, Unix milliseconds (exchange-reported) |
    | `pair`     | `TradingPair` | Canonical pair, e.g. `BTC/USDT` |
    | `side`     | `TradeSide` | Taker (aggressor) side |
    | `amount`   | `f64` | Filled quantity, base-currency units |
    | `price`    | `f64` | Execution price, quote-currency units |
    | `exchange` | `String` | Source exchange |
    | `id`       | `String` | Exchange-assigned trade id |

=== "Orderbook"

    | Field | Type | Meaning |
    |-------|------|---------|
    | `orderbook_id` | `u32` | Snapshot id |
    | `orderbook_ts` | `u64` | Snapshot timestamp, Unix milliseconds |
    | `pair`         | `TradingPair` | Canonical pair |
    | `exchange`     | `String` | Source exchange |
    | `bids`         | price → `Level` | Bid levels (best bid = highest price) |
    | `asks`         | price → `Level` | Ask levels (best ask = lowest price) |

Synchronized (`sync`) collection composes these into a `MarketSnapshot` per grid tick —
`ts_ns` (grid-aligned), the carried-forward `orderbook`, and the `trades`, `liquidations`,
`funding_rate`, and `open_interest` observed in that interval. See
[Architecture](../sdk/architecture.md) for how the synchronizer builds them.

## Reading it

The [`atelier-io`](../sdk/io/index.md) crate reads each datatype back into the typed records:

```rust
use atelier_io::trades::read_trades_parquet;
use atelier_io::orderbooks::ob_parquet::load_parquet_to_ob;

let trades = read_trades_parquet("…/binance_BTC-USDT_trades_sync_20260602_044413.927.parquet".as_ref())?;
let books  = load_parquet_to_ob("…/coinbase_BTC-USDT_ob_sync_20260601_195024.176.parquet".as_ref())?;
```

From there the data is ready for [`atelier-quant`](../sdk/quant/index.md) — for example the
interarrival extraction and Hawkes fitting in
[When are crypto order arrivals self-exciting?](../research/posts/2026-06-16-self-exciting-arrivals.md).

## Reproduce / extend

- **Collect fresh data:** [Tutorial 1: Bybit → Parquet](../guides/01-bybit-to-parquet.md).
- **Multi-exchange, synchronized:** [Tutorial 2: multi-exchange sync](../guides/02-multi-exchange-sync.md).
