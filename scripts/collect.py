#!/usr/bin/env python3
"""
Design System Reverse Engineering - Collection Script (collect_v3)
Collects UI/UX evidence from target websites using Playwright.
"""

import argparse
import asyncio
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright, Page, Browser, Request, Response
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    raise SystemExit(1)


DEFAULT_BREAKPOINTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 834, "height": 1112},
    "mobile": {"width": 390, "height": 844},
}

STATE_DIFF_PROPS = [
    "color",
    "background-color",
    "border-color",
    "outline-color",
    "outline-width",
    "outline-offset",
    "box-shadow",
    "opacity",
    "transform",
]

TYPOGRAPHY_PROPS = [
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
    "letter-spacing",
    "font-style",
    "font-variation-settings",
    "text-transform",
    "color",
]

LAYOUT_PROPS = [
    "display",
    "gap",
    "grid-template-columns",
    "justify-content",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "width",
    "max-width",
    "height",
    "border-radius",
    "border-width",
    "border-style",
]

EFFECT_PROPS = [
    "background-color",
    "border-color",
    "outline-color",
    "outline-width",
    "outline-offset",
    "box-shadow",
    "backdrop-filter",
    "opacity",
    "transform",
]

MOTION_PROPS = [
    "transition-property",
    "transition-duration",
    "transition-timing-function",
    "transition-delay",
]

ALL_PROPS = list(dict.fromkeys(TYPOGRAPHY_PROPS + LAYOUT_PROPS + EFFECT_PROPS + MOTION_PROPS + ["z-index"]))

CANDIDATE_PROPS = [
    "color",
    "background-color",
    "background-image",
    "border-color",
    "border-radius",
    "box-shadow",
    "font-size",
    "font-weight",
    "letter-spacing",
    "text-transform",
    "height",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "opacity",
]


SYSTEM_FONTS = {
    "-apple-system",
    "blinkmacsystemfont",
    "segoe ui",
    "roboto",
    "helvetica",
    "arial",
    "noto sans",
    "sans-serif",
    "serif",
    "ui-sans-serif",
    "ui-serif",
    "ui-monospace",
    "system-ui",
}


def extract_site_name(base_url: str) -> str:
    domain = urlparse(base_url).netloc
    name = domain.replace("www.", "").split(".")[0]
    return name or "site"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now().isoformat()


def normalize_text(text: str, limit: int = 140) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean[:limit]


def safe_filename(value: str) -> str:
    return re.sub(r"[^\w\-]", "_", value)


def parse_breakpoints(raw: Optional[str]) -> Dict[str, Dict[str, int]]:
    if not raw:
        return DEFAULT_BREAKPOINTS
    result = {}
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        name, size = part.split("=", 1)
        if "x" not in size:
            continue
        width_str, height_str = size.lower().split("x", 1)
        try:
            result[name.strip()] = {"width": int(width_str), "height": int(height_str)}
        except ValueError:
            continue
    return result or DEFAULT_BREAKPOINTS


def parse_theme_modes(raw: Optional[str]) -> List[str]:
    if not raw:
        return ["default"]
    modes = [m.strip() for m in raw.split(",") if m.strip()]
    return modes or ["default"]

def parse_selected_paths(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    path = Path(raw)
    if not path.exists():
        return []
    try:
        data = json.loads(read_text(path))
    except Exception:
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return [s for s in data if isinstance(s, str)]
        if data and isinstance(data[0], dict):
            paths = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                selector_path = item.get("selector_path")
                selector = item.get("selector")
                if selector_path:
                    paths.append(selector_path)
                elif selector:
                    paths.append(selector)
            return paths
    return []


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def flatten_values(values: List[Any]) -> List[Any]:
    out = []
    for v in values:
        if isinstance(v, list):
            out.extend(v)
        else:
            out.append(v)
    return out


def rgba_to_hsl(r: float, g: float, b: float) -> Tuple[float, float, float]:
    r /= 255.0
    g /= 255.0
    b /= 255.0
    maxc = max(r, g, b)
    minc = min(r, g, b)
    l = (minc + maxc) / 2.0
    if minc == maxc:
        return 0.0, 0.0, l
    if l <= 0.5:
        s = (maxc - minc) / (maxc + minc)
    else:
        s = (maxc - minc) / (2.0 - maxc - minc)
    rc = (maxc - r) / (maxc - minc)
    gc = (maxc - g) / (maxc - minc)
    bc = (maxc - b) / (maxc - minc)
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2.0 + rc - bc
    else:
        h = 4.0 + gc - rc
    h = (h / 6.0) % 1.0
    return h * 360.0, s, l


def parse_color(value: str) -> Optional[Tuple[int, int, int, float]]:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"transparent", "none"}:
        return None
    rgba_match = re.match(r"rgba?\(([^)]+)\)", value)
    if rgba_match:
        parts = [p.strip() for p in rgba_match.group(1).split(",")]
        if len(parts) >= 3:
            try:
                r = int(float(parts[0]))
                g = int(float(parts[1]))
                b = int(float(parts[2]))
                a = float(parts[3]) if len(parts) > 3 else 1.0
                return r, g, b, a
            except ValueError:
                return None
    hex_match = re.match(r"#([0-9a-f]{3,8})", value)
    if hex_match:
        h = hex_match.group(1)
        if len(h) in {3, 4}:
            r = int(h[0] * 2, 16)
            g = int(h[1] * 2, 16)
            b = int(h[2] * 2, 16)
            a = int(h[3] * 2, 16) / 255.0 if len(h) == 4 else 1.0
            return r, g, b, a
        if len(h) in {6, 8}:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
            return r, g, b, a
    return None


def color_to_string(rgba: Tuple[int, int, int, float]) -> str:
    r, g, b, a = rgba
    if a >= 0.999:
        return f"rgb({r}, {g}, {b})"
    return f"rgba({r}, {g}, {b}, {round(a, 3)})"


def color_is_neutral(rgba: Tuple[int, int, int, float]) -> bool:
    h, s, _ = rgba_to_hsl(rgba[0], rgba[1], rgba[2])
    return s < 0.18 or h is None


