# `atelier_connect::workers::market_worker`

Synchronised market data worker.
Synchronised market data worker.

`MarketWorker` composes an `IngestionCore` with a
`MarketSynchronizer` to produce grid-aligned `MarketSnapshot`s
from raw exchange events.

# Design

```text
┌──────────────┐     mpsc     ┌────────────────┐   sync    ┌──────────┐
│ IngestionCore│─────────────→│ MarketWorker   │──────────→│ Sinks    │
│ (WSS + reconn│  TopicMsg    │ (feed_event +  │ Snapshot  │ (channel │
│  + classify) │              │  synchronizer) │           │  / term) │
└──────────────┘              └────────────────┘           └──────────┘
```

The worker:
1. Spawns an `IngestionCore` in a background task.
2. Receives classified `TopicMessage`s.
3. Converts raw exchange events into normalised types
   (`Trade`, `Orderbook`, etc.) and feeds them into the synchroniser.
4. Drains ready `MarketSnapshot`s and emits them to output sinks.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::market_worker`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/workers/market_worker/).

## Structs

| Item | Summary |
| --- | --- |
| [`MarketWorker`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/market_worker/struct.MarketWorker.html) | A single-symbol synchronised market data worker. |
| [`MarketWorkerReport`](https://docs.rs/atelier-connect/latest/atelier_connect/workers/market_worker/struct.MarketWorkerReport.html) | Summary statistics returned when a `MarketWorker` finishes. |
