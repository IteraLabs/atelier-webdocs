# Manual — atelier-webdocs v0.1.0-beta

End-to-end operating manual for the docs site. Quick reference, not
a tutorial. For the design rationale see
`implementation-plan-webdocs-v0.0.1-beta-2.md`. For the production
cutover sequence see `docs/operations/cutover-runbook.md`.

---

## 1. Quick start

```bash
git clone git@github.com:IteraLabs/atelier-webdocs.git
cd atelier-webdocs
make install
make serve     # http://127.0.0.1:8000, live reload
```

That's the loop. Edit Markdown under `docs/`, save, refresh.

---

## 2. Daily commands

| Command                          | What it does                                                         |
|----------------------------------|----------------------------------------------------------------------|
| `make serve`                     | Live-reload dev server, strict mode                                   |
| `make build`                     | Strict static build into `./site` — the **gate**                      |
| `make lint`                      | Markdown style lint, no network                                       |
| `make linkcheck`                 | Anchor audit on built HTML, internal-only                             |
| `make linkcheck CHECK_EXTERN=1`  | Same plus external URL sweep (slow, network)                          |
| `make sdk-api SDK_PATH=../atelier-sdk` | Regenerate API skeleton from local SDK checkout                |
| `make version-deploy VERSION=0.1.0-beta` | Publish via mike to gh-pages                                  |
| `make docker-build TAG=0.1.0-beta` | Build the deploy container image                                   |
| `make docker-run`                | Build + run at `http://localhost:8080/atelier/docs/`                 |

Build is the gate. Lint and linkcheck are independent audits — neither
is a prerequisite of build.

---

## 3. File taxonomy

```
atelier-webdocs/
├── SDK_VERSION                         # canonical SDK version string
├── mkdocs.yml                          # site config — nav, theme, mike, validation
├── requirements.txt                    # runtime deps
├── requirements-dev.txt                # dev deps (lint, linkcheck)
├── Makefile                            # all daily commands
├── Dockerfile                          # 2-stage builder + nginx runtime
├── nginx.conf                          # serves /atelier/docs/ for parity
├── .pymarkdown.json                    # lint config (rule disables documented inline)
├── .github/workflows/{ci,deploy}.yml   # CI: PR build; deploy: tag → image + mike
├── docs/                               # content tree
│   ├── index.md                        # landing
│   ├── about.md                        # site narrative
│   ├── sdk/                            # conceptual SDK pages + API skeleton
│   ├── guides/                         # 3 flagship tutorials
│   ├── backend/                        # REST/WS/gRPC reference
│   ├── operations/                     # operator runbooks
│   └── _readme-drafts/                 # excluded; pointers to copy into atelier-sdk
├── overrides/partials/copyright.html   # footer renders SDK version from metadata
└── scripts/
    ├── cargo_doc_to_md.py              # rustdoc-JSON → Markdown skeleton
    ├── deploy-version.sh               # mike publish wrapper
    └── {serve,build}.sh                # convenience wrappers
```

---

## 4. Configuration knobs

Everything tunable lives in one of four places:

| File / variable                       | What it controls                                                      |
|---------------------------------------|-----------------------------------------------------------------------|
| `SDK_VERSION` (file)                  | SDK version surfaced in the page footer; drives `--sdk-version` for regen |
| `mkdocs.yml`                          | Nav, theme, validation strictness, mike integration, plugins          |
| `Makefile` vars (`SDK_PATH`, `DOCS_RS_VERSION`, `IMAGE`, `TAG`, `CHECK_EXTERN`) | Override on the CLI: `make foo SDK_PATH=…` |
| `.pymarkdown.json`                    | Markdown-lint rule overrides                                          |

Notable defaults:

- `DOCS_RS_VERSION=latest` — out-links use docs.rs's `/latest/` so they
  don't 404 when the local SDK is newer than what's published.
- `IMAGE=ghcr.io/iteralabs/atelier-webdocs`, `TAG=dev` — override on
  release builds.
- `CHECK_EXTERN=0` (implicit) — `make linkcheck` is internal-only by
  default; pass `CHECK_EXTERN=1` to audit external URLs.

---

## 5. Versioning model

Two independent axes:

| Axis                     | Where it's set        | What it represents                              |
|--------------------------|-----------------------|-------------------------------------------------|
| **Doc-site version**     | mike (gh-pages branch) | The docs themselves — structure, content, tutorials |
| **Documented SDK version** | `SDK_VERSION` file    | Which SDK release the API skeleton was extracted from |