def parse_length(value: str, root_font_size: float = 16.0) -> Optional[float]:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"auto", "normal", "none"}:
        return None
    if value.endswith("px"):
        try:
            return float(value.replace("px", ""))
        except ValueError:
            return None
    if value.endswith("rem"):
        try:
            return float(value.replace("rem", "")) * root_font_size
        except ValueError:
            return None
    if value.endswith("em"):
        try:
            return float(value.replace("em", "")) * root_font_size
        except ValueError:
            return None
    if value.endswith("%"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_duration(value: str) -> Optional[float]:
    if not value:
        return None
    value = value.strip().lower()
    if value.endswith("ms"):
        try:
            return float(value.replace("ms", ""))
        except ValueError:
            return None
    if value.endswith("s"):
        try:
            return float(value.replace("s", "")) * 1000.0
        except ValueError:
            return None
    return None


def contrast_ratio(fg: Tuple[int, int, int], bg: Tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    lum_fg = 0.2126 * channel(fg[0]) + 0.7152 * channel(fg[1]) + 0.0722 * channel(fg[2])
    lum_bg = 0.2126 * channel(bg[0]) + 0.7152 * channel(bg[1]) + 0.0722 * channel(bg[2])
    lighter = max(lum_fg, lum_bg)
    darker = min(lum_fg, lum_bg)
    return (lighter + 0.05) / (darker + 0.05)


@dataclass
class NetworkEntry:
    url: str
    method: str
    resource_type: str
    status: Optional[int]
    content_type: Optional[str]
    initiator: Dict[str, Any]
    page_tag: str
    breakpoint: str
    theme: str


class NetworkLogger:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        ensure_dir(output_dir)
        self.entries: List[NetworkEntry] = []
        self._request_map: Dict[int, int] = {}

    def attach(self, page: Page, page_tag: str, breakpoint: str, theme: str):
        async def on_request(request: Request):
            entry = NetworkEntry(
                url=request.url,
                method=request.method,
                resource_type=request.resource_type,
                status=None,
                content_type=None,
                initiator={
                    "page_url": page.url,
                    "frame_url": request.frame.url if request.frame else page.url,
                },
                page_tag=page_tag,
                breakpoint=breakpoint,
                theme=theme,
            )
            self.entries.append(entry)
            self._request_map[id(request)] = len(self.entries) - 1

        async def on_response(response: Response):
            req = response.request
            idx = self._request_map.get(id(req))
            if idx is None:
                return
            self.entries[idx].status = response.status
            self.entries[idx].content_type = response.headers.get("content-type", "")

        page.on("request", on_request)
        page.on("response", on_response)

    def classify_fonts(self) -> List[Dict[str, Any]]:
        fonts = []
        for entry in self.entries:
            url = entry.url.split("?")[0].lower()
            content_type = (entry.content_type or "").lower()
            is_font = url.endswith((".woff", ".woff2", ".ttf", ".otf")) or "font" in content_type
            if is_font:
                fonts.append({
                    "url": entry.url,
                    "status": entry.status,
                    "content_type": entry.content_type,
                    "initiator": entry.initiator,
                    "page_tag": entry.page_tag,
                    "breakpoint": entry.breakpoint,
                    "theme": entry.theme,
                })
        return fonts

    def write(self) -> Tuple[Path, Path]:
        network_path = self.output_dir / "requests.jsonl"
        font_path = self.output_dir.parent / "fonts" / "font-requests.json"
        ensure_dir(font_path.parent)

        with open(network_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")

        font_items = self.classify_fonts()
        write_json(font_path, {"count": len(font_items), "items": font_items})
        return network_path, font_path


class DesignSystemCollector:
    def __init__(
        self,
        base_url: str,
        output_dir: str,
        home_path: str = "/",
        nav_path: Optional[str] = None,
        theme_modes: Optional[List[str]] = None,
        breakpoints: Optional[Dict[str, Dict[str, int]]] = None,
        skip_overlays: bool = False,
        candidates_only: bool = False,
        selected_paths: Optional[List[str]] = None,
        allow_anchor_active: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.home_path = home_path
        self.nav_path = nav_path
        self.theme_modes = theme_modes or ["default"]
        self.breakpoints = breakpoints or DEFAULT_BREAKPOINTS

        self.output_dir = Path(output_dir)
        self.artifacts_dir = self.output_dir / "artifacts"
        self.templates_dir = Path(__file__).resolve().parent.parent / "templates"

        self.screenshots_dir = self.artifacts_dir / "screenshots"
        self.html_dir = self.artifacts_dir / "html"
        self.css_dir = self.artifacts_dir / "css"
        self.samples_dir = self.artifacts_dir / "samples"
        self.network_dir = self.artifacts_dir / "network"
        self.fonts_dir = self.artifacts_dir / "fonts"
        self.crops_dir = self.artifacts_dir / "crops"

        for path in [
            self.artifacts_dir,
            self.screenshots_dir,
            self.html_dir,
            self.css_dir,
            self.samples_dir,
            self.network_dir,
            self.fonts_dir,
            self.crops_dir,
        ]:
            ensure_dir(path)

        self.network_logger = NetworkLogger(self.network_dir)

        self.samples: List[Dict[str, Any]] = []
        self.candidates: List[Dict[str, Any]] = []
        self.pages: Dict[str, Dict[str, Any]] = {}
        self.font_faces: List[Dict[str, Any]] = []
        self.font_probes: List[Dict[str, Any]] = []
        self.limits: List[str] = []

        self.tech_stack: Dict[str, Any] = {}
        self.reduced_motion_detected: bool = False
        self.skip_overlays: bool = skip_overlays
        self.candidates_only: bool = candidates_only
        self.selected_selector_paths = set(selected_paths or [])
        self.allow_anchor_active: bool = allow_anchor_active

        self.evidence_paths = {
            "screenshots": set(),
            "crops": set(),
            "html": set(),
            "css": set(),
            "fonts": set(),
            "samples": set(),
            "network": set(),
        }

    async def collect_all(self) -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            pages_to_collect = [("home", self.home_path)]
            if self.nav_path:
                pages_to_collect.append(("nav", self.nav_path))

            for theme in self.theme_modes:
                for page_name, path in pages_to_collect:
                    for bp_name, bp_config in self.breakpoints.items():
                        await self.collect_page(
                            browser=browser,
                            page_name=page_name,
                            path=path,
                            breakpoint=bp_name,
                            bp_config=bp_config,
                            theme_mode=theme,
                        )

            await browser.close()

        network_path, font_request_path = self.network_logger.write()
        self.evidence_paths["network"].add(str(network_path.relative_to(self.output_dir)))
        self.evidence_paths["fonts"].add(str(font_request_path.relative_to(self.output_dir)))

        samples_path = self.samples_dir / "samples.json"
        write_json(samples_path, self.samples)
        self.evidence_paths["samples"].add(str(samples_path.relative_to(self.output_dir)))

        if self.candidates:
            candidates_path = self.samples_dir / "candidates.json"
            write_json(candidates_path, self.candidates)
            self.evidence_paths["samples"].add(str(candidates_path.relative_to(self.output_dir)))

        font_face_path = self.fonts_dir / "font-face.json"
        font_probe_path = self.fonts_dir / "computed-font-probes.json"
        write_json(font_face_path, {"count": len(self.font_faces), "items": self.font_faces})
        write_json(font_probe_path, {"count": len(self.font_probes), "items": self.font_probes})
        self.evidence_paths["fonts"].add(str(font_face_path.relative_to(self.output_dir)))
        self.evidence_paths["fonts"].add(str(font_probe_path.relative_to(self.output_dir)))

        results = self.build_results(font_request_path=font_request_path)
        results_path = self.artifacts_dir / "results.json"
        write_json(results_path, results)

        report_path = self.artifacts_dir / "report.md"
        report_content = self.render_report(results)
        write_text(report_path, report_content)

        guide_path = self.artifacts_dir / "guide.md"
        guide_content = self.render_guide(results)
        write_text(guide_path, guide_content)

        ui_ux_path = self.artifacts_dir / "ui-ux.md"
        ui_ux_content = self.render_ui_ux(results)
        write_text(ui_ux_path, ui_ux_content)

        print("\n✅ Collection complete")
        print(f"Artifacts: {self.artifacts_dir}")
        print(f"Report: {report_path}")

    async def collect_page(
        self,
        browser: Browser,
        page_name: str,
        path: str,
        breakpoint: str,
        bp_config: Dict[str, int],
        theme_mode: str,
    ) -> None:
        url = urljoin(self.base_url, path)
        safe_tag = safe_filename(f"{page_name}_{breakpoint}_{theme_mode}")
        page_key = f"{page_name}_{breakpoint}_{theme_mode}"
        stage = "init"

        context = await browser.new_context(
            viewport=bp_config,
            device_scale_factor=1,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        self.network_logger.attach(page, page_tag=page_name, breakpoint=breakpoint, theme=theme_mode)

        try:
            stage = "goto"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            stage = "wait_body"
            await page.wait_for_selector("body", state="attached", timeout=15000)
            try:
                stage = "wait_networkidle"
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            stage = "post_wait"
            await page.wait_for_timeout(2000)

            stage = "apply_theme"
            await self.apply_theme_mode(page, theme_mode)

            stage = "screenshots"
            await self.capture_screenshots(page, safe_tag)
            stage = "save_html"
            html_path = await self.save_html(page, safe_tag)

            stage = "extract_css"
            css_urls = await self.extract_css_urls(page)
            stage = "download_css"
            css_data, css_font_faces, css_texts = await self.download_css(page, css_urls, safe_tag)
            stage = "inline_fonts"
            inline_font_faces, inline_css_texts = await self.collect_inline_font_faces(page, safe_tag)
            for face in css_font_faces + inline_font_faces:
                face["page"] = page_key
                self.font_faces.append(face)
            self.reduced_motion_detected = self.reduced_motion_detected or self.scan_reduced_motion(css_texts + inline_css_texts)

            stage = "font_probes"
            font_probes = await self.collect_font_probes(page, safe_tag, page_key)
            self.font_probes.extend(font_probes)

            if page_name == "home" and breakpoint == "desktop" and theme_mode == "default":
                stage = "tech_fingerprint"
                self.tech_stack = await self.collect_tech_fingerprint(page, css_data)

            stage = "collect_candidates"
            candidates = await self.collect_candidates(page, page_name, breakpoint, theme_mode, safe_tag)
            self.candidates.extend(candidates)

            if self.candidates_only:
                self.pages[page_key] = {
                    "url": url,
                    "html": str(html_path.relative_to(self.output_dir)),
                    "css": css_data,
                    "samples": [],
                    "candidates": [c.get("id") for c in candidates],
                    "font_probes_count": len(font_probes),
                }
                return

            stage = "collect_samples"
            samples = await self.collect_samples(page, page_name, breakpoint, theme_mode, safe_tag)
            if self.selected_selector_paths:
                samples = [
                    s for s in samples
                    if s.get("selector_path") in self.selected_selector_paths
                    or s.get("selector") in self.selected_selector_paths
                ]
            if not self.skip_overlays:
                stage = "collect_overlays"
                await self.collect_overlay_samples(page, page_name, breakpoint, theme_mode, safe_tag, samples)
            stage = "collect_states"
            await self.collect_states(page, samples)
            self.samples.extend(samples)

            stage = "page_finalize"
            self.pages[page_key] = {
                "url": url,
                "html": str(html_path.relative_to(self.output_dir)),
                "css": css_data,
                "samples": [s.get("id") for s in samples],
                "font_probes_count": len(font_probes),
            }

        except Exception as exc:
            self.pages[page_key] = {"url": url, "error": str(exc), "stage": stage}
            self.limits.append(f"Failed to collect {page_key} at {stage}: {exc}")
        finally:
            await context.close()

    async def apply_theme_mode(self, page: Page, theme_mode: str) -> None:
        if theme_mode == "default":
            return
        try:
            await page.evaluate(
                """(mode) => {
                    const root = document.documentElement;
                    root.setAttribute('data-theme', mode);
                    if (mode === 'dark') {
                        root.classList.add('dark');
                    }
                }""",
                theme_mode,
            )
            await page.wait_for_timeout(500)
        except Exception:
            self.limits.append(f"Theme mode '{theme_mode}' could not be applied programmatically")

    async def capture_screenshots(self, page: Page, safe_tag: str) -> None:
        full_path = self.screenshots_dir / f"{safe_tag}_full.png"
        await page.screenshot(path=str(full_path), full_page=True)
        self.evidence_paths["screenshots"].add(str(full_path.relative_to(self.output_dir)))

        navbar_path = self.screenshots_dir / f"{safe_tag}_navbar.png"
        try:
            navbar = await page.query_selector("nav, header, [role='navigation']")
            if navbar:
                await navbar.screenshot(path=str(navbar_path))
            else:
                viewport = page.viewport_size or {"width": 1440, "height": 900}
                await page.screenshot(
                    path=str(navbar_path),
                    clip={"x": 0, "y": 0, "width": viewport["width"], "height": 120},
                )
            self.evidence_paths["screenshots"].add(str(navbar_path.relative_to(self.output_dir)))
        except Exception:
            pass

    async def save_html(self, page: Page, safe_tag: str) -> Path:
        html_content = await page.evaluate("() => document.documentElement.outerHTML")
        html_path = self.html_dir / f"{safe_tag}.html"
        write_text(html_path, html_content)
        self.evidence_paths["html"].add(str(html_path.relative_to(self.output_dir)))
        return html_path

    async def extract_css_urls(self, page: Page) -> List[str]:
        css_urls = await page.evaluate(
            """() => {
                const urls = [];
                document.querySelectorAll('link[rel="stylesheet"]').forEach(el => urls.push(el.href));
                document.querySelectorAll('style').forEach(el => {
                    const matches = el.textContent.match(/@import\\s+url\\(['"]?([^'")]+)['"]?\\)/g);
                    if (matches) {
                        matches.forEach(m => {
                            const url = m.match(/@import\\s+url\\(['"]?([^'")]+)['"]?\\)/)[1];
                            urls.push(url);
                        });
                    }
                });
                return Array.from(new Set(urls));
            }"""
        )
        return css_urls

    async def download_css(self, page: Page, css_urls: List[str], safe_tag: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
        css_data: Dict[str, Any] = {}
        font_faces: List[Dict[str, Any]] = []
        css_texts: List[str] = []
        seen = set()

        for idx, url in enumerate(css_urls):
            if url in seen:
                continue
            seen.add(url)
            try:
                response = await page.request.get(url)
                content = await response.body()
                try:
                    css_text = content.decode("utf-8")
                except Exception:
                    css_text = content.decode("latin-1", errors="ignore")

                filename = f"{safe_tag}_{idx}.css"
                css_path = self.css_dir / filename
                write_text(css_path, css_text)
                self.evidence_paths["css"].add(str(css_path.relative_to(self.output_dir)))

                css_texts.append(css_text)
                font_faces.extend(self.parse_font_faces(css_text, {
                    "type": "external",
                    "url": url,
                    "file": str(css_path.relative_to(self.output_dir)),
                }))

                css_data[url] = {
                    "file": str(css_path.relative_to(self.output_dir)),
                    "size": len(content),
                    "keywords": self.scan_css_keywords(css_text),
                }
            except Exception as exc:
                css_data[url] = {"error": str(exc)}
        return css_data, font_faces, css_texts

    async def collect_inline_font_faces(self, page: Page, safe_tag: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        inline_styles = await page.evaluate(
            """() => Array.from(document.querySelectorAll('style')).map(el => el.textContent || '')"""
        )
        font_faces: List[Dict[str, Any]] = []
        css_texts: List[str] = []
        for idx, css_text in enumerate(inline_styles):
            if not css_text.strip():
                continue
            css_texts.append(css_text)
            inline_name = f"{safe_tag}_inline_{idx}.css"
            inline_path = self.css_dir / inline_name
            write_text(inline_path, css_text)
            self.evidence_paths["css"].add(str(inline_path.relative_to(self.output_dir)))
            font_faces.extend(self.parse_font_faces(css_text, {
                "type": "inline",
                "index": idx,
                "file": str(inline_path.relative_to(self.output_dir)),
            }))
        return font_faces, css_texts

    def parse_font_faces(self, css_text: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        faces = []
        for match in re.finditer(r"@font-face\s*{([^}]*)}", css_text, re.IGNORECASE | re.DOTALL):
            block = match.group(1)
            props = {}
            for decl in re.split(r";\s*", block):
                if not decl.strip() or ":" not in decl:
                    continue
                name, value = decl.split(":", 1)
                props[name.strip().lower()] = value.strip()
            faces.append({
                "font_family": props.get("font-family"),
                "src": props.get("src"),
                "font_style": props.get("font-style"),
                "font_weight": props.get("font-weight"),
                "unicode_range": props.get("unicode-range"),
                "source": source,
            })
        return faces

    def scan_css_keywords(self, css_text: str) -> Dict[str, Any]:
        keywords = {
            "tailwind": ["--tw-", "@layer", "ring-", "prose-", "preflight"],
            "bootstrap": ["--bs-", ".container", ".row", ".col-", ".btn"],
            "antd": [".ant-", "--ant-"],
            "mui": [".mui", "css-", "@emotion"],
            "chakra": ["--chakra-"],
            "radix": ["data-radix-", "[data-state"],
        }
        found = {}
        lower = css_text.lower()
        for framework, patterns in keywords.items():
            matches = [p for p in patterns if p.lower() in lower]
            if matches:
                found[framework] = {
                    "matches": matches,
                    "count": sum(lower.count(p.lower()) for p in patterns),
                }
        return found

    def scan_reduced_motion(self, css_texts: List[str]) -> bool:
        for css in css_texts:
            if "prefers-reduced-motion" in css:
                return True
        return False

    async def collect_font_probes(self, page: Page, safe_tag: str, page_key: str) -> List[Dict[str, Any]]:
        probes: List[Dict[str, Any]] = []
        probe_selectors = {
            "body": ["body"],
            "hero_h1": ["h1"],
            "section_h2": ["section h2", "h2"],
            "nav_link": ["nav a", "[role='navigation'] a", "header a"],
            "button_label": ["button", "[role='button']", "a[class*='button']", ".btn", ".button"],
            "card_title": [
                ".card h1", ".card h2", ".card h3",
                "[class*='card'] h1", "[class*='card'] h2", "[class*='card'] h3",
                "article h1", "article h2", "article h3",
            ],
        }

        for probe, selectors in probe_selectors.items():
            selected = None
            selected_meta = None
            selector_used = None
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    meta = await self.element_candidate_info(el, allow_empty_text=True)
                    if meta:
                        selected = el
                        selected_meta = meta
                        selector_used = selector
                        break
                if selected:
                    break

            if not selected or not selected_meta:
                continue

            styles = await self.computed_style(selected, TYPOGRAPHY_PROPS)
            probe_entry = {
                "page": page_key,
                "probe": probe,
                "selector_used": selector_used,
                "text": selected_meta.get("text"),
                "bbox": selected_meta.get("bbox"),
                "styles": styles,
            }
            probes.append(probe_entry)

        return probes

    async def computed_style(self, element, props: List[str]) -> Dict[str, str]:
        return await element.evaluate(
            """(el, props) => {
                const computed = window.getComputedStyle(el);
                const result = {};
                props.forEach(p => { result[p] = computed.getPropertyValue(p); });
                return result;
            }""",
            props,
        )

    async def element_candidate_info(self, el, allow_empty_text: bool = False) -> Optional[Dict[str, Any]]:
        try:
            box = await el.bounding_box()
            if not box or box["width"] < 24 or box["height"] < 24:
                return None
            meta = await el.evaluate(
                """el => {
                    const style = window.getComputedStyle(el);
                    return {
                        text: (el.textContent || '').trim(),
                        role: el.getAttribute('role'),
                        aria_label: el.getAttribute('aria-label'),
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                    };
                }"""
            )
            if meta.get("display") == "none" or meta.get("visibility") == "hidden":
                return None
            try:
                opacity_val = float(meta.get("opacity") or "1")
            except ValueError:
                opacity_val = 1.0
            if opacity_val <= 0:
                return None

            text = normalize_text(meta.get("text", ""))
            if not allow_empty_text and not text and not meta.get("role") and not meta.get("aria_label"):
                return None

            return {
                "text": text,
                "role": meta.get("role"),
                "aria_label": meta.get("aria_label"),
                "bbox": box,
            }
        except Exception:
            return None

    async def build_selector_path(self, el) -> str:
        return await el.evaluate(
            """(el) => {
                if (el.id) {
                    return '#' + CSS.escape(el.id);
                }
                const parts = [];
                let node = el;
                let depth = 0;
                while (node && node.nodeType === 1 && depth < 5) {
                    let selector = node.tagName.toLowerCase();
                    const classes = (node.className || '').toString().trim().split(/\\s+/).filter(Boolean);
                    if (classes.length) {
                        selector += '.' + classes.slice(0, 2).map(c => CSS.escape(c)).join('.');
                    }
                    const siblings = node.parentElement ? Array.from(node.parentElement.children).filter(n => n.tagName === node.tagName) : [];
                    if (siblings.length > 1) {
                        const index = siblings.indexOf(node) + 1;
                        selector += `:nth-of-type(${index})`;
                    }
                    parts.unshift(selector);
                    node = node.parentElement;
                    depth += 1;
                }
                return parts.join(' > ');
            }"""
        )

    def score_candidate(self, meta: Dict[str, Any], computed: Dict[str, Any], group: str, viewport_height: int) -> float:
        score = 0.0
        text = (meta.get("text") or "").lower()
        area = 0.0
        bbox = meta.get("bbox") or {}
        try:
            area = float(bbox.get("width", 0)) * float(bbox.get("height", 0))
        except Exception:
            area = 0.0

        if group in {"cta", "button"}:
            score += 2.5
        if group in {"headline"}:
            score += 2.0
        if group in {"nav"}:
            score += 1.0
        if any(k in text for k in ["get started", "start", "free", "trial", "sign up", "register"]):
            score += 3.0

        if area >= 20000:
            score += 1.0
        if bbox.get("y", 0) < viewport_height:
            score += 1.0

        font_weight = computed.get("font-weight", "").strip()
        try:
            if int(float(font_weight)) >= 700:
                score += 1.0
        except Exception:
            pass

        bg = (computed.get("background-color") or "").lower()
        bg_img = (computed.get("background-image") or "").lower()
        if bg and bg not in {"rgba(0, 0, 0, 0)", "transparent"}:
            score += 0.5
        if bg_img and bg_img != "none":
            score += 1.0

        return score

    async def collect_candidates(
        self,
        page: Page,
        page_name: str,
        breakpoint: str,
        theme_mode: str,
        safe_tag: str,
    ) -> List[Dict[str, Any]]:
        selector_groups = {
            "cta": [".hero__cta a", ".btn.btn-primary", ".btn-primary", "a.btn", "button"],
            "button": ["button", "a", "[role='button']", ".btn"],
            "nav": ["nav a", "header a", "[role='navigation'] a"],
            "headline": ["h1", "h2"],
            "text": ["p"],
            "media": ["img", "video", "picture"],
            "card": ["article", ".card", "[class*='card']"],
            "tag": [".tag", ".badge", ".pill", "[class*='tag']", "[class*='pill']", "[class*='badge']"],
        }

        candidates: List[Dict[str, Any]] = []
        seen_keys = set()
        max_per_group = 12
        viewport = page.viewport_size or {"width": 1440, "height": 900}
        viewport_height = viewport.get("height", 900)

        for group, selectors in selector_groups.items():
            collected = 0
            allow_empty = group in {"media"}
            for selector in selectors:
                if collected >= max_per_group:
                    break
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if collected >= max_per_group:
                        break
                    meta = await self.element_candidate_info(el, allow_empty_text=allow_empty)
                    if not meta:
                        continue

                    selector_path = await self.build_selector_path(el)
                    dedupe_key = (group, meta.get("text"), round(meta["bbox"]["width"], 1), round(meta["bbox"]["height"], 1))
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)

                    computed = await self.computed_style(el, CANDIDATE_PROPS)
                    score = self.score_candidate(meta, computed, group, viewport_height)

                    crop_name = f"{safe_tag}_candidate_{group}_{collected}.png"
                    crop_path = self.crops_dir / crop_name
                    crop_rel = None
                    try:
                        await el.screenshot(path=str(crop_path))
                        crop_rel = str(crop_path.relative_to(self.output_dir))
                        self.evidence_paths["crops"].add(crop_rel)
                    except Exception:
                        crop_rel = None

                    candidate_id = f"{safe_tag}_candidate_{group}_{collected}"
                    candidates.append({
                        "id": candidate_id,
                        "group": group,
                        "page": page_name,
                        "breakpoint": breakpoint,
                        "theme": theme_mode,
                        "selector": selector,
                        "selector_path": selector_path,
                        "text": meta.get("text"),
                        "role": meta.get("role"),
                        "aria_label": meta.get("aria_label"),
                        "bbox": meta.get("bbox"),
                        "crop_path": crop_rel,
                        "computed": computed,
                        "score": round(score, 2),
                    })
                    collected += 1

        return candidates

    async def collect_samples(
        self,
        page: Page,
        page_name: str,
        breakpoint: str,
        theme_mode: str,
        safe_tag: str,
    ) -> List[Dict[str, Any]]:
        selector_groups = {
            "typography": ["h1", "h2", "p", "small", "label"],
            "navbar": ["header", "nav", "[role='navigation']"],
            "nav_link": ["nav a", "[role='navigation'] a", "header a"],
            "container": ["main", "[role='main']", ".container", ".content", "#root", "#app"],
            "card": ["article", ".card", "[class*='card']", "[role='listitem']"],
            "grid_container": ["[class*='grid']", ".grid", "[role='list']", ".list"],
            "input": ["input", "textarea", "select", "[role='searchbox']", "form input"],
            "chip": [".chip", ".tag", ".badge", ".pill", "[class*='chip']"],
            "button": [
                "button",
                "a[class*='button']",
                "a.btn",
                "a.btn-primary",
                ".btn.btn-primary",
                ".btn-primary",
                ".btn",
                "[role='button']",
                ".button",
                ".hero__cta a",
            ],
        }

        samples: List[Dict[str, Any]] = []
        seen_keys = set()
        max_per_group = 6

        for component_type, selectors in selector_groups.items():
            collected = 0
            for selector in selectors:
                if collected >= max_per_group:
                    break
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if collected >= max_per_group:
                        break
                    meta = await self.element_candidate_info(el)
                    if not meta:
                        continue
                    if component_type == "chip":
                        if not await self.is_chip_like(el, meta):
                            continue

                    selector_path = await self.build_selector_path(el)
                    dedupe_key = (component_type, meta.get("text"), round(meta["bbox"]["width"], 1), round(meta["bbox"]["height"], 1))
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)

                    computed = await self.computed_style(el, ALL_PROPS)
                    crop_name = f"{safe_tag}_{component_type}_{collected}.png"
                    crop_path = self.crops_dir / crop_name
                    crop_rel = None
                    try:
                        await el.screenshot(path=str(crop_path))
                        crop_rel = str(crop_path.relative_to(self.output_dir))
                        self.evidence_paths["crops"].add(crop_rel)
                    except Exception:
                        crop_rel = None

                    sample_id = f"{safe_tag}_{component_type}_{collected}"
                    sample = {
                        "id": sample_id,
                        "component_type": component_type,
                        "page": page_name,
                        "breakpoint": breakpoint,
                        "theme": theme_mode,
                        "selector": selector,
                        "selector_path": selector_path,
                        "role": meta.get("role"),
                        "aria_label": meta.get("aria_label"),
                        "text": meta.get("text"),
                        "bbox": meta.get("bbox"),
                        "crop_path": crop_rel,
                        "computed": computed,
                        "states": {},
                        "diffs": {},
                    }
                    samples.append(sample)
                    collected += 1

        return samples

    async def is_chip_like(self, el, meta: Dict[str, Any]) -> bool:
        try:
            styles = await self.computed_style(el, ["border-radius", "height", "display"])
            height = parse_length(styles.get("height", "")) or meta["bbox"]["height"]
            radius = parse_length(styles.get("border-radius", "")) or 0
            display = (styles.get("display") or "").lower()
            return height <= 40 and radius >= height / 2 and "inline" in display
        except Exception:
            return False

    async def collect_overlay_samples(
        self,
        page: Page,
        page_name: str,
        breakpoint: str,
        theme_mode: str,
        safe_tag: str,
        samples: List[Dict[str, Any]],
    ) -> None:
        triggers = await page.query_selector_all(
            "[aria-haspopup], [aria-expanded], [data-state], button, [role='button']"
        )
        trigger_candidates = []
        for el in triggers:
            meta = await self.element_candidate_info(el, allow_empty_text=True)
            if not meta:
                continue
            text = (meta.get("text") or "").lower()
            if any(k in text for k in ["filter", "sort", "menu", "more", "options"]):
                trigger_candidates.append(el)
            if len(trigger_candidates) >= 3:
                break

        for idx, trigger in enumerate(trigger_candidates):
            try:
                await trigger.scroll_into_view_if_needed()
                await trigger.click(timeout=3000)
            except Exception:
                try:
                    await trigger.hover()
                except Exception:
                    self.limits.append("Overlay trigger could not be activated")
                    continue

            await page.wait_for_timeout(500)
            panels = await page.query_selector_all(
                "[role='dialog'], [role='menu'], [role='listbox'], [role='tooltip'], [data-state='open']"
            )
            panel = None
            panel_meta = None
            for candidate in panels:
                meta = await self.element_candidate_info(candidate, allow_empty_text=True)
                if meta:
                    panel = candidate
                    panel_meta = meta
                    break

            if not panel or not panel_meta:
                self.limits.append("Overlay panel not detected after trigger")
                continue

            selector_path = await self.build_selector_path(panel)
            computed = await self.computed_style(panel, ALL_PROPS)
            crop_name = f"{safe_tag}_overlay_panel_{idx}.png"
            crop_path = self.crops_dir / crop_name
            crop_rel = None
            try:
                await panel.screenshot(path=str(crop_path))
                crop_rel = str(crop_path.relative_to(self.output_dir))
                self.evidence_paths["crops"].add(crop_rel)
            except Exception:
                pass

            samples.append({
                "id": f"{safe_tag}_overlay_panel_{idx}",
                "component_type": "overlay_panel",
                "page": page_name,
                "breakpoint": breakpoint,
                "theme": theme_mode,
                "selector": "overlay_panel",
                "selector_path": selector_path,
                "role": panel_meta.get("role"),
                "aria_label": panel_meta.get("aria_label"),
                "text": panel_meta.get("text"),
                "bbox": panel_meta.get("bbox"),
                "crop_path": crop_rel,
                "computed": computed,
                "states": {},
                "diffs": {},
            })

    async def collect_states(self, page: Page, samples: List[Dict[str, Any]]) -> None:
        base_url = page.url
        for sample in samples:
            if sample["component_type"] not in {"button", "nav_link", "input", "chip", "card"}:
                continue
            selector_path = sample.get("selector_path")
            if not selector_path:
                continue
            try:
                el = await page.query_selector(selector_path)
                if not el:
                    el = await self.find_element_by_text_role(page, sample)
                if not el:
                    sample["diffs"] = {"error": "element_not_found"}
                    continue

                try:
                    await el.scroll_into_view_if_needed()
                except Exception:
                    pass

                default_styles = await self.computed_style(el, STATE_DIFF_PROPS)
                sample["states"]["default"] = default_styles

                is_navigational = await el.evaluate(
                    """el => {
                        const tag = (el.tagName || '').toLowerCase();
                        if (tag === 'a') return true;
                        if (el.getAttribute('role') === 'link') return true;
                        if (el.closest('a')) return true;
                        const href = el.getAttribute('href');
                        if (href && href !== '#' && href !== 'javascript:void(0)') return true;
                        return false;
                    }"""
                )

                hover_styles, hover_reason = await self.try_hover(el)
                focus_styles, focus_reason = await self.try_focus_visible(page, el)
                if is_navigational and not self.allow_anchor_active:
                    active_styles, active_reason = {"error": "active skipped for navigational element"}, "skipped navigational element"
                else:
                    active_styles, active_reason = await self.try_active(page, el)

                states = {
                    "hover": hover_styles,
                    "focus_visible": focus_styles,
                    "active": active_styles,
                }

                sample["states"].update(states)
                sample["diffs"] = {
                    "hover": self.compute_state_diff(default_styles, hover_styles, hover_reason),
                    "focus_visible": self.compute_state_diff(default_styles, focus_styles, focus_reason),
                    "active": self.compute_state_diff(default_styles, active_styles, active_reason),
                }
            except Exception as exc:
                sample["diffs"] = {"error": str(exc)}
                try:
                    if page.url != base_url:
                        await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

    async def try_hover(self, el) -> Tuple[Dict[str, Any], str]:
        try:
            await el.hover()
            styles = await self.computed_style(el, STATE_DIFF_PROPS)
            return styles, ""
        except Exception as exc:
            return {"error": "hover failed"}, str(exc)

    async def try_focus_visible(self, page: Page, el) -> Tuple[Dict[str, Any], str]:
        try:
            await page.keyboard.press("Tab")
            await el.evaluate("el => el.focus()")
            styles = await self.computed_style(el, STATE_DIFF_PROPS)
            return styles, ""
        except Exception as exc:
            return {"error": "focus failed"}, str(exc)

    async def try_active(self, page: Page, el) -> Tuple[Dict[str, Any], str]:
        try:
            box = await el.bounding_box()
            if not box:
                raise RuntimeError("no bounding box")
            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            await page.mouse.down()
            styles = await self.computed_style(el, STATE_DIFF_PROPS)
            return styles, ""
        except Exception as exc:
            return {"error": "active failed"}, str(exc)
        finally:
            try:
                await page.mouse.up()
            except Exception:
                pass

    def compute_state_diff(self, default: Dict[str, Any], state: Dict[str, Any], reason: str) -> Dict[str, Any]:
        if not isinstance(state, dict) or "error" in state:
            return {"changed": {}, "reason": reason or "state failed"}
        changed = {}
        for prop, val in state.items():
            if prop in default and val != default[prop]:
                changed[prop] = [default[prop], val]
        return {"changed": changed, "reason": ""}

    async def find_element_by_text_role(self, page: Page, sample: Dict[str, Any]):
        text = sample.get("text") or ""
        role = sample.get("role")
        if not text and not role:
            return None
        handle = await page.evaluate_handle(
            """({text, role}) => {
                const candidates = Array.from(document.querySelectorAll('*'));
                for (const el of candidates) {
                    const matchesRole = role ? el.getAttribute('role') === role : true;
                    const matchesText = text ? (el.textContent || '').trim().includes(text) : true;
                    if (matchesRole && matchesText) return el;
                }
                return null;
            }""",
            {"text": text, "role": role},
        )
        return handle.as_element() if handle else None

    async def collect_tech_fingerprint(self, page: Page, css_data: Dict[str, Any]) -> Dict[str, Any]:
        fingerprint = {
            "framework": {"name": "", "confidence": "Uncertain", "evidence": []},
            "styling": {"name": "", "confidence": "Uncertain", "evidence": []},
            "icons": {"name": "", "confidence": "Uncertain", "evidence": []},
            "ui_libs": {"items": [], "evidence": []},
        }

        runtime_checks = await page.evaluate(
            """() => ({
                next: !!window.__NEXT_DATA__,
                nuxt: !!window.__NUXT__,
                vue: !!window.__VUE_DEVTOOLS_GLOBAL_HOOK__,
                react: !!window.__REACT_DEVTOOLS_GLOBAL_HOOK__,
                astro: !!document.querySelector('html[data-astro]'),
            })"""
        )

        if runtime_checks.get("next"):
            fingerprint["framework"] = {"name": "Next.js", "confidence": "Confirmed", "evidence": ["window.__NEXT_DATA__"]}
        elif runtime_checks.get("nuxt"):
            fingerprint["framework"] = {"name": "Nuxt", "confidence": "Confirmed", "evidence": ["window.__NUXT__"]}
        elif runtime_checks.get("react"):
            fingerprint["framework"] = {"name": "React", "confidence": "Likely", "evidence": ["React devtools hook"]}
        elif runtime_checks.get("vue"):
            fingerprint["framework"] = {"name": "Vue", "confidence": "Likely", "evidence": ["Vue devtools hook"]}
        elif runtime_checks.get("astro"):
            fingerprint["framework"] = {"name": "Astro", "confidence": "Likely", "evidence": ["html[data-astro]"]}

        keyword_hits = defaultdict(int)
        for url, meta in css_data.items():
            for lib, info in (meta.get("keywords") or {}).items():
                keyword_hits[lib] += info.get("count", 0)
        if keyword_hits:
            top = max(keyword_hits.items(), key=lambda x: x[1])
            if top[0] == "tailwind":
                fingerprint["styling"] = {"name": "Tailwind", "confidence": "Likely", "evidence": ["CSS keyword hits"]}
            else:
                fingerprint["styling"] = {"name": top[0], "confidence": "Likely", "evidence": ["CSS keyword hits"]}

        icon_system = await page.evaluate(
            """() => {
                const svgCount = document.querySelectorAll('svg').length;
                const useCount = document.querySelectorAll('svg use').length;
                return {svgCount, useCount};
            }"""
        )
        if icon_system.get("svgCount", 0) > 10:
            fingerprint["icons"] = {"name": "Inline SVG", "confidence": "Likely", "evidence": ["svg elements detected"]}

        ui_libs = []
        for lib in ["mui", "antd", "chakra", "radix"]:
            if keyword_hits.get(lib, 0) > 0:
                ui_libs.append(lib)
        if ui_libs:
            fingerprint["ui_libs"] = {"items": ui_libs, "evidence": ["CSS keyword hits"]}

        return fingerprint

    def build_results(self, font_request_path: Path) -> Dict[str, Any]:
        template_path = self.templates_dir / "results.json"
        results = json.loads(read_text(template_path))

        results["meta"] = {
            "site_name": extract_site_name(self.base_url),
            "target_site_base_url": self.base_url,
            "home_path": self.home_path,
            "nav_path": self.nav_path or "",
            "collected_at": now_iso(),
            "theme_modes": self.theme_modes,
            "breakpoints": {
                name: f"{cfg['width']}x{cfg['height']}" for name, cfg in self.breakpoints.items()
            },
        }

        results["evidence"] = {
            "screenshots": sorted(self.evidence_paths["screenshots"]),
            "crops": sorted(self.evidence_paths["crops"]),
            "html": sorted(self.evidence_paths["html"]),
            "css": sorted(self.evidence_paths["css"]),
            "fonts": sorted(self.evidence_paths["fonts"]),
            "samples": sorted(self.evidence_paths["samples"]),
            "network": sorted(self.evidence_paths["network"]),
        }

        results["tech_stack"] = self.tech_stack or results.get("tech_stack", {})

        font_requests = json.loads(read_text(font_request_path)).get("items", [])
        font_conclusion = self.build_font_conclusion(font_requests)
        results["font_forensics"] = {
            "verified_status": font_conclusion.get("status"),
            "network_requests": font_requests,
            "font_faces": self.font_faces,
            "computed_probes": self.font_probes,
            "conclusion": font_conclusion.get("conclusion"),
        }

        tokens = self.cluster_tokens()
        results["tokens"]["primitive"] = tokens.get("primitive")
        results["tokens"]["semantic"] = tokens.get("semantic")
        results["tokens"]["component"] = tokens.get("component")

        interaction_model = self.build_interaction_model()
        results["interaction_model"] = interaction_model

        results["density_rhythm"] = self.build_density_rhythm()
        results["layout_grammar"] = self.build_layout_grammar()
        results["accessibility"] = self.build_accessibility()

        if self.limits:
            results["notes"] = ["Limits:"] + self.limits
        else:
            results["notes"] = ["Limits: none detected"]

        return results

    def build_font_conclusion(self, font_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        families = []
        from_faces = [f.get("font_family") for f in self.font_faces if f.get("font_family")]
        for fam in from_faces:
            fam = fam.replace('"', "").replace("'", "")
            families.append(fam)
        primary = sorted(set(families))

        computed_families = []
        for probe in self.font_probes:
            styles = probe.get("styles", {})
            fam = styles.get("font-family", "")
            if fam:
                computed_families.append(fam)

        verified = False
        for fam in computed_families:
            first = fam.split(",")[0].strip().strip("\"").lower()
            if first and first not in SYSTEM_FONTS and any(first in f.lower() for f in primary):
                verified = True
                break
        if not verified and font_requests and computed_families:
            verified = True

        return {
            "status": "VERIFIED" if verified else "UNVERIFIED",
            "conclusion": {
                "primary_families": primary,
                "fallbacks": [],
                "variable_axes": [],
                "notes": [],
            },
        }

    def cluster_tokens(self) -> Dict[str, Any]:
        primitive = json.loads(read_text(self.templates_dir / "results.json")).get("tokens", {}).get("primitive", {})
        semantic = json.loads(read_text(self.templates_dir / "results.json")).get("tokens", {}).get("semantic", {})
        component = json.loads(read_text(self.templates_dir / "results.json")).get("tokens", {}).get("component", {})

        color_neutrals = Counter()
        color_accents = Counter()
        color_opacity = Counter()

        font_sizes = Counter()
        line_heights = Counter()
        letter_spacing = Counter()
        font_weights = Counter()

        spacing_values = Counter()
        radius_values = Counter()
        border_values = Counter()
        shadow_values = Counter()
        motion_durations = Counter()
        motion_easings = Counter()
        motion_properties = Counter()
        z_index_values = Counter()

        for sample in self.samples:
            computed = sample.get("computed", {})
            if not computed:
                continue

            fg = parse_color(computed.get("color", ""))
            bg = parse_color(computed.get("background-color", ""))
            border = parse_color(computed.get("border-color", ""))
            outline = parse_color(computed.get("outline-color", ""))

            for color in [fg, bg, border, outline]:
                if not color:
                    continue
                color_str = color_to_string(color)
                if color_is_neutral(color):
                    color_neutrals[color_str] += 1
                else:
                    color_accents[color_str] += 1
                if color[3] < 1:
                    color_opacity[str(round(color[3], 3))] += 1

            for key, counter in [
                ("font-size", font_sizes),
                ("line-height", line_heights),
                ("letter-spacing", letter_spacing),
                ("font-weight", font_weights),
            ]:
                val = computed.get(key, "")
                if not val:
                    continue
                counter[val.strip()] += 1

            for key in [
                "padding-top",
                "padding-right",
                "padding-bottom",
                "padding-left",
                "margin-top",
                "margin-right",
                "margin-bottom",
                "margin-left",
                "gap",
            ]:
                val = computed.get(key, "")
                if val and val not in {"0px", "0"}:
                    spacing_values[val.strip()] += 1

            radius = computed.get("border-radius")
            if radius and radius != "0px":
                radius_values[radius.strip()] += 1

            border_w = computed.get("border-width")
            if border_w and border_w != "0px":
                border_values[border_w.strip()] += 1

            shadow = computed.get("box-shadow")
            if shadow and shadow != "none":
                shadow_values[shadow.strip()] += 1

            duration = computed.get("transition-duration")
            if duration and duration != "0s":
                motion_durations[duration.strip()] += 1
            easing = computed.get("transition-timing-function")
            if easing and easing != "ease":
                motion_easings[easing.strip()] += 1
            props = computed.get("transition-property")
            if props and props != "all":
                for prop in props.split(","):
                    prop = prop.strip()
                    if prop:
                        motion_properties[prop] += 1

            z_index = computed.get("z-index")
            if z_index and z_index not in {"auto", "0"}:
                z_index_values[z_index.strip()] += 1

        neutral_top, neutral_outliers = self.split_counter(color_neutrals)
        accent_top, accent_outliers = self.split_counter(color_accents)
        opacity_top, opacity_outliers = self.split_counter(color_opacity)
        primitive["color"]["neutrals"] = neutral_top
        primitive["color"]["accents"] = accent_top
        primitive["color"]["opacity"] = opacity_top
        primitive["color"]["outliers"] = neutral_outliers + accent_outliers + opacity_outliers

        font_scale_top, font_scale_outliers = self.split_counter(font_sizes)
        line_height_top, line_height_outliers = self.split_counter(line_heights)
        letter_spacing_top, letter_spacing_outliers = self.split_counter(letter_spacing)
        font_weight_top, font_weight_outliers = self.split_counter(font_weights)
        primitive["typography"]["scale"] = font_scale_top
        primitive["typography"]["line_heights"] = line_height_top
        primitive["typography"]["letter_spacing"] = letter_spacing_top
        primitive["typography"]["weights"] = font_weight_top
        primitive["typography"]["outliers"] = (
            font_scale_outliers
            + line_height_outliers
            + letter_spacing_outliers
            + font_weight_outliers
        )

        spacing_top, spacing_outliers = self.split_counter(spacing_values)
        primitive["spacing"]["scale"] = spacing_top
        primitive["spacing"]["outliers"] = spacing_outliers

        radius_top, radius_outliers = self.split_counter(radius_values)
        primitive["radius"]["scale"] = radius_top
        primitive["radius"]["outliers"] = radius_outliers

        border_top, border_outliers = self.split_counter(border_values)
        primitive["border_width"]["scale"] = border_top
        primitive["border_width"]["outliers"] = border_outliers

        shadow_top, shadow_outliers = self.split_counter(shadow_values)
        primitive["shadow"]["scale"] = shadow_top
        primitive["shadow"]["outliers"] = shadow_outliers

        duration_top, duration_outliers = self.split_counter(motion_durations)
        easing_top, easing_outliers = self.split_counter(motion_easings)
        properties_top, properties_outliers = self.split_counter(motion_properties)
        primitive["motion"]["durations"] = duration_top
        primitive["motion"]["easings"] = easing_top
        primitive["motion"]["properties"] = properties_top
        primitive["motion"]["outliers"] = duration_outliers + easing_outliers + properties_outliers

        z_top, z_outliers = self.split_counter(z_index_values)
        primitive["z_index"]["scale"] = z_top
        primitive["z_index"]["outliers"] = z_outliers

        return {"primitive": primitive, "semantic": semantic, "component": component}

    def split_counter(
        self, counter: Counter, top_n: int = 12
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        items = counter.most_common()
        top = [{"value": v, "count": c} for v, c in items[:top_n]]
        outliers = [{"value": v, "count": c} for v, c in items[top_n:]]
        return top, outliers

    def build_interaction_model(self) -> Dict[str, Any]:
        state_matrix = []
        state_diffs = []
        patterns = {
            "hover": [],
            "focus_visible": [],
            "pressed_selected": [],
            "overlays": [],
        }

        for sample in self.samples:
            states = sample.get("states", {})
            if not states:
                continue
            entry = {
                "component": sample.get("component_type"),
                "id": sample.get("id"),
                "states": list(states.keys()),
            }
            state_matrix.append(entry)

            diffs = sample.get("diffs", {})
            for state_name, diff in diffs.items():
                if not diff:
                    continue
                state_diffs.append({
                    "component": sample.get("component_type"),
                    "id": sample.get("id"),
                    "state": state_name,
                    "changed": diff.get("changed", {}),
                    "reason": diff.get("reason", ""),
                })

        return {
            "state_matrix": state_matrix,
            "patterns": patterns,
            "state_diffs": state_diffs,
        }

    def build_density_rhythm(self) -> Dict[str, Any]:
        controls = defaultdict(list)
        card_paddings = []
        list_row_heights = []
        section_spacing = []

        for sample in self.samples:
            bbox = sample.get("bbox") or {}
            height = bbox.get("height")
            if sample.get("component_type") in {"button", "input", "chip"} and height:
                controls[sample["component_type"]].append(height)
            if sample.get("component_type") == "card" and height:
                card_paddings.append(height)

        density = {
            "control_heights": {k: self.stats_summary(v) for k, v in controls.items()},
            "section_spacing": {"values": section_spacing},
            "list_row_heights": {"values": list_row_heights},
            "card_padding_gaps": {"values": card_paddings},
            "breakpoint_deltas": [],
            "evidence": [],
        }
        return density

    def stats_summary(self, values: List[float]) -> Dict[str, Any]:
        if not values:
            return {}
        values_sorted = sorted(values)
        return {
            "median": statistics.median(values_sorted),
            "p25": statistics.quantiles(values_sorted, n=4)[0] if len(values_sorted) >= 4 else values_sorted[0],
            "p75": statistics.quantiles(values_sorted, n=4)[2] if len(values_sorted) >= 4 else values_sorted[-1],
            "count": len(values_sorted),
        }

    def build_layout_grammar(self) -> Dict[str, Any]:
        container_steps = []
        gutters = {}
        grid_rules = []
        min_card_width = {}

        for sample in self.samples:
            if sample.get("component_type") == "container":
                computed = sample.get("computed", {})
                entry = {
                    "breakpoint": sample.get("breakpoint"),
                    "width": computed.get("width"),
                    "max_width": computed.get("max-width"),
                    "padding_left": computed.get("padding-left"),
                    "padding_right": computed.get("padding-right"),
                }
                container_steps.append(entry)
                bp = sample.get("breakpoint")
                if bp:
                    gutters.setdefault(bp, []).append({
                        "left": computed.get("padding-left"),
                        "right": computed.get("padding-right"),
                    })
            if sample.get("component_type") == "grid_container":
                computed = sample.get("computed", {})
                grid_rules.append({
                    "display": computed.get("display"),
                    "grid_template": computed.get("grid-template-columns"),
                    "gap": computed.get("gap"),
                    "breakpoint": sample.get("breakpoint"),
                })
            if sample.get("component_type") == "card":
                bbox = sample.get("bbox") or {}
                width = bbox.get("width")
                if width:
                    min_card_width.setdefault(sample.get("breakpoint"), []).append(width)

        for bp, values in min_card_width.items():
            if values:
                min_card_width[bp] = min(values)

        for bp, values in gutters.items():
            if not values:
                continue
            gutters[bp] = values[:3]

        layout = {
            "container_steps": container_steps,
            "gutters": gutters,
            "grid_rules": grid_rules,
            "min_card_width": min_card_width,
            "evidence": [],
        }
        return layout

    def build_accessibility(self) -> Dict[str, Any]:
        focus_rings = []
        target_sizes = []
        contrast_samples = []

        for sample in self.samples:
            bbox = sample.get("bbox") or {}
            if bbox.get("width") and bbox.get("height"):
                if bbox.get("width") < 44 or bbox.get("height") < 44:
                    target_sizes.append({
                        "id": sample.get("id"),
                        "component": sample.get("component_type"),
                        "width": bbox.get("width"),
                        "height": bbox.get("height"),
                    })

            focus_state = (sample.get("states") or {}).get("focus_visible")
            if focus_state and isinstance(focus_state, dict) and "error" not in focus_state:
                focus_rings.append({
                    "id": sample.get("id"),
                    "outline": focus_state.get("outline-color"),
                    "outline_width": focus_state.get("outline-width"),
                    "outline_offset": focus_state.get("outline-offset"),
                    "box_shadow": focus_state.get("box-shadow"),
                })

            computed = sample.get("computed", {})
            fg = parse_color(computed.get("color", ""))
            bg = parse_color(computed.get("background-color", ""))
            if fg and bg and bg[3] > 0.9:
                ratio = contrast_ratio((fg[0], fg[1], fg[2]), (bg[0], bg[1], bg[2]))
                contrast_samples.append({
                    "id": sample.get("id"),
                    "component": sample.get("component_type"),
                    "fg": color_to_string(fg),
                    "bg": color_to_string(bg),
                    "ratio": round(ratio, 2),
                })

        accessibility = {
            "focus_ring": {"samples": focus_rings},
            "target_sizes": target_sizes,
            "contrast_samples": contrast_samples,
            "reduced_motion": {"detected": self.reduced_motion_detected},
            "notes": [],
        }
        return accessibility

    def render_report(self, results: Dict[str, Any]) -> str:
        template = read_text(self.templates_dir / "report.md")
        meta = results.get("meta", {})
        tech = results.get("tech_stack", {})
        font_forensics = results.get("font_forensics", {})

        def join_list(items: List[str]) -> str:
            if not items:
                return "-"
            return "\n".join([f"- {item}" for item in items])

        def simple_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
            if not rows:
                return "(none)"
            header = "| " + " | ".join(columns) + " |\n"
            divider = "|" + "|".join([" --- " for _ in columns]) + "|\n"
            body = ""
            for row in rows[:10]:
                body += "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |\n"
            return header + divider + body

        replacements = {
            "site_name": meta.get("site_name", ""),
            "collected_at": meta.get("collected_at", ""),
            "target_site_base_url": meta.get("target_site_base_url", ""),
            "home_path": meta.get("home_path", ""),
            "nav_path": meta.get("nav_path", ""),
            "theme_modes": ", ".join(meta.get("theme_modes", [])),
            "bp_desktop": meta.get("breakpoints", {}).get("desktop", ""),
            "bp_tablet": meta.get("breakpoints", {}).get("tablet", ""),
            "bp_mobile": meta.get("breakpoints", {}).get("mobile", ""),
            "framework.name": tech.get("framework", {}).get("name", ""),
            "framework.confidence": tech.get("framework", {}).get("confidence", ""),
            "framework.evidence": join_list(tech.get("framework", {}).get("evidence", [])),
            "styling.name": tech.get("styling", {}).get("name", ""),
            "styling.confidence": tech.get("styling", {}).get("confidence", ""),
            "styling.evidence": join_list(tech.get("styling", {}).get("evidence", [])),
            "icons.name": tech.get("icons", {}).get("name", ""),
            "icons.confidence": tech.get("icons", {}).get("confidence", ""),
            "icons.evidence": join_list(tech.get("icons", {}).get("evidence", [])),
            "ui_libs": ", ".join(tech.get("ui_libs", {}).get("items", [])),
            "ui_libs_evidence": join_list(tech.get("ui_libs", {}).get("evidence", [])),
            "font_requests_table": simple_table(
                font_forensics.get("network_requests", []),
                ["url", "status", "content_type"],
            ),
            "font_face_table": simple_table(
                font_forensics.get("font_faces", []),
                ["font_family", "font_weight", "font_style"],
            ),
            "computed_font_probes_table": simple_table(
                font_forensics.get("computed_probes", []),
                ["probe", "selector_used", "page"],
            ),
            "font_verified_status": font_forensics.get("verified_status", "UNVERIFIED"),
            "paths_screenshots": join_list(results.get("evidence", {}).get("screenshots", [])),
            "paths_key_sections": join_list([]),
            "paths_crops": join_list(results.get("evidence", {}).get("crops", [])),
            "paths_html": join_list(results.get("evidence", {}).get("html", [])),
            "paths_css": join_list(results.get("evidence", {}).get("css", [])),
            "paths_fonts": join_list(results.get("evidence", {}).get("fonts", [])),
            "paths_samples": join_list(results.get("evidence", {}).get("samples", [])),
            "paths_network": join_list(results.get("evidence", {}).get("network", [])),
            "primitive_colors_neutrals": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("color", {}).get("neutrals", [])]),
            "primitive_colors_accents": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("color", {}).get("accents", [])]),
            "primitive_opacity": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("color", {}).get("opacity", [])]),
            "primitive_glass_blur": "-",
            "primitive_typography_scale": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("typography", {}).get("scale", [])]),
            "primitive_spacing_core": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("spacing", {}).get("scale", [])]),
            "primitive_spacing_outliers": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("spacing", {}).get("outliers", [])]),
            "primitive_size_scale": join_list([]),
            "primitive_radius": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("radius", {}).get("scale", [])]),
            "primitive_border_width": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("border_width", {}).get("scale", [])]),
            "primitive_shadow": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("shadow", {}).get("scale", [])]),
            "primitive_motion_durations": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("motion", {}).get("durations", [])]),
            "primitive_motion_easings": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("motion", {}).get("easings", [])]),
            "primitive_motion_properties": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("motion", {}).get("properties", [])]),
            "primitive_z_index": join_list([str(i) for i in results.get("tokens", {}).get("primitive", {}).get("z_index", {}).get("scale", [])]),
            "layout_container_steps": join_list(results.get("layout_grammar", {}).get("container_steps", [])),
            "layout_gutters": join_list([str(i) for i in results.get("layout_grammar", {}).get("gutters", {}).items()]),
            "layout_grid_primitives": join_list([str(i) for i in results.get("layout_grammar", {}).get("grid_rules", [])]),
            "semantic_tokens_block": "(pending)",
            "interaction_state_matrix_table": simple_table(
                results.get("interaction_model", {}).get("state_matrix", []),
                ["component", "id", "states"],
            ),
            "component_navbar": "(pending)",
            "component_button": "(pending)",
            "component_input": "(pending)",
            "component_card": "(pending)",
            "component_chip": "(pending)",
            "component_grid": "(pending)",
            "component_map_block": "(pending)",
            "responsive_rules_block": "(pending)",
            "implementation.strategy": "TBD",
            "implementation.tailwind_config_path": "",
            "implementation.tokens_ts_path": "",
            "implementation.css_vars_path": "",
            "implementation.examples": "",
            "limits_block": join_list(results.get("notes", [])),
        }

        for key, value in replacements.items():
            template = template.replace("{{" + key + "}}", str(value))

        return template

    def render_guide(self, results: Dict[str, Any]) -> str:
        template = read_text(self.templates_dir / "guide.md")
        meta = results.get("meta", {})
        replacements = {
            "target_site_base_url": meta.get("target_site_base_url", ""),
            "home_path": meta.get("home_path", ""),
            "nav_path": meta.get("nav_path", ""),
            "theme_modes": ", ".join(meta.get("theme_modes", [])),
            "collected_at": meta.get("collected_at", ""),
            "limit": " | ".join(results.get("notes", [])),
            "owner_or_team": "",
        }
        for key, value in replacements.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template

    def render_ui_ux(self, results: Dict[str, Any]) -> str:
        template = read_text(self.templates_dir / "ui-ux.md")
        meta = results.get("meta", {})
        evidence = results.get("evidence", {})
        tokens = results.get("tokens", {}).get("primitive", {})
        density = results.get("density_rhythm", {})
        layout = results.get("layout_grammar", {})
        accessibility = results.get("accessibility", {})
        interaction = results.get("interaction_model", {})

        def join_list(items: List[str]) -> str:
            if not items:
                return "-"
            return "\n".join([f"- {item}" for item in items])

        def format_top(items: List[Dict[str, Any]], limit: int = 4) -> str:
            if not items:
                return "-"
            values = []
            for item in items[:limit]:
                value = item.get("value", item)
                values.append(str(value))
            return ", ".join(values)

        def summarize_control_heights() -> str:
            control_heights = density.get("control_heights", {})
            if not control_heights:
                return "No control height evidence"
            parts = []
            for name, stats in control_heights.items():
                if not stats:
                    continue
                parts.append(f"{name}: ~{round(stats.get('median', 0), 1)}px")
            return ", ".join(parts) if parts else "No control height evidence"

        def summarize_layout() -> str:
            container_steps = layout.get("container_steps", [])
            grid_rules = layout.get("grid_rules", [])
            if not container_steps and not grid_rules:
                return "No layout evidence"
            details = []
            if container_steps:
                sample = container_steps[:2]
                details.append(f"Containers: {len(container_steps)} samples")
                if sample[0].get("max_width"):
                    details.append(f"max-width {sample[0].get('max_width')}")
            if grid_rules:
                details.append(f"Grid rules: {len(grid_rules)} samples")
            return "; ".join(details)

        def summarize_motion() -> str:
            motion = tokens.get("motion", {})
            durations = format_top(motion.get("durations", []))
            easings = format_top(motion.get("easings", []))
            if durations == "-" and easings == "-":
                return "No motion evidence"
            return f"durations {durations}; easings {easings}"

        def summarize_accessibility() -> str:
            focus_samples = accessibility.get("focus_ring", {}).get("samples", [])
            target_sizes = accessibility.get("target_sizes", [])
            reduced_motion = accessibility.get("reduced_motion", {}).get("detected", False)
            return (
                f"focus ring samples {len(focus_samples)}, "
                f"small targets {len(target_sizes)}, "
                f"reduced motion {'detected' if reduced_motion else 'not detected'}"
            )

        def summarize_interaction() -> Tuple[str, str]:
            diffs = interaction.get("state_diffs", [])
            changed = [d for d in diffs if d.get("changed")]
            components = {d.get("component") for d in diffs if d.get("component")}
            if not diffs:
                return ("No interaction diffs captured", "No state evidence")
            return (
                f"{len(changed)} diffs across {len(components)} components",
                f"{len(diffs)} state captures",
            )

        def summarize_typography() -> str:
            typography = tokens.get("typography", {})
            scale = format_top(typography.get("scale", []))
            weights = format_top(typography.get("weights", []))
            return f"scale {scale}; weights {weights}"

        def summarize_colors() -> str:
            colors = tokens.get("color", {})
            neutrals = format_top(colors.get("neutrals", []))
            accents = format_top(colors.get("accents", []))
            return f"neutrals {neutrals}; accents {accents}"

        def summarize_components() -> str:
            component_types = sorted({s.get("component_type") for s in self.samples if s.get("component_type")})
            return ", ".join(component_types) if component_types else "No component samples"

        interaction_summary, state_summary = summarize_interaction()
        nav_samples = [s for s in self.samples if s.get("component_type") in {"navbar", "nav_link"}]
        if nav_samples:
            navigation_summary = f"nav samples {len(nav_samples)}"
        else:
            navigation_summary = "No navigation samples"

        replacements = {
            "site_name": meta.get("site_name", ""),
            "collected_at": meta.get("collected_at", ""),
            "target_site_base_url": meta.get("target_site_base_url", ""),
            "theme_modes": ", ".join(meta.get("theme_modes", [])),
            "bp_desktop": meta.get("breakpoints", {}).get("desktop", ""),
            "bp_tablet": meta.get("breakpoints", {}).get("tablet", ""),
            "bp_mobile": meta.get("breakpoints", {}).get("mobile", ""),
            "ux_interaction_summary": interaction_summary,
            "ux_navigation_summary": navigation_summary,
            "ux_state_summary": state_summary,
            "ux_motion_summary": summarize_motion(),
            "ux_accessibility_summary": summarize_accessibility(),
            "ui_typography_summary": summarize_typography(),
            "ui_color_summary": summarize_colors(),
            "ui_density_summary": summarize_control_heights(),
            "ui_layout_summary": summarize_layout(),
            "ui_component_summary": summarize_components(),
            "paths_screenshots": join_list(evidence.get("screenshots", [])),
            "paths_samples": join_list(evidence.get("samples", [])),
            "state_diffs_summary": interaction_summary,
            "limits_block": join_list(results.get("notes", [])),
        }

        for key, value in replacements.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template


