---
description: Financial research infrastructure for collecting, replaying, and modelling crypto market microstructure — the Atelier SDK.
---

# Atelier SDK

**Financial research infrastructure for crypto market microstructure.** A Rust workspace for
collecting microstructure data from cryptocurrency exchanges, replaying it deterministically,
fitting quantitative models, and evaluating strategies — built by
[IteraLabs](https://github.com/IteraLabs).

## Start here

<div class="grid cards" markdown>

-   __Getting started__

    ---

    From `cargo new` to a Parquet file of live Bybit data in thirty lines of Rust.

    [Get started →](sdk/getting-started.md)

-   __Architecture__

    ---

    The cross-crate data flow, from WebSocket frames to fitted models, with diagrams.

    [Read the architecture →](sdk/architecture.md)

-   __Tutorials__

    ---

    Three end-to-end walkthroughs: single-exchange persistence, multi-exchange sync, Hawkes fitting.

    [Browse tutorials →](guides/index.md)

-   __Research__

    ---

    Dated, authored methodology notes — the reasoning behind the numbers, with reproducible code.

    [Read the research →](research/index.md)

</div>

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
SDK checkout — see [Platform → Operations](operations/index.md)).

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

- [Research](research/index.md) — methodology notes from the lab
- [Dataset catalog](datasets/index.md) — collected microstructure data + schema
- [Platform API](backend/index.md) — REST / WebSocket / gRPC contract
- [About this site](about.md) — scope, contribution, versioning
- [GitHub: atelier-sdk](https://github.com/IteraLabs/atelier-sdk)
- [GitHub: atelier-webdocs](https://github.com/IteraLabs/atelier-webdocs)
