# `atelier_quant::config`

Configuration schemas for inter-arrival model binaries.

These structs are shared between `inter_fit` and `inter_serve`,
and can be reused by any downstream tool that needs to parse the
same TOML configuration format.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::config`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/config/).

## Structs

| Item | Summary |
| --- | --- |
| [`FitConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/config/struct.FitConfig.html) | Root configuration for the inter-arrival fitting pipeline. |
| [`ForecastConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/config/struct.ForecastConfig.html) | Monte-Carlo ensemble forecast settings. |
| [`InputConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/config/struct.InputConfig.html) | Specifies where to find the input parquet data. |
| [`ModelConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/config/struct.ModelConfig.html) | MLE estimation hyperparameters and train/test split ratio. |
| [`OutputConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/config/struct.OutputConfig.html) | Where and how to write the model artifact. |

## Enums

| Item | Summary |
| --- | --- |
| [`EnsembleStatistic`](https://docs.rs/atelier-quant/latest/atelier_quant/config/enum.EnsembleStatistic.html) | Statistic used to reduce an ensemble of Monte-Carlo forecast trajectories into a single consensus trajectory. |