async def main_async(args: argparse.Namespace) -> None:
    selected_paths = parse_selected_paths(args.selected)
    collector = DesignSystemCollector(
        base_url=args.base_url,
        output_dir=args.output,
        home_path=args.home,
        nav_path=args.nav,
        theme_modes=parse_theme_modes(args.theme_modes),
        breakpoints=parse_breakpoints(args.breakpoints),
        skip_overlays=args.skip_overlays,
        candidates_only=args.candidates_only,
        selected_paths=selected_paths,
        allow_anchor_active=args.allow_anchor_active,
    )
    await collector.collect_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect design system evidence from a website")
    parser.add_argument("base_url", help="Target website base URL")
    parser.add_argument("--output", "-o", default="./design-system-output", help="Output directory")
    parser.add_argument("--home", default="/", help="Home page path")
    parser.add_argument("--nav", help="Navigation/catalog page path")
    parser.add_argument("--theme-modes", help="Comma-separated theme modes (default,dark)")
    parser.add_argument(
        "--breakpoints",
        help="Comma-separated breakpoints, e.g. desktop=1440x900,tablet=834x1112",
    )
    parser.add_argument(
        "--skip-overlays",
        action="store_true",
        help="Skip overlay sampling to avoid navigations triggered by click-based triggers",
    )
    parser.add_argument(
        "--candidates-only",
        action="store_true",
        help="Collect candidates (broad elements) and skip component sampling",
    )
    parser.add_argument(
        "--selected",
        help="Path to JSON list of selector_path or selector strings used to filter samples",
    )
    parser.add_argument(
        "--allow-anchor-active",
        action="store_true",
        help="Allow active state sampling on anchor elements (may navigate)",
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
