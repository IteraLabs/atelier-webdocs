# `atelier_connect::workers::data_worker`

Lean ingestion-only data worker (no preprocessing).
Lea  ingestion-only data worker.

`DataWorker` is the core runtime for the `data_worker` binary.
It establishes a persistent WebSocket connection to a single exchange
+ symbol pair, decodes raw frames through the existing exchange
decoders, and publishes them — **without any pre-processing** — to
configured output sinks.

# Design

| Concern | Approach |
|---------|----------|
| Output | Pluggable `OutputSink`s (channel, terminal, parquet) |
| Processing | **None** — raw decoded events |
| Reconnection | Delegated to `IngestionCore` |
| Gap tracking | Delegated to `IngestionCore` |
| Stale detection | Delegated to `IngestionCore` |

# Event classification

Each decoded `ExchangeEvent` variant is mapped to a canonical topic
name.  The mapping is exchange-specific:

| Exchange | Event | Topic |
|----------|-------|-------|
| Bybit | `OrderbookData` | `orderbook.{depth}.{symbol}` |
| Bybit | `TradeData` | `publicTrade.{symbol}` |
| Bybit | `LiquidationData` | `lquidation.all.{symbol}` |
| Bybit | `TickerData` (funding) | `funding.all.{symbol}` |
| Bybit | `TickerData` (OI) | `open_interest.all.{symbol}` |

| Binance | `DepthUpdate` | `orderbook.{depth}.{symbol}` |
| Binance | `DepthSnapshot` | `orderbook.{depth}.{symbol}` |
| Binance | `TradeData` | `trade.all.{symbol}` |

| Coinbase | `OrderbookData` | `orderbook.{depth}.{symbol}` |
| Coinbase | `TradeData` | `trade.all.{symbol}` |

| Kraken | `OrderbookData` | `orderbook.{depth}.{symbol}` |
| Kraken | `TradeData` | `trade.all.{symbol}` |

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::data_worker`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/data_worker/).

## Structs

| Item | Summary |
| --- | --- |
| [`DataWorker`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/data_worker/struct.DataWorker.html) | A single-symbol raw data ingestion worker. |
| [`DataWorkerReport`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/data_worker/struct.DataWorkerReport.html) | Summary statistics returned when a [`DataWorker`] finishes. |
