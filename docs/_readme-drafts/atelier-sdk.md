# atelier-sdk

Rust SDK for the Atelier quantitative & ML research simulator —
collect microstructure data from cryptocurrency exchanges, replay it
deterministically, fit quantitative models, evaluate strategies.

## Documentation

**[www.iteralabs.xyz/atelier/docs/](https://www.iteralabs.xyz/atelier/docs/)**
is the canonical reference. Quick links:

- [Getting started](https://www.iteralabs.xyz/atelier/docs/getting-started/)
- [Architecture overview](https://www.iteralabs.xyz/atelier/docs/architecture/)
- [Tutorials](https://www.iteralabs.xyz/atelier/docs/guides/)
- [Full API reference](https://www.iteralabs.xyz/atelier/docs/api/) (and on [docs.rs](https://docs.rs/atelier-sdk))

## Workspace

This repository is a Cargo workspace. The published library crates are:

| Crate                | What it is                                                                                  |
|----------------------|---------------------------------------------------------------------------------------------|
| [`atelier-types`](https://crates.io/crates/atelier-types)         | Canonical schema (orderbook, trades, snapshots, exchange enums)        |
| [`atelier-connect`](https://crates.io/crates/atelier-connect)     | Exchange WebSocket clients, workers, synchronizers, output sinks       |
| [`atelier-io`](https://crates.io/crates/atelier-io)               | Parquet / CSV / JSON persistence                                       |
| [`atelier-data`](https://crates.io/crates/atelier-data)           | Arrow-backed columnar layer (early stage)                              |
| [`atelier-quant`](https://crates.io/crates/atelier-quant)         | Hawkes, Poisson, interarrival analysis                                 |
| [`atelier-telemetry`](https://crates.io/crates/atelier-telemetry) | OpenTelemetry instrumentation                                          |

Plus `atelier-agent`, a binary-only crate (the remote-agent runner — see
the [operator reference](https://www.iteralabs.xyz/atelier/docs/operations/agent/)).

## License

Apache-2.0
