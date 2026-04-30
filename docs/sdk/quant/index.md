# `atelier-quant`

Quantitative models for the Atelier SDK. The crate ships
implementations of two point-process families — Hawkes and Poisson —
along with an interarrival-time analysis module that bridges raw
microstructure data into the inputs those models expect, and a small
probability-distribution sampling kit.

If `atelier-connect` and `atelier-io` are about getting data, and
`atelier-types` is about representing it, `atelier-quant` is about
*reasoning over it*: parametric model fitting, log-likelihood
inference, simulation, and goodness-of-fit checks.

## Modules

| Module       | What's there                                                                                              |
|--------------|-----------------------------------------------------------------------------------------------------------|
| `hawkes`     | `HawkesProcess`: simulation (Ogata's thinning), kernel trait, quadrature, MLE fit with Armijo line search, AIC/BIC, goodness-of-fit |
| `poisson`    | `PoissonProcess`: closed-form MLE                                                                          |
| `arrivals`   | Interarrival-delta extraction from event streams; descriptive statistics                                   |
| `probs`      | Sampling trait + four distributions: Uniform, Normal, Poisson, Exponential                                 |
| `artifact`   | Model-artifact serialization (fit results to disk)                                                         |
| `config`     | TOML configuration structures                                                                              |
| `forecast`   | Forecasting machinery (early stage)                                                                        |
| `errors`     | Convergence and parameter errors                                                                           |

## Hawkes process — the headline feature

A self-exciting point process where the conditional intensity at
time $t$ depends on the history of past events through an
excitation kernel. The crate's `HawkesProcess` covers:

- **Simulation** via Ogata's thinning algorithm, suitable for
  generating synthetic event streams.
- **Kernels** — exponential is provided; the `Kernel` trait lets
  you plug in alternatives.
- **Likelihood evaluation** with quadrature for the integral term
  in the log-likelihood.
- **Maximum-likelihood fit** with Armijo line search.
- **Model selection** via AIC / BIC.
- **Goodness-of-fit** diagnostics.

For a runnable end-to-end fit against orderbook arrivals, see the
[Hawkes tutorial](../../guides/03-hawkes-on-arrivals.md).

## Poisson process — the baseline

Stateless homogeneous and inhomogeneous Poisson with closed-form
MLE. Used both as a model in its own right and as a benchmark
against which Hawkes fits are compared (the Hawkes model should
*beat* a Poisson on AIC / BIC for it to be a reasonable claim of
self-excitation).

## Arrivals — bridging data and models

`arrivals` extracts interarrival deltas from event streams (trades,
liquidations, orderbook crossings) and computes descriptive
statistics on them. This is the canonical input shape for fitting
either point-process model.

## Probability sampling kit

`probs` provides a `Sampling` trait and four implementations:
Uniform, Normal, Poisson, Exponential. Used internally by the Hawkes
simulator and exposed for downstream consumers who want
deterministic sampling without pulling in a heavier dependency.

## Binaries

Two example binaries ship with the crate:

| Binary       | What it does                                                                                              |
|--------------|-----------------------------------------------------------------------------------------------------------|
| `inter_fit`  | Loads Parquet data, fits a univariate Hawkes process via MLE, compares against a Poisson benchmark, and writes a model artifact to disk. Configured via `atelier-quant/configs/inter_fit.toml`. |
| `inter_serve`| Serves a fitted model artifact (early stage).                                                              |

Run with:

```bash
inter_fit --config configs/inter_fit.toml
```

## Where to go next

- [Tutorial: Fit a Hawkes process to orderbook arrivals](../../guides/03-hawkes-on-arrivals.md)
- [API reference for `atelier-quant`](../api/atelier-quant/index.md)
- [`atelier-types`](../types/index.md) — the data this crate reasons over.
- [`atelier-io`](../io/index.md) — how Parquet arrivals are loaded.
