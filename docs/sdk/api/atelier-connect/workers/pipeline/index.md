# `atelier_connect::workers::pipeline`

Composable event pipeline between ingestion and workers.
Composable event pipeline between `IngestionCore` and workers.

The pipeline transforms or filters `TopicMessage`s flowing from
the ingestion layer to the worker event loop.  For most exchanges
the pipeline is `PassthroughPipeline` (identity).  For exchanges
that require multi-source coordination (e.g. Binance REST snapshot
+ WSS deltas) a specialised stage is interposed.

# Architecture

```text
IngestionCore ──mpsc──▶ EventPipeline ──mpsc──▶ Worker
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::pipeline`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/pipeline/).

## Structs

| Item | Summary |
| --- | --- |
| [`PassthroughPipeline`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/pipeline/struct.PassthroughPipeline.html) | Identity pipeline — forwards all events unchanged. |

## Traits

| Item | Summary |
| --- | --- |
| [`EventPipeline`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/pipeline/trait.EventPipeline.html) | A composable transform stage in the event pipeline. |

## Functions

| Item | Summary |
| --- | --- |
| [`build_pipeline`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/pipeline/fn.build_pipeline.html) | Construct the appropriate pipeline for the given exchange. |
