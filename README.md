# atelier-webdocs

Source for the Atelier SDK documentation site.

- **Live:** [www.iteralabs.xyz/atelier/docs/](https://www.iteralabs.xyz/atelier/docs/)
- **Builder:** MkDocs + Material, with [mike](https://github.com/jimporter/mike) for versioned releases.
- **Deploy artifact:** an nginx container image consumed by the Cloudflare Tunnel host.
- **Documents:** `atelier-sdk` (the SDK version is read from the `SDK_VERSION` file at this repo root).
- **Scope:** SDK conceptual reference, three flagship tutorials, backend API contract, atelier-agent operator reference, and a skeleton API mirror that links out to docs.rs.

## Quick start

```bash
git clone git@github.com:IteraLabs/atelier-webdocs.git
cd atelier-webdocs
make install     # creates .venv, installs deps
make serve       # http://127.0.0.1:8000, live reload
```

`make serve` runs MkDocs in strict mode — broken links and orphan
files fail the dev server, not just CI. Edit Markdown under `docs/`,
save, refresh.

## Build architecture

Two stages, mirroring the production Dockerfile:

```
┌─ Stage 1: builder (python:3.12-slim)
│  ├─ pip install -r requirements.txt
│  └─ mkdocs build --strict --site-dir /site
│
└─ Stage 2: runtime (nginx:1.27-alpine)
   └─ COPY /site → /usr/share/nginx/docs
      └─ served by nginx.conf at /atelier/docs/
```

A single `docker build .` produces the deploy artifact. **No
host-side Rust toolchain is required** to build or deploy the docs —
the API skeleton is committed Markdown, regenerated separately
against a local SDK checkout (see below).

```bash
make docker-build              # build the image
make docker-run                # run at http://localhost:8080/atelier/docs/
```

## Repository layout

```
atelier-webdocs/
├── mkdocs.yml                    # site config (theme, nav, plugins, mike, validation)
├── SDK_VERSION                   # single source of truth for the documented SDK version
├── requirements.txt              # runtime deps (mkdocs, material, mike, plugins)
├── requirements-dev.txt          # linters + linkcheck
├── docs/
│   ├── index.md                  # landing
│   ├── about.md                  # site narrative
│   ├── sdk/
│   │   ├── index.md              # SDK overview
│   │   ├── getting-started.md
│   │   ├── architecture.md       # cross-crate Mermaid diagrams
│   │   ├── {types,connect,io,data,quant,telemetry}/index.md   # crate landings
│   │   └── api/
│   │       ├── index.md          # API reference index
│   │       └── atelier-{types,connect,io,data,quant,telemetry}/index.md
│   ├── backend/index.md          # REST/WebSocket/gRPC reference
│   ├── guides/                   # 3 flagship tutorials
│   ├── operations/
│   │   ├── agent.md              # atelier-agent operator reference
│   │   └── cutover-runbook.md
│   ├── _readme-drafts/           # excluded from build; pointer-style READMEs to copy into atelier-sdk after launch
│   └── stylesheets/extra.css
├── overrides/partials/copyright.html   # footer with SDK version
├── scripts/
│   ├── cargo_doc_to_md.py        # rustdoc-JSON → docs/sdk/api/*.md (skeleton mode)
│   ├── serve.sh / build.sh       # convenience wrappers around `make`
│   └── deploy-version.sh         # mike publish wrapper
├── Dockerfile                    # standalone build + nginx runtime
├── nginx.conf                    # serves /atelier/docs/ for parity
├── Makefile                      # install, serve, build, sdk-api, lint, etc.
├── implementation-plan-webdocs-v0.0.1-beta-2.md   # design + cutover plan
└── .github/workflows/
    ├── ci.yml                    # PR build + linkcheck
    └── deploy.yml                # main → :dev image; tag → versioned image + mike publish
```

## SDK_VERSION — single source of truth

The `SDK_VERSION` file at the repo root is read by:

- `scripts/cargo_doc_to_md.py` — uses it for docs.rs link-out URLs.
- `Makefile` — exports it as `ATELIER_SDK_VERSION` to mkdocs builds.
- `overrides/partials/copyright.html` — renders it in every page footer.

Changing the documented SDK version is a one-line edit:

```bash
echo "0.0.11" > SDK_VERSION
```

Then regenerate the API skeleton (next section) and rebuild.

## Versioned releases (mike)

The version selector dropdown in the site header is populated by
[mike](https://github.com/jimporter/mike). Each tagged release
publishes its own subdirectory:

```
/atelier/docs/0.1.0-beta/   # first beta release
/atelier/docs/0.1.0/        # first stable
/atelier/docs/0.1.1/        # patch
/atelier/docs/latest/       # alias for the most recent stable
```

To cut a release:

```bash
git tag v0.1.0-beta
git push origin v0.1.0-beta
# CI: deploy.yml builds the image and runs scripts/deploy-version.sh,
# which publishes 0.1.0-beta to gh-pages and points 'latest' at it.
```

Manually:

```bash
make version-deploy VERSION=0.1.0-beta
```

**Doc-site version is decoupled from SDK version.** The docs site
follows its own semver track that reflects changes to the docs
themselves (structure, content, tutorials). The SDK version
documented is whatever `SDK_VERSION` says, surfaced in the page
footer.

## Regenerating the SDK API skeleton

Skeleton API pages under `docs/sdk/api/` are committed Markdown,
generated from a local SDK checkout via:

```bash
make sdk-api SDK_PATH=../atelier-sdk
```

This invokes `scripts/cargo_doc_to_md.py`, which:

1. Runs `cargo +nightly rustdoc --output-format json` per
   crate (the 6 library crates).
2. Parses the (unstable) JSON output.
3. Emits per-module Markdown under `docs/sdk/api/<crate>/`.

Requires the **nightly** Rust toolchain — rustdoc's JSON format is
gated on `-Z unstable-options`. The script pins a minimum
`format_version` and refuses to run against an unrecognised payload.
Bump deliberately.

Pre-generating and committing means:

- the production Docker image doesn't need a Rust toolchain,
- the API surface is reviewable in PRs (git diff shows what changed),
- a flaky nightly doesn't block docs deploys.

## Linting, link-checking, strict mode

```bash
make build       # strict mode catches broken links + orphan files at build time
make linkcheck   # full HTML link sweep against ./site
make lint        # markdown linter + linkcheck
```

`strict: true` plus the `validation:` block in `mkdocs.yml` means
any markdown file in `docs/` that isn't wired into `nav` (or
explicitly excluded via `exclude_docs`) fails the build. Add new
pages to `nav` in the same PR.

`docs/_readme-drafts/` is excluded from the build via `exclude_docs:
_readme-drafts/` — it holds pointer-style README drafts to copy into
`atelier-sdk` post-launch, not site content.

## Cutover (going live for the first time)

The atomic-swap procedure for moving `/atelier/docs/` from the
webapp container to this standalone container is documented end to
end in
[`docs/operations/cutover-runbook.md`](docs/operations/cutover-runbook.md).

The same procedure (with additional design context) appears in §6
of [`implementation-plan-webdocs-v0.0.1-beta-2.md`](implementation-plan-webdocs-v0.0.1-beta-2.md)
at this repo root.

## Why a separate repo

The SDK is a Rust workspace. Mixing a Python docs build into it
would add a Python dependency for SDK contributors, bloat the
repo with theme assets and CI, and couple SDK release cadence to
docs deploy cadence. Keeping the docs here lets the SDK stay
small and lets docs ship on their own schedule.

## License

Documentation content and build configuration: Apache-2.0,
matching the SDK.

## Related repos

- [`atelier-sdk`](https://github.com/IteraLabs/atelier-sdk) — the Rust workspace this site documents.
- `atelier-webapp` — the Leptos dashboard previously hosting these docs.
- `atelier-backend` — the REST / WebSocket / gRPC services documented under `/backend`.
- `atelier-infra` — K8s manifests + Terraform for the platform; deferred for the docs beta.
