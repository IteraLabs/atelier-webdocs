# `atelier_types::temporal::resolutions`

Timestamp resolution conversions.
Temporal validation utilities for timestamp sequences.

Orderbook timestamps are in nanoseconds, trade timestamps in milliseconds,
and other datasets might be in microseconds or seconds.
This module provides a canonical representation (nanoseconds) and conversion
utilities to normalize heterogeneous timestamp sources.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::temporal::resolutions`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/).

## Enums

| Item | Summary |
| --- | --- |
| [`TimeResolution`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/enum.TimeResolution.html) | Supported temporal resolutions for timestamp data. |

## Functions

| Item | Summary |
| --- | --- |
| [`from_nanos`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/fn.from_nanos.html) | Convert a nanosecond timestamp to the target resolution as `f64`. |
| [`to_nanos`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/fn.to_nanos.html) | Convert a timestamp from the given resolution to nanoseconds. |

## Constants

| Item | Summary |
| --- | --- |
| [`NS_PER_MS`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/constant.NS_PER_MS.html) | Nanoseconds per millisecond. |
| [`NS_PER_S`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/constant.NS_PER_S.html) | Nanoseconds per second. |
| [`NS_PER_US`](https://docs.rs/atelier-types/latest/atelier_types/temporal/resolutions/constant.NS_PER_US.html) | Nanoseconds per microsecond. |
