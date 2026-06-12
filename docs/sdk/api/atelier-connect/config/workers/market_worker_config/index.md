# `atelier_connect::config::workers::market_worker_config`

Configuration for `MarketWorker`.

`MarketWorkerConfig` extends `CommonWorkerFields` with synchronisation
parameters (clock mode, grid spacing, flush threshold).

`MarketWorkerManifest` is the multi-worker TOML manifest that resolves
into a `Vec<MarketWorkerConfig>`.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::config::workers::market_worker_config`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/).

## Structs

| Item | Summary |
| --- | --- |
| [`MarketWorkerCollect`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/struct.MarketWorkerCollect.html) | Shared collect instructions for a `MarketWorkerManifest`. |
| [`MarketWorkerConfig`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/struct.MarketWorkerConfig.html) | Fully-resolved configuration for a single `MarketWorker`. |
| [`MarketWorkerEntry`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/struct.MarketWorkerEntry.html) | A single worker entry in a `MarketWorkerManifest`. |
| [`MarketWorkerManifest`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/struct.MarketWorkerManifest.html) | Top-level TOML manifest for spawning multiple `MarketWorker`s. |
| [`SyncSection`](https://docs.rs/atelier-connect/latest/atelier_connect/config/workers/market_worker_config/struct.SyncSection.html) | Synchronisation parameters for the MarketWorker. |
