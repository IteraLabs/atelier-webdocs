# `atelier_connect::config::workers::data_worker_config`

Configuration for [`DataWorker`](crate::workers::data_worker::DataWorker).

[`DataWorkerConfig`] is the lean, DataWorker-specific config — no
synchronisation fields, no Parquet flush cadence, no grid spacing.
Just exchange + symbol + datatypes + output sinks.

[`DataWorkerManifest`] is the multi-worker TOML manifest that resolves
into a `Vec<DataWorkerConfig>`.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::config::workers::data_worker_config`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/).

## Structs

| Item | Summary |
| --- | --- |
| [`DataWorkerCollect`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/struct.DataWorkerCollect.html) | Shared collect section in a [`DataWorkerManifest`]. |
| [`DataWorkerConfig`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/struct.DataWorkerConfig.html) | Fully-resolved configuration for a single [`DataWorker`](crate::workers::data_worker::DataWorker). |
| [`DataWorkerEntry`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/struct.DataWorkerEntry.html) | A single worker entry — identifies a symbol (exchange comes from collect). |
| [`DataWorkerManifest`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/struct.DataWorkerManifest.html) | Top-level TOML manifest for spawning multiple [`DataWorker`](crate::workers::data_worker::DataWorker)s. |
| [`SessionSection`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/config/workers/data_worker_config/struct.SessionSection.html) | Session parameters (shared with MarketWorkerManifest). |
