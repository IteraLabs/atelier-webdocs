# webdocs-content-beta — Atelier docs uplift

> **Purpose.** This is the working specification for elevating **atelier-webdocs** (the
> MkDocs Material site documenting the Atelier SDK) from a competent reference manual into a
> **research-grade laboratory presence**, benchmarked against Citadel Securities, Jane
> Street, Jump / Firedancer, Chaos Labs, Helius, and Solana.
>
> **Status.** Planning document. Nothing in the live site is changed by this file. Each
> pillar is specified here first, then implemented in a later, separately-reviewed pass.
>
> **Pillars** (this doc grows one section at a time):
> - **Pillar 0 — Identity** — ✅ implemented on `docs/content-beta`
> - **Pillar 1 — Research surface** — ✅ implemented on `docs/content-beta` (seed article)
> - **Pillar 2 — Information architecture** — ✅ implemented on `docs/content-beta`
> - **Pillar 3 — Content inclusion** — ✅ implemented (datasets + methodology; benchmarks deferred)
> - Pillar 4 — Live / data surfaces *(later)*

---

# Pillar 0 — Identity

> **Status — ✅ implemented on `docs/content-beta` (2026-06-16).** Build green
> (`mkdocs build --no-strict`). Verified live: dark default, azure accent (zero indigo),
> Space Grotesk / DM Sans / JetBrains Mono, IteraLabs header mark + favicon, branded code +
> admonitions, Mermaid in brand colours, light-mode parity, brand page. Header logo set from
> `media/iteralabs_logo.png`; favicon + apple-touch regenerated from that same file.

**Goal:** make the docs site a visually identical sibling of `atelier-webapp` and read,
at a glance, as a deliberate lab — not a stock Material template. Scope is brand, palette,
typography, logo/favicon/OG, theme chrome, and branded figures. Landing-page redesign and
header hero are **out of scope** (Pillar 2+).

## 0.0 Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Brand accent | **Azure `#3DA9E8`** (from the webapp). Remove Material's stock indigo. |
| 2 | Default theme | **Dark-first** (`slate`, canvas `#151920`); light is a toggle. |
| 3 | Header logo | **IteraLabs company mark** leads (the *lab* is the identity). **Atelier** is the documented *product* — it stays in the site title and inline where the SDK is named. |
| 4 | Typography | **Space Grotesk** headings · **DM Sans** body · **JetBrains Mono** code. |

## 0.1 The bar — identity moves these labs share

The recurring, transferable identity moves from the reference set, with how achievable each
is in MkDocs Material:

| Move | Exemplified by | Material achievability |
|---|---|---|
| Deep-dark default, near-black canvas | Jump, Chaos, Solana | Easy — palette order |
| Near-monochrome base + **one** disciplined accent | Helius, Jane St, Citadel | Easy — CSS vars |
| One accent across *all* interactive states (no color noise) | Helius, Jump, Chaos | Easy |
| Display face for headings, mono elevated for code | Jane St, Solana | Medium — CSS heading rule |
| Generous whitespace / restraint / ~70ch measure | Jane St, Helius, Jump | Medium |
| Code **and** charts/diagrams as *branded* first-class elements | Solana, Chaos | Medium |
| Explicit logo clearspace + min-size rule | Helius (published kit) | Medium — doc + CSS |
| Branded favicon + OG/social cards | all | Easy — `social` plugin |
| Sparse, high-contrast, consistent diagram language | Jump, Solana | Medium — Mermaid theme |
| Light option, but dark is the identity | all | Easy |

> The point of leverage: **Atelier's own webapp already made every one of these decisions.**
> The docs simply never inherited them.

## 0.2 What we already HAVE  *(verified in-repo)*

### A complete design-token system — currently only in the webapp
`atelier-webapp/style/tailwind.css` (2,956 lines) defines a Catppuccin-flavored token
system. **Dark is the default (on `:root`); light overrides via a `.theme-light` class.**
Verified values:

