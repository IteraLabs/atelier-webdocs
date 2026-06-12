# `atelier_quant::artifact`

Model artifact schema for inter-arrival forecasting.

The `ModelArtifact` struct is written by `inter_fit` (as JSON) and
consumed by `inter_serve` to initialise forecasting parameters.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::artifact`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/).

## Structs

| Item | Summary |
| --- | --- |
| [`DataMeta`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/struct.DataMeta.html) | Metadata about the data used for fitting. |
| [`Diagnostics`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/struct.Diagnostics.html) | Goodness-of-fit diagnostics from the Hawkes MLE. |
| [`HawkesParams`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/struct.HawkesParams.html) | Fitted Hawkes (μ, α, β) parameters. |
| [`ModelArtifact`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/struct.ModelArtifact.html) | Serialisable model artifact produced by `inter_fit`. |
| [`PoissonBaseline`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/struct.PoissonBaseline.html) | Poisson baseline comparison for model selection. |
