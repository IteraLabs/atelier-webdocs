# `atelier-quant` — API reference

Skeleton API reference for crate
[`atelier-quant`](https://docs.rs/atelier-quant/latest/atelier_quant/) at
version `0.0.11`.

!!! info "Preliminary skeleton"
    Hand-derived from the Phase-1 survey. Run
    `make sdk-api SDK_PATH=../atelier-sdk` before cutover to refresh.

## Modules

| Module                                                                              | Public items                                                                                       |
|-------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| [`hawkes`](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/)               | `HawkesProcess`, `Kernel` trait, `estimate_hawkes_mle`, `compensator`, `time_rescaling_residuals`  |
| [`hawkes::estimation`](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/estimation/) | `HawkesEstimationConfig`, `HawkesMleResult`                                                |
| [`poisson`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/)             | `PoissonProcess`                                                                                   |
| [`poisson::estimation`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/) | `PoissonEstimationConfig`, `estimate_poisson_mle`, `time_rescaling_residuals`         |
| [`probs`](https://docs.rs/atelier-quant/latest/atelier_quant/probs/)                 | `Sampling` trait, `Uniform`, `Normal`, `Poisson`, `Exponential`                                    |
| [`arrivals`](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/)           | `compute_interarrivals`, `descriptive_stats`, `extract_orderbook_timestamps`, `extract_trade_timestamps` |
| [`artifact`](https://docs.rs/atelier-quant/latest/atelier_quant/artifact/)           | Model artifact serialization                                                                       |
| [`config`](https://docs.rs/atelier-quant/latest/atelier_quant/config/)               | TOML configuration types                                                                           |
| [`forecast`](https://docs.rs/atelier-quant/latest/atelier_quant/forecast/)           | _early-stage; documented as such on the conceptual page_                                           |
| [`errors`](https://docs.rs/atelier-quant/latest/atelier_quant/errors/)               | Convergence and parameter errors                                                                   |

## Quick links to high-traffic items

| Item                       | docs.rs                                                                                                                              |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `HawkesProcess`            | [link](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/struct.HawkesProcess.html)                                          |
| `Kernel`                   | [link](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/trait.Kernel.html)                                                  |
| `estimate_hawkes_mle`      | [link](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/estimation/fn.estimate_hawkes_mle.html)                              |
| `time_rescaling_residuals` | [link](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/estimation/fn.time_rescaling_residuals.html)                         |
| `PoissonProcess`           | [link](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/struct.PoissonProcess.html)                                        |
| `estimate_poisson_mle`     | [link](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.estimate_poisson_mle.html)                            |
| `compute_interarrivals`    | [link](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/fn.compute_interarrivals.html)                                     |
| `descriptive_stats`        | [link](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/fn.descriptive_stats.html)                                         |

Full reference (docs.rs): <https://docs.rs/atelier-quant/latest/atelier_quant/>