| Token | Dark (`:root`) | Light (`.theme-light`) | Role |
|---|---|---|---|
| `--c-base` | `#151920` | `#fafbfd` | canvas |
| `--c-base-card` | `#1a1e24` | `#f1f2f6` | panels |
| `--c-base-elevated` | `#282d36` | `#e8eaef` | wells |
| `--c-accent` / `--c-live` | `#3DA9E8` | `#3DA9E8` | **azure — brand accent** |
| `--c-accent-text` | `#c2c9d6` | `#4a5568` | labels / nav |
| `--c-text` | `#8e95a4` | `#4a5264` | secondary text |
| `--c-rosewater` (primary text) | `#b4bdd0` | `#1a1e24` | primary text |
| `--c-highlight1` (tertiary) | `#586074` | `#8890a0` | muted UI |
| `--c-green`/`--c-red`/`--c-yellow`/`--c-blue` | `#34b872`/`#e05470`/`#daa030`/`#4a90d4` | dimmed variants | signal colors |
| `--c-plot-1..6` | azure/green/gold/rose/violet/blue | light variants | chart palette |
| `--c-plot-grid/axis/label/crosshair` | defined | defined | chart furniture |
| `--radius-sm..xl` | 4 / 8 / 12 / 16px | — | radii |
| motion | `pulseDot` 2s · `heartbeat` 1.5s · durations 120/200/400ms · ease `cubic-bezier(0.16,1,0.3,1)` | — | live-data feel |

**Type stack (webapp):** Space Grotesk (300–700) · DM Sans (300–600 + italic) · JetBrains
Mono (300–700), via Google Fonts.

### Brand assets (raster) that already exist
- **IteraLabs (company):** `media/IteraLabs_single_logo*.png` (≤2000²), `media/IteraLabs_Banner*.png` (1584×396).
- **Atelier (product):** `media/atelier_logo.png` + `media/atelier_logo_grey.png` (2000² color + mono), `atelier-sdk/assets/images/atelier_banner.png` (1280×640).
- App mark: `atelier-webapp/images/Official_Logo.png` (2000²), `official-logo.png` (256²).
- Favicons: `atelier-sdk/assets/favicon.ico` (16/32), `…/site/assets/images/favicon.png` (48²).
- Product screenshots: `atelier-webapp/images/web-1..5.png` (860²) — candidate hero/OG imagery.

### Theming surface already wired
`mkdocs.yml` has `custom_dir: overrides`, a working light/dark palette split, `extra_css`,
and a footer partial (`overrides/partials/copyright.html`). The hooks exist; they're just
under-used — `extra.css` is ~3 cosmetic tweaks and the palette is stock `primary: black` /
`accent: indigo`.

## 0.3 What's MISSING

**Brand continuity**
- Docs ship Material's **indigo** accent — directly contradicting the real brand accent (azure `#3DA9E8`). Docs and webapp look like two different companies.
- No token bridge in the docs (`--c-*` / `--radius-*` / motion absent).
- Docs use **Inter**, not the brand display stack.

**Assets**
- **No vector (SVG) logo anywhere** — marks are raster PNG only.
- **No OG / social card**; `social` plugin off → shared links render generic.
- Thin favicon coverage: no `favicon.svg`, no `apple-touch-icon` (180²), no `site.webmanifest`.
- No light-mode logo variant; no horizontal mark+wordmark lockup.

**Governance**
- **No brand/style reference** in the tree — no palette spec, type scale, or logo-usage/clearspace rules. The tokens are the only de-facto source of truth, and they're undocumented.

**Branded figures**
- Mermaid renders in default theme colors.
- No Plotly layout template bound to `--c-plot-*` (needed the moment research charts land).

## 0.4 What to DERIVE / replicate (reference labs → Atelier)

| Lab signal | Replicate as |
|---|---|
| Helius — one accent + monochrome + explicit clearspace | Azure `#3DA9E8` as the *single* accent; near-monochrome neutrals from `--c-base*`; publish a clearspace + min-size rule. |
| Jump / Chaos / Solana — deep-dark default | Dark (`slate`) is the default palette; canvas `#151920`; light is a toggle. |
| Jane Street — deliberate type, restraint, whitespace | Space Grotesk headings / DM Sans body; ~70ch measure; generous vertical rhythm. |
| Citadel — austere, no visual noise | Drop indigo; one accent for *all* interactive states; flat (no gradients / heavy shadows). |
| Solana / Chaos — figures as brand | Brand-theme Mermaid + a Plotly template from `--c-plot-*` so every figure is recognizably Atelier's. |
| All — branded favicon + OG | Favicon set + auto OG cards via the `social` plugin, brand fonts/colors. |
| Helius / Solana docs — code-forward | Accent-bordered code blocks, JetBrains Mono, code titles + line-highlight (extensions already enabled in `mkdocs.yml`). |

**Net direction:** azure-accented · deep-dark-default · monospace-forward · restrained.

