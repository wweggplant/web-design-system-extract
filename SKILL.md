---

name: web-design-system-reverse
short-description: "Reverse engineer design system + UX interaction model"
description: "Design System Reverse Engineer. Use Playwright (via MCP/skill) to reverse-engineer a live website’s design system for pixel-perfect recreation. Produces: tech stack fingerprint, font forensics, design tokens (primitive/semantic/component), interaction model + state matrix, density/rhythm rules, responsive layout grammar, accessibility checks, and minimal implementation (Tailwind config or CSS vars + tokens.ts). Optimized for results: correct sampling, UI-defining tokens, reproducible specs, and explainable decision traces."
---

# Design System Reverse Engineer (Pixel-Accurate + UX-Complete)

## Goal

Reverse-engineer a site’s design system AND the UX-defining interaction rules that create its “feel”: typography (incl. variable fonts), density/rhythm, surfaces/materials, states, motion, layout grammar, and accessibility behaviors.

The output must be reproducible (tokens + component specs + state matrix + responsive rules), and explainable (decision traces + evidence index).

## Required Inputs

* `target_site_base_url`
* `home_path` (default `/`)
* `nav_path` (catalog/list page; if unknown, auto-discover via internal links such as “Browse / Library / Categories / Explore”)
* Theme: `theme_modes` (`default`, optionally `dark` if toggle exists)
* Auth: do not login; if blocked, continue with accessible pages and report limits

## Output Contract

You must produce:

1. Tech Stack Summary with evidence (framework + styling + UI libs + icon system)
2. Font Forensics (network + @font-face + computed probes, per breakpoint)
3. Decision Trace (Typography/Color/Interaction/Density/Layout/Surface/Motion/A11y)
4. Tokens:

   * Primitive: color / opacity / type / space / size / radius / border / shadow / blur / motion / z-index / layout
   * Semantic: bg/text/border/interactive/focus/overlay/elevation
   * Component tokens: navbar/button/input/search/chip/card/grid + popover/dropdown/modal/tooltip/pagination (as evidenced)
5. Interaction Model:

   * State Matrix (component × state)
   * State diffs (hover/focus-visible/active/disabled + selected/pressed/visited/loading if present)
6. Density & Rhythm Rules:

   * control heights, paddings, list row heights, section spacing
7. Layout Grammar:

   * container max-width steps, gutters, grid columns/min card width per breakpoint
8. Surface & Material Model:

   * surface levels (page/surface/elevated/overlay), divider/border usage, glass/blur patterns
9. Accessibility Checks (best effort): focus ring spec, target sizes, contrast samples, reduced-motion handling
10. Minimal implementation: Tailwind config if Tailwind; else CSS vars + tokens.ts + 2 component examples
11. Evidence index: screenshots, crops, samples.json, CSS/HTML snapshots, font logs

## Hard Constraints

1. Evidence-first: tokens and rules must derive from collected evidence.
2. No silent assumptions: any inference must be labeled `ASSUMPTION` with required evidence to confirm.
3. Anti-mis-sampling: only visible, non-trivial, meaningful nodes (visible=true, bbox>=24×24, role/text present).
4. Font forensics mandatory: verify via network + @font-face + computed probes; otherwise mark `UNVERIFIED FONT`.
5. Interaction model mandatory: output state matrix + diffs; missing states must include reasons.
6. Density/rhythm mandatory: output control heights and section/list spacing rules.
7. A11y best-effort mandatory: focus-visible spec + target-size sampling; missing data must be explained.
8. Multi-page + multi-breakpoint required.
9. Token economy: finite scales + outliers.
10. No “Missing Data: None”. Always list limits.

## Breakpoints

* Desktop: 1440×900
* Tablet: 834×1112
* Mobile: 390×844

## States

* default
* hover
* focus-visible (Tab navigation)
* active (pointer-down)
* disabled (if present)
* selected/pressed/checked/visited/loading (capture if present)

## Artifacts Layout

```
artifacts/
├── screenshots/                # full page per bp + key sections
├── crops/                      # per-sample cropped screenshots
├── html/                       # DOM snapshot per page/bp
├── css/                        # downloaded css assets
├── fonts/                      # @font-face extracts + font requests + computed probes
├── samples/                    # samples.json + per-state snapshots + diffs
├── results.json                # clustering + token proposals + rule summaries
├── report.md                   # final report (template-based)
└── guide.md                    # consumer guide
```

## Fixed Templates (Required)

Use templates under `templates/`:

* `templates/report.md` -> `artifacts/report.md`
* `templates/results.json` -> `artifacts/results.json`
* `templates/guide.md` -> `artifacts/guide.md`

Do not rename headings. Keep JSON valid.

## Workflow

### Step 0 — Tech Stack Fingerprint

Collect (desktop is enough):

* Network: JS bundle patterns, CSS assets, font requests, icon assets
* DOM markers: framework roots
* CSS signatures: Tailwind/CSS Modules/CSS-in-JS/UI libs
* Icon system: inline SVG vs sprite vs icon font

Output Confirmed/Likely + evidence bullets.

### Step 0.5 — Font Forensics (mandatory)

A) Network: log font requests (URL/status/mime/initiator/domain)
B) CSS: extract `@font-face` from downloaded CSS + inline `<style>`
C) Computed probes (per breakpoint) for:

* body
* hero h1
* section h2
* nav link
* primary button label
* card title
  Record font-family/weight/size/line-height/letter-spacing/font-variation-settings.

### Step 1 — Page Acquisition

For each page (home + nav) × breakpoint:

