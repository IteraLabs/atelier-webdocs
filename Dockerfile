# ─────────────────────────────────────────────────────────────────────
#  atelier-webdocs — standalone docs container.
#
#  Stage 1 (`builder`):  python:3.12-slim + mkdocs/mike → static HTML.
#  Stage 2 (`runtime`):  nginx:1.27-alpine serving the build at
#                        /atelier/docs/  (subpath parity with prod).
#
#  Consumed by `atelier-infra`: build the image, point the existing
#  Cloudflare Tunnel route for /atelier/docs/* at this container's
#  port 80. No host-side toolchain required.
#
#  Build args
#  ──────────
#    DOCS_VERSION  — passed to mike if VERSIONED=1 (defaults to "dev")
#    VERSIONED     — "1" to publish via mike to a gh-pages-like branch
#                    inside the image, "0" to do a single mkdocs build.
#
#  Most local/CI builds use VERSIONED=0 for speed; release builds set
#  VERSIONED=1 so the version selector dropdown is populated.
# ─────────────────────────────────────────────────────────────────────

# ── Stage 1: build the site ──────────────────────────────────────────
FROM python:3.12-slim AS builder

# git is required so the git-revision-date-localized plugin can read
# commit timestamps for the "last updated" footer. No other system deps.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /webdocs

# Cache the pip layer when only docs content changes.
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the repo. The .dockerignore keeps node_modules,
# .venv, site/, and CI configs out.
COPY . .

# strict mode: orphan files, broken links, and unrecognised links fail
# the build. This is the same gate CI runs on every PR.
RUN mkdocs build --strict --site-dir /site

# ── Stage 2: serve via nginx ─────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Replace the stock default.conf with our /atelier/docs/ subpath config.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/atelier-docs.conf

COPY --from=builder /site /usr/share/nginx/docs

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
