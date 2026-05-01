# `atelier_types::orders`

Implementation of orders
Order primitives: side, type, ID encoding, and builder.

This module defines the core types for representing orders in an
in-memory orderbook.  `OrderId` is a bit-packed `u64` that
encodes side, type, and timestamp into a single sortable value.
`OrderBuilder` provides a validated construction path for
`Order` instances.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::orders`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/).

## Structs

| Item | Summary |
| --- | --- |
| [`Order`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/struct.Order.html) | A single order in the orderbook. |
| [`OrderBuilder`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/struct.OrderBuilder.html) | Builder for constructing an [`Order`] with validated fields. |
| [`OrderId`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/struct.OrderId.html) | Compact order identifier that bit-packs side, type, and timestamp into a single `u64`. |

## Enums

| Item | Summary |
| --- | --- |
| [`OrderSide`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/enum.OrderSide.html) | Side of an order book: bid (buy) or ask (sell). |
| [`OrderType`](https://docs.rs/atelier-types/0.0.10/atelier_types/orders/enum.OrderType.html) | Supported order types: market or limit. |
