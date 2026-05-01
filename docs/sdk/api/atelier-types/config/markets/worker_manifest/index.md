# `atelier_types::config::markets::worker_manifest`

Multi-worker manifest configuration.

[`WorkerManifest`] is the top-level config for multi-symbol collection
runs.  It declares shared defaults and a list of per-symbol workers,
each of which resolves into a full [`MarketSnapshotConfig`].

# Example TOML

```toml
[defaults]
sync_mode = "on_trade"
flush_threshold = 36000

[defaults.update_frequency]
value = 100
unit  = "Millis"

[defaults.datatypes.orderbook]
enabled = true
depth   = 50

[defaults.datatypes.trades]
enabled = true

[defaults.datatypes.liquidations]
enabled = true

[defaults.datatypes.funding_rates]
enabled = true

[defaults.datatypes.open_interest]
enabled = true

[defaults.logs]
n_orderbooks    = 500
n_trades        = 500
n_liquidations  = 1
n_fundings      = 50
n_open_interests = 50

[[workers]]
exchange = "bybit"
symbol   = "BTCUSDT"

[[workers]]
exchange = "bybit"
symbol   = "ETHUSDT"
sync_mode = "on_orderbook"   # per-worker override

[output]
base_dir = "datasets/collected"

[session]
duration_hours = 8
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::config::markets::worker_manifest`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/).

## Structs

| Item | Summary |
| --- | --- |
| [`DefaultsSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/struct.DefaultsSection.html) | Shared defaults applied to every worker unless overridden. |
| [`ManifestOutputSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/struct.ManifestOutputSection.html) | `[output]` — base directory for all workers. |
| [`SessionSection`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/struct.SessionSection.html) | `[session]` — optional run-time parameters. |
| [`WorkerEntry`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/struct.WorkerEntry.html) | A single worker entry — identifies an exchange + symbol pair. |
| [`WorkerManifest`](https://docs.rs/atelier-types/0.0.10/atelier_types/config/markets/worker_manifest/struct.WorkerManifest.html) | Top-level multi-worker manifest deserialized from TOML. |
