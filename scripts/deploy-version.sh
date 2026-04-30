#!/usr/bin/env bash
# scripts/deploy-version.sh — publish a new mike version of the docs.
#
# Usage:
#   ./scripts/deploy-version.sh 0.1.0-beta
#   ./scripts/deploy-version.sh 0.1.0 --no-push     # dry run, local only
#   ./scripts/deploy-version.sh 0.1.1 --skip-clean  # bypass clean-tree check
#
# What this does
# ──────────────
#   1. Verifies the working tree is clean (commits required for
#      reproducibility).  Override with --skip-clean if you really
#      mean to publish from a dirty checkout (don't, but it's there).
#   2. Sources SDK_VERSION and exports ATELIER_SDK_VERSION so the
#      footer partial in the published build reflects the SDK
#      version this docs version documents.
#   3. If `latest` already aliases another version, prompts before
#      reassigning it. (First-time publishes skip this.)
#   4. `mike deploy --update-aliases <VERSION> latest` publishes the
#      build to the gh-pages branch under /<VERSION>/ and updates
#      the `latest` alias.
#   5. `mike set-default latest` writes the redirect at /atelier/docs/
#      pointing at /atelier/docs/latest/.
#   6. Pushes the gh-pages branch (skipped with --no-push).
#
# Called by .github/workflows/deploy.yml on tag push, and runnable
# manually for hotfix releases.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <version> [--no-push] [--skip-clean]" >&2
    echo "" >&2
    echo "examples:" >&2
    echo "  $0 0.1.0-beta         # first beta publish" >&2
    echo "  $0 0.1.0              # promote beta to release" >&2
    echo "  $0 0.1.1 --no-push    # dry run; commit locally only" >&2
    exit 1
fi

VERSION="$1"
shift

PUSH_FLAG="--push"
SKIP_CLEAN=0
while (( "$#" )); do
    case "$1" in
        --no-push)    PUSH_FLAG=""; shift ;;
        --skip-clean) SKIP_CLEAN=1; shift ;;
        *) echo "unknown flag: $1" >&2; exit 1 ;;
    esac
done

cd "$(dirname "$0")/.."

# ── 1. clean-tree check ─────────────────────────────────────────
if [[ $SKIP_CLEAN -eq 0 && -n "$(git status --porcelain)" ]]; then
    echo "error: working tree is dirty; commit or stash before deploying." >&2
    echo "(or pass --skip-clean if you really mean it)" >&2
    git status --short >&2
    exit 1
fi

# ── 2. SDK_VERSION → ATELIER_SDK_VERSION env ────────────────────
if [[ ! -f SDK_VERSION ]]; then
    echo "error: SDK_VERSION file missing at repo root" >&2
    exit 1
fi
export ATELIER_SDK_VERSION
ATELIER_SDK_VERSION="$(cat SDK_VERSION | tr -d '[:space:]')"
echo "→ docs version:    $VERSION"
echo "→ SDK version:     $ATELIER_SDK_VERSION (from SDK_VERSION)"

MIKE="${MIKE:-mike}"

# ── 3. latest-alias guard ───────────────────────────────────────
# If `latest` already exists and points at something other than the
# version we're about to publish, prompt before clobbering. Skip
# entirely on first-time publishes where mike's gh-pages doesn't
# yet exist.
if "$MIKE" list 2>/dev/null | grep -E "^(.+) \[latest\]" >/dev/null 2>&1; then
    CURRENT_LATEST="$("$MIKE" list 2>/dev/null | grep -E '\[latest\]' | awk '{print $1}')"
    if [[ "$CURRENT_LATEST" != "$VERSION" ]]; then
        echo "" >&2
        echo "warning: 'latest' currently aliases '$CURRENT_LATEST'." >&2
        echo "         This run will reassign 'latest' → '$VERSION'." >&2
        if [[ -t 0 ]]; then
            read -rp "proceed? [y/N] " confirm
            [[ "$confirm" =~ ^[Yy]$ ]] || { echo "aborted." >&2; exit 1; }
        else
            echo "(non-interactive; proceeding)" >&2
        fi
    fi
fi

# ── 4. mike deploy ──────────────────────────────────────────────
echo "→ deploying version $VERSION as 'latest'..."
"$MIKE" deploy --update-aliases $PUSH_FLAG "$VERSION" latest

# ── 5. mike set-default ─────────────────────────────────────────
echo "→ setting 'latest' as the default version..."
"$MIKE" set-default $PUSH_FLAG latest

# ── 6. summary ──────────────────────────────────────────────────
echo ""
echo "→ done. Published versions:"
"$MIKE" list
