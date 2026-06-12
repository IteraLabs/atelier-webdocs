# `atelier_telemetry::exporters`

Exporter configuration and construction.

Provides `ExporterKind` for selecting between OTLP (production) and
stdout (development) metric exporters, plus builder functions for
constructing the corresponding `MeterProvider`.

# Examples

```ignore
// Development: print metrics to stderr
let provider = build_meter_provider(ExporterKind::Stdout, Duration::from_secs(5))?;

// Production: push to OTLP collector
let provider = build_meter_provider(
    ExporterKind::Otlp { endpoint: "http://localhost:4317".into() },
    Duration::from_secs(2),
)?;
```

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_telemetry::exporters`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/exporters/).

## Enums

| Item | Summary |
| --- | --- |
| [`ExporterKind`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/exporters/enum.ExporterKind.html) | Which metrics exporter to use. |

## Functions

| Item | Summary |
| --- | --- |
| [`build_meter_provider`](https://docs.rs/atelier-telemetry/latest/atelier_telemetry/exporters/fn.build_meter_provider.html) | Build a `SdkMeterProvider` with the specified exporter and collection interval. |
