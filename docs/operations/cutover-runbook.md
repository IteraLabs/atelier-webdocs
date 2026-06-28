# Cutover runbook — atomic swap

The procedure for moving `/atelier/docs/` from the webapp container's
embedded MkDocs build to the standalone `atelier-webdocs` container,
in one operation.

This is the **atomic-swap** strategy chosen on Q2 of the design
interview. There's a brief window during the cutover where the URL
might 502 if any step fails; rollback restores the previous state.

!!! info "Source of truth"
    This page is the operator-facing copy. The same procedure (with
    additional design context) lives in §6 of
    `implementation-plan-webdocs-v0.0.1-beta-2.md` at the repo root.
    If the two ever drift, **this page wins** for runtime
    operations.

## Before you start

You should have, all in one terminal session:

- A working clone of `atelier-webdocs` on the host that runs the
  Cloudflare-Tunnel'd containers.
- A working clone of `atelier-webapp` on the same host (you'll
  rebuild it without the docs-builder stage).
- A working clone of `atelier-sdk` (for the API regen step).
- Docker logged in to GHCR (`docker login ghcr.io`).
- Your Cloudflare Tunnel config file path memorized
  (`~/.cloudflared/config.yml` or wherever you keep it). Take a
  backup before editing.
- Read access to the webapp container's current logs so you can
  diff before/after.

If you don't have all of those, stop here. The cutover is fast but
unforgiving — you don't want to be debugging missing tools mid-swap.

## Pre-flight (≥ 24 hours before)

These steps don't affect production; they prepare the artifacts.

### 1. Regenerate the API skeleton authoritatively

The Phase-B9 skeleton committed in this repo was hand-derived from a
survey of the SDK source. Before going live, regenerate it from
nightly rustdoc against your real SDK checkout:

```bash
cd atelier-webdocs
make sdk-api SDK_PATH=../atelier-sdk
```

Review the diff under `docs/sdk/api/`. Common things to expect:

