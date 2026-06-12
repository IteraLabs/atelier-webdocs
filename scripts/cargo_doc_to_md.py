#!/usr/bin/env python3
"""
cargo_doc_to_md.py — extract atelier-sdk's public API into Markdown skeletons.

This is the **beta / skeleton** renderer (Q5 of the design interview):

  * Per-module page = a Markdown table of (item, one-line summary,
    docs.rs link).
  * No signatures, no impl blocks, no field rendering — that's deferred
    to a future `--mode=full` upgrade. The architecture is in place;
    only the rendering is minimal.
  * Every linked-out URL points at docs.rs/<crate>/<sdk_version>/...
    The SDK version is read from the SDK_VERSION file at the repo root
    (overridable via --sdk-version) so all link-outs match the version
    documented in the page footer.

Pipeline (per crate)
────────────────────
1. Run `cargo +nightly rustdoc --lib -p <crate>` against the SDK
   workspace, asking rustdoc for its (unstable) JSON output:

       cargo +nightly rustdoc --lib -p <crate> -- \\
           -Z unstable-options --output-format json

   This produces `target/doc/<crate>.json` (the workspace's shared
   target/ directory).

2. Walk the JSON index, group public items by their owning module.

3. Emit `docs/sdk/api/<crate>/index.md` (crate-level overview) plus
   `docs/sdk/api/<crate>/<module>/index.md` for each module that has
   at least one public item.

4. Emit a per-crate top page that lists every module as a sub-link.

Why nightly
───────────
rustdoc's `--output-format json` is gated on `-Z unstable-options` and
is only available on the nightly toolchain. The schema is unstable
across nightly versions; this script is pinned to a minimum
`format_version` and refuses to run against a JSON payload it doesn't
recognise — bump deliberately.

Why pre-generate instead of build-time
──────────────────────────────────────
Per Q6: the docs site is built from committed Markdown. Production
Dockerfile only needs Python + nginx, no Rust toolchain. Pre-generating
and committing means:

  * docs builds are fast and deterministic
  * the API surface is reviewable in PRs (diff shows what changed)
  * a broken nightly doesn't break docs deploys

Usage
─────
    python scripts/cargo_doc_to_md.py \\
        --sdk-path /path/to/atelier-sdk \\
        --crates atelier-types,atelier-connect,atelier-io,atelier-data,atelier-quant,atelier-telemetry \\
        --out docs/sdk/api

Or via the Makefile:

    make sdk-api SDK_PATH=../atelier-sdk

Limitations (skeleton mode)
───────────────────────────
  * Type signatures are not rendered. Click through to docs.rs.
  * `impl` blocks and trait implementations are not enumerated.
  * Macro and proc-macro items are listed by name only.
  * Re-exports (`pub use`) appear as items in their canonical module.

Each of these is addressable when we upgrade to full-mirror mode.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Pinned rustdoc JSON schema version. Bump deliberately when nightly
# moves the format. Find the current value at the top of the JSON output
# under the `format_version` key.
EXPECTED_FORMAT_VERSION_MIN = 28

# Default crate set — the six library crates published by the SDK
# workspace. Override on the CLI with --crates to add or remove.
# atelier-agent is excluded (binary-only, no rustdoc JSON output).
DEFAULT_CRATES = (
    "atelier-types",
    "atelier-connect",
    "atelier-io",
    "atelier-data",
    "atelier-quant",
    "atelier-telemetry",
)


# ─── data model ────────────────────────────────────────────────────────


@dataclass
class Item:
    """A subset of the rustdoc-JSON `Item` type, just enough for skeleton render."""

    id: str
    name: str | None
    kind: str
    docs: str
    path: list[str]


# ─── rustdoc invocation ────────────────────────────────────────────────


def run_rustdoc(sdk_path: Path, crate: str) -> Path:
    """Invoke `cargo +nightly rustdoc -p <crate>`; return the JSON path."""
    if shutil.which("cargo") is None:
        sys.exit("error: `cargo` not found in PATH")

    cmd = [
        "cargo",
        "+nightly",
        "rustdoc",
        "--lib",
        "-p",
        crate,
        "--manifest-path",
        str(sdk_path / "Cargo.toml"),
        "--",
        "-Z",
        "unstable-options",
        "--output-format",
        "json",
    ]
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)

    # rustdoc replaces hyphens with underscores in output filenames.
    crate_underscore = crate.replace("-", "_")
    json_path = sdk_path / "target" / "doc" / f"{crate_underscore}.json"
    if not json_path.exists():
        sys.exit(f"error: rustdoc JSON not produced at {json_path}")
    return json_path


def load_rustdoc(json_path: Path) -> dict[str, Any]:
    payload = json.loads(json_path.read_text())
    fmt = payload.get("format_version")
    if fmt is None or fmt < EXPECTED_FORMAT_VERSION_MIN:
        sys.exit(
            f"error: unexpected rustdoc format_version {fmt!r} "
            f"(expected >= {EXPECTED_FORMAT_VERSION_MIN}). "
            "Check the script's pinned schema and bump deliberately."
        )
    return payload


# ─── walking the index ─────────────────────────────────────────────────


def collect_items(payload: dict[str, Any]) -> list[Item]:
    """Flatten the rustdoc index into Item dataclass list (public only)."""
    index = payload["index"]
    paths = payload["paths"]
    root_id = payload["root"]

    out: list[Item] = []
    for item_id, raw in index.items():
        vis = raw.get("visibility")
        if vis != "public" and item_id != root_id:
            continue

        kind = _kind_of(raw)
        if kind is None:
            continue

        path_info = paths.get(item_id)
        if path_info is None:
            continue

        out.append(
            Item(
                id=item_id,
                name=raw.get("name"),
                kind=kind,
                docs=raw.get("docs") or "",
                path=path_info["path"],
            )
        )
    return out


def _kind_of(raw: dict[str, Any]) -> str | None:
    inner = raw.get("inner")
    if not isinstance(inner, dict) or not inner:
        return raw.get("kind")
    if len(inner) == 1:
        return next(iter(inner))
    return raw.get("kind")


# ─── rendering ─────────────────────────────────────────────────────────

# Heading + URL-fragment shape used on docs.rs for each item kind.
# rustdoc's HTML uses `<kind>.<name>` anchors on the parent module page;
# this map keeps us link-honest.
DOCS_RS_KIND_PREFIX = {
    "struct": "struct",
    "enum": "enum",
    "trait": "trait",
    "function": "fn",
    "type_alias": "type",
    "constant": "constant",
    "static": "static",
    "macro": "macro",
}

KIND_HEADING = {
    "struct": "Structs",
    "enum": "Enums",
    "trait": "Traits",
    "function": "Functions",
    "type_alias": "Type aliases",
    "constant": "Constants",
    "static": "Statics",
    "macro": "Macros",
}


# ── Rust intra-doc link sanitiser ─────────────────────────────────────
#
# Rust doc comments can carry intra-doc links that look fine to rustdoc
# but blow up under mkdocs strict mode:
#
#   [`Foo`](crate::module::Bar)         ← Rust path target
#   [`Foo`](atelier_types::config::Bar) ← cross-crate Rust path
#   [`Foo`]                             ← unresolved bare reference
#
# mkdocs reads the `(...)` half as a relative URL and warns when it's
# unresolvable. We strip the link target but keep the visible label
# (the inline-code text) so the rendered Markdown still reads naturally.
#
# The patterns below match conservatively — only paths that look like
# Rust idioms (segments separated by `::`, or beginning with crate /
# self / super / std / atelier_*).
_RUST_PATH = (
    r"(?:crate|self|super|std|core|alloc|atelier_[a-z_]+)"
    r"(?:::[a-zA-Z_][a-zA-Z0-9_]*)+"
)
_RUST_LINK_RE = re.compile(
    rf"\[(`[^`]+`|[A-Za-z_][A-Za-z0-9_]*)\]\(\s*{_RUST_PATH}\s*\)"
)
_BARE_INTRA_RE = re.compile(r"\[(`[^`]+`)\](?!\()")


def neutralize_rust_doc_links(text: str) -> str:
    """Strip Rust intra-doc link targets, leaving the visible label.

    `[\`Foo\`](crate::bar::Baz)` becomes `\`Foo\``.
    `[\`Foo\`]` (bare) becomes `\`Foo\``.

    Plain Markdown links (`[text](http://…)`) are untouched because
    their URL doesn't match the Rust-path pattern.
    """
    text = _RUST_LINK_RE.sub(r"\1", text)
    text = _BARE_INTRA_RE.sub(r"\1", text)
    return text


def first_sentence(docs: str) -> str:
    """Extract the first sentence of a `///` doc comment for the table summary."""
    if not docs:
        return ""
    text = docs.strip().split("\n\n", 1)[0]
    # Take up to the first period that's followed by whitespace or end of string.
    for i, ch in enumerate(text):
        if ch == "." and (i + 1 == len(text) or text[i + 1].isspace()):
            return neutralize_rust_doc_links(
                text[: i + 1].replace("\n", " ").strip()
            )
    # No period found — return the whole first paragraph, trimmed.
    return neutralize_rust_doc_links(text.replace("\n", " ").strip()[:200])


def render_per_crate(
    crate: str,
    items: list[Item],
    out_dir: Path,
    sdk_version: str,
    docs_rs_version: str,
) -> list[str]:
    """Emit module pages for one crate. Return list of module path strings."""
    crate_underscore = crate.replace("-", "_")
    crate_dir = out_dir / crate
    crate_dir.mkdir(parents=True, exist_ok=True)

    # Group items by their owning module path (everything except the item's own name).
    by_module: dict[tuple[str, ...], list[Item]] = defaultdict(list)
    module_docs: dict[tuple[str, ...], str] = {}

    for it in items:
        if it.kind == "module":
            module_docs[tuple(it.path)] = it.docs
            continue
        module = tuple(it.path[:-1])
        by_module[module].append(it)

    written: list[str] = []
    for module_path in sorted(by_module):
        if not module_path:
            continue
        # Module path includes the crate name as the first segment; strip it
        # for the URL so the tree under docs/sdk/api/<crate>/ feels natural.
        rel_segments = module_path[1:]
        if rel_segments:
            page_path = crate_dir / Path(*rel_segments) / "index.md"
        else:
            # Crate root items live on the crate's index page.
            page_path = crate_dir / "index.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            _render_module_page(
                crate=crate,
                crate_underscore=crate_underscore,
                module_path=module_path,
                items=by_module[module_path],
                module_doc=module_docs.get(module_path, ""),
                docs_rs_version=docs_rs_version,
            )
        )
        written.append("/".join(rel_segments) if rel_segments else "")

    # If we haven't already written a crate-level index (no root items), do so now.
    crate_index = crate_dir / "index.md"
    if not crate_index.exists():
        crate_index.write_text(
            _render_crate_index(
                crate, crate_underscore, written, sdk_version, docs_rs_version
            )
        )
    return sorted(set(written))


def _render_module_page(
    *,
    crate: str,
    crate_underscore: str,
    module_path: tuple[str, ...],
    items: list[Item],
    module_doc: str,
    docs_rs_version: str,
) -> str:
    """One module = one Markdown page with a table per item-kind."""
    title_path = "::".join(module_path)
    docs_rs_module_url = (
        f"https://docs.rs/{crate}/{docs_rs_version}/{crate_underscore}/"
        + "/".join(module_path[1:])
        + ("/" if len(module_path) > 1 else "")
    )

    lines: list[str] = [
        f"# `{title_path}`",
        "",
    ]
    if module_doc.strip():
        lines.extend([neutralize_rust_doc_links(module_doc.strip()), ""])

    lines.extend(
        [
            f"!!! info \"Skeleton API reference\"",
            f"    This page lists the public items in `{title_path}`. For full",
            f"    signatures, source links, and trait implementations, see the",
            f"    [docs.rs page for this module]({docs_rs_module_url}).",
            "",
        ]
    )

    # Bucket items by kind for a stable, readable layout.
    buckets: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        buckets[it.kind].append(it)

    section_order = (
        "struct",
        "enum",
        "trait",
        "function",
        "type_alias",
        "constant",
        "static",
        "macro",
    )

    any_rendered = False
    for kind in section_order:
        bucket = sorted(buckets.get(kind, []), key=lambda x: x.name or "")
        if not bucket:
            continue
        any_rendered = True
        lines.append(f"## {KIND_HEADING[kind]}")
        lines.append("")
        lines.append("| Item | Summary |")
        lines.append("| --- | --- |")
        for it in bucket:
            anchor = f"{DOCS_RS_KIND_PREFIX[kind]}.{it.name}.html"
            link = f"{docs_rs_module_url}{anchor}"
            summary = first_sentence(it.docs).replace("|", r"\|")
            lines.append(f"| [`{it.name}`]({link}) | {summary} |")
        lines.append("")

    if not any_rendered:
        lines.append("_This module exposes no public items at this version._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_crate_index(
    crate: str,
    crate_underscore: str,
    modules: list[str],
    sdk_version: str,
    docs_rs_version: str,
) -> str:
    """Crate-level landing page: lists every module as a link."""
    docs_rs = f"https://docs.rs/{crate}/{docs_rs_version}/{crate_underscore}/"
    lines = [
        f"# `{crate}` — API reference",
        "",
        f"Skeleton API reference for crate [`{crate}`]({docs_rs}); "
        f"this page documents source at SDK version `{sdk_version}`. "
        "Out-links target the most recent published docs on docs.rs "
        "(see the README's docs-rs-version note for why). Each module "
        "page lists its public items with a one-line summary and a link "
        "to the corresponding entry on docs.rs for full signatures, "
        "source, and trait implementations.",
        "",
        "## Modules",
        "",
    ]
    if not modules:
        lines.append("_No public modules at this version._")
    else:
        for mod in modules:
            display = mod.replace("/", "::") if mod else "(crate root)"
            href = f"{mod}/index.md" if mod else "index.md"
            lines.append(f"- [`{crate_underscore}::{display}`]({href})")
    lines.extend(["", f"Full reference (docs.rs): <{docs_rs}>"])
    return "\n".join(lines) + "\n"


def render_top_index(
    crates: list[str], out_dir: Path, sdk_version: str, docs_rs_version: str
) -> None:
    """Rewrite docs/sdk/api/index.md with a list of all six (or N) crates."""
    lines = [
        "# API reference",
        "",
        f"Skeleton API reference for the **atelier-sdk v{sdk_version}** workspace.",
        f"Out-links target docs.rs `/{docs_rs_version}/` so they continue to "
        "resolve as the SDK iterates ahead of any single pinned version.",
        "Every public item has a row in its module's table with a one-line",
        "summary and a link to docs.rs for the full signature.",
        "",
        "## Crates",
        "",
    ]
    for crate in crates:
        lines.append(f"- [`{crate}`]({crate}/index.md)")
    lines.extend(
        [
            "",
            "!!! note \"Skeleton mode\"",
            "    The beta of this docs site links out to docs.rs for full type",
            "    signatures, source, and trait implementations. A future release",
            "    will inline the signatures here. The skeleton makes the surface",
            "    diffable in PRs and the architecture upgrade-ready.",
            "",
        ]
    )
    (out_dir / "index.md").write_text("\n".join(lines))


# ─── entry point ───────────────────────────────────────────────────────


def _read_sdk_version_file(repo_root: Path) -> str:
    """Read SDK_VERSION at the repo root; the canonical source for link-outs."""
    sv = repo_root / "SDK_VERSION"
    if not sv.exists():
        sys.exit(
            f"error: {sv} not found. Create it with the SDK version this docs "
            "build documents (e.g. `echo 0.0.10 > SDK_VERSION`)."
        )
    return sv.read_text().strip()


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--sdk-path", type=Path, required=True, help="Path to a local atelier-sdk checkout."
    )
    p.add_argument(
        "--crates",
        default=",".join(DEFAULT_CRATES),
        help="Comma-separated list of workspace crates to document.",
    )
    p.add_argument(
        "--out", type=Path, default=Path("docs/sdk/api"), help="Output directory under docs/."
    )
    p.add_argument(
        "--sdk-version",
        default=None,
        help="Override SDK_VERSION (otherwise read from SDK_VERSION at repo root).",
    )
    p.add_argument(
        "--docs-rs-version",
        default="latest",
        help=(
            "Version segment used in docs.rs out-links. Defaults to 'latest' "
            "to avoid 404s when the local SDK source is newer than the "
            "version pinned in SDK_VERSION (a common state during rapid "
            "iteration). Pass an explicit version (e.g. '0.0.10') if you "
            "want the link targets to match the documented version exactly."
        ),
    )
    p.add_argument(
        "--skip-rustdoc",
        action="store_true",
        help="Reuse existing target/doc/*.json instead of re-running cargo.",
    )
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    sdk_version = args.sdk_version or _read_sdk_version_file(repo_root)
    docs_rs_version = args.docs_rs_version
    crates = [c.strip() for c in args.crates.split(",") if c.strip()]

    args.out.mkdir(parents=True, exist_ok=True)
    print(
        f"sdk_version={sdk_version} docs_rs_version={docs_rs_version} crates={crates}",
        file=sys.stderr,
    )

    for crate in crates:
        crate_underscore = crate.replace("-", "_")
        if args.skip_rustdoc:
            json_path = args.sdk_path / "target" / "doc" / f"{crate_underscore}.json"
            if not json_path.exists():
                sys.exit(f"--skip-rustdoc set but {json_path} does not exist")
        else:
            json_path = run_rustdoc(args.sdk_path, crate)

        payload = load_rustdoc(json_path)
        items = collect_items(payload)
        modules = render_per_crate(
            crate, items, args.out, sdk_version, docs_rs_version
        )
        print(
            f"  {crate}: {len(items)} items across {len(modules)} modules",
            file=sys.stderr,
        )

    render_top_index(crates, args.out, sdk_version, docs_rs_version)
    print(f"wrote API skeleton for {len(crates)} crates under {args.out}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
