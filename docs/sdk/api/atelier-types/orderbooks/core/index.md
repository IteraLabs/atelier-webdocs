# `atelier_types::orderbooks::core`

Core orderbook data structure and operations.
Core orderbook structure and operations.

Provides the `Orderbook` data structure for managing bid/ask levels
and orders, along with utility functions for decimal/f64 conversion.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::orderbooks::core`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/core/).

## Structs

| Item | Summary |
| --- | --- |
| [`Orderbook`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/core/struct.Orderbook.html) | Represents the Limit Order Book data structure. |

## Functions

| Item | Summary |
| --- | --- |
| [`decimal_to_f64`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/core/fn.decimal_to_f64.html) | Convert a `Decimal` to `f64`. |
| [`f64_to_decimal`](https://docs.rs/atelier-types/latest/atelier_types/orderbooks/core/fn.f64_to_decimal.html) | Convert an `f64` to `Decimal`. |