- New items appear if the SDK has gained surface since v0.0.10.
- Reordered tables (rustdoc's iteration order vs my survey's order).
- Slightly different one-line summaries (rustdoc's first sentence vs
  my survey's interpretation).

If the diff is mostly mechanical, commit it:

```bash
git add docs/sdk/api
git commit -m "docs(api): regenerate skeleton against atelier-sdk v0.0.10 (authoritative)"
```

If the diff reveals surprises (a module disappeared, a type renamed),
investigate before committing — it might be a sign that
`SDK_VERSION` is stale.

### 2. Local build + linkcheck

```bash
make build      # mkdocs build --strict
make linkcheck  # full HTML link sweep
```

Both must pass. Strict mode + the validation block catches orphan
files; linkcheck catches broken refs.

### 3. Publish the docs version via mike

```bash
./scripts/deploy-version.sh 0.1.0-beta
```

The script:

- refuses to run with a dirty git tree (releases must be reproducible),
- runs `mike deploy --update-aliases --push 0.1.0-beta latest`,
- runs `mike set-default --push latest`,
- prints the final `mike list`.

Result: the `gh-pages` branch (or your configured mike target) now
has a `0.1.0-beta/` subdirectory and a `latest` alias pointing at
it.

### 4. Build the Docker image

```bash
make docker-build IMAGE=ghcr.io/iteralabs/atelier-webdocs TAG=0.1.0-beta
docker push ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta
```

The Dockerfile is two stages: Python + mkdocs builder, then nginx.
The image is small (~50 MB) and serves at `/atelier/docs/` directly
from the baked HTML.

### 5. Pre-pull on the host

On the same host that runs the Cloudflare-Tunnel'd containers:

```bash
docker pull ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta
```

Pulling now means the cutover step won't pause on a 50 MB download
in the middle of the production swap.

## Cutover window (~10 minutes)

This is the section where production is briefly affected. Run it
when traffic to `/atelier/docs/` is low.

### 6. Tear down the webapp's docs-builder

In the `atelier-webapp` repo, on a new branch `chore/strip-docs-builder`:

- Delete stage 2 (`docs-builder`) from the `Dockerfile`. The block
  starts at `FROM python:3.12-slim AS docs-builder` and ends at the
  next `FROM` directive.
- Delete the `COPY --from=docs-builder /site /usr/share/nginx/docs`
  line in stage 3.
- In `deploy/nginx.conf`, delete the entire `^~ /atelier/docs/`
  location block and the `= /atelier/docs` redirect.
- Delete the entire `webdocs/` subdirectory (`mkdocs.yml`,
  `requirements.txt`, `docs/`).

```bash
cd ../atelier-webapp
git checkout -b chore/strip-docs-builder
# ... edits ...
git diff --stat
git commit -am "chore: remove docs-builder; docs now served by atelier-webdocs container"
```

Don't merge yet — push the branch and let CI confirm the build still
succeeds before merging.

### 7. Rebuild the webapp image

```bash
cd ../atelier-webapp
docker build -t ghcr.io/iteralabs/atelier-webapp:next .
docker push ghcr.io/iteralabs/atelier-webapp:next
```

You're explicitly tagging `:next` rather than `:latest` so the
running container isn't replaced until you flip the tag.

### 8. Atomic swap — the actual cutover

```bash
# Take a backup of the current Tunnel config.
cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.pre-cutover

# Edit the Tunnel ingress: replace the existing /atelier/docs/*
# mapping (which currently points at the webapp container's port)
# with one pointing at the new docs container's port (e.g. 8081).
$EDITOR ~/.cloudflared/config.yml

# Stop the old webapp container (which is currently serving docs).
docker stop atelier-webapp

# Pull the new webapp without docs.
docker pull ghcr.io/iteralabs/atelier-webapp:next

# Start the new docs container.
docker run -d \
  --name atelier-webdocs \
  --restart unless-stopped \
  -p 8081:80 \
  ghcr.io/iteralabs/atelier-webdocs:0.1.0-beta

# Start the new webapp container (without docs serving).
docker run -d \
  --name atelier-webapp \
  --restart unless-stopped \
  -p 8080:80 \
  ghcr.io/iteralabs/atelier-webapp:next

# Reload the Tunnel.
sudo systemctl restart cloudflared
# or, if running in foreground: cloudflared service restart
```

The 10-15 second window between `docker stop atelier-webapp` and
`systemctl restart cloudflared` is when both `/atelier/` and
`/atelier/docs/` will return 502. Plan accordingly.

### 9. Smoke tests

In sequence — each must succeed before moving to the next:

```bash
# Webapp itself works.
curl -fI https://www.iteralabs.xyz/atelier/

# Docs root works.
curl -fI https://www.iteralabs.xyz/atelier/docs/

# A deep page resolves (proves the alias + try_files chain).
curl -fI https://www.iteralabs.xyz/atelier/docs/sdk/architecture/

# Static assets cache correctly.
curl -fI https://www.iteralabs.xyz/atelier/docs/assets/javascripts/bundle.83f73b43.min.js
```

Then a browser check:

- Open `https://www.iteralabs.xyz/atelier/docs/`.
- Confirm the **version dropdown** in the top-right shows
  `0.1.0-beta (latest)`.
- Scroll to the page footer; confirm it reads
  *Documenting `atelier-sdk` v0.0.10*.
- Click into a few pages: SDK overview, Architecture (diagram should
  render), one tutorial, the API reference index.
- Open the search box; type "Hawkes"; verify hits.

If all of those work — the cutover is done.

## Rollback (if any step fails)

The 502 window is brief; the rollback window is even briefer
because the old containers and Tunnel config are still around.

```bash
# Stop the new containers.
docker stop atelier-webdocs atelier-webapp
docker rm   atelier-webdocs atelier-webapp

# Restore the pre-cutover Tunnel config.
cp ~/.cloudflared/config.yml.pre-cutover ~/.cloudflared/config.yml

# Restart the old webapp container.
docker run -d --name atelier-webapp \
  --restart unless-stopped -p 8080:80 \
  ghcr.io/iteralabs/atelier-webapp:latest  # the old tag

# Reload the Tunnel.
sudo systemctl restart cloudflared
```

Then file an issue against `atelier-webdocs` describing what failed
in the smoke-test step.

## Post-cutover (within a week)

### 10. Apply the README pointer drafts to atelier-sdk

The drafts live in `docs/_readme-drafts/`. Apply them to `atelier-sdk`:

```bash
cd atelier-sdk
cp ../atelier-webdocs/docs/_readme-drafts/atelier-sdk.md      README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-types.md    atelier-types/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-connect.md  atelier-connect/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-io.md       atelier-io/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-data.md     atelier-data/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-quant.md    atelier-quant/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-telemetry.md atelier-telemetry/README.md
cp ../atelier-webdocs/docs/_readme-drafts/atelier-agent.md    atelier-agent/README.md

git diff
git commit -am "docs: replace per-crate READMEs with pointers to atelier-webdocs"
```

### 11. Watch the docs site for a week

Every page that's promised gets clicked. Every tutorial gets at
least one cargo run. Every search query that gets entered, you
read in the access logs (or just `tail -f` the docs container's
nginx logs).

Anything that breaks → file an issue against `atelier-webdocs`,
fix on a branch, ship as v0.1.1-beta:

```bash
make sdk-api SDK_PATH=../atelier-sdk     # if SDK changed
git commit
./scripts/deploy-version.sh 0.1.1-beta
make docker-build TAG=0.1.1-beta
docker push ghcr.io/iteralabs/atelier-webdocs:0.1.1-beta
docker pull ghcr.io/iteralabs/atelier-webdocs:0.1.1-beta
docker stop atelier-webdocs && docker rm atelier-webdocs
docker run -d --name atelier-webdocs --restart unless-stopped -p 8081:80 \
  ghcr.io/iteralabs/atelier-webdocs:0.1.1-beta
```

(Patch deploys don't require Tunnel changes — same port, just a new
image.)

### 12. Drop the `-beta` when confident

When you're happy with the docs site as-is — typically after
a few patch releases — promote it:

```bash
mike alias --update-aliases 0.1.0-beta 0.1.0
mike set-default 0.1.0
mike retire 0.1.0-beta   # optional, keeps the dropdown clean
```

The bare `/atelier/docs/` URL will redirect to `0.1.0/` instead of
`0.1.0-beta/`. The `-beta` version still resolves at its own URL for
anyone who bookmarked it.
