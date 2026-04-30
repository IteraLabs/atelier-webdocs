# ─────────────────────────────────────────────────────────────────────
#  atelier-webdocs — developer task runner.
#
#  Conventions
#  ───────────
#  * `make install`        → set up local venv + deps
#  * `make serve`          → live-reload dev server at :8000
#  * `make build`          → strict static build into ./site
#  * `make sdk-api`        → regenerate docs/sdk/api/ from atelier-sdk
#  * `make version-deploy` → publish a new mike version
#  * `make docker-build`   → produce the deploy container image
#  * `make lint`           → run linters (markdown + linkcheck against ./site)
#  * `make clean`          → remove ./site
#
#  All Python commands run inside .venv/. If you prefer your own venv
#  manager, set VENV_BIN before invoking make: `VENV_BIN=/path/bin make serve`.
# ─────────────────────────────────────────────────────────────────────

VENV     ?= .venv
VENV_BIN ?= $(VENV)/bin
PY       ?= $(VENV_BIN)/python
PIP      ?= $(VENV_BIN)/pip
MKDOCS   ?= $(VENV_BIN)/mkdocs
MIKE     ?= $(VENV_BIN)/mike

# Path to the atelier-sdk checkout for `make sdk-api`. Override on the
# command line: `make sdk-api SDK_PATH=../atelier-sdk`.
SDK_PATH ?= ../atelier-sdk

# Library crates documented by `make sdk-api`. atelier-agent is binary
# only and gets a hand-written operator-reference page instead.
SDK_CRATES ?= atelier-types,atelier-connect,atelier-io,atelier-data,atelier-quant,atelier-telemetry

# Read SDK version from the SDK_VERSION file. Honoured by both the
# script (for docs.rs link-outs) and the build (for the page footer).
SDK_VERSION := $(shell cat SDK_VERSION 2>/dev/null || echo unknown)

# Container image coordinates for `make docker-build`.
IMAGE ?= ghcr.io/iteralabs/atelier-webdocs
TAG   ?= dev

.PHONY: install serve build strict sdk-api version-deploy version-list \
        docker-build docker-run lint linkcheck clean help

help:
	@echo "Targets:"
	@grep -E '^[a-zA-Z][a-zA-Z0-9_-]*:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  SDK_VERSION     $(SDK_VERSION) (from ./SDK_VERSION)"
	@echo "  SDK_PATH        $(SDK_PATH)"
	@echo "  SDK_CRATES      $(SDK_CRATES)"
	@echo "  IMAGE:TAG       $(IMAGE):$(TAG)"

install: $(VENV)/.installed ## Create venv and install runtime + dev deps.

$(VENV)/.installed: requirements.txt requirements-dev.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip wheel
	$(PIP) install -r requirements-dev.txt
	@touch $@

# ─── build / serve ───────────────────────────────────────────────────

# ATELIER_SDK_VERSION is consumed by mkdocs.yml's extra.atelier_sdk_version,
# which feeds the page footer via overrides/partials/copyright.html.
serve: install ## Live-reload dev server at http://127.0.0.1:8000.
	ATELIER_SDK_VERSION=$(SDK_VERSION) $(MKDOCS) serve --strict

build: install ## Strict static build into ./site.
	ATELIER_SDK_VERSION=$(SDK_VERSION) $(MKDOCS) build --strict

# Alias for clarity in CI logs.
strict: build

# ─── SDK API regen ───────────────────────────────────────────────────

sdk-api: install ## Regenerate docs/sdk/api/ from a local atelier-sdk checkout.
	@test -d "$(SDK_PATH)" || \
	  (echo "error: SDK_PATH=$(SDK_PATH) not a directory; pass SDK_PATH=..." && exit 1)
	@echo "regenerating API skeleton against atelier-sdk in $(SDK_PATH) (v$(SDK_VERSION))"
	$(PY) scripts/cargo_doc_to_md.py \
	    --sdk-path "$(SDK_PATH)" \
	    --crates "$(SDK_CRATES)" \
	    --sdk-version "$(SDK_VERSION)" \
	    --out docs/sdk/api

# ─── mike versioning ─────────────────────────────────────────────────

version-deploy: install ## Publish current main as a new mike version. Pass VERSION=0.1.0-beta.
	@test -n "$(VERSION)" || (echo "error: pass VERSION=<x.y.z> on the command line" && exit 1)
	ATELIER_SDK_VERSION=$(SDK_VERSION) ./scripts/deploy-version.sh "$(VERSION)"

version-list: install ## List all published mike versions.
	$(MIKE) list

# ─── docker ──────────────────────────────────────────────────────────

docker-build: ## Build the deploy container image.
	docker build \
	    --build-arg ATELIER_SDK_VERSION=$(SDK_VERSION) \
	    -t $(IMAGE):$(TAG) .

docker-run: docker-build ## Build and run the image at http://localhost:8080/atelier/docs/.
	docker run --rm -p 8080:80 $(IMAGE):$(TAG)

# ─── linting ─────────────────────────────────────────────────────────

lint: install linkcheck ## Run all linters.
	$(VENV_BIN)/pymarkdown --config .pymarkdown.json scan docs/ || true

linkcheck: build ## HTML link checker against the built ./site tree.
	$(VENV_BIN)/linkchecker --check-extern site/index.html || true

# ─── clean ───────────────────────────────────────────────────────────

clean: ## Remove build outputs.
	rm -rf site/