## 0.5 What to BUILD — deliverables

> Implemented in a later, separately-reviewed pass. Listed here with target paths so the
> build is unambiguous.

**B1 — Brand assets** *(IteraLabs mark = header identity; Atelier = product)*
- Vectorize the **IteraLabs** mark → `docs/assets/logo.svg` (+ light/dark variants) = the **header logo**. Also vectorize the **Atelier** mark for inline/product use. Interim fallback: 2× PNG from the 2000² masters.
- Favicon set from the **IteraLabs** mark: `favicon.svg`, `favicon.ico` (reuse `atelier-sdk/assets/favicon.ico` if it matches, else regenerate), `apple-touch-icon.png` (180²), `site.webmanifest`.
- One **OG card** 1200×630 (azure on `#151920`): IteraLabs wordmark + "Atelier SDK" + tagline — or generated by the `social` plugin.

**B2 — Design-token bridge** → `docs/stylesheets/tokens.css`
- Port `--c-*`, `--radius-*`, and motion tokens. **Re-scope the theme split:** dark values under `[data-md-color-scheme="slate"]`, light under `[data-md-color-scheme="default"]` — Material toggles via this *attribute*, not the webapp's `.theme-light` *class*. (This is the one place a verbatim copy would break.)

**B3 — Material mapping** → `docs/stylesheets/theme.css`
- Override Material's `--md-*` from the tokens. Concrete mapping (dark; light mirrors via the light token column above):

| Material variable | ← token | Dark value | Note |
|---|---|---|---|
| `--md-default-bg-color` | `--c-base` | `#151920` | page canvas |
| `--md-typeset-color` | `--c-rosewater` | `#b4bdd0` | body text |
| `--md-default-fg-color--light` | `--c-text` | `#8e95a4` | secondary |
| `--md-default-fg-color--lighter` | `--c-highlight1` | `#586074` | muted UI |
| `--md-primary-fg-color` | `--c-base-card` | `#1a1e24` | header stays monochrome |
| `--md-accent-fg-color` | `--c-accent` | `#3DA9E8` | hover / interactive accent |
| `--md-typeset-a-color` | `--c-accent` | `#3DA9E8` | links |
| `--md-code-bg-color` | `--c-base-card` | `#1a1e24` | code block bg |
| `--md-code-fg-color` | `--c-rosewater` | `#b4bdd0` | code text |
| `--md-footer-bg-color` | `--c-base-card` | `#1a1e24` | footer |
| admonition note/info | `--c-blue` | `#4a90d4` | |
| admonition tip/success | `--c-green` | `#34b872` | |
| admonition warning | `--c-yellow` | `#daa030` | |
| admonition danger/error | `--c-red` | `#e05470` | |

- Add an accent-colored left border + `--c-base-elevated` title bar on code blocks (Helius/Solana code-forward feel).

**B4 — Typography**
- `mkdocs.yml`: `theme.font.text: DM Sans`, `theme.font.code: JetBrains Mono`.
- CSS rule assigning **Space Grotesk** to `.md-typeset h1,h2,h3,h4,h5,h6` and `.md-header__title` (Material's single body font can't carry a separate heading face). Load Space Grotesk via `@import`/`@font-face`. Document the weights used.

**B5 — `mkdocs.yml` chrome**
- `theme.logo` = IteraLabs mark; `theme.favicon` set; keep `site_name: Atelier SDK`.
- Reorder `palette` so **dark (`slate`) is the default**; neutralize stock `primary`/`accent` (drive color from `theme.css` instead).
- Register `extra_css` in order: `tokens.css` → `theme.css` → `extra.css`.
- Enable the **`social`** plugin for OG cards — note the build deps (Cairo / Pango / Pillow); add to `requirements.txt` and the Dockerfile.

**B6 — Branded figures**
- Mermaid: bind theme variables to the brand palette (`primaryColor`/`lineColor`/`textColor` → azure + neutrals) via the Mermaid init config.
- Plotly: a shared layout template built from `--c-plot-*` + `--c-plot-grid/axis/label` (consumed once research charts arrive in Pillar 3).

**B7 — Brand reference page** → `docs/about/brand.md`
- Single source of truth: palette swatches (dark + light), type scale + weights, logo usage + clearspace + min-size, the token table. Doubles as a Helius-style mini brand kit and as visible proof the identity is deliberate.

