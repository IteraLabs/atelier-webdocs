# `atelier_types::orderbooks::delta`

Incremental orderbook delta updates.
Delta orderbook updates and normalization.

Provides `NormalizedDelta` for exchange-agnostic representation of
orderbook updates and `OrderbookDelta` for incremental state management.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::orderbooks::delta`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/delta/).

## Structs

| Item | Summary |
| --- | --- |
| [`NormalizedDelta`](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/delta/struct.NormalizedDelta.html) | Exchange-agnostic orderbook delta/snapshot representation. |
| [`OrderbookDelta`](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/delta/struct.OrderbookDelta.html) | A Delta Orderbook state from WebSocket updates |
| [`OrderbookSnapshot`](https://docs.rs/atelier-types/0.0.10/atelier_types/orderbooks/delta/struct.OrderbookSnapshot.html) | Full orderbook snapshot for JSON serialization. |
