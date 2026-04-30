# Implementation Plan — atelier-webdocs v0.0.1-beta-2

**Status:** plan-of-record, awaiting "go" to begin Phase A
**Author:** synthesized from grill-me interview Q1–Q9
**Target deploy:** `www.iteralabs.xyz/atelier/docs/` (Cloudflare Tunnel, beta)
**Docs version label:** `0.1.0-beta` (mike)
**SDK version documented:** `atelier-sdk` v0.0.10
**Cutover model:** atomic swap, single operation
**Scope of this session:** modify only `atelier-webdocs`. All other repos are read-only; cross-repo changes are produced as drafts and executed by the user post-handover.

---

## 1. Decision summary

Resolved during the grill-me interview. Each row below is load-bearing — every implementation step traces back to one of these.

| #   | Topic                  | Decision                                                                                                                                                                |
|-----|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Q1  | Deploy target          | `www.iteralabs.xyz/atelier/docs/` via existing Cloudflare Tunnel; K8s deferred                                                                                          |
| Q2  | Cutover                | Atomic swap — webapp's docs-serving torn down and new docs container repointed in one operation                                                                          |
| Q3  | API reference shape    | Skeleton (item table + docs.rs link-out) for beta; full mirror deferred                                                                                                  |
| Q4  | Crate scope            | 6 library crates mirrored; `atelier-agent` documented as operator reference                                                                                              |
| Q5  | Script quality         | Lightweight skeleton renderer; architecture supports later upgrade                                                                                                       |
| Q6  | Regen workflow         | Manual local `make sdk-api`, output committed; production Dockerfile stays Python + nginx                                                                                |
| Q7  | Sourcing strategy      | Hybrid — lift tables/configs/diagrams; write fresh narrative                                                                                                             |
| Q7b | SDK READMEs            | Produce pointer-style draft READMEs inside `docs/_readme-drafts/`; user copies them into atelier-sdk after launch                                                        |
| Q8  | Tutorials              | 3 flagship: Bybit→Parquet, multi-exchange sync, Hawkes on arrivals; inline code; source SHA in frontmatter                                                               |
| Q9  | Versioning             | Doc-version decoupled from SDK-version. Ship `0.1.0-beta` via mike. Page footer renders SDK version from `SDK_VERSION` metadata file                                     |

---

## 2. Repository scope

| Repo                  | Writable in this session?                | Role in this plan                                                                                                                  |
|-----------------------|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `atelier-webdocs`     | **Yes** — all changes happen here        | Source of the docs site, container image, regen scripts, runbooks                                                                  |
| `atelier-webapp`      | No — read-only                           | Currently serves `/atelier/docs/`. Cutover requires the user to delete the docs-builder stage post-handover (steps spelled out below) |
| `atelier-sdk`         | No — read-only                           | Source of API skeleton + tutorial code + lifted README content. Pointer-style READMEs delivered as drafts inside `atelier-webdocs` for the user to copy across post-launch |
| `atelier-backend`     | No — read-only, untouched                | The existing `docs/backend/index.md` already documents this repo's wire contract; no changes needed                                |
| `atelier-infra`       | No — read-only, untouched in beta        | K8s migration is post-beta. No changes during the atomic swap                                                                      |
| Cloudflare Tunnel     | Lives outside repos on the user's machine | One ingress rule swap during atomic cutover; not touched by this session                                                           |

---

## 3. Files in `atelier-webdocs` — full inventory

Color codes: **MODIFY** (file exists, contents change), **CREATE** (new file), **DELETE** (file exists, removed), **KEEP** (no change in this phase).

### 3.1 Repo root

