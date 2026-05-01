# `atelier_types::temporal::validations`

Timestamp validation and gap detection.
Data validation utilities for timestamp sequences.

Provides checks for monotonicity, deduplication, and gap detection
on sorted nanosecond timestamp vectors before interarrival computation.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_types::temporal::validations`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/validations/).

## Structs

| Item | Summary |
| --- | --- |
| [`GapInfo`](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/validations/struct.GapInfo.html) | Information about a detected gap in a timestamp sequence. |

## Functions

| Item | Summary |
| --- | --- |
| [`deduplicate`](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/validations/fn.deduplicate.html) | Remove consecutive duplicate timestamps in-place. |
| [`detect_gaps`](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/validations/fn.detect_gaps.html) | Detect gaps in the timestamp sequence that exceed a threshold. |
| [`validate_monotonic`](https://docs.rs/atelier-types/0.0.10/atelier_types/temporal/validations/fn.validate_monotonic.html) | Validate that timestamps are strictly monotonically increasing. |
