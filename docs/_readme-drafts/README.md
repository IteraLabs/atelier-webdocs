# SDK README pointer drafts

Excluded from the docs build (see `mkdocs.yml`'s `exclude_docs` block).
This directory is a **deliverable** for the post-launch step of the
cutover: replacing each `atelier-sdk/<crate>/README.md` with a short
pointer to the docs site, so the SDK repo's READMEs stop drifting from
the canonical content.

## How to apply

After the docs site is live and verified at
`https://www.iteralabs.xyz/atelier/docs/`, in the `atelier-sdk`
checkout:

```bash
# From the atelier-webdocs repo root:
cp docs/_readme-drafts/atelier-sdk.md      ../atelier-sdk/README.md
cp docs/_readme-drafts/atelier-types.md    ../atelier-sdk/atelier-types/README.md
cp docs/_readme-drafts/atelier-connect.md  ../atelier-sdk/atelier-connect/README.md
cp docs/_readme-drafts/atelier-io.md       ../atelier-sdk/atelier-io/README.md
cp docs/_readme-drafts/atelier-data.md     ../atelier-sdk/atelier-data/README.md
cp docs/_readme-drafts/atelier-quant.md    ../atelier-sdk/atelier-quant/README.md
cp docs/_readme-drafts/atelier-telemetry.md ../atelier-sdk/atelier-telemetry/README.md
cp docs/_readme-drafts/atelier-agent.md    ../atelier-sdk/atelier-agent/README.md
```

Then commit in `atelier-sdk` with a message like
`docs: replace per-crate READMEs with pointers to atelier-webdocs`.

## Why this is in `_readme-drafts/` not at the repo root

These files document atelier-sdk, not atelier-webdocs. Keeping them
inside `docs/` (and excluded from the build) means:

- they version with the docs they point at,
- review happens in the same PR that updates the canonical content,
- if a draft contains a broken link or stale phrasing, that's caught
  by the docs-site review process before the SDK repo sees it.