A doc-site release does **not** require an SDK release, and vice versa.
The footer of every page reads "Documenting `atelier-sdk` vX.Y.Z" —
that's the SDK version. The version-selector dropdown in the header
shows mike's docs-site versions (`0.1.0-beta`, etc.).

---

## 6. SDK API regen flow

```bash
# 1. local atelier-sdk must be on a clean commit
cd ../atelier-sdk && git status

# 2. regenerate (writes to docs/sdk/api/, ~100 files)
cd ../atelier-webdocs
make sdk-api SDK_PATH=../atelier-sdk

# 3. review and commit
git diff docs/sdk/api/
git commit -am "docs(api): regenerate skeleton against atelier-sdk vX.Y.Z"
```

Requires Rust nightly locally. The script pins the rustdoc JSON
`format_version` and refuses unrecognised schemas — bump deliberately.

---

## 7. Release flow (cutting v0.1.x-beta or beyond)

```bash
# 0. confirm strict + lint + linkcheck pass
make build && make lint && make linkcheck

# 1. publish a new mike version (pushes to gh-pages)
./scripts/deploy-version.sh 0.1.0-beta

# 2. build + push the container image
make docker-build TAG=0.1.0-beta
docker push ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta

# 3. on the host that runs the Cloudflare Tunnel
docker pull ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta
docker stop atelier-webdocs && docker rm atelier-webdocs
docker run -d --name atelier-webdocs --restart unless-stopped \
  -p 8081:80 ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta
```

Patch deploys (no Tunnel changes): only steps 1–3.
First-time cutover (Tunnel reroute, webapp cleanup): see
`docs/operations/cutover-runbook.md`.

When ready to drop the `-beta` suffix:

```bash
mike alias --update-aliases 0.1.0-beta 0.1.0
mike set-default 0.1.0
```

---

## 8. Built artifacts

| Artifact                                  | Where it lands                         | Consumer            |
|-------------------------------------------|----------------------------------------|---------------------|
| Static HTML (`./site/`)                   | local, `make build`                    | `make linkcheck`, ad-hoc preview |
| `gh-pages` branch                         | git remote, after `mike deploy`        | mike's version selector + fallback hosting |
| Docker image                              | `ghcr.io/iteralabs/atelier-webdocs:<TAG>` | Cloudflare-Tunnel'd container |
| README pointer drafts                     | `docs/_readme-drafts/atelier-*.md`     | Copy into atelier-sdk after launch |

---

## 9. Public URL & routing

- Live URL: `https://www.iteralabs.xyz/atelier/docs/`
- Cloudflare Tunnel forwards `iteralabs.xyz/atelier/docs/*` to the
  docs container (port 80 by default, mapped to host 8081 in §7).
- nginx inside the container aliases `/atelier/docs/` to
  `/usr/share/nginx/docs/` and falls back to `index.html` for SPA-style
  deep links.
- `/healthz` returns `200 ok` for liveness probes.

---

## 10. When something breaks

| Symptom                                        | Likely cause / fix                                                             |
|------------------------------------------------|--------------------------------------------------------------------------------|
| `make build` fails on broken internal link     | Real: fix the ref or the page it points at                                      |
| `make build` fails on missing nav entry        | New page added but not wired into `mkdocs.yml`'s `nav:`                         |
| `make sdk-api` warns on rustdoc                | SDK source has bad intra-doc links — fix in `atelier-sdk`                       |
| `make linkcheck` reports docs.rs 404s          | SDK version skew — check `DOCS_RS_VERSION`; regen with `latest` if needed      |
| Footer shows old SDK version                   | `SDK_VERSION` file unchanged; bump it and rebuild                              |
| Mike dropdown empty in browser                 | No mike publish has run yet — `./scripts/deploy-version.sh 0.1.0-beta`          |
| Spanish output from linkchecker                | Locale leakage — `make linkcheck` already pins `LANG=C`; check shell overrides  |
| Lint complains about every page                | `.pymarkdown.json` missing or unreadable                                        |

---

## 11. What's deferred (post-beta)

- Full API mirror (currently skeleton + docs.rs link-out).
- Auto-generated `cargo doc` JSON pipeline (currently manual local regen).
- K8s migration (currently Cloudflare Tunnel + Docker container).
- atelier-agent Docker image documentation (image not yet published).
- README pointer replacement in atelier-sdk (drafts exist; copy-across is post-launch).
