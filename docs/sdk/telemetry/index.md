# `atelier-telemetry`

OpenTelemetry instrumentation for the Atelier SDK engine. Provides a
configuration struct, an initialization function, an RAII guard, and
a small set of pre-named meters that the workers and sinks call into.

The crate is deliberately scoped: it does **not** define metrics
abstractions, business-level dashboards, or alerting policies. It is
a thin opinionated layer over the [OpenTelemetry Rust SDK](https://docs.rs/opentelemetry)
that enforces a shared metric vocabulary across `atelier-connect`'s
workers and `atelier-io`'s sinks so an operator dashboard can be
built once and consume telemetry from any worker.

## Public API

### Top-level

| Item                | Purpose                                                                                                  |
|---------------------|----------------------------------------------------------------------------------------------------------|
| `TelemetryConfig`   | Deserializable config: exporter kind, endpoint, sampling, service name                                   |
| `TelemetryGuard`    | RAII guard returned by `init_telemetry` — holds the global tracer-provider; flushes on drop              |
| `init_telemetry()`  | Sets up the global tracer / meter provider from a `TelemetryConfig`. Returns a `TelemetryGuard`.         |
| `ingestion_meters()`| Factory that returns an `IngestionMeters` (the fixed set of pre-named meters)                            |

### `attributes` module

A vocabulary of attribute keys (`EXCHANGE`, `SYMBOL`, `MARKET_TYPE`,
`WORKER_ID`, `TOPIC`, `SINK_NAME`, `TOPIC_CATEGORY`) plus a few
helper functions that build attribute sets for events, workers, and
topic classifications.

### `exporters` module

`ExporterKind` enum (`Stdout`, `Otlp`, `None`) plus a
`build_meter_provider()` factory. The `Otlp` variant uses the
gRPC exporter (`opentelemetry-otlp` with the `grpc-tonic` feature).

### `meters` module

The fixed-name metric vocabulary every worker and sink shares:

| Constant                     | Metric                                                              |
|------------------------------|---------------------------------------------------------------------|
| `MESSAGES_RECEIVED`          | Counter — events received                                           |
| `EVENT_LATENCY_MS`           | Histogram — milliseconds between event timestamp and ingestion       |
| `WORKER_CONNECTION_STATE`    | Gauge — encoded state (Connected / Disconnected / etc.)              |
| `SINK_QUEUE_DEPTH`           | Gauge — current backpressure depth                                   |

Plus `LATENCY_BUCKETS_MS` (the histogram bucket boundaries) and
`IngestionMeters` itself, which exposes:

- `IngestionMeters::new(meter_name)`
- `record_event(...)`
- `record_latency(...)`
- `set_connection_state(...)`
- `set_queue_depth(...)`

## Quick start

```rust
use atelier_telemetry::{TelemetryConfig, init_telemetry, ingestion_meters};

let config = TelemetryConfig {
    service_name: "atelier-worker".to_string(),
    exporter: atelier_telemetry::exporters::ExporterKind::Otlp,
    endpoint: Some("http://otel-collector:4317".to_string()),
    ..Default::default()
};

let _guard = init_telemetry(&config)?;
let meters = ingestion_meters("atelier_connect.bybit");

// Inside a worker loop:
meters.record_event(/* ... */);
meters.record_latency(/* ... */);
```

The `_guard` binding is load-bearing — when it drops, the
tracer-provider flushes and shuts down cleanly. Don't shadow it
with `_`.

## Configuration

`TelemetryConfig` deserializes from TOML, JSON, or env vars (via
`serde`). A typical TOML block:

```toml
[telemetry]
service_name = "atelier-worker"
exporter = "otlp"
endpoint = "http://otel-collector:4317"
```

## Where to go next

- [API reference for `atelier-telemetry`](../api/atelier-telemetry/index.md)
- [docs.rs/atelier-telemetry](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/) — full signatures.
- [`atelier-connect`](../connect/index.md) — the primary caller of `IngestionMeters`.
