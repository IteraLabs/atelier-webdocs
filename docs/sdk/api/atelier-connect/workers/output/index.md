# `atelier_connect::workers::output`

Pluggable output sinks for worker event delivery.
Pluggable output sinks for worker event delivery.

The `OutputSink` trait defines the interface that both `DataWorker` and
`MarketWorker` use to emit data.  Multiple sinks can be active
simultaneously via `OutputSinkSet`, which fans out every call.

# Implemented sinks

| Sink | Status | Description |
|------|--------|-------------|
| `ChannelSink` | Working | Wraps existing `TopicRegistry` broadcast channels |
| `TerminalSink` | Stub | Debug/tracing terminal output |
| `ParquetSink` | Working | Buffers `MarketSnapshot`s, decomposes and flushes to per-datatype Parquet files |

# Adding a new sink

1. Implement `OutputSink` for your type.
2. Add a variant to `OutputSinkConfig` in `config::workers::common`.
3. Handle the new variant in `build_sinks()`.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::output`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/).

## Structs

| Item | Summary |
| --- | --- |
| [`BufferedSink`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.BufferedSink.html) | Buffers `MarketSnapshot`s in memory and delegates persistence to an injected `SnapshotFlusher` on `OutputSink::flush`. |
| [`BufferedSinkFlushEvent`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.BufferedSinkFlushEvent.html) | Event emitted by `BufferedSink` after each successful flush. |
| [`ChannelSink`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.ChannelSink.html) | Publishes raw events to broadcast channels via `TopicRegistry`. |
| [`FlushReport`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.FlushReport.html) | Report returned by a `SnapshotFlusher` after a successful flush. |
| [`OutputSinkSet`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.OutputSinkSet.html) | Fan-out wrapper that delegates every call to all contained sinks. |
| [`SinkStatus`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.SinkStatus.html) | Snapshot of a sink's runtime status at a point in time. |
| [`TerminalSink`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.TerminalSink.html) | Prints events to the terminal via `tracing::debug!`. |
| [`TerminalSinkRawEvent`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/struct.TerminalSinkRawEvent.html) | A raw terminal sink event forwarded to the dashboard. |

## Enums

| Item | Summary |
| --- | --- |
| [`SinkState`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/enum.SinkState.html) | Runtime operational state of an output sink. |

## Traits

| Item | Summary |
| --- | --- |
| [`OutputSink`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/trait.OutputSink.html) | A destination for worker output. |
| [`SnapshotFlusher`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/trait.SnapshotFlusher.html) | Trait for flushing buffered `MarketSnapshot`s to persistent storage. |

## Functions

| Item | Summary |
| --- | --- |
| [`build_sinks`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/fn.build_sinks.html) | Build an `OutputSinkSet` from config entries. |

## Type aliases

| Item | Summary |
| --- | --- |
| [`BufferedSinkFlushCallback`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/type.BufferedSinkFlushCallback.html) | Callback type for forwarding buffered sink (Parquet) flush events. |
| [`TerminalEventCallback`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/output/type.TerminalEventCallback.html) | Callback type for forwarding terminal sink events. |