| Path                         | Action  | Notes                                                                                                  |
|------------------------------|---------|--------------------------------------------------------------------------------------------------------|
| `mkdocs.yml`                 | MODIFY  | New nav for 6-crate API ref tree, Operations section, Tutorials section, footer-override `custom_dir`. Keep `strict: true`, validation block, mike provider, all current plugins |
| `SDK_VERSION`                | CREATE  | Single line: `0.0.10`. Read by the script (for docs.rs links), the footer partial, and CI logs        |
| `requirements.txt`           | KEEP    | Already pins mkdocs, material, pymdown, mike, git-revision-date plugin                                 |
| `requirements-dev.txt`       | KEEP    | linkchecker + pymarkdown                                                                                |
| `Dockerfile`                 | KEEP    | Already python:3.12-slim → nginx:1.27-alpine; no Rust toolchain (per Q6 decision)                       |
| `nginx.conf`                 | KEEP    | Already serves `/atelier/docs/` for Tunnel parity                                                      |
| `.dockerignore`              | KEEP    | Already excludes `_readme-drafts/` candidate path — verify on second pass                               |
| `.gitignore`                 | KEEP    |                                                                                                         |
| `.editorconfig`              | KEEP    |                                                                                                         |
| `Makefile`                   | MODIFY  | `sdk-api` target loops over 6 crates; new `version-deploy` target documents the `0.1.0-beta` workflow   |
| `README.md`                  | MODIFY  | Update repo description, link to runbook, mention `SDK_VERSION` workflow, link to draft-READMEs        |
| `CONTRIBUTING.md`            | MODIFY  | Update API regen workflow (now multi-crate); document the lift-from-README convention                  |
| `implementation-plan-webdocs-v0.0.1-beta-2.md` | CREATE | This file. Lives at root; not part of `nav`, not built into the site                |

### 3.2 `docs/` — site content

```
docs/
├── index.md                              MODIFY — refreshed landing, points at new sections
├── about.md                              MODIFY — drop webapp Dockerfile leftovers, focus on docs scope
│
├── stylesheets/
│   └── extra.css                         KEEP
│
├── sdk/
│   ├── index.md                          MODIFY — SDK overview, links to subsections, "Documenting v0.0.10" callout
│   ├── getting-started.md                CREATE — Cargo.toml + 30-line Bybit MarketWorker walkthrough
│   ├── architecture.md                   CREATE — cross-crate story + 1 Mermaid diagram of the data-flow
│   │
│   ├── types/
│   │   └── index.md                      CREATE — atelier-types crate landing (lift+rewrite from its README)
│   ├── connect/
│   │   └── index.md                      CREATE — atelier-connect crate landing
│   ├── io/
│   │   └── index.md                      CREATE — atelier-io crate landing
│   ├── data/
│   │   └── index.md                      CREATE — atelier-data crate landing
│   ├── quant/
│   │   └── index.md                      CREATE — atelier-quant crate landing
│   ├── telemetry/
│   │   └── index.md                      CREATE — atelier-telemetry crate landing
│   │
│   └── api/
│       ├── index.md                      MODIFY — list 6 crate trees, "API reference index" landing
│       ├── atelier-types/
│       │   ├── index.md                  CREATE — generated, item table, docs.rs links
│       │   └── <module>/index.md         CREATE — one per public module (script-emitted)
│       ├── atelier-connect/              CREATE — same shape
│       ├── atelier-io/                   CREATE
│       ├── atelier-data/                 CREATE
│       ├── atelier-quant/                CREATE
│       └── atelier-telemetry/            CREATE
│
├── backend/
│   └── index.md                          KEEP — existing 541-line REST/WebSocket/gRPC reference
│
├── guides/
│   ├── index.md                          MODIFY — turn from stub into Tutorials section landing
│   ├── 01-bybit-to-parquet.md            CREATE — first flagship tutorial
│   ├── 02-multi-exchange-sync.md         CREATE — second flagship tutorial
│   └── 03-hawkes-on-arrivals.md          CREATE — third flagship tutorial
│
├── operations/
│   ├── index.md                          CREATE — Operations section landing
│   ├── agent.md                          CREATE — atelier-agent operator reference (CLI, env, JWT, deploy)
│   └── cutover-runbook.md                CREATE — atomic swap procedure (this is also referenced from README)
│
└── _readme-drafts/                       CREATE — out-of-nav, excluded via mkdocs validation; pure deliverables
    ├── README.md                         CREATE — explains the drafts and the post-launch copy procedure
    ├── atelier-sdk.md                    CREATE — facade README pointer
    ├── atelier-types.md                  CREATE
    ├── atelier-connect.md                CREATE
    ├── atelier-io.md                     CREATE
    ├── atelier-data.md                   CREATE
    ├── atelier-quant.md                  CREATE
    ├── atelier-telemetry.md              CREATE
    └── atelier-agent.md                  CREATE — operator-reference variant (binary, not lib)
```

