# `atelier_quant::probs::probabilistic`

# Probabilistic generators

This module provides implementations for sampling from various probability
distributions, including:

- Normal
- Poisson
- Exponential

## References

- [rand_distr](https://docs.rs/rand_distr/latest/rand_distr/)

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::probs::probabilistic`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/).

## Structs

| Item | Summary |
| --- | --- |
| [`Exponential`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/struct.Exponential.html) | Exponential distribution with rate parameter `lambda`. |
| [`NormalDistribution`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/struct.NormalDistribution.html) | Normal (Gaussian) distribution with mean `mu` and standard deviation `sigma`. |
| [`Poisson`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/struct.Poisson.html) | Poisson distribution with rate parameter `lambda`. |
| [`UniformDistribution`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/struct.UniformDistribution.html) | Continuous uniform distribution on `[lower, upper)`. |

## Traits

| Item | Summary |
| --- | --- |
| [`PDF`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/trait.PDF.html) | Trait for distributions whose parameters can be estimated from data. |
| [`Sampling`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/probs/probabilistic/trait.Sampling.html) | Trait for types that can produce random samples. |
