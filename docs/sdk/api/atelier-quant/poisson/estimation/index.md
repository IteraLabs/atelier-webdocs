# `atelier_quant::poisson::estimation`

Closed-form Maximum Likelihood Estimation for the homogeneous Poisson process.

# Model

Homogeneous Poisson process with constant intensity:

$$
  \lambda(t) = \lambda
$$

# Log-Likelihood

For n events on the observation window $[t_1, t_n]$:

$$
  \ell(\lambda) = (n - 1) \ln \lambda - \lambda \, T
$$

where $T = t_n - t_1$.  The MLE is $\hat\lambda = (n-1) / T$.

We use $n-1$ interarrivals (not $n$) because the observation window
is $[t_1, t_n]$, consistent with how the Hawkes compensator integral
is defined.  This ensures AIC/BIC are directly comparable.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::poisson::estimation`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/).

## Structs

| Item | Summary |
| --- | --- |
| [`PoissonEstimationConfig`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/struct.PoissonEstimationConfig.html) | Configuration for the Poisson MLE. |
| [`PoissonEstimationResult`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/struct.PoissonEstimationResult.html) | Output of the Poisson MLE estimation. |

## Functions

| Item | Summary |
| --- | --- |
| [`compensator`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.compensator.html) | Compute the compensator (integrated intensity) over $[t_1, t]$. |
| [`estimate_poisson_mle`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.estimate_poisson_mle.html) | Estimate the Poisson rate parameter via closed-form MLE. |
| [`log_likelihood`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.log_likelihood.html) | Compute the log-likelihood of a homogeneous Poisson process. |
| [`time_rescaling_residuals`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.time_rescaling_residuals.html) | Compute time-rescaling residuals for goodness-of-fit assessment. |
| [`validate_events`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/estimation/fn.validate_events.html) | Validate event times for MLE input. |