**Notes on the `_readme-drafts/` directory.** The leading underscore signals "internal." This folder is:
- explicitly listed in `mkdocs.yml`'s `validation.omitted_files: ignore` exception list, so strict mode doesn't fail it for being orphaned
- excluded from the build (will not appear in the site nav or be rendered as HTML)
- included in `.dockerignore` so it doesn't bloat the runtime image
- **the deliverable artifact** for the SDK README pointer-replacement; the user copies these files into `atelier-sdk/<crate>/README.md` after the docs site is verified live

### 3.3 `overrides/` — Material theme partials

```
overrides/
├── .gitkeep                              DELETE — no longer needed once partials directory is real
└── partials/
    └── copyright.html                    CREATE — small partial: rendered at the bottom of every page; reads SDK_VERSION env var, outputs "Documenting atelier-sdk v0.0.10 · last built {date}"
```

### 3.4 `scripts/`

| Path                              | Action  | Notes                                                                                                                                |
|-----------------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------|
| `scripts/cargo_doc_to_md.py`      | MODIFY  | Rewrite in skeleton mode. Multi-crate (loop over 6 member crates). Output: per-module table (item, one-line summary, docs.rs link). Drops the lossy signature renderer; pinned to rustdoc JSON `format_version` (refuses to run against an unrecognised payload). ~150 lines down from 250 |
| `scripts/serve.sh`                | KEEP    |                                                                                                                                      |
| `scripts/build.sh`                | KEEP    |                                                                                                                                      |
| `scripts/deploy-version.sh`       | MODIFY  | Wire it for the `0.1.0-beta` first publish. Add a check that prints "publishing 0.1.0-beta as latest" and asks for confirmation if `latest` already exists |

### 3.5 `.github/workflows/`

| Path                              | Action  | Notes                                                                                                       |
|-----------------------------------|---------|-------------------------------------------------------------------------------------------------------------|
| `.github/workflows/ci.yml`        | KEEP    | Already runs `mkdocs build --strict` + linkcheck on PRs                                                     |
| `.github/workflows/deploy.yml`    | MODIFY  | Conditional: tag push triggers mike publish via `scripts/deploy-version.sh ${tag#v}`; main push pushes `:dev` image |

---

## 4. Files outside `atelier-webdocs` — what changes, who does it

These are **read-only in this session**. The user executes them post-handover, guided by `docs/operations/cutover-runbook.md`.

### 4.1 `atelier-webapp`

| Path                                | Action  | Why                                                                                              |
|-------------------------------------|---------|--------------------------------------------------------------------------------------------------|
| `Dockerfile`                        | MODIFY  | Delete stage 2 (`docs-builder`) and the `COPY --from=docs-builder` line in stage 3              |
| `deploy/nginx.conf`                 | MODIFY  | Delete the `^~ /atelier/docs/` location block and the `= /atelier/docs` redirect line           |
| `webdocs/`                          | DELETE  | Entire folder: `mkdocs.yml`, `requirements.txt`, `docs/{index,about,backend}.md`. All migrated  |

The atelier-webapp diff after these changes is small — about 20 deleted lines in the Dockerfile and nginx.conf, plus the entire `webdocs/` removal. The cutover runbook contains the exact sed/git commands.

### 4.2 `atelier-sdk`

