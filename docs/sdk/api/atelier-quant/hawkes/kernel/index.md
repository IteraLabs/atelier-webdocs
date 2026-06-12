# `atelier_quant::hawkes::kernel`

Excitation kernel abstraction for Hawkes processes.

The `ExcitationKernel` trait decouples the Hawkes process simulation
and forecasting machinery from a specific kernel shape.  Any kernel
that can express its contribution through a recursive *state* variable
— initialised once from history in O(n), then maintained in O(1) —
can be plugged into `HawkesProcess<K>`.

## Provided implementation

`ExponentialKernel` — the classical $\phi(t) = \alpha e^{-\beta t}$
kernel, whose state is a single `f64` (the recursive auxiliary $A$).

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::hawkes::kernel`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/kernel/).

## Structs

| Item | Summary |
| --- | --- |
| [`ExponentialKernel`](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/kernel/struct.ExponentialKernel.html) | Classical exponential excitation kernel. |

## Traits

| Item | Summary |
| --- | --- |
| [`ExcitationKernel`](https://docs.rs/atelier-quant/latest/atelier_quant/hawkes/kernel/trait.ExcitationKernel.html) | Trait abstracting the excitation kernel of a univariate Hawkes process. |
