# `atelier_quant::forecast`

Forecast evaluation and Monte-Carlo ensemble reduction.

This module provides:

- `ForecastMetrics` — MAE, RMSE computed from cumulative gap errors.
- `ensemble_forecast` — run multiple stochastic paths and reduce
  to a consensus trajectory.
- `percentile` — linearly interpolated quantile from a sorted slice.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::forecast`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/).

## Structs

| Item | Summary |
| --- | --- |
| [`ForecastMetrics`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/struct.ForecastMetrics.html) | Forecast error metrics computed on cumulative gaps from the train/test boundary. |
| [`LRTestResult`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/struct.LRTestResult.html) | Result of a likelihood-ratio test comparing a full model (Hawkes) against a restricted model (Poisson). |

## Functions

| Item | Summary |
| --- | --- |
| [`ensemble_forecast`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/fn.ensemble_forecast.html) | Run an ensemble of stochastic forecasts and reduce each event-index column with the chosen statistic. |
| [`forecast_errors`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/fn.forecast_errors.html) | Compute MAE and RMSE between actual and forecast cumulative gaps. |
| [`likelihood_ratio_test`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/fn.likelihood_ratio_test.html) | Perform a likelihood-ratio test. |
| [`percentile`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/fn.percentile.html) | Linearly interpolated percentile from a **sorted** slice. |
