# `atelier_types::snapshots::market`

Market snapshot joining all data sources.
Multi-source market snapshot aggregation.

A `MarketSnapshot` joins orderbook state, trades, liquidations, funding
rates, and open interest at a single grid-aligned timestamp. This is the
canonical input to multi-source feature computation.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::snapshots::market`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/market/).

## Structs

| Item | Summary |
| --- | --- |
| [`MarketSnapshot`](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/market/struct.MarketSnapshot.html) | A point-in-time view of the market across all data sources. |
