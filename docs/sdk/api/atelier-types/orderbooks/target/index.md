# `atelier_types::orderbooks::target`

Orderbook loading targets and result types.
Orderbook loading targets and update result types.

Defines `OrderbookTarget` to specify which orderbook representation
to load, and result types for update operations.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::orderbooks::target`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/target/).

## Structs

| Item | Summary |
| --- | --- |
| [`OrderbookUpdate`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/target/struct.OrderbookUpdate.html) | Result of applying an update to the orderbook. |

## Enums

| Item | Summary |
| --- | --- |
| [`OrderbookTarget`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/target/enum.OrderbookTarget.html) | Specifies which orderbook representation to load into. |
| [`OrderbookTargetData`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/target/enum.OrderbookTargetData.html) | Result of reading an orderbook file in either delta or snapshot format. |
| [`OrderbookUpdateType`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/target/enum.OrderbookUpdateType.html) | Type of orderbook update (snapshot or incremental delta). |
