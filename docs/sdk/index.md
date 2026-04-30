# SDK overview

The Atelier SDK is a Rust crate that provides the building blocks for
quantitative and machine-learning research experiments on the Atelier
platform: data collection workers, deterministic replay sessions,
strategy and evaluator interfaces, and the wire types shared with the
backend.

!!! note "Stub page"
    This page is a placeholder. Conceptual documentation — what the SDK
    is for, the mental model, the major traits — will land here as the
    SDK stabilises.

## Adding the SDK to a project

```toml
# Cargo.toml
[dependencies]
atelier-sdk = { git = "https://github.com/IteraLabs/atelier-sdk" }
```

A versioned release on crates.io is planned but not yet published.

## What's documented where

- **[API reference](api/index.md)** — auto-generated from the SDK's
  public Rust API by `scripts/cargo_doc_to_md.py`. Updated on each docs
  build that runs against a checkout of `atelier-sdk`.
- **[Backend reference](../backend/index.md)** — the wire contract the
  SDK speaks to. Read this if you're building a non-Rust client or
  debugging at the protocol level.
- **[Guides](../guides/index.md)** — task-oriented walkthroughs.

## Source

The crate lives at
[`IteraLabs/atelier-sdk`](https://github.com/IteraLabs/atelier-sdk).
File issues against the SDK in that repo; file documentation issues
against this repo (`atelier-webdocs`).
