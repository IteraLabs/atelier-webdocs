#!/usr/bin/env bash
# scripts/serve.sh — convenience wrapper for `make serve`.
#
# Useful when you don't have `make` installed (uncommon) or want to
# bypass the Makefile's venv management. Honors $MKDOCS if set.

set -euo pipefail

cd "$(dirname "$0")/.."

MKDOCS="${MKDOCS:-mkdocs}"
exec "$MKDOCS" serve --strict
