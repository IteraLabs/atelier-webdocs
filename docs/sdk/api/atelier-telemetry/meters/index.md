# `atelier_telemetry::meters`

OpenTelemetry metric instrument definitions for the atelier-sdk engine.

This module defines the four beta instruments that back the dashboard's
metrics row:

| Instrument | OTel Kind | Dashboard Panel |
|---|---|---|
| `messages_received` | `Counter<u64>` | MESSAGES/S, LOB/S, TRADES/S |
| `event_latency_ms` | `Histogram<f64>` | LATENCY P99 |
| `worker_connection_state` | `Gauge<u64>` | Sidebar state badges |
| `sink_queue_depth` | `Gauge<u64>` | Sink status panel |

# Usage

```ignore
use atelier_telemetry::meters::IngestionMeters;

let meters = IngestionMeters::new(&meter);
meters.record_event(&attrs);
meters.record_latency(12.5, &attrs);
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_telemetry::meters`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/).

## Structs

| Item | Summary |
| --- | --- |
| [`IngestionMeters`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/struct.IngestionMeters.html) | Holds the four beta OTel instruments for the ingestion pipeline. |

## Functions

| Item | Summary |
| --- | --- |
| [`connection_state_code`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/fn.connection_state_code.html) | Encode a connection state name to a numeric gauge value. |

## Constants

| Item | Summary |
| --- | --- |
| [`EVENT_LATENCY_MS`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/constant.EVENT_LATENCY_MS.html) | Histogram: end-to-end event latency in milliseconds (exchange timestamp → local receive time). |
| [`LATENCY_BUCKETS_MS`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/constant.LATENCY_BUCKETS_MS.html) | Histogram bucket boundaries tuned for WebSocket event latency. |
| [`MESSAGES_RECEIVED`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/constant.MESSAGES_RECEIVED.html) | Counter: total messages received (one increment per classified event). |
| [`SINK_QUEUE_DEPTH`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/constant.SINK_QUEUE_DEPTH.html) | Gauge: number of pending messages in a channel sink's queue. |
| [`WORKER_CONNECTION_STATE`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/meters/constant.WORKER_CONNECTION_STATE.html) | Gauge: current connection state as a numeric code. |