* load networkidle
* ensure key content visible
* save full screenshot + key section screenshots + HTML snapshot + CSS assets

### Step 2 — Component Sampling (UX-complete set)

Per page × breakpoint sample:

Core visual/structure:

* Typography: H1/H2/body/caption (>=3 each)
* Navbar: container/link/active (>=3)
* Card/Tile: container/title/meta/media (>=5)
* Grid/List container: columns+gap controller (>=2)

Navigation/search UX:

* Search input (>=2)
* Filter chip/tag (>=3 if exists)
* Pagination/segmented control (>=2 if exists)

Overlay UX (if present on public pages):

* Dropdown/Popover (trigger + panel)
* Tooltip (trigger + tooltip)
* Modal/Overlay (open trigger + overlay surface)

Sampling rules:

* prefer semantic/accessibility/data-* selectors
* reject invisible/small/meaningless wrappers
* store selector + role/aria + text snippet + bbox + visibility + crop screenshot

### Step 3 — Style Evidence Collection

For each sample collect:

* computed styles (typography/color/layout/effects/motion)
* CSS var resolution chain (best-effort)
* rule attribution (CDP matched rules if available; else classname+asset hits)

### Step 4 — State Capture & Diffs

For interactive samples capture:

* default/hover/focus-visible/active
* disabled/selected/pressed/visited/loading if present

Compute diffs:

* `changed: { prop: [default, state] }` only

### Step 5 — Clustering into Scales (token economy)

Primitive scales:

* colors: bg/text/border/interactive/focus (keep alpha separate)
* opacity scale
* typography scale (size steps + linked lh/ls/weight distributions)
* spacing scale
* radius, border width
* shadow + blur/backdrop-filter levels
* motion: durations + easings (+ properties used)
* z-index scale (overlay ordering if detectable)
* layout: container widths, gutters, grid columns/min card width

### Step 6 — Semantic Tokens

Map primitives to roles:

* bg: page/surface/elevated/overlay/inverse/brand
* text: primary/secondary/tertiary/inverse/link
* border: subtle/divider/strong
* interactive: primary + hover/active
* focus.ring
* elevation levels
* motion tiers

### Step 7 — Component Tokens + Specs

For evidenced components output:

* Navbar, Button, Input/Search, Chip/Tag, Card/Tile, Grid/List
* If present: Dropdown/Popover, Tooltip, Modal/Overlay, Pagination

Each includes:

* size (height/padding)
* typography (token refs)
* surface (bg/border/shadow)
* states (diff summary)

### Step 8 — Interaction Model (mandatory)

Output:

* State Matrix table (component × captured states)
* Interaction patterns:

  * what changes on hover (shadow/translate/color)
  * focus-visible ring pattern
  * pressed/selected conventions
  * overlay open/close affordances (if present)

### Step 9 — Density & Rhythm Rules (mandatory)

Derive and state:

* control heights: button/input/chip
* list row heights (if list UI exists)
* section spacing: top/between sections
* typical card padding and internal gaps
* breakpoint-specific density changes

### Step 10 — Surface & Material Model

Summarize:

* surface levels (page/surface/elevated/overlay)
* divider usage rules
* glass/blur tokens and where used

### Step 11 — Accessibility Checks (best effort)

Sample-based checks:

* focus ring thickness/color/offset/contrast behavior
* pointer target size sampling for key controls
* contrast spot checks (primary text on page bg; secondary text)
* reduced motion handling (`prefers-reduced-motion`) if detectable

### Step 12 — Decision Trace (mandatory)

Write concise, high-signal logs for:

* Typography (font verification + variable axis usage + fallback)
* Color roles
* Interaction patterns
* Density/rhythm
* Layout grammar
* Surface/material
* Motion
* A11y

Each: conclusion + evidence paths + rejected alternatives/uncertainty.

### Step 13 — Minimal Implementation

If Tailwind Confirmed/Likely:

* `tailwind.config` (semantic colors, fontSize scale, spacing/radius/shadow/motion)
* 2 components: Navbar + Card

Else:

* tokens.ts + CSS vars
* 2 components: Navbar + Card

No fake Tailwind class names.

## Final Report Format (report.md)

Keep headings unchanged in the template:

1. Tech Stack Summary (with evidence)
2. Font Forensics
3. Decision Trace
4. Evidence Index
5. Primitive Tokens (with outliers)
6. Semantic Tokens
7. Interaction Model (state matrix + patterns)
8. Density & Rhythm Rules
9. Layout Grammar
10. Surface & Material Model
11. Accessibility Checks
12. Component Tokens (with state diffs summary)
13. Component Map
14. Minimal Implementation
15. Limits / Missing Items

## Implementation Notes (scripts/collect.py)

Collector must output:

* `artifacts/fonts/` (font requests + @font-face + computed probes)
* `artifacts/samples/samples.json` (incl. crops + per-state diffs)
* `artifacts/results.json` (clusters + token proposals + rule summaries)

Do not embed full CSS. Link to assets.

Optional candidate-only workflow:

* Use `--candidates-only` to capture broad UI candidates (hero CTA, nav links, media, tags) into `artifacts/samples/candidates.json`.
* Use `--selected <path>` with a JSON list of `selector_path` or `selector` strings to filter samples to a curated set.
* Use `--allow-anchor-active` only if safe to capture active state on anchors.

## What Not To Do

* Don’t dump `:root` vars and call it a system.
* Don’t name typography tokens with Tailwind class strings.
* Don’t invent components/states.
* Don’t claim completeness; always list limits.
