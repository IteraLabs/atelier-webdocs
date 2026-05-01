# `atelier_telemetry`

OpenTelemetry instrumentation for the atelier-sdk engine.

`atelier-telemetry` provides a self-contained OTel foundation:

- **Metrics**: Counter, Histogram, and Gauge instruments for ingestion
  pipeline observability (`meters::IngestionMeters`).
- **Traces**: Bridged from the `tracing` crate via `tracing-opentelemetry`,
  so existing `tracing::info_span!` calls automatically become OTel spans.
- **Exporters**: Pluggable backend selection — stdout for development,
  OTLP gRPC for production, no-op for tests (`exporters::ExporterKind`).

# Quick Start

```ignore
use atelier_telemetry::{TelemetryConfig, init_telemetry};

let config = TelemetryConfig::default();
let guard = init_telemetry(&config)?;

// … run workers …

drop(guard); // flushes and shuts down providers
```

# Crate Organisation

| Module | Purpose |
|---|---|
| `attributes` | Shared OTel attribute keys and builders |
| `meters` | Instrument definitions and recording helpers |
| `exporters` | Exporter selection and `MeterProvider` construction |

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_telemetry`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/).

## Structs

| Item | Summary |
| --- | --- |
| [`TelemetryConfig`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/struct.TelemetryConfig.html) | Top-level telemetry configuration, typically deserialized from TOML. |
| [`TelemetryGuard`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/struct.TelemetryGuard.html) | RAII guard that shuts down the OTel `MeterProvider` on drop. |

## Functions

| Item | Summary |
| --- | --- |
| [`ingestion_meters`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/fn.ingestion_meters.html) | Create `IngestionMeters` from the global meter provider. |
| [`init_telemetry`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/fn.init_telemetry.html) | Initialize the OpenTelemetry telemetry stack. |
