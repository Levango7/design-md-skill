#!/usr/bin/env python3
"""
WCAG 2.1 contrast gate for design tokens (design-md skill).

Input:
  --tokens FILE      tokens.css  (":root" / ":root[data-theme='light']" + "--name: #RRGGBB;")
                     or design-tokens.json ({"color": {...}, "colorLight": {...}} with {"value": "#hex"} entries)
  --pair "FG:BG[:MIN]"   repeatable; FG/BG = token name (needs --tokens) or #hex
  --pairs FILE       optional pairs file; one per line: "FG BG [MIN]"  ('//' = comment)
  --strict           also check translucent banner composites: tone@10% over bg
Output: per-theme pair table, PASS/FAIL markers, summary. Exit 0 all pass, 1 otherwise.

Thresholds: text 4.5:1 (WCAG 2.1 AA), interactive/UI 3:1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- color math


def hex_to_rgb(value: str):
    s = value.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"not a #RRGGBB color: {value!r}")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{int(round(c)):02X}" for c in rgb)


def relative_luminance(rgb) -> float:
    def chan(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1, rgb2) -> float:
    l1, l2 = relative_luminance(rgb1), relative_luminance(rgb2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg_rgb, alpha: float, bg_rgb):
    """Composite fg at `alpha` over bg (like rgba over solid background)."""
    return tuple(fg_rgb[i] * alpha + bg_rgb[i] * (1 - alpha) for i in range(3))


# ---------------------------------------------------------------- parsers

CSS_HEADER_RE = re.compile(r":root\[data-theme=['\"]light['\"]\]")
CSS_COLOR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;")


def parse_css(text: str) -> dict:
    """Return {"dark": {...}, "light": {...}} token maps from a tokens.css."""
    m = CSS_HEADER_RE.search(text)
    dark_part = text[: m.start()] if m else text
    light_part = text[m.start() :] if m else ""

    def collect(block: str) -> dict:
        return {k: v.lower() for k, v in CSS_COLOR_RE.findall(block)}

    out = {"dark": collect(dark_part)}
    if light_part:
        out["light"] = collect(light_part)
    return out


def parse_json_tokens(text: str) -> dict:
    """Return {"dark": {...}, "light": {...}} from a design-tokens.json.

    Convention: top-level keys whose values are maps of {"value": "#hex"} objects.
    Keys containing 'light' (case-insensitive) are treated as the light theme.
    """
    data = json.loads(text)
    themes: dict[str, dict[str, str]] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        tokens = {}
        for name, spec in value.items():
            if isinstance(spec, dict) and isinstance(spec.get("value"), str):
                v = spec["value"].strip()
                if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                    tokens[name] = v.lower()
        if tokens:
            theme = "light" if "light" in key.lower() else "dark"
            # merge multiple maps per theme (e.g. color + colorDark)
            themes.setdefault(theme, {}).update(tokens)
    return themes


# ---------------------------------------------------------------- auto pairs

TEXTS = ["fg", "fg-2", "muted", "accent", "success", "warn", "danger"]
SURFACES = ["bg", "surface", "surface-2"]
TONES = ["accent", "success", "warn", "danger"]


def auto_pairs(c: dict) -> list:
    """Convention-aware pairs matching this skill's token naming."""
    pairs = []
    for t in TEXTS:
        if t not in c:
            continue
        for s in SURFACES:
            if s in c:
                pairs.append((t, s, 4.5, "text on surface"))
    for solid in ("accent-solid", "accent-solid-hover", "accent-solid-active"):
        if solid in c and "accent-on" in c:
            pairs.append(("accent-on", solid, 4.5, "solid button"))
    if "danger-solid" in c and "danger-on" in c:
        pairs.append(("danger-on", "danger-solid", 4.5, "danger button"))
    for tone in TONES:
        soft = f"{tone}-soft"
        if tone in c and soft in c:
            pairs.append((tone, soft, 4.5, "badge soft"))
    if "border-strong" in c:
        for s in ("bg", "surface"):
            if s in c:
                pairs.append(("border-strong", s, 3.0, "interactive border"))
    return pairs


def strict_pairs(c: dict) -> list:
    """Extra checks for translucent banner backgrounds (tone @10% over bg)."""
    pairs = []
    if "bg" not in c:
        return pairs
    for tone in TONES:
        if tone not in c:
            continue
        for text_tok in ("fg", tone):
            if text_tok not in c:
                continue
            pairs.append((text_tok, f"@blend:{tone}:0.10:bg", 4.5, "banner tone/10 over bg"))
    return pairs


# ---------------------------------------------------------------- checking


def resolve(token: str, colors: dict):
    """Token name (hex string or {"value": ...} dict) or #hex -> rgb tuple."""

    def pick(name: str):
        val = colors[name]
        return val.get("value", "") if isinstance(val, dict) else val

    if token.startswith("#"):
        return hex_to_rgb(token)
    if token.startswith("@blend:"):
        _, tone, alpha, bg = token.split(":")
        return blend(hex_to_rgb(pick(tone)), float(alpha), hex_to_rgb(pick(bg)))
    if token in colors:
        return hex_to_rgb(pick(token))
    raise KeyError(token)