| Path                                | Action  | Why                                                                                              |
|-------------------------------------|---------|--------------------------------------------------------------------------------------------------|
| `README.md`                         | MODIFY  | Replace with `docs/_readme-drafts/atelier-sdk.md` (10–15 line pointer + crates.io/docs.rs links) |
| `atelier-types/README.md`           | MODIFY  | Replace with `docs/_readme-drafts/atelier-types.md`                                              |
| `atelier-connect/README.md`         | MODIFY  | Replace with `docs/_readme-drafts/atelier-connect.md`                                            |
| `atelier-io/README.md`              | MODIFY  | Replace with `docs/_readme-drafts/atelier-io.md`                                                 |
| `atelier-data/README.md`            | MODIFY  | Replace with `docs/_readme-drafts/atelier-data.md`                                               |
| `atelier-quant/README.md`           | MODIFY  | Replace with `docs/_readme-drafts/atelier-quant.md`                                              |
| `atelier-telemetry/README.md`       | MODIFY  | (atelier-telemetry has no current README — this is a CREATE on the SDK side)                    |
| `atelier-agent/README.md`           | MODIFY/CREATE | Pointer to docs site's operator reference                                                  |

These are scheduled for **after** the docs site goes live, not during the atomic swap. The drafts in `docs/_readme-drafts/` are the canonical source.

### 4.3 `atelier-infra`, `atelier-backend`

No changes during the beta. Listed for completeness.

### 4.4 Cloudflare Tunnel (lives on the user's host machine, not in any repo)

| Action  | What                                                                                                                                  |
|---------|---------------------------------------------------------------------------------------------------------------------------------------|
| MODIFY  | One ingress rule update during the atomic swap window: `/atelier/docs/*` route now points at the new docs container's port (instead of the webapp container's port) |

The runbook spells out the exact `cloudflared` config edit and the `cloudflared service restart` (or equivalent) command.

---

## 5. Implementation phases

Three phases inside this session, then handover.

### Phase A — script + structure (architecture)

Goal: the *skeleton* of the new site is in place. Nav renders. Build passes strict mode. No new content yet.

| Step | Action                                                                                                                                                       | Files touched                                            |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| A1   | Create `SDK_VERSION` at repo root with value `0.0.10`                                                                                                         | `SDK_VERSION` (CREATE)                                   |
| A2   | Restructure `mkdocs.yml` nav: `Home / Getting started / SDK / Architecture / Tutorials / API reference / Operations / About`. Add `_readme-drafts/` to validation exclusions. Wire `custom_dir: overrides` (already done). | `mkdocs.yml` (MODIFY)                                    |
| A3   | Replace `overrides/.gitkeep` with `overrides/partials/copyright.html` that renders SDK version + last-built date                                              | `overrides/.gitkeep` (DELETE), `overrides/partials/copyright.html` (CREATE) |
| A4   | Rewrite `scripts/cargo_doc_to_md.py` in skeleton mode for multi-crate                                                                                          | `scripts/cargo_doc_to_md.py` (MODIFY)                    |
| A5   | Update `Makefile`'s `sdk-api` target to loop over 6 crates                                                                                                    | `Makefile` (MODIFY)                                      |
| A6   | Create empty/placeholder index pages so nav resolves: `docs/sdk/{getting-started, architecture}.md`, `docs/sdk/{types,connect,io,data,quant,telemetry}/index.md`, `docs/sdk/api/atelier-{type,connect,io,data,quant,telemetry}/index.md`, `docs/operations/{index, agent, cutover-runbook}.md`, `docs/guides/0{1,2,3}-*.md`, `docs/_readme-drafts/{README, atelier-*}.md` | (CREATE many)                                            |
| A7   | `mkdocs build --strict` passes. If a placeholder doesn't yet have an H1, the build will fail; iterate until clean.                                             | (verify only)                                            |

**End of Phase A:** site builds, has the right shape, all pages are stubs. URL-flippable in principle (just stubs everywhere).

### Phase B — content (the writing)

Goal: every page that's promised by Q3–Q9 has its real content. Tutorials run in concept (code is taken from `examples/`, which already runs). Lifted content is properly attributed and reorganized.

