# `atelier_types::snapshots::aggregate`

Aggregated market statistics module.
Aggregated per-snapshot statistics.

[`MarketAggregate`] reduces each [`MarketSnapshot`] to 15 scalar features
(3 per data type), suitable for low-dimensional analysis, feature
engineering, and efficient Parquet storage.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::snapshots::aggregate`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/aggregate/).

## Structs

| Item | Summary |
| --- | --- |
| [`MarketAggregate`](https://docs.rs/atelier-types/0.0.10/atelier_types/snapshots/aggregate/struct.MarketAggregate.html) | Aggregated statistics for a single [`MarketSnapshot`] period. |