def check_theme(theme: str, colors: dict, explicit_pairs, strict: bool, out_lines: list) -> tuple[int, int]:
    pairs = list(auto_pairs(colors))
    if strict:
        pairs += strict_pairs(colors)
    pairs += explicit_pairs

    passed = failed = 0
    out_lines.append(f"\n== theme: {theme} ==")
    out_lines.append(f"{'foreground':>18} {'background':>22} {'ratio':>6} {'min':>4}  result  use")
    for fg_tok, bg_tok, minimum, use in pairs:
        try:
            fg_rgb, bg_rgb = resolve(fg_tok, colors), resolve(bg_tok, colors)
        except KeyError as e:
            out_lines.append(f"{fg_tok:>18} {bg_tok:>22} {'—':>6} {'—':>4}  SKIP    (missing token: {e})")
            continue
        ratio = contrast_ratio(fg_rgb, bg_rgb)
        ok = ratio >= minimum - 1e-9
        passed += ok
        failed += (not ok)
        marker = "PASS" if ok else "FAIL"
        out_lines.append(f"{fg_tok:>18} {bg_tok:>22} {ratio:>6.2f} {minimum:>4.1f}  {marker}    {use}")
    out_lines.append(f"-- {theme}: {passed} pass / {failed} fail")
    return passed, failed


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description="WCAG 2.1 contrast gate for design tokens")
    ap.add_argument("--tokens", type=Path, help="tokens.css or design-tokens.json")
    ap.add_argument("--pair", action="append", default=[], help='FG:BG[:MIN] e.g. "#E6E9EF:#0A0C10:4.5"')
    ap.add_argument("--pairs", type=Path, help="pairs file: each line 'FG BG [MIN]', '//' comment")
    ap.add_argument("--strict", action="store_true", help="also check translucent banner composites")
    ap.add_argument("--theme", help="only check this theme (dark/light)")
    ap.add_argument("--json-out", type=Path, help="write machine-readable report")
    args = ap.parse_args()

    themes: dict[str, dict] = {}
    if args.tokens:
        text = args.tokens.read_text(encoding="utf-8")
        if args.tokens.suffix.lower() == ".css":
            themes = parse_css(text)
        else:
            themes = parse_json_tokens(text)
        # light theme inherits non-overridden tokens from dark (CSS cascade semantics)
        if "light" in themes and "dark" in themes:
            themes["light"] = {**themes["dark"], **themes["light"]}
        if args.theme:
            themes = {k: v for k, v in themes.items() if k == args.theme}
        if not themes:
            print("no themes/tokens parsed — check the file format", file=sys.stderr)
            return 2

    # explicit pairs (token names resolved per-theme when available)
    explicit_raw = []
    for spec in args.pair:
        parts = spec.split(":")
        if len(parts) == 3 and not parts[2].startswith(("4", "3")):
            # e.g. #RRGGBB:#RRGGBB:4.5 stays; handle 8-char '#aabbccdd' mis-split
            parts = [":".join(parts[:2]), parts[2]]
        fg, bg = parts[0], parts[1]
        minimum = float(parts[2]) if len(parts) > 2 else 4.5
        explicit_raw.append((fg, bg, minimum, "explicit"))
    if args.pairs:
        for line in args.pairs.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            parts = line.split()
            fg, bg = parts[0], parts[1]
            minimum = float(parts[2]) if len(parts) > 2 else 4.5
            explicit_raw.append((fg, bg, minimum, "pairs-file"))

    out_lines = []
    report = {"themes": {}, "explicit": []}
    total_fail = 0

    if themes:
        for theme, colors in themes.items():
            p, f = check_theme(theme, colors, explicit_raw, args.strict, out_lines)
            report["themes"][theme] = {"pass": p, "fail": f}
            total_fail += f
    else:
        # no tokens file: only explicit #hex pairs are possible
        for fg, bg, minimum, use in explicit_raw:
            try:
                ratio = contrast_ratio(hex_to_rgb(fg), hex_to_rgb(bg))
            except ValueError as e:
                print(f"skip {fg}:{bg} ({e})", file=sys.stderr)
                continue
            ok = ratio >= minimum - 1e-9
            total_fail += (not ok)
            out_lines.append(f"{fg} on {bg}: {ratio:.2f} (min {minimum}) -> {'PASS' if ok else 'FAIL'}")
            report["explicit"].append({"fg": fg, "bg": bg, "ratio": round(ratio, 3), "min": minimum, "pass": ok})

    print("\n".join(out_lines))
    print(f"\nTOTAL: {'ALL PASS' if total_fail == 0 else str(total_fail) + ' FAIL'}")

    if args.json_out:
        report["total_fail"] = total_fail
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report written: {args.json_out}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