| Step | Action                                                                                                                                                       | Files touched                                            |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| B1   | Lift + rewrite per-crate landing pages from each member crate's README. Tables, configs, exchange matrices lifted verbatim; intros and "what this crate is for" rewritten. | `docs/sdk/{types,connect,io,data,quant,telemetry}/index.md` (MODIFY each) |
| B2   | Write `docs/sdk/architecture.md` from scratch with one Mermaid sequence/flow diagram of the data path: Source → Worker → Synchronizer → Sink → I/O → Quant. Cite atelier-data README as source for the pipeline narrative. | `docs/sdk/architecture.md` (MODIFY)                     |
| B3   | Write `docs/sdk/getting-started.md`: Cargo.toml snippet, the 30-line Bybit MarketWorker walk-through, run command, expected output. Lifted from `atelier-connect/examples/md_worker/md_worker_bybit.toml`. | `docs/sdk/getting-started.md` (MODIFY)                   |
| B4   | Tutorial 1 — `docs/guides/01-bybit-to-parquet.md`. Lift `atelier-connect/examples/md_worker/md_worker_bybit.{rs,toml}` inline. Frontmatter records source SHA at v0.0.10. Add prose framing, expected output, "next steps." | `docs/guides/01-bybit-to-parquet.md` (MODIFY)            |
| B5   | Tutorial 2 — `docs/guides/02-multi-exchange-sync.md`. Lift from `atelier-connect/examples/multi_sync/`. The longest tutorial; introduces `EventSynchronizer` mental model. | `docs/guides/02-multi-exchange-sync.md` (MODIFY)         |
| B6   | Tutorial 3 — `docs/guides/03-hawkes-on-arrivals.md`. Lift `atelier-quant/examples/eg_hawkes_ob_arrivals.rs`. Add interpretation of AIC/BIC and goodness-of-fit. | `docs/guides/03-hawkes-on-arrivals.md` (MODIFY)          |
| B7   | Operations / atelier-agent — `docs/operations/agent.md`. CLI flags from `atelier-agent/src/main.rs` clap derive (lift the help text), env vars (`GATEWAY_URL`, `JWT_SECRET`, etc.), JWT/Gateway protocol from main.rs preamble, deployment placeholder ("Docker image: TBD; will live at ghcr.io/iteralabs/atelier-agent once published"). | `docs/operations/agent.md` (MODIFY)                      |
| B8   | Operations / cutover runbook — `docs/operations/cutover-runbook.md`. The atomic swap procedure (see §6 of this plan; the runbook is its operator-facing form). | `docs/operations/cutover-runbook.md` (MODIFY)            |
| B9   | API skeleton pages — manually derive item lists per module from the Phase-1 SDK survey, since the sandbox lacks Rust nightly. Output is a "preliminary skeleton" the user will regenerate authoritatively before flipping the switch (`make sdk-api SDK_PATH=../atelier-sdk`). | `docs/sdk/api/atelier-*/...` (MODIFY many)                |
| B10  | SDK README pointer drafts — one per crate. Each is ~15 lines: 1-line description, "Full documentation: www.iteralabs.xyz/atelier/docs/sdk/<crate>/", crates.io badge, docs.rs badge, license. | `docs/_readme-drafts/atelier-*.md` (MODIFY each)         |
| B11  | Final pass on `docs/index.md` and `docs/about.md` — refresh nav references and remove webapp-Dockerfile leftovers. | `docs/index.md`, `docs/about.md` (MODIFY)                |

**End of Phase B:** the site has 75% coverage of major SDK functionality per the Q4–Q8 contract. Tutorials work. Architecture page reads as a coherent overview.

### Phase C — operationalization

Goal: ready for handover. The user can build the image, run the cutover, and have the URL live without further design questions.

| Step | Action                                                                                                                                                       | Files touched                                            |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| C1   | Update `README.md` with the new structure, the cutover runbook reference, the `SDK_VERSION` workflow                                                         | `README.md` (MODIFY)                                     |
| C2   | Update `CONTRIBUTING.md` for multi-crate API regen + the lift-from-README convention                                                                          | `CONTRIBUTING.md` (MODIFY)                               |
| C3   | Update `scripts/deploy-version.sh` for the `0.1.0-beta` first-publish, with a confirmation prompt if `latest` already exists                                  | `scripts/deploy-version.sh` (MODIFY)                     |
| C4   | Update `.github/workflows/deploy.yml` for the mike-publish-on-tag flow                                                                                        | `.github/workflows/deploy.yml` (MODIFY)                  |
| C5   | Final `mkdocs build --strict` + `linkchecker` against `site/`                                                                                                 | (verify only)                                            |
| C6   | Spot-check rendered pages: tutorials display code, footer shows SDK version, version dropdown placeholder is correctly empty (mike not yet run in sandbox)    | (verify only)                                            |

