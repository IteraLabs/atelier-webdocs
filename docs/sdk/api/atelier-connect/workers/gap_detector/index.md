# `atelier_connect::workers::gap_detector`

Per-topic ingestion gap detection.
Per-topic ingestion gap detection.

`GapDetector` tracks the wall-clock time between consecutive events
on a single topic.  When the silence exceeds a configurable threshold,
the detector records it as an **ingestion gap metric** — *not* as
corrupted data.

This distinction is critical: during exchange maintenance windows,
network blips, or naturally quiet markets, there is simply no data to
ingest.  Downstream consumers must be aware of gaps but should not
treat them as data-integrity failures.

# Metric name

`ingestion_gap_duration_ms` — emitted as a `tracing::warn!` span
whenever a gap exceeding the threshold is detected.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::gap_detector`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/gap_detector/).

## Structs

| Item | Summary |
| --- | --- |
| [`GapDetector`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/gap_detector/struct.GapDetector.html) | Per-topic ingestion gap tracker. |
| [`GapDetectorSet`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/gap_detector/struct.GapDetectorSet.html) | Collection of `GapDetector`s keyed by topic name. |
| [`GapStats`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/gap_detector/struct.GapStats.html) | Summary stats for one gap detector. |

## Constants

| Item | Summary |
| --- | --- |
| [`DEFAULT_SILENCE_THRESHOLD`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/gap_detector/constant.DEFAULT_SILENCE_THRESHOLD.html) | Default silence threshold: 5 seconds without events = gap. |
