#!/usr/bin/env python3
"""
Fetch a reference DESIGN.md from awesome-design-md (design-md skill).

Channels (in order):
  1) raw.githubusercontent.com (urllib)
  2) gh api contents (base64) — fallback when raw is unreachable

Usage:
  python3 fetch_ref.py --list [--category fintech]
  python3 fetch_ref.py --slug linear.app [--out DESIGN.reference-linear.app.md]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = "VoltAgent/awesome-design-md"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/design-md/{{slug}}/DESIGN.md"
UA = "design-md-skill/0.1 (+python-urllib)"

CATALOG = {
    "fintech": ["binance", "coinbase", "kraken", "mercury", "stripe", "revolut", "wise", "nerdwallet", "mastercard"],
    "devtools": ["vercel", "linear.app", "cursor", "raycast", "warp", "supabase", "sentry", "posthog", "clickhouse",
                 "mongodb", "hashicorp", "composio", "sanity", "resend", "mintlify", "expo", "lovable", "superhuman"],
    "ai": ["claude", "cohere", "elevenlabs", "minimax", "mistral.ai", "ollama", "opencode.ai", "replicate",
           "runwayml", "together.ai", "voltagent", "x.ai", "jobright"],
    "saas": ["notion", "cal", "intercom", "sap", "zapier", "airtable", "figma", "framer", "miro", "webflow", "clay"],
    "consumer": ["apple", "meta", "airbnb", "shopify", "nike", "starbucks", "spotify", "pinterest", "uber", "playstation",
                 "oura", "dji", "hp", "ibm", "nvidia", "spacex", "tesla", "theverge", "wired", "vodafone", "aljazeera",
                 "1win", "mydealz"],
    "auto": ["bmw", "bmw-m", "bugatti", "ferrari", "lamborghini", "renault"],
    "retro": ["dell-1996", "nintendo-2001"],
}
ALL_SLUGS = [s for group in CATALOG.values() for s in group]


def list_catalog(category: str | None) -> int:
    if category:
        group = CATALOG.get(category)
        if not group:
            print(f"unknown category {category!r}; choose from: {', '.join(CATALOG)}", file=sys.stderr)
            return 2
        print("\n".join(group))
        return 0
    for name, slugs in CATALOG.items():
        print(f"[{name}]")
        print("  " + ", ".join(slugs))
    print(f"\ntotal: {len(ALL_SLUGS)} slugs")
    return 0


def fetch_raw(slug: str) -> bytes:
    req = urllib.request.Request(RAW.format(slug=slug), headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_gh(slug: str) -> bytes:
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("gh CLI not found")
    path = f"repos/{REPO}/contents/design-md/{slug}/DESIGN.md"
    proc = subprocess.run([gh, "api", path, "--jq", ".content"], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api failed: {proc.stderr.strip()[:200]}")
    return base64.b64decode("".join(proc.stdout.split()))


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch a reference DESIGN.md from awesome-design-md")
    ap.add_argument("--list", action="store_true", help="list available slugs")
    ap.add_argument("--category", help="filter --list by category")
    ap.add_argument("--slug", help="slug, e.g. linear.app")
    ap.add_argument("--out", type=Path, help="output path (default: ./DESIGN.reference-<slug>.md)")
    args = ap.parse_args()

    if args.list:
        return list_catalog(args.category)
    if not args.slug:
        ap.error("--slug required (or use --list)")
    if args.slug not in ALL_SLUGS:
        print(f"warning: {args.slug!r} not in local catalog; trying anyway", file=sys.stderr)

    data = None
    source = ""
    try:
        data = fetch_raw(args.slug)
        source = "raw.githubusercontent.com"
    except Exception as e_raw:  # noqa: BLE001
        print(f"raw channel failed ({e_raw}); trying gh api ...", file=sys.stderr)
        try:
            data = fetch_gh(args.slug)
            source = "gh api"
        except Exception as e_gh:  # noqa: BLE001
            print(f"ERROR: both channels failed.\n  raw: {e_raw}\n  gh : {e_gh}", file=sys.stderr)
            return 2

    out = args.out or Path(f"DESIGN.reference-{args.slug}.md")
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()[:16]
    headers = [ln for ln in data.decode("utf-8", errors="replace").splitlines() if ln.startswith("## ")][:8]
    print(f"saved  : {out}")
    print(f"source : {source}")
    print(f"size   : {len(data)} B  sha256:{digest}")
    print(f"sections: {', '.join(h[3:] for h in headers)}")
    print("\n提示：这是分析参考，用于学习其方法与取舍；消化后的决策请写进你自己项目的 DESIGN.md（不要把参考文件直接放进项目根目录）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
