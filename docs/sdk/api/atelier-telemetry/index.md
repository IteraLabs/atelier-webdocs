# `atelier-telemetry` — API reference

Skeleton API reference for crate
[`atelier-telemetry`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/) at
version `0.0.10`.

!!! info "Preliminary skeleton"
    Hand-derived from the Phase-1 survey. Run
    `make sdk-api SDK_PATH=../atelier-sdk` before cutover to refresh.

## Top-level items

| Item                                                                                                          | What it is                                                                                  |
|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`TelemetryConfig`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/struct.TelemetryConfig.html)    | Deserializable config: exporter kind, endpoint, sampling, service name                       |
| [`TelemetryGuard`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/struct.TelemetryGuard.html)      | RAII guard returned by `init_telemetry`; flushes on drop                                     |
| [`init_telemetry`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/fn.init_telemetry.html)          | Sets up the global tracer / meter provider from a `TelemetryConfig`                         |
| [`ingestion_meters`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/fn.ingestion_meters.html)      | Factory returning an `IngestionMeters` instance                                             |

## Modules

### [`attributes`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/)

Attribute-key vocabulary plus helper functions that build attribute
sets for events, workers, and topic classifications.

| Constant         | Purpose                                          |
|------------------|--------------------------------------------------|
| `EXCHANGE`       | Attribute key for the exchange name              |
| `SYMBOL`         | Attribute key for the trading pair / symbol       |
| `MARKET_TYPE`    | Attribute key for spot / futures / etc.          |
| `WORKER_ID`      | Attribute key for the worker identifier          |
| `TOPIC`          | Attribute key for the event topic                |
| `SINK_NAME`      | Attribute key for the output sink name           |
| `TOPIC_CATEGORY` | Attribute key for the topic category             |

Helper functions: `topic_category()`, `event_attributes()`, `worker_attributes()`.

### [`exporters`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/exporters/)

| Item                       | What it is                                                          |
|----------------------------|---------------------------------------------------------------------|
| `ExporterKind`             | Enum: `Stdout`, `Otlp`, `None`                                      |
| `build_meter_provider`     | Factory for a meter-provider given an `ExporterKind` + endpoint     |

### [`meters`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/meters/)

The fixed-name metric vocabulary every worker and sink shares:

| Constant                  | Metric                                                                  |
|---------------------------|-------------------------------------------------------------------------|
| `MESSAGES_RECEIVED`       | Counter — events received                                               |
| `EVENT_LATENCY_MS`        | Histogram — milliseconds between event timestamp and ingestion          |
| `WORKER_CONNECTION_STATE` | Gauge — encoded connection state                                         |
| `SINK_QUEUE_DEPTH`        | Gauge — current backpressure depth                                       |
| `LATENCY_BUCKETS_MS`      | The histogram bucket boundaries used by `EVENT_LATENCY_MS`              |

Plus `IngestionMeters` (struct) and its 8 public methods, and the
free function `connection_state_code()`.

Full reference (docs.rs): <https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/>