> **Out of scope for Pillar 0:** full landing redesign, header hero, nav/IA changes. Pillar 0
> stops at palette parity, type, logo/favicon/OG, token bridge, branded figures, brand page.

## 0.6 Verification (definition of done)

- `mkdocs build --strict` passes; site serves.
- Header shows the **IteraLabs** mark; title reads "Atelier SDK"; tab shows the favicon; **dark is default**.
- Accent is **azure** everywhere — **zero indigo remains**; side-by-side palette parity with the webapp.
- Headings render in Space Grotesk, body in DM Sans, code in JetBrains Mono.
- A shared-link preview (or `social`-plugin output) shows a branded OG card.
- Mermaid diagrams use brand colors; text contrast meets **WCAG AA** in both themes.

## 0.7 Effort / sequencing

| Step | Deliverables | Rough effort |
|---|---|---|
| Config + token bridge | B2, B3, B4, B5 (minus social plugin) | ~half day CSS + yaml |
| Assets | B1 (SVG vectorization, favicon set, OG card) | ~half day, design-bound |
| Social plugin | B5 (plugin + build deps) | ~1–2 hrs incl. Docker |
| Figures | B6 | ~2–3 hrs |
| Brand page | B7 | ~2–3 hrs |

Critical path is **B2 → B3** (the token bridge + Material mapping); everything visible
depends on it. Assets (B1) can proceed in parallel.

---

# Pillar 1 — Research surface

> **Status — ✅ implemented on `docs/content-beta` (2026-06-16).** Research section live with
> one flagship article; build green. This is the single biggest move from "SDK reference" to
> "research lab": the site now *publishes dated, authored, citable thinking*, not just API
> surface.

**Goal:** stand up a `/research` hub where the lab publishes methodology — short, dated,
authored, reproducible notes. The bar is Jane Street's tech blog and Chaos Labs' research:
a body of work that signals rigor, with every result tied to the code that produced it.

## 1.0 Locked decision — use Material's built-in blog plugin

The research surface is built on **Material for MkDocs' `blog` plugin**, not hand-rolled
pages. It provides the "scholarly furniture" natively and with **no new pip dependencies**:
per-post **author**, **publish date**, **reading time**, **categories/topics**, an
**archive**, and a **topic index** — exactly the dated/authored/citable conventions that make
a site read as a lab rather than a wiki. Posts live in `docs/research/posts/`, authors in
`docs/research/.authors.yml`.

## 1.1 The bar

| Move | Exemplified by | Status |
|---|---|---|
| Publish *thinking* (methodology), not just API surface | Jane Street, Chaos Labs | ✅ seed article |
| Every post **dated + authored** | all research labs | ✅ blog plugin |
| **Reading time + topics/categories** | Helius, Jane Street | ✅ blog plugin |
| **Reproducibility** — result links to exact code/commit/version | Jump, Chaos Labs | ✅ convention + seed |
| **Citable** — stable URL + "cite this" block | academic labs | ✅ pinned slug + BibTeX |
| Research is a **first-class nav peer**, not buried | Citadel, Jane Street | ✅ top-level `Research` |

## 1.2 What we already HAD (and surfaced)

The substance was already in-repo, unpublished: the `atelier-quant` Hawkes/Poisson machinery,
the Hawkes tutorial (`guides/03-hawkes-on-arrivals.md`), the architecture page's offline
boundary / Parquet-as-contract design, and the deep `notes/beta` corpus (Taxonomy + FSM
Atlas + the 50-agent adversarial audit). Pillar 1 turns that latent material into published
research.

## 1.3 What was BUILT

| Deliverable | Path |
|---|---|
| **R1** — blog plugin + `Research` nav entry | `mkdocs.yml` |
| **R2** — research landing (frames the surface, reproducibility ethos) | `docs/research/index.md` |
| **R3** — author identity | `docs/research/.authors.yml` (`iteralabs` → "IteraLabs Research") |
| **R4** — flagship article: *"When are crypto order arrivals self-exciting?"* | `docs/research/posts/2026-06-16-self-exciting-arrivals.md` |

The flagship piece is a **methodology** note, not a tutorial: it frames the Hawkes claim as a
falsifiable hypothesis (α > 0) and lays out the five-diagnostic consistency check
(CV → AIC/BIC → LR test → time-rescaling residuals → out-of-sample MAE) used to validate or
*reject* it — the same adversarial-verification discipline applied to the platform's own
audits. Slug pinned to `self-exciting-arrivals`; ends with a reproduce-it command and a
BibTeX cite block whose URL matches the slug.

