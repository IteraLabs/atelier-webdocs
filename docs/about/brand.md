---
description: The Atelier / IteraLabs visual identity — palette, typography, logo usage, and design tokens.
---

# Brand & identity

This page is the single source of truth for the visual identity of these docs. The same
tokens drive [`atelier-webapp`](https://github.com/IteraLabs); the docs site mirrors them so
the two properties read as one lab.

!!! abstract "Two-tier brand"
    **IteraLabs** is the lab — its mark leads the header and the social card. **Atelier** is
    the product these docs describe — it names the site (*Atelier SDK*) and appears wherever
    the SDK is referenced. Tagline: *Financial Research Infrastructure*.

## Logo

![IteraLabs mark](../assets/iteralabs-mark.png){ width="120" }

The mark is the stacked-squares **`i_`** emblem in azure over blue-grey. Usage rules:

- **Clearspace** — keep padding of at least the height of one inner square on all sides; never crowd the mark.
- **Minimum size** — 24 px tall in UI, 16 px for a favicon (use the *filled* variant so the shape survives).
- **Variants** — outline emblem for the header (on dark or light chrome); filled emblem for the favicon / app icon.
- **Don't** — recolor the azure, add effects, or stretch the aspect ratio.

## Color

One disciplined accent — **azure `#3DA9E8`** — over near-monochrome blue-grey surfaces. The
accent hue is identical in both themes; surfaces invert.

=== "Dark (default)"

    <div class="grid" markdown>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#151920;color:#b4bdd0">`#151920` canvas</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#1a1e24;color:#b4bdd0">`#1a1e24` panel</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#282d36;color:#b4bdd0">`#282d36` well</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#3DA9E8;color:#0b0e13">`#3DA9E8` accent</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#b4bdd0;color:#151920">`#b4bdd0` text</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#8e95a4;color:#151920">`#8e95a4` text-2</span>
    </div>

=== "Light"

    <div class="grid" markdown>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#fafbfd;color:#1a1e24;border:1px solid #d8dae3">`#fafbfd` canvas</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#f1f2f6;color:#1a1e24;border:1px solid #d8dae3">`#f1f2f6` panel</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#e8eaef;color:#1a1e24">`#e8eaef` well</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#3DA9E8;color:#fff">`#3DA9E8` accent</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#1a1e24;color:#fafbfd">`#1a1e24` text</span>
    <span style="display:inline-block;width:100%;padding:.6rem .75rem;border-radius:8px;background:#4a5264;color:#fafbfd">`#4a5264` text-2</span>
    </div>

**Signal palette** (status, charts) — green `#34b872` · gold `#daa030` · rose `#e05470` ·
blue `#4a90d4` · violet `#8868b8`. Reserved for state and data, never decoration.

## Typography

| Role | Typeface | Notes |
|------|----------|-------|
| Headings | **Space Grotesk** | 600/700, slight negative tracking |
| Body | **DM Sans** | 400–600 |
| Code & data | **JetBrains Mono** | 400–600 |

<p style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;letter-spacing:-0.01em;margin:.2rem 0">Space Grotesk — research-grade headings</p>
<p style="font-family:'DM Sans',sans-serif;font-size:1rem">DM Sans — body copy for long-form reading at a comfortable measure.</p>
<p style="font-family:'JetBrains Mono',monospace;font-size:.9rem">JetBrains Mono — fn fit_hawkes(λ: f64) -&gt; Result&lt;Model&gt;</p>

## Tokens

- **Radii** — `4 / 8 / 12 / 16 px` (sm / md / lg / xl), `9999px` full.
- **Motion** — durations `120 / 200 / 400 ms`; easing `cubic-bezier(0.16, 1, 0.3, 1)`.

The implementation lives in [`docs/stylesheets/tokens.css`](https://github.com/IteraLabs/atelier-webdocs/blob/main/docs/stylesheets/tokens.css)
(brand tokens) and `theme.css` (mapping onto Material's `--md-*` variables).
