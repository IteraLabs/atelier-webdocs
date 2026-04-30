# API reference

Skeleton API reference for the **atelier-sdk** workspace at version
`0.0.10`. Each crate has its own subsection; every public item links
out to [docs.rs](https://docs.rs) for full signatures, source, and
trait implementations.

!!! note "Skeleton mode (Q5 of the design interview)"
    The beta of this docs site runs in **skeleton mode**: per-module
    pages list public items with one-line summaries and links to
    docs.rs, but do not inline full type signatures. The architecture
    is in place to upgrade to a full mirror later — only the
    rendering is minimal. See
    [About → Versioning](../../about.md#versioning) for why.

## Crates

| Crate                                         | Conceptual page                                             | API reference                                               | docs.rs                                                                                  |
|-----------------------------------------------|-------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`atelier-types`](atelier-types/index.md)     | [Schema layer](../types/index.md)                            | [Skeleton](atelier-types/index.md)                          | [docs.rs/atelier-types/0.0.10](https://docs.rs/atelier-types/0.0.10/atelier_types/)         |
| [`atelier-connect`](atelier-connect/index.md) | [Exchange clients & workers](../connect/index.md)            | [Skeleton](atelier-connect/index.md)                        | [docs.rs/atelier-connect/0.0.10](https://docs.rs/atelier-connect/0.0.10/atelier_connect/)   |
| [`atelier-io`](atelier-io/index.md)           | [Persistence](../io/index.md)                                | [Skeleton](atelier-io/index.md)                             | [docs.rs/atelier-io/0.0.10](https://docs.rs/atelier-io/0.0.10/atelier_io/)                 |
| [`atelier-data`](atelier-data/index.md)       | [Columnar (early)](../data/index.md)                         | [Skeleton](atelier-data/index.md)                           | [docs.rs/atelier-data/0.0.15](https://docs.rs/atelier-data/0.0.15/atelier_data/)           |
| [`atelier-quant`](atelier-quant/index.md)     | [Quantitative models](../quant/index.md)                     | [Skeleton](atelier-quant/index.md)                          | [docs.rs/atelier-quant/0.0.11](https://docs.rs/atelier-quant/0.0.11/atelier_quant/)         |
| [`atelier-telemetry`](atelier-telemetry/index.md) | [OpenTelemetry instrumentation](../telemetry/index.md) | [Skeleton](atelier-telemetry/index.md)                      | [docs.rs/atelier-telemetry/0.0.10](https://docs.rs/atelier-telemetry/0.0.10/atelier_telemetry/) |

`atelier-agent` is binary-only and therefore has no API reference.
See [Operations → atelier-agent](../../operations/agent.md) for its
operator reference (CLI flags, env vars, JWT contract).

## Regeneration workflow

Per Q6 of the design interview: API skeletons are **manually
regenerated** against a local SDK checkout. Run before each
docs-version cut:

```bash
make sdk-api SDK_PATH=../atelier-sdk
git diff docs/sdk/api/
git commit -am "docs(api): regenerate against atelier-sdk vX.Y.Z"
```

The script (`scripts/cargo_doc_to_md.py`) drives `cargo +nightly
rustdoc --output-format json` per crate, parses the JSON, and
emits per-module Markdown. It pins the rustdoc JSON
`format_version` and refuses to run against an unrecognized
schema — bump deliberately. See the [Cutover runbook](../../operations/cutover-runbook.md)
for the full pre-flight sequence.
