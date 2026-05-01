# `atelier_types::liquidations`

Liquidations of positions in CEX
Liquidation events: data model and builder.

Liquidations occur when a trader's collateral falls below the
maintenance margin requirement, forcing their position to be
automatically closed at market prices.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::liquidations`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/liquidations/).

## Structs

| Item | Summary |
| --- | --- |
| [`Liquidation`](https://docs.rs/atelier-types/0.0.10/atelier_types/liquidations/struct.Liquidation.html) | A single forced-liquidation event observed on an exchange. |
| [`LiquidationBuilder`](https://docs.rs/atelier-types/0.0.10/atelier_types/liquidations/struct.LiquidationBuilder.html) | Builder for constructing a `Liquidation` with validated fields. |
