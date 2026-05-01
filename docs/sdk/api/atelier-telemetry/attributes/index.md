# `atelier_telemetry::attributes`

Shared OpenTelemetry attribute keys for the atelier-sdk engine.

These constants define the dimensional labels attached to every metric,
span, and log record.  Using shared constants ensures consistency across
all instrumentation points and prevents typo-induced cardinality explosions.

# Cardinality Guidelines

- **Low cardinality** (safe on metrics): `EXCHANGE`, `SYMBOL`, `MARKET_TYPE`,
  `WORKER_ID`, `TOPIC`, `SINK_NAME`.
- **High cardinality** (spans/logs only, never on metrics): trade IDs,
  update IDs, order timestamps, raw prices.

!!! info "Skeleton API reference"
    This page lists the public items in `atelier_telemetry::attributes`. For full
    signatures, source links, and trait implementations, see the
    [docs.rs page for this module](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/).

## Functions

| Item | Summary |
| --- | --- |
| [`event_attributes`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/fn.event_attributes.html) | Build the common per-event attribute set used on every counter/histogram observation. |
| [`topic_category`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/fn.topic_category.html) | Extract the topic category from a canonical topic name. |
| [`worker_attributes`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/fn.worker_attributes.html) | Build the per-worker attribute set used on gauges and worker-level metrics. |

## Constants

| Item | Summary |
| --- | --- |
| [`EXCHANGE`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.EXCHANGE.html) | Exchange identifier (e.g. |
| [`MARKET_TYPE`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.MARKET_TYPE.html) | Market type: `"spot"`, `"perpetual"`, or `"inverse"`. |
| [`SINK_NAME`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.SINK_NAME.html) | Output sink name (e.g. |
| [`SYMBOL`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.SYMBOL.html) | Trading pair / instrument symbol (e.g. |
| [`TOPIC`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.TOPIC.html) | Canonical topic name (e.g. |
| [`TOPIC_CATEGORY`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.TOPIC_CATEGORY.html) | Topic category for dashboard metric filtering. |
| [`WORKER_ID`](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/attributes/constant.WORKER_ID.html) | Unique worker identifier (e.g. |
