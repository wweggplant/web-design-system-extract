# {{site_name}} Design System + UX Report

> Collected on {{collected_at}}
> Source: {{target_site_base_url}} (home: {{home_path}}, nav: {{nav_path}})
> Theme modes: {{theme_modes}}
> Breakpoints: desktop {{bp_desktop}}, tablet {{bp_tablet}}, mobile {{bp_mobile}}

## 1. Tech Stack Summary (with evidence)

- Framework: {{framework.name}} ({{framework.confidence}})
  - Evidence:
    {{framework.evidence}}
- Styling: {{styling.name}} ({{styling.confidence}})
  - Evidence:
    {{styling.evidence}}
- Icon system: {{icons.name}} ({{icons.confidence}})
  - Evidence:
    {{icons.evidence}}
- UI libraries (if any): {{ui_libs}}
  - Evidence:
    {{ui_libs_evidence}}

## 2. Font Forensics (mandatory)

### 2.1 Network font requests
- Files:
  {{font_requests_table}}

### 2.2 @font-face inventory
- Families:
  {{font_face_table}}

### 2.3 Computed font probes (per breakpoint)
- Probes:
  {{computed_font_probes_table}}

### 2.4 Font conclusion
- Primary font family(ies):
- Variable font axes used (if any):
- Fallback behavior:
- Verification status: {{font_verified_status}} (VERIFIED / UNVERIFIED)
- Notes / gaps:

## 3. Decision Trace (explainable layer)

**Typography**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Color System**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Interaction Model**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Density & Rhythm**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Layout Grammar**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Surface & Material**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Motion**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

**Accessibility**
- Conclusion:
- Evidence:
- Alternatives rejected / uncertainty:

## 4. Evidence Index

- Screenshots:
  {{paths_screenshots}}
- Key sections:
  {{paths_key_sections}}
- Crops (per-sample):
  {{paths_crops}}
- HTML snapshots:
  {{paths_html}}
- CSS assets:
  {{paths_css}}
- Fonts:
  {{paths_fonts}}
- Samples + clustering:
  {{paths_samples}}
- Network logs:
  {{paths_network}}

## 5. Primitive Tokens (with outliers)

**Colors — neutrals (HSL/RGB)**
{{primitive_colors_neutrals}}

**Colors — accents (HSL/RGB)**
{{primitive_colors_accents}}

**Opacity scale**
{{primitive_opacity}}

**Glass/Blur tokens**
{{primitive_glass_blur}}

**Typography scale**
{{primitive_typography_scale}}

**Spacing scale**
- Core:
  {{primitive_spacing_core}}
- Outliers:
  {{primitive_spacing_outliers}}

**Size scale (control heights etc.)**
{{primitive_size_scale}}

**Radius scale**
{{primitive_radius}}

**Border width**
{{primitive_border_width}}

**Shadow levels**
{{primitive_shadow}}

**Motion**
- Durations:
  {{primitive_motion_durations}}
- Easings:
  {{primitive_motion_easings}}
- Properties most transitioned:
  {{primitive_motion_properties}}

**Z-index scale (if detectable)**
{{primitive_z_index}}

**Layout primitives**
- Container steps:
  {{layout_container_steps}}
- Gutters (per breakpoint):
  {{layout_gutters}}
- Grid primitives:
  {{layout_grid_primitives}}

## 6. Semantic Tokens

{{semantic_tokens_block}}

## 7. Interaction Model (mandatory)

### 7.1 State matrix
{{interaction_state_matrix_table}}

### 7.2 Interaction patterns
- Hover pattern(s):
- Focus-visible ring pattern:
- Pressed/selected conventions:
- Overlay open/close affordances (if present):
- Notes / gaps:

## 8. Density & Rhythm Rules (mandatory)

- Control heights (button/input/chip/etc.):
- Typical paddings (card/list rows):
- Section spacing (vertical rhythm):
- Breakpoint deltas (how density changes):
- Notes / gaps:

## 9. Layout Grammar (mandatory)

- Container max-width steps:
- Side padding/gutters per breakpoint:
- Grid columns / min card width per breakpoint:
- Gap rules (row/col):
- Notes / gaps:

## 10. Surface & Material Model

- Surface levels (page/surface/elevated/overlay):
- Divider/border usage rules:
- Glass/blur usage rules:
- Notes / gaps:

## 11. Accessibility Checks (best effort)

- Focus ring spec (thickness/color/offset):
- Target size sampling (e.g., 44px rule adherence):
- Contrast spot checks (primary/secondary text on page bg):
- Reduced motion handling (prefers-reduced-motion):
- Notes / gaps:

## 12. Component Tokens (with state diffs summary)

**Navbar**
{{component_navbar}}

**Button (Primary CTA)**
{{component_button}}

**Input / Search**
{{component_input}}

**Card / Tile**
{{component_card}}

**Chip / Tag**
{{component_chip}}

**Grid / List**
{{component_grid}}

**Overlay components (if present)**
- Dropdown/Popover:
- Tooltip:
- Modal/Overlay:
- Pagination/Segmented:

## 13. Component Map

{{component_map_block}}

## 14. Responsive Rules (evidenced)

{{responsive_rules_block}}

## 15. Minimal Implementation

- Strategy chosen: {{implementation.strategy}} (Tailwind config OR CSS vars + tokens.ts)
- Tailwind config:
  {{implementation.tailwind_config_path}}
- tokens.ts:
  {{implementation.tokens_ts_path}}
- CSS vars:
  {{implementation.css_vars_path}}
- Example components:
  {{implementation.examples}}

## 16. Limits / Missing Items

{{limits_block}}
