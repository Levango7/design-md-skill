#!/usr/bin/env python3
"""
Extract a design-token draft from a URL (design-md skill) — stdlib only.

Fetches the page HTML (+ up to --max-css linked stylesheets) and ranks:
  · colors    (#RRGGBB / #RGB / rgb())  weighted: stylesheet 3x, inline style attr 2x, text 1x
  · fonts     (font-family declarations)
  · radii     (border-radius values)

Outputs:
  <out-dir>/tokens-draft.json    machine-readable ranking
  <out-dir>/DESIGN.draft.md      skeleton DESIGN.md draft (roles left TODO for human/agent)

Usage:
  python3 extract.py --url https://example.com [--out-dir ./design-draft] [--max-css 5]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) design-md-skill/0.1 (+python-urllib)"
MAX_BYTES = 1_500_000


def fetch(url: str, limit: int = MAX_BYTES) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,text/css,*/*;q=0.8",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read(limit)
    return data.decode("utf-8", errors="replace")


class PageParser(HTMLParser):
    """Collect <style>, <link rel=stylesheet>, meta theme-color, title, style attrs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_style = False
        self.styles: list[str] = []
        self.sheets: list[str] = []
        self.style_attrs: list[str] = []
        self.theme_color = None
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style":
            self.in_style = True
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if href and "stylesheet" in rel:
                self.sheets.append(href)
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "theme-color" and a.get("content"):
                self.theme_color = a["content"].strip()
        elif tag == "title":
            self._in_title = True
        if a.get("style"):
            self.style_attrs.append(a["style"])

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)
        elif self._in_title and self.title is None:
            self.title = data.strip()


HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{!]+)", re.I)
RADIUS_RE = re.compile(r"border-radius\s*:\s*([^;}{!]+)", re.I)
GENERIC_FONTS = {"inherit", "initial", "unset", "revert", "var", "sans-serif-serif"}


def normalize_color(token: str) -> str | None:
    token = token.strip()
    m = HEX_RE.fullmatch(token)
    if m:
        s = token.lstrip("#")
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        return "#" + s.upper()
    m = RGB_RE.match(token)
    if m:
        r, g, b = (max(0, min(255, int(x))) for x in m.groups())
        return f"#{r:02X}{g:02X}{b:02X}"
    return None


def collect_colors(text: str, weight: int, counter: Counter):
    for tok in HEX_RE.findall(text):
        c = normalize_color(tok)
        if c:
            counter[c] += weight
    for tok in RGB_RE.finditer(text):
        c = normalize_color(tok.group(0))
        if c:
            counter[c] += weight
    # handle rgb() inside rgba(): rgb part already matched above


def collect_fonts(text: str, counter: Counter):
    for m in FONT_RE.finditer(text):
        for fam in m.group(1).split(","):
            fam = fam.strip().strip("\"'").strip()
            if not fam or fam.lower() in GENERIC_FONTS or fam.startswith("var("):
                continue
            counter[fam] += 1


