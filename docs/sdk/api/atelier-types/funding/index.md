# `atelier_types::funding`

Funding rate data for perpetual futures
Funding rate data structures.

Funding rates are periodic payments between long and short position holders
in perpetual futures markets. A positive rate means longs pay shorts; negative
means shorts pay longs.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::funding`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/funding/).

## Structs

| Item | Summary |
| --- | --- |
| [`FundingRate`](https://docs.rs/atelier-types/0.0.10/atelier_types/funding/struct.FundingRate.html) | A single funding rate observation. |
| [`FundingRateBuilder`](https://docs.rs/atelier-types/0.0.10/atelier_types/funding/struct.FundingRateBuilder.html) | Builder for constructing a [`FundingRate`] with validated fields. |
