# Design System Reverse Engineer Guide

## Project Summary

- Site: {{target_site_base_url}}
- Pages: home={{home_path}}, nav={{nav_path}}
- Theme modes: {{theme_modes}}
- Collected at: {{collected_at}}

## What You Get

- `artifacts/report.md` - Evidence-backed narrative of tokens, components, and decisions.
- `artifacts/results.json` - Structured tokens and mappings for programmatic use.
- `artifacts/samples/samples.json` - Sample metadata and computed styles.
- `artifacts/screenshots/` - Full-page and key section captures.
- `artifacts/css/` + `artifacts/html/` - Raw evidence sources.

## How To Use

1. Start with `artifacts/report.md` to understand system structure and decisions.
2. Use `artifacts/results.json` to drive code tokens and theme config.
3. Validate with `artifacts/screenshots/` and `artifacts/samples/` when implementing components.

## Reproduce This Run

- Breakpoints: 1440x900, 834x1112, 390x844
- Pages: home + nav
- Notes: no auth, public pages only

## Known Limits

- {{limit}}

## Contact / Notes

- {{owner_or_team}}
