# Contributing to atelier-webdocs

Thanks for considering a contribution. This repo is the sole source
for the Atelier SDK documentation site at
[www.iteralabs.xyz/atelier/docs/](https://www.iteralabs.xyz/atelier/docs/).

## Workflow

1. Fork or branch, then clone.
2. `make install && make serve` to spin up a live-reload preview at
   <http://127.0.0.1:8000>.
3. Edit Markdown under `docs/`. New pages must also be added to
   `nav:` in `mkdocs.yml` — the build is strict and orphan files
   fail CI.
4. Run `make build` locally to confirm strict mode passes.
5. Open a PR. CI runs `mkdocs build --strict` plus a link checker.

## Style guide

Concise, technical, accurate. Prefer:

- **One H1 per page.** MkDocs uses it as the page title.
- **Sentence case for headings.** "Worker lifecycle", not "Worker Lifecycle".
- **Examples that run.** Tutorial code is lifted from
  `atelier-sdk/{atelier-connect,atelier-quant}/examples/` — code
  that already compiles. Don't paraphrase from memory.
- **Tables for fields.** Especially for env vars, request/response
  fields, enum variants.
- **Admonitions for callouts.** `!!! note`, `!!! warning`,
  `!!! tip`, `!!! info`. Don't use bold-italic-emoji combos.
- **Relative links between docs pages**, absolute links to external
  resources. Avoid `/atelier/docs/...` — those break under mike's
  versioned subdirectories.

Avoid:

- Marketing prose. Reference docs are for people doing work.
- Long preambles before the first code block.
- Screenshots of code or config. Paste source instead.

## Strict mode and you

The site builds with `strict: true` plus the `validation:` block.
The build fails on:

- Broken internal links.
- Orphan files (markdown in `docs/` not in `nav`).
- Missing files referenced in `nav`.
- Unrecognised cross-references.

If you add a page, add it to `nav` in the same commit. If you
remove one, remove the `nav` entry too.

`docs/_readme-drafts/` is exempt — listed in `mkdocs.yml`'s
`exclude_docs` block. It's deliverable content for post-launch
README replacement in `atelier-sdk`, not site content.

## Adding a new section

For a new top-level section (say, "Cookbook"):

1. Create `docs/cookbook/index.md` with an H1 and a short overview.
2. Add to `mkdocs.yml`:

   ```yaml
   nav:
     ...
     - Cookbook:
         - Overview: cookbook/index.md
   ```

3. Add subpages as you go, each registered in `nav`.

## Versioning model

We use [mike](https://github.com/jimporter/mike). Conceptually:

| Branch / tag        | Where it lands                   | Audience                |
|---------------------|----------------------------------|-------------------------|
| `main` (untagged)   | not auto-published as a version  | preview via `make serve` |
| `dev` Docker tag    | built from main on every push    | staging deploys         |
| `vX.Y.Z` git tag    | `/atelier/docs/X.Y.Z/`           | end users               |
| `latest` alias      | `/atelier/docs/latest/`          | default landing         |

Tag pushes trigger `.github/workflows/deploy.yml`, which builds the
image and runs `scripts/deploy-version.sh` to update mike's
`gh-pages` branch and the `latest` alias.

For a hotfix on an old version, branch from the tag, fix, then run
`./scripts/deploy-version.sh X.Y.Z+1` *without* updating the
`latest` alias (the script's clean-tree check guards against
accidentally clobbering it; you can confirm interactively).

## SDK API skeleton — multi-crate regen

`docs/sdk/api/` is generated, not hand-written. The repo currently
ships a hand-derived skeleton (Phase B9 of the original
implementation plan). Before each docs-version cut, regenerate
authoritatively:

```bash
make sdk-api SDK_PATH=../atelier-sdk
git diff docs/sdk/api/
git add docs/sdk/api
git commit -m "docs(api): regenerate skeleton against atelier-sdk vX.Y.Z"
```

The regen runs `cargo +nightly rustdoc` against each of the 6
library crates (`atelier-types`, `-connect`, `-io`, `-data`,
`-quant`, `-telemetry`). `atelier-agent` is binary-only and has no
API skeleton — it's documented under
[Operations → atelier-agent](docs/operations/agent.md).

If your PR touches the SDK's public API, bump `SDK_VERSION` and
regenerate the skeleton in the same PR.

## SDK_VERSION discipline

The `SDK_VERSION` file at the repo root is the single source of
truth for the SDK version this docs build documents. Surfaced in:

- The page footer (every page).
- `docs.rs/<crate>/<sdk-version>/...` link-outs throughout the API
  skeleton.
- The `make sdk-api` regen step.

If you bump it, regenerate the skeleton. If you regenerate against
a different SDK checkout, bump it. Don't let the two drift.

## Lifting from per-crate SDK READMEs (Q7 of the design)

The SDK's per-crate READMEs are a starting point for the
conceptual pages under `docs/sdk/<crate>/index.md`. The convention:

- **Lift directly:** all tables (exchange matrix, type listings,
  file format support, sync mode comparison, env var reference),
  all code snippets, configuration TOML samples, directory diagrams.
- **Write fresh:** section landing intros, "why this exists" prose,
  cross-crate narrative, getting-started flow.

Tables and configs are data — the SDK author already verified them.
Prose intros need to be shaped for a docs-site reader, not a
GitHub-repo reader.

After a docs-site landing page is canonical for a crate, the SDK's
own README becomes a short pointer (see
`docs/_readme-drafts/atelier-{crate}.md`). Replacement of the
SDK's READMEs is a post-launch step, executed in `atelier-sdk` by
copying the drafts across.

## Filing issues

- **Documentation issues** (typos, missing pages, unclear explanations)
  → file in this repo (`atelier-webdocs`).
- **SDK bugs / API behaviour** → file in
  [`atelier-sdk`](https://github.com/IteraLabs/atelier-sdk).
- **Backend API behaviour** → file against the backend repo.

## Code of conduct

Be useful and kind. Disagreements are welcome; personal attacks
aren't.
