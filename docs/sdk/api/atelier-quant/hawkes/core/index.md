# `atelier_quant::hawkes::core`

# Point process discrete simulation

A Hawkes Process is a self-exciting point process where the intensity of
events increases following the occurrence of previous events.

## Linear - Univariate.

The simplest case is a self-exciting, one dimensional effect, i.e. the
arrival of an event increases the likelihood of observing events in the
near future. It is also useful to consider the case when there is
more than one type of event, and there is mutual excitement
between the different events. For $d$ such events, we define a
$d$-dimensional Hawkes process:

$$
  \lambda_{i}(t) = \mu_{i} + \sum_{j=1}^{d} \sum_{t_{j,r} \leq t} \phi_{ij}(t - t_{j,r})
$$

Where:

$\mu_{i} \in R_{+}$: Base line (exogenous) intensities. \
$\phi_{ij}$: The (exciting) Kernel functions. \
$t_{j,r}$ : the time of the $j^{th}$ event of type $r$
\
\
As for the $\phi_{ij}$ kernel definition, exponential kernels
are among the most commonly used in Hawkes
processes due to their simplicity and mathematical properties:

$$
 \phi_{ij}(t) = \alpha_{ij} e^{-\beta_{ij}t}
$$

Where:

$\alpha$: Excitation factor (how much each event excites the
future events). \
$\beta$: Decay rate (how quickly the excitement diminishes).\

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::hawkes::core`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/core/).

## Structs

| Item | Summary |
| --- | --- |
| [`HawkesProcess`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/hawkes/core/struct.HawkesProcess.html) | Univariate Hawkes process parameterised by an excitation kernel `K`. |
