# `atelier_connect::synchronizers::event_sync`

Market-event-aligned snapshot synchronizer.

Unlike the grid-based `MarketSynchronizer`,
`EventSynchronizer` emits a `MarketSnapshot` each time a designated
**reference market event** is received. Reference events are configurable
and can be any combination of: new orderbook delta, new trade, or new
liquidation — all originating from the exchange WSS feed.

# Semantics

- **Orderbook** is *state-based*: the most recent full snapshot is carried
  forward into every emitted `MarketSnapshot`.
- **Trades, liquidations** are *event-based*: accumulated between
  consecutive reference events. Buffers are drained on emission.
- **Funding rate, open interest** are *state-based*: the latest values are
  cloned into each emitted snapshot.

A snapshot is emitted only when:
  1. A reference event arrives, **and**
  2. At least one orderbook has been observed (the synchronizer is
     *initialized*).

# Usage

```ignore
use atelier_connect::synchronizers::{EventSynchronizer, ReferenceEventType};

// Emit a snapshot on every orderbook delta:
let mut sync = EventSynchronizer::orderbook_only();

// Or on every trade and liquidation:
let mut sync = EventSynchronizer::new(vec![
    ReferenceEventType::Trade,
    ReferenceEventType::Liquidation,
]);

// Feed events as they arrive from the WSS stream:
sync.on_orderbook("BTCUSDT", ts_ns, orderbook);
sync.on_trade(trade);
sync.on_liquidation(liquidation);
sync.on_funding(funding_rate);
sync.on_open_interest(oi);

// At end of stream:
sync.finalize();
let snapshots: Vec<MarketSnapshot> = sync.drain();
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::synchronizers::event_sync`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/event_sync/).

## Structs

| Item | Summary |
| --- | --- |
| [`EventSynchronizer`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/event_sync/struct.EventSynchronizer.html) | Event-driven snapshot synchronizer. |

## Enums

| Item | Summary |
| --- | --- |
| [`ReferenceEventType`](https://docs.rs/atelier-connect/latest/atelier_connect/synchronizers/event_sync/enum.ReferenceEventType.html) | Which market event type triggers snapshot emission. |
