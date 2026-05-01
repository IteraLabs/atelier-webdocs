# `atelier_quant::arrivals::validate`

Timestamp validation and gap detection.

Pre-flight checks for timestamp sequences before they enter the
estimation pipeline.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_quant::arrivals::validate`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/validate/).

## Structs

| Item | Summary |
| --- | --- |
| [`GapInfo`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/validate/struct.GapInfo.html) | A gap between consecutive timestamps that exceeds the threshold. |

## Enums

| Item | Summary |
| --- | --- |
| [`MonotonicityResult`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/validate/enum.MonotonicityResult.html) | Result of monotonicity validation. |

## Functions

| Item | Summary |
| --- | --- |
| [`check_monotonicity`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/validate/fn.check_monotonicity.html) | Check whether a timestamp sequence is strictly monotonically increasing. |
| [`detect_gaps`](https://docs.rs/atelier-quant/0.0.10/atelier_quant/arrivals/validate/fn.detect_gaps.html) | Detect all gaps between consecutive timestamps that exceed a threshold. |
