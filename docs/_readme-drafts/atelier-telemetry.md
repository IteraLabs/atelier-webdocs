# atelier-telemetry

OpenTelemetry instrumentation for the Atelier SDK engine.
`TelemetryConfig` plus `init_telemetry` for setup; a fixed set of
pre-named meters (messages received, event latency, connection state,
sink queue depth) for the workers and sinks to call into.

## Documentation

- **Conceptual & usage:**
  [www.iteralabs.xyz/atelier/docs/sdk/telemetry/](https://www.iteralabs.xyz/atelier/docs/sdk/telemetry/)
- **API reference (docs.rs):**
  [docs.rs/atelier-telemetry](https://docs.rs/atelier-telemetry)

## Crate badges

[![Crates.io](https://img.shields.io/crates/v/atelier-telemetry.svg)](https://crates.io/crates/atelier-telemetry)
[![docs.rs](https://docs.rs/atelier-telemetry/badge.svg)](https://docs.rs/atelier-telemetry)

## License

Apache-2.0 — part of the [atelier-sdk](https://github.com/IteraLabs/atelier-sdk) workspace.
