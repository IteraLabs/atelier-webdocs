#!/usr/bin/env bash
# scripts/build.sh — convenience wrapper for `make build`.
#
# Produces a strict static build into ./site. Mirrors the command run
# by both the Dockerfile and CI, so a green local run = green CI run.

set -euo pipefail

cd "$(dirname "$0")/.."

MKDOCS="${MKDOCS:-mkdocs}"
exec "$MKDOCS" build --strict --site-dir site