def collect_radii(text: str, counter: Counter):
    for m in RADIUS_RE.finditer(text):
        for v in re.split(r"[\s/]+", m.group(1).strip()):
            v = v.strip()
            if re.fullmatch(r"\d+(\.\d+)?(px|rem|em|%)", v):
                counter[v] += 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract design-token draft from a URL")
    ap.add_argument("--url", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("./design-draft"))
    ap.add_argument("--max-css", type=int, default=5)
    args = ap.parse_args()

    url = args.url
    print(f"fetching: {url}")
    try:
        html = fetch(url)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR fetching page: {e}", file=sys.stderr)
        return 2

    parser = PageParser()
    parser.feed(html)

    colors, fonts, radii = Counter(), Counter(), Counter()
    sources = [url]

    # weight 3: stylesheets (inline <style> + linked CSS)
    css_blob = "\n".join(parser.styles)
    fetched_sheets = 0
    for href in parser.sheets:
        if fetched_sheets >= args.max_css:
            break
        css_url = urljoin(url, href)
        if not css_url.startswith(("http://", "https://")):
            continue
        try:
            css_blob += "\n" + fetch(css_url, limit=512_000)
            sources.append(css_url)
            fetched_sheets += 1
        except Exception:  # noqa: BLE001
            print(f"  (skip stylesheet: {css_url})")
    collect_colors(css_blob, 3, colors)
    collect_fonts(css_blob, fonts)
    collect_radii(css_blob, radii)

    # weight 2: inline style attributes; weight 1: raw HTML text
    attrs_blob = "\n".join(parser.style_attrs)
    collect_colors(attrs_blob, 2, colors)
    collect_colors(html, 1, colors)

    draft = {
        "source": {"url": url, "title": parser.title, "theme_color": parser.theme_color,
                   "css_sources": sources},
        "colors": [{"hex": c, "count": n} for c, n in colors.most_common(24)],
        "fonts": [{"family": f, "count": n} for f, n in fonts.most_common(10)],
        "radii": [{"value": v, "count": n} for v, n in radii.most_common(10)],
        "note": "自动提炼草稿：count = 加权出现次数。角色需人工/agent 归并后写入 DESIGN.md。",
    }

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens-draft.json").write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")

    # DESIGN.draft.md skeleton
    top_colors = draft["colors"][:16]
    rows = "\n".join(
        f"| `c{i+1}` | `{c['hex']}` | {c['count']} | TODO | TODO |" for i, c in enumerate(top_colors)
    )
    font_rows = "\n".join(f"| `{f['family']}` | {f['count']} | TODO |" for f in draft["fonts"]) or "| (未提取到) | | |"
    radius_rows = "\n".join(f"| `{r['value']}` | {r['count']} |" for r in draft["radii"]) or "| (未提取到) | |"
    draft_md = f"""---
version: alpha
name: TODO-design-analysis
description: "TODO：基于 {url} 的提炼草稿（自动生成，需人工归并角色后定稿）"
colors:
{chr(10).join(f'  c{i+1}: "{c["hex"]}"' for i, c in enumerate(top_colors))}
---

## Overview
TODO（3-6 个关键词 + 一句设计哲学）。参考素材：{url}

## Colors
> 来源：{url}（theme-color: {parser.theme_color or "无"}）
> 角色列必须人工归并：不要暴露 c1/c2 这种占位名，改成语义名（bg/surface/accent/success…）。

| 草稿名 | hex | 加权计数 | 建议角色 | 禁用场景 |
|---|---|---|---|---|
{rows}

## Typography
| family | 计数 | 角色 |
|---|---|---|
{font_rows}

## Layout
TODO（栅格/容器/节区节奏）

## Elevation & Depth
TODO

## Shapes
| radius | 计数 |
|---|---|
{radius_rows}

## Components
TODO

## Do's and Don'ts
TODO（参考此站点的取舍，写出你自己的护栏）

## Responsive Behavior
TODO

## Iteration Guide
1. 用 `scripts/scaffold.py` 把归并后的 tokens JSON 生成 tokens.css / tailwind 映射 / preview.html。
2. 改任何色值前先跑 `scripts/wcag.py` 验收对比度。

## Known Gaps
- 本文件为自动提炼草稿：角色归并、交互态、响应式行为均未裁定。
- 未提取：hover/focus 态、动效、阴影细节（建议人工补充或参考 awesome-design-md 同行业文件）。
- 提取来源：{", ".join(sources)}
"""
    (out_dir / "DESIGN.draft.md").write_text(draft_md, encoding="utf-8")

    print(f"\ncolors (top 12 of {len(draft['colors'])}):")
    for c in draft["colors"][:12]:
        print(f"  {c['hex']}  x{c['count']}")
    print(f"fonts: {[f['family'] for f in draft['fonts'][:5]]}")
    print(f"radii: {[r['value'] for r in draft['radii'][:5]]}")
    print(f"\nwritten: {out_dir / 'tokens-draft.json'}")
    print(f"written: {out_dir / 'DESIGN.draft.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
