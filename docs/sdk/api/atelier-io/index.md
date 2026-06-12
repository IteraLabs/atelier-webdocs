# `atelier-io` — API reference

Skeleton API reference for crate
[`atelier-io`](https://docs.rs/atelier-io/latest/atelier_io/) at
version `0.0.10`.

!!! info "Preliminary skeleton"
    Hand-derived from the Phase-1 survey. Run
    `make sdk-api SDK_PATH=../atelier-sdk` before cutover to refresh.

## Modules

| Module                                                                                | Public items                                                                                  |
|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [`orderbooks`](https://docs.rs/atelier-io/latest/atelier_io/orderbooks/)               | `write_ob_parquet`, `read_ob_parquet`, plus CSV/JSON readers/writers                          |
| [`trades`](https://docs.rs/atelier-io/latest/atelier_io/trades/)                       | `write_trades_parquet_timestamped`, `read_trades_parquet`                                     |
| [`funding`](https://docs.rs/atelier-io/latest/atelier_io/funding/)                     | `write_funding_parquet_timestamped`, `read_funding_parquet`                                   |
| [`liquidations`](https://docs.rs/atelier-io/latest/atelier_io/liquidations/)           | `write_liquidations_parquet_timestamped`, `read_liquidations_parquet`                         |
| [`open_interest`](https://docs.rs/atelier-io/latest/atelier_io/open_interest/)         | `write_oi_parquet_timestamped`, `read_oi_parquet`                                              |
| [`snapshots`](https://docs.rs/atelier-io/latest/atelier_io/snapshots/)                 | Aggregate snapshot I/O                                                                         |
| `flush` *(features: `connect` + `parquet`)*                                            | `FlushToParquet`, `FlushObSyncToParquet`, `FlushAggregateToParquet`                           |
| `sink` *(feature: `connect`)*                                                          | `ParquetSnapshotFlusher`                                                                       |

## Quick links

| Item                                  | docs.rs                                                                                                                       |
|---------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `FlushToParquet`                      | [link](https://docs.rs/atelier-io/latest/atelier_io/flush/trait.FlushToParquet.html)                                          |
| `FlushObSyncToParquet`                | [link](https://docs.rs/atelier-io/latest/atelier_io/flush/trait.FlushObSyncToParquet.html)                                    |
| `FlushAggregateToParquet`             | [link](https://docs.rs/atelier-io/latest/atelier_io/flush/trait.FlushAggregateToParquet.html)                                 |
| `ParquetSnapshotFlusher`              | [link](https://docs.rs/atelier-io/latest/atelier_io/sink/struct.ParquetSnapshotFlusher.html)                                   |
| `read_ob_parquet`                     | [link](https://docs.rs/atelier-io/latest/atelier_io/orderbooks/fn.read_ob_parquet.html)                                       |
| `read_trades_parquet`                 | [link](https://docs.rs/atelier-io/latest/atelier_io/trades/fn.read_trades_parquet.html)                                       |
| `write_trades_parquet_timestamped`    | [link](https://docs.rs/atelier-io/latest/atelier_io/trades/fn.write_trades_parquet_timestamped.html)                          |

Full reference (docs.rs): <https://docs.rs/atelier-io/latest/atelier_io/>
