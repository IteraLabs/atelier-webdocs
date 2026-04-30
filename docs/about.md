# About

Atelier is a quantitative and machine-learning research simulator
platform. The SDK is the Rust-native entry point: collect
microstructure data from cryptocurrency exchanges, replay it
deterministically, run custom strategies, evaluators, and learners
against it, and persist results to Parquet.

## Scope of these docs

The site is the canonical reference for the Atelier SDK and the
public contract of the surrounding platform services. It is
organized into:

- **SDK** — conceptual overviews of each workspace crate, an
  architecture page that walks the cross-crate data flow, and an API
  reference per crate.
- **Tutorials** — three task-oriented walkthroughs (Bybit → Parquet,
  multi-exchange sync, Hawkes on arrivals).
- **Backend** — the REST, WebSocket, and gRPC contract exposed by
  the Atelier backend that the SDK and dashboard speak to.
- **Operations** — the operator reference for `atelier-agent` (the
  binary-only crate) and the cutover runbook for this docs site.

What this site is **not**: the SDK's internal architecture decisions,
ADRs, or release notes — those live alongside the source in
[`atelier-sdk`](https://github.com/IteraLabs/atelier-sdk). The SDK
repo's per-crate READMEs are short pointers back to this site.

## Why a separate repo

The SDK is a Rust workspace. Mixing a Python docs build into it
would:

- Add a Python toolchain dependency for anyone hacking on the SDK.
- Bloat the workspace with `mkdocs.yml`, theme assets, CI for docs.
- Couple SDK release cadence to docs deploy cadence.

Keeping the docs here — in their own repo, deployed as a separate
container — means the SDK stays small and the docs ship on their
own schedule. The docs *reference* the SDK by link and by
auto-extracted API skeletons regenerated with `make sdk-api`.

## Versioning

Two version axes that move independently:

- **Doc-site version** (`0.1.0-beta`) — managed by
  [mike](https://github.com/jimporter/mike). Reflects changes to the
  *docs* (structure, content quality, tutorials, navigation). Each
  tagged release publishes its own subdirectory; the `latest` alias
  points at the most recent stable.
- **SDK version** documented (`0.0.10`) — read from the `SDK_VERSION`
  file at the repo root. Surfaced in every page footer
  ("*Documenting `atelier-sdk` v0.0.10*").

Decoupling them means an SDK patch release that doesn't change docs
content doesn't force a docs republish, and a docs improvement
doesn't force an SDK release. They reflect different things.

See [Operations → Cutover runbook](operations/cutover-runbook.md) for
the publish workflow.

## Contributing

The build, deploy, and contribution workflow is documented in
[`README.md`](https://github.com/IteraLabs/atelier-webdocs/blob/main/README.md)
and
[`CONTRIBUTING.md`](https://github.com/IteraLabs/atelier-webdocs/blob/main/CONTRIBUTING.md)
in the docs repo. In short: clone, `make install`, `make serve`,
edit Markdown, open a PR.

Strict mode is on; any new page must be in `nav` in `mkdocs.yml` or
the build fails. CI runs `mkdocs build --strict` plus a link check
on every PR.

## License

Documentation content and build configuration are Apache-2.0,
matching the SDK.
