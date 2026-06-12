# `atelier_types::utils`

General utilities
Utility functions for market data processing.

Provides timestamp formatting, decimal conversion, and normalization
of exchange-specific side and symbol representations.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::utils`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/latest/atelier_types/utils/).

## Functions

| Item | Summary |
| --- | --- |
| [`current_timestamp_ms`](https://docs.rs/atelier-types/latest/atelier_types/utils/fn.current_timestamp_ms.html) | Get the current system timestamp in Unix milliseconds. |
| [`decimal_to_f64`](https://docs.rs/atelier-types/latest/atelier_types/utils/fn.decimal_to_f64.html) | Convert a Rust Decimal to f64, returning 0.0 on failure. |
| [`format_ts`](https://docs.rs/atelier-types/latest/atelier_types/utils/fn.format_ts.html) | Format a timestamp in nanoseconds to RFC 3339 with nanosecond precision. |
| [`normalize_side`](https://docs.rs/atelier-types/latest/atelier_types/utils/fn.normalize_side.html) | Normalize a trade/liquidation side string to a `crate::trades::TradeSide` variant. |
| [`normalize_symbol`](https://docs.rs/atelier-types/latest/atelier_types/utils/fn.normalize_symbol.html) | Normalize a trading pair symbol to lowercase, separator-free format. |