**End of Phase C:** session is done. Handover state below.

---

## 6. Cutover runbook (atomic swap)

Lives in the repo at `docs/operations/cutover-runbook.md`. Reproduced here so this plan is self-contained.

### Pre-flight (~24 hours before)

1. Run `make sdk-api SDK_PATH=../atelier-sdk` against your local atelier-sdk checkout. Review the diff against the manually-derived skeleton committed in Phase B9. Commit the authoritative regen.
2. Run `make build` and `make linkcheck` locally. Both must pass.
3. Bump the docs version: `./scripts/deploy-version.sh 0.1.0-beta` — this publishes to the `gh-pages` branch (or wherever mike is configured to push) and sets `latest` to point at `0.1.0-beta`.
4. Build the Docker image: `make docker-build IMAGE=ghcr.io/iteralabs/atelier-webdocs TAG=0.1.0-beta`. Push: `docker push ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta`.
5. On the host that runs the Cloudflare-Tunnel'd containers, pull the new image: `docker pull ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta`.

### Cutover window (~10 minutes)

6. **Tear down webapp's docs serving.** In the atelier-webapp repo, on a new branch `chore/strip-docs-builder`:
   - Remove stage 2 (`docs-builder`) from the Dockerfile, and the `COPY --from=docs-builder` line from stage 3.
   - Remove the `^~ /atelier/docs/` location block and the `= /atelier/docs` redirect from `deploy/nginx.conf`.
   - Delete the entire `webdocs/` directory.
   - Commit, push, merge.
7. **Rebuild the webapp image** without the docs stage. Push to its registry.
8. **Atomic swap on the host:**
   - `docker stop atelier-webapp` (or whatever the running container is called)
   - `docker pull ghcr.io/iteralabs/atelier-webapp:latest` (the new docs-less webapp)
   - Edit the Cloudflare Tunnel config (`~/.cloudflared/config.yml` or equivalent): replace the existing `/atelier/docs/*` ingress mapping with one pointing at the new docs container's port (default 80).
   - `docker run -d --name atelier-webdocs -p 8081:80 ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta`
   - `docker run -d --name atelier-webapp -p 8080:80 ghcr.io/iteralabs/atelier-webapp:latest`
   - `cloudflared service restart` (or `systemctl restart cloudflared`)
9. **Smoke test:**
   - `curl -I https://www.iteralabs.xyz/atelier/docs/` → expect `200`
   - `curl -I https://www.iteralabs.xyz/atelier/` → expect `200` (webapp still works)
   - `curl https://www.iteralabs.xyz/atelier/docs/sdk/architecture/` → expect `200` and a Mermaid diagram in the body
   - Open `https://www.iteralabs.xyz/atelier/docs/` in a browser; verify version dropdown shows `0.1.0-beta (latest)` and footer reads "Documenting atelier-sdk v0.0.10."

### Rollback (if any step fails)

10. Stop the new docs container: `docker stop atelier-webdocs`.
11. Revert the Cloudflare Tunnel config to its pre-swap state (`git stash pop` or restore the backup).
12. Restart cloudflared.
13. The previous webapp container is still running and still serves `/atelier/docs/` from its baked-in MkDocs build.
14. File a ticket against atelier-webdocs with the failure mode.

### Post-cutover (within a week)

15. Copy each `docs/_readme-drafts/atelier-*.md` into the corresponding `atelier-sdk/<crate>/README.md` and commit in the SDK repo.
16. Watch the docs site for one week of usage. Fix any feedback issues as v0.1.1-beta releases.
17. When confident, drop the `-beta` suffix and cut `0.1.0` (mike: `mike alias --update-aliases 0.1.0-beta 0.1.0; mike set-default 0.1.0`).