## 1.4 Verification (done)

- `mkdocs build` green; blog plugin generated landing, post, `/archive/2026/`, and
  `/category/{methodology,microstructure}/`.
- Live: `Research` is a top-level nav peer; landing shows the post card with
  **author · date · topics · "5 min read" · excerpt · continue-reading**.
- Post renders with the **author card + metadata sidebar**, brand-styled tables/code, the
  five-diagnostic table, and the BibTeX cite block. Git "last updated" stamp present.

## 1.5 Next within this pillar (not yet done)

- **More seed articles** from existing material — e.g. *"Deterministic replay of market
  microstructure"* (the Parquet-as-contract design) and a public distillation of the
  *engine design language* (Taxonomy + FSM Atlas from `notes/beta`).
- **RSS feed** — `mkdocs-rss-plugin` (one extra dep) for subscribability.
- **Author avatar** currently points at the absolute production URL (resolves on the deployed
  site; falls back locally). Revisit if a site-relative asset path is preferred.
- The empty **Tutorials overview stub** (`guides/index.md`) is a credibility nit better
  handled under Pillar 2 (IA).

---

# Pillar 2 — Information architecture

> **Status — ✅ implemented on `docs/content-beta` (2026-06-16).** Build green, no link
> warnings. The flat product-docs tree is now a tabbed "Lab vs Build" structure with a
> thesis-led home.

**Goal:** reshape the navigation skeleton and the home page so the site reads as a research
hub, not a flat reference manual — and close the credibility holes (empty stub, internal
runbook in public nav, utilitarian home).

## 2.0 Locked decisions *(confirmed with user)*

1. **Nav paradigm** — **top tabs** (Material `navigation.tabs`), grouped *Lab vs Build*:
   **Overview · Research · SDK · Platform · About**. Sidebar shows the section tree per tab.
2. **Home page** — **thesis-led reframe**: a one-line positioning statement + the reading
   paths as branded grid cards, with the reference tables kept lower.

## 2.1 What was BUILT

| # | Change | Where |
|---|--------|-------|
| **I1** | Enable `navigation.tabs`; restructure nav into 5 tabs (Overview / Research / SDK / Platform / About). Each tab's first child is its index (`navigation.indexes`). | `mkdocs.yml` |
| **I2** | Thesis-led home: positioning line + 4 grid cards (Getting started · Architecture · Tutorials · Research); reference tables retained below. | `docs/index.md` |
| **I3** | Fill the empty **Tutorials** overview stub with a real 3-card overview + a cross-link to the research methodology article. | `docs/guides/index.md` |
| **I4** | Rename **Backend → Platform API** (nav label + page H1). | `mkdocs.yml`, `docs/backend/index.md` |
| **I5** | Demote the internal **cutover-runbook** out of public nav (file kept, reachable by URL/search). | `mkdocs.yml` |

### Nav: before → after

```
BEFORE (flat):  Home · Getting started · Architecture · Research · SDK · Tutorials ·
                API reference · Backend · Operations(+cutover) · About

AFTER (tabs):   Overview ─ Home · Getting started · Architecture
                Research ─ (blog: posts · archive · topics)
                SDK ────── overview · 6 crates · Tutorials · API reference
                Platform ─ Platform API · Operations(agent)
                About ──── overview · Brand & identity
```

## 2.2 Decisions made while implementing

- **No "Concepts" sub-group** under SDK. Wrapping the 6 crate pages in a "Concepts" section
  caused `navigation.indexes` to promote the first crate (`atelier-types`) into the section
  landing, hiding its own entry. The crates are now listed directly under SDK; the
  `API reference` sub-section still separates conceptual pages from generated ones.
- **Grid cards without the icon extension.** Used Material's `.grid.cards` with Unicode
  arrows rather than adding `pymdownx.emoji` — keeps the markdown-extension surface
  unchanged. Adding icons later is trivial.
- **Blog-post links use the source path.** A regular page linking to a blog post must target
  the post's *source* file (`research/posts/<dated>.md`); MkDocs rewrites it to the permalink
  (`/research/<slug>/`). Linking the URL path fails strict link validation.

## 2.3 Verification (done)

- `mkdocs build` green; **zero link/unrecognized warnings** (only the expected untracked-file
  git-log notices remain, which clear on commit).
