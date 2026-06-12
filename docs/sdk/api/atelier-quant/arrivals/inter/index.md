# `atelier_quant::arrivals::inter`

Interarrival time computation and descriptive statistics.

Given a sequence of arrival timestamps (in nanoseconds), this module
computes the interarrival deltas $\Delta t_i = t_{i+1} - t_i$ and
provides summary statistics useful for distribution fitting.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::arrivals::inter`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/inter/).

## Structs

| Item | Summary |
| --- | --- |
| [`ArrivalStats`](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/inter/struct.ArrivalStats.html) | Descriptive statistics for a set of interarrival times. |
| [`InterarrivalResult`](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/inter/struct.InterarrivalResult.html) | Result of an interarrival computation. |

## Functions

| Item | Summary |
| --- | --- |
| [`compute_interarrivals`](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/inter/fn.compute_interarrivals.html) | Compute interarrival times from a sorted sequence of nanosecond timestamps. |
| [`descriptive_stats`](https://docs.rs/atelier-quant/latest/atelier_quant/arrivals/inter/fn.descriptive_stats.html) | Compute descriptive statistics for a slice of interarrival times. |