---

## 7. Acceptance criteria (definition of "done" for this session)

The session ends successfully when **all** of the following hold:

- [ ] `mkdocs build --strict` passes against the new structure with no warnings or errors
- [ ] All 6 crate landing pages exist with real content (tables lifted, narrative written)
- [ ] All 6 API skeleton trees exist with at least the top-level item table (manually derived from the Phase-1 survey)
- [ ] All 3 tutorials exist with inline code and source-SHA frontmatter
- [ ] `docs/operations/agent.md` and `docs/operations/cutover-runbook.md` exist with usable content
- [ ] `docs/_readme-drafts/atelier-*.md` exist (one per library crate plus atelier-sdk facade plus atelier-agent)
- [ ] `SDK_VERSION` file exists at root and is referenced by the footer partial
- [ ] `scripts/cargo_doc_to_md.py` is rewritten in skeleton mode and is executable (`./scripts/cargo_doc_to_md.py --help` works)
- [ ] `Makefile`, `README.md`, `CONTRIBUTING.md` are updated for the new workflow
- [ ] The implementation plan (this file) sits at the repo root

The session deliberately **does not** require:

- The `make sdk-api` regen against the actual SDK to have run (sandbox lacks Rust nightly; user does it)
- The mike `0.1.0-beta` publish to have run (sandbox lacks the gh-pages branch + push credentials)
- The Docker image to have been pushed to GHCR (CI does it on tag push, or user does it manually)
- The Cloudflare Tunnel reroute (lives on user's host machine)
- The atelier-webapp cleanup PR (read-only repo in this session)
- The atelier-sdk README replacement (read-only repo in this session)

These six items live entirely in the user's hands, guided by `docs/operations/cutover-runbook.md`.

---

## 8. Risks & known gaps

| Risk                                                                                                                  | Mitigation                                                                                                                                |
|-----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Manually-derived API skeleton (Phase B9) drifts from the actual SDK surface                                           | User runs `make sdk-api` before cutover; pre-flight step 1 of the runbook                                                                  |
| `mkdocs.yml` strict mode fails CI when a draft README ends up in `nav` accidentally                                    | `_readme-drafts/` listed in `validation` exclusions; CI catches it                                                                         |
| Cloudflare Tunnel restart causes a brief outage of the webapp during the atomic swap                                   | Accepted (per Q2); rollback path in step 10–13 of the runbook                                                                              |
| `cargo_doc_to_md.py` script breaks on a future nightly schema bump                                                     | Script pins `format_version`; refuses to run against unrecognised schema; bump deliberately                                                |
| Tutorial code drifts from the SDK examples after a v0.0.11+ release                                                    | Source SHA in tutorial frontmatter; future linter could check; for the beta, manual                                                       |
| `mike` first-publish failure leaves the site in an inconsistent state                                                  | Pre-flight step 3 runs the publish locally first; only step 8 in the cutover window touches production                                    |
| Footer partial reads `SDK_VERSION` at build time, not runtime — a stale value would silently misrepresent the docs    | Plan: assert in `scripts/build.sh` that the `SDK_VERSION` file is non-empty and matches a regex `\d+\.\d+\.\d+` before invoking mkdocs    |
| `atelier-data` is mostly unimplemented; its API skeleton will be near-empty, looking unfinished                        | Crate landing page explicitly notes "early-stage; the implemented surface is small. Roadmap below." Lift roadmap from atelier-data README |
| `atelier-agent` operator page mentions a Docker image that doesn't yet exist                                          | Page explicitly marks it as TBD: "Docker image: planned at `ghcr.io/iteralabs/atelier-agent` once the agent is published"                 |

---

## 9. What I'm asking for next

A single "go" to begin **Phase A**. After Phase A I'll surface the structure for a quick eyeball, then continue into B and C without further check-ins unless something forces a decision.

If anything in this plan looks wrong — particularly the file-by-file inventory in §3, the cutover steps in §6, or the acceptance criteria in §7 — flag it now. Once Phase A starts, changes get more expensive.
