# `atelier_quant::poisson::core`

# Homogeneous Poisson process

A Poisson process is a memoryless point process with constant intensity
λ(t) = λ.  Interarrival times are i.i.d. Exp(λ).

This serves as the natural null-hypothesis baseline when benchmarking
self-exciting models such as Hawkes.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::poisson::core`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/core/).

## Structs

| Item | Summary |
| --- | --- |
| [`PoissonProcess`](https://docs.rs/atelier-quant/latest/atelier_quant/poisson/core/struct.PoissonProcess.html) | Homogeneous Poisson process with constant rate λ. |
