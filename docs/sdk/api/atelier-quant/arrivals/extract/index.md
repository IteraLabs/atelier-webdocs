# `atelier_quant::arrivals::extract`

Timestamp extraction from atelier-data types.

Provides functions to pull raw arrival timestamps (in nanoseconds) from
`Vec<Orderbook>` and `Vec<Trade>` loaded via the atelier-data parquet I/O.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::arrivals::extract`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/extract/).

## Functions

| Item | Summary |
| --- | --- |
| [`extract_orderbook_timestamps`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/extract/fn.extract_orderbook_timestamps.html) | Extract arrival timestamps from orderbook snapshots. |
| [`extract_trade_timestamps`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/extract/fn.extract_trade_timestamps.html) | Extract arrival timestamps from public trades. |
