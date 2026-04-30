# `atelier-data` — API reference

Skeleton API reference for crate
[`atelier-data`](https://docs.rs/atelier-data/0.0.15/atelier_data/) at
version `0.0.15`. Note this crate's own version is independent of
the workspace marker `0.0.10`.

!!! info "Preliminary skeleton"
    Hand-derived from the Phase-1 survey. The crate is intentionally
    early-stage; the public surface is small. Run
    `make sdk-api SDK_PATH=../atelier-sdk` before cutover to refresh.

## Public surface

`atelier-data`'s `lib.rs` is currently 32 lines, mostly a roadmap
comment. The crate documents itself as the home for "Future
Arrow-backed columnar modules":

```rust
// Future Arrow-backed columnar modules will be added here.
// Example: #[cfg(feature = "arrow")] pub mod columnar;
```

What's exported today is mostly re-export of types and machinery
that overlap with [`atelier-connect`](../atelier-connect/index.md).
See the [`atelier-data` conceptual page](../../data/index.md) for
the planned shape and the consolidation roadmap.

| Module                                                                       | Notes                                                                       |
|------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`config`](https://docs.rs/atelier-data/0.0.15/atelier_data/config/)          | TOML configuration types (overlaps with atelier-connect's `config`)         |
| (rest of the surface)                                                         | _early-stage; expect significant churn between releases_                    |

## Roadmap excerpts

The crate's README lists a handful of items currently being worked
on; rather than enumerate them here, see the dedicated
[Roadmap section on the conceptual page](../../data/index.md#roadmap).

Full reference (docs.rs): <https://docs.rs/atelier-data/0.0.15/atelier_data/>
