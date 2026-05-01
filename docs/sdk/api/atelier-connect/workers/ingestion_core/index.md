# `atelier_connect::workers::ingestion_core`

Shared ingestion engine (reconnection, classification, health).
Shared ingestion core used by both `DataWorker` and `MarketWorker`.

`IngestionCore` encapsulates the full reconnection loop, exchange
client spawning, event classification, health monitoring, and gap
detection.  It sends classified `TopicMessage`s to an
`mpsc::Sender<TopicMessage>` — the owning worker decides what to do
with them (publish to sinks, feed into a synchroniser, etc.).

# Architecture

```text
┌──────────────┐     mpsc     ┌──────────────┐    mpsc    ┌──────────┐
│ ExchangeWSS  │─────────────→│ IngestionCore │───────────→│  Worker  │
│ Client Task  │  raw events  │ (reconnect +  │  TopicMsg  │ (output  │
│              │              │  classify)    │            │  sinks)  │
└──────────────┘              └──────────────┘            └──────────┘
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_connect::workers::ingestion_core`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/).

## Structs

| Item | Summary |
| --- | --- |
| [`IngestionCore`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/struct.IngestionCore.html) | Shared ingestion engine composed by both worker types. |
| [`IngestionReport`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/struct.IngestionReport.html) | Summary statistics returned when an `IngestionCore` finishes. |

## Functions

| Item | Summary |
| --- | --- |
| [`classify_event`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/fn.classify_event.html) | Map an `ExchangeEvent` to zero or more canonical topic names. |
| [`wall_clock_ns`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/fn.wall_clock_ns.html) | Current wall-clock time as nanoseconds since UNIX epoch. |
| [`wss_streams`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/fn.wss_streams.html) | Build exchange-specific WSS subscription topics from common fields. |
| [`wss_topic_names`](https://docs.rs/atelier-connect/0.0.10/atelier_connect/workers/ingestion_core/fn.wss_topic_names.html) | Build canonical topic names for event classification. |