- Live: tabs render (Overview · Research · SDK · Platform · About); home shows the thesis
  line + 2×2 grid cards; SDK sidebar lists all 6 crates (incl. `atelier-types`) + Tutorials +
  API reference; Platform tab shows "Platform API" + Operations (no cutover-runbook);
  Tutorials overview shows the 3-card overview.

## 2.4 Next within this pillar (optional)

- **Home reading-paths icons** — add `pymdownx.emoji` for `:material-*:` card icons.
- **About prose** still references "Backend" in one list item (`docs/about.md`) — cosmetic.
- A short **404 page** and **section landing copy** for the SDK/Platform tab indexes could be
  richer (currently the SDK overview is a light stub).

---

# Pillar 3 — Content inclusion

> **Status — ✅ implemented on `docs/content-beta` (2026-06-16).** The "evidence & data" tier:
> a dataset catalog and a validation-methodology note, both grounded in **real, verified
> in-repo evidence**. Benchmarks deferred (see below). Build green, all cross-links resolve.

**Goal:** move from "we describe an SDK" to "we publish evidence" — the Chaos-Labs / Jump
signal. The hard constraint here is **integrity**: a research lab's credibility rests on
real, reproducible numbers, so nothing on these pages is fabricated.

## 3.0 What real evidence exists (audited before writing)

| Candidate | Reality in-repo | Decision |
|---|---|---|
| **Datasets** | `datasets/collected/` — **407 Parquet files, ~3.8 MB**, 3 exchanges (Binance/Bybit/Coinbase), 5 symbols, trades + L2 orderbook snapshots | ✅ build a catalog |
| **Methodology** | `v0.1-integration.md` — a live-deployment + 50-agent static audit with adversarial verification of every load-bearing finding | ✅ publish the *process* |
| **Benchmarks** | Orderbook-generation **plots** exist, but **no `[[bench]]` targets / criterion results** → no sourced numbers | ⛔ **deferred** — publishing numbers would be fabrication |

## 3.1 What was BUILT

| Deliverable | Path | Home |
|---|---|---|
| **C1 — Dataset catalog** | `docs/datasets/index.md` | Platform tab + home Quick links |
| **C2 — Methodology note** *"How we validate the Atelier platform"* | `docs/research/posts/2026-06-16-how-we-validate.md` (slug `how-we-validate`) | Research tab (post #2) |

- **C1** documents the real corpus honestly (incl. its skew toward Binance L2 books), the
  `{exchange}_{symbol}_{datatype}_{mode}_{ts}.parquet` convention with real example
  filenames, the `Trade` / `Orderbook` / `MarketSnapshot` schema (fields lifted from
  `atelier-types`), and the SDK readers (`read_trades_parquet`, `load_parquet_to_ob`). Framed
  as **"format, not a download"** — it documents schema + how to reproduce, not a hosted file.
- **C2** publishes the validation **discipline** — spec-as-source-of-truth (FSM Atlas +
  Taxonomy), two independent evidence streams (live deployment + static multi-agent audit),
  and **adversarial verification** as the gate — explicitly tied back to the five-diagnostic
  discipline of the Hawkes post. It deliberately publishes the *method*, **not** the internal
  gap findings or compliance scores from the source audit.

## 3.2 Integrity decisions

- **No fabricated benchmarks.** With no criterion results or `[[bench]]` targets, no
  throughput/latency numbers are published. Benchmarks are a real next step *once the SDK
  exposes a bench harness* — logged here rather than faked.
- **Methodology, not findings.** The source `v0.1-integration.md` contains internal
  compliance gaps and scores; the public note describes only the *process*, which reveals no
  internal posture and is credibility-positive.
- **Honest dataset coverage.** The catalog states the corpus is a seed sample skewed to
  Binance L2, not a balanced multi-venue panel.

## 3.3 Verification (done)

- `mkdocs build` green; **zero link warnings**. Research index lists **2 posts**; Topics index
  spans Methodology + Microstructure; dataset catalog renders under Platform with the real
  407-file coverage table; all dataset↔research↔tutorial cross-links resolve.

## 3.4 Next within this pillar

- **Benchmarks page** once a criterion/bench harness lands in `atelier-sdk` — throughput,
  latency distributions, model-fit quality, *with reproduction commands and commit hashes*.
- **More dataset depth** — publish actual downloadable samples (or a manifest) if/when a
  hosting location exists; broaden beyond the Binance-heavy seed.
- A third research note (e.g. *"Deterministic replay of market microstructure"*) to round out
  the methodology set.
