# `atelier_quant::hawkes::estimation`

Maximum Likelihood Estimation for the univariate Hawkes process.

# Model

Univariate Hawkes process with exponential kernel:

$$
  \lambda(t) = \mu + \alpha \sum_{t_j < t} e^{-\beta(t - t_j)}
$$

# Log-Likelihood

$$
  \ell(\mu, \alpha, \beta) = \sum_i \ln \lambda(t_i)
    - \mu T
    - \frac{\alpha}{\beta} \sum_i \bigl(1 - e^{-\beta(T - t_i)}\bigr)
$$

Evaluated in $O(n)$ via the auxiliary recursion:

$$
  A_i = e^{-\beta(t_i - t_{i-1})} \cdot (1 + A_{i-1}), \quad A_0 = 0
$$

# Optimization

Gradient ascent with analytical gradients, Armijo backtracking line
search, and parameter projection to maintain the feasibility set
$\mu > 0,\; \alpha > 0,\; \beta > 0,\; \alpha / \beta < 1$.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::hawkes::estimation`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/).

## Structs

| Item | Summary |
| --- | --- |
| [`HawkesEstimationConfig`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/struct.HawkesEstimationConfig.html) | Configuration for the Hawkes MLE optimizer. |
| [`HawkesEstimationResult`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/struct.HawkesEstimationResult.html) | Output of the Hawkes MLE estimation. |

## Functions

| Item | Summary |
| --- | --- |
| [`compensator`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.compensator.html) | Compute the compensator (integrated intensity) over `[0, T]`. |
| [`compute_recursion_arrays`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.compute_recursion_arrays.html) | Compute the A_i and B_i recursion arrays for testing/diagnostics. |
| [`estimate_hawkes_mle`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.estimate_hawkes_mle.html) | Estimate Hawkes process parameters via Maximum Likelihood. |
| [`grad_norm`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.grad_norm.html) | Infinity-norm of a 3-vector. |
| [`gradient`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.gradient.html) | Compute the analytical gradient of the log-likelihood. |
| [`log_likelihood`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.log_likelihood.html) | Compute the log-likelihood of a univariate Hawkes process with exponential kernel, given event times and parameters. |
| [`project`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.project.html) | Project parameters onto the feasible set. |
| [`time_rescaling_residuals`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.time_rescaling_residuals.html) | Compute time-rescaling residuals for goodness-of-fit assessment. |
| [`validate_events`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/estimation/fn.validate_events.html) | Validate event times for MLE input. |
