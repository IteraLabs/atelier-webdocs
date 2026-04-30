# Atelier SDK

Documentation for the [Atelier SDK](https://github.com/IteraLabs/atelier-sdk),
a Rust workspace for building quantitative and machine-learning
research experiments on the Atelier platform — collect microstructure
data from cryptocurrency exchanges, replay it deterministically, fit
quantitative models, evaluate strategies.

The site is organized around four reading paths:

- **Just starting out?** Go to [Getting started](sdk/getting-started.md) — a
  thirty-line Rust walkthrough that gets you from `cargo new` to a
  Parquet file with live Bybit data in it.
- **Want the big picture?** [Architecture](sdk/architecture.md)
  walks the cross-crate story with a Mermaid data-flow diagram.
- **Want to do something specific?** [Tutorials](guides/index.md)
  has three flagship walkthroughs — single-exchange persistence,
  multi-exchange synchronized collection, and Hawkes-process fitting
  on real arrival data.
- **Looking up an API?** [API reference](sdk/api/index.md) is the
  exhaustive view, organized by crate, with links out to docs.rs for
  full type signatures.

## Where things live

| What                         | Where                                                                                                            |
|------------------------------|------------------------------------------------------------------------------------------------------------------|
| **SDK source code**          | [`IteraLabs/atelier-sdk`](https://github.com/IteraLabs/atelier-sdk) — Cargo workspace, 7 crates                  |
| **These docs**               | [`IteraLabs/atelier-webdocs`](https://github.com/IteraLabs/atelier-webdocs) — Markdown rendered by MkDocs Material |
| **This site (live)**         | [`www.iteralabs.xyz/atelier/docs/`](https://www.iteralabs.xyz/atelier/docs/) — served by an nginx container       |
| **Per-crate API references** | [`docs.rs/atelier-sdk`](https://docs.rs/atelier-sdk) and the 5 sibling crates — auto-published from crates.io     |

The docs are intentionally **not** in the SDK repo so the SDK can
stay a focused Rust workspace. Documentation references the SDK via
links and auto-extracted API skeletons (regenerated against a local
SDK checkout — see [Operations → Cutover runbook](operations/cutover-runbook.md)).

## Workspace shape

The Atelier SDK is a Cargo workspace of 6 published library crates
plus 1 binary:

| Crate                                                                  | What it is                                                                                  |
|------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`atelier-types`](sdk/types/index.md)                                  | Canonical schema (orderbook, trades, snapshots, exchange enums)                              |
| [`atelier-connect`](sdk/connect/index.md)                              | Exchange WebSocket clients, workers, synchronizers, output sinks                             |
| [`atelier-io`](sdk/io/index.md)                                        | Parquet / CSV / JSON persistence                                                             |
| [`atelier-data`](sdk/data/index.md)                                    | Arrow-backed columnar layer (early stage)                                                    |
| [`atelier-quant`](sdk/quant/index.md)                                  | Hawkes, Poisson, interarrival analysis                                                       |
| [`atelier-telemetry`](sdk/telemetry/index.md)                          | OpenTelemetry instrumentation                                                                |
| [`atelier-agent`](operations/agent.md) — **binary only**               | Remote-agent runner (no library API)                                                         |

The [Architecture page](sdk/architecture.md) walks how they fit
together.

## Quick links

- [Backend reference](backend/index.md) — REST / WebSocket / gRPC API contract
- [About this site](about.md) — scope, contribution, versioning
- [GitHub: atelier-sdk](https://github.com/IteraLabs/atelier-sdk)
- [GitHub: atelier-webdocs](https://github.com/IteraLabs/atelier-webdocs)
