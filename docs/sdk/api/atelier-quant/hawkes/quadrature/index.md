# `atelier_quant::hawkes::quadrature`

Numerical quadrature for conditional-mean forecasting.

The expected gap to the next event given current kernel state is:

$$E[\Delta] = \int_0^\infty S(s)\,ds$$

where the survival function is:

$$S(s) = \exp\!\bigl(-\mu\,s - K(s)\bigr)$$

and $K(s)$ is the integrated intensity contribution from the kernel
([`ExcitationKernel::integrated_intensity_contribution`](super::kernel::ExcitationKernel::integrated_intensity_contribution)).

We apply the substitution $x = \mu \cdot s$ so the integration
domain becomes $[0, x_{\max}]$ with $x_{\max} \approx 40$ (since
$e^{-40} \approx 4 \times 10^{-18}$), regardless of the scale of $\mu$.

The integrand under the substitution is:

$$\frac{1}{\mu}\,\exp\!\bigl(-x - K(x/\mu)\bigr)$$

We use adaptive Simpson's rule for robust accuracy.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::hawkes::quadrature`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/quadrature/).

## Functions

| Item | Summary |
| --- | --- |
| [`adaptive_simpson`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/quadrature/fn.adaptive_simpson.html) | Adaptive Simpson's quadrature of `f` on `[a, b]`. |
| [`conditional_mean_gap`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/quadrature/fn.conditional_mean_gap.html) | Compute the conditional expected gap $E[\Delta \mid \text{state}]$. |
