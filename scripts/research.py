#!/usr/bin/env python3
"""
DeepSeek Search / Fetch helper (design-md skill) — the API key is never echoed.

Key resolution order (first hit wins):
  1) --key-file PATH
  2) env DEEPSEEK_API_KEY                    (may be invisible to already-running processes)
  3) env DEEPSEEK_API_KEY_FILE               (path to a file containing the key)
  4) %USERPROFILE%/.deepseek/api_key         <-- recommended on Windows (create it yourself)

Setup (run in YOUR terminal, key never leaves your machine):
    mkdir "%USERPROFILE%\\.deepseek" 2>nul
    notepad "%USERPROFILE%\\.deepseek\\api_key"      # paste the key as the only line, save

Commands:
  check                                     verify the key works (1 minimal search request)
  search --query Q [--count N] [--need-content] [--ori-question S] [--out FILE]
  fetch  --url URL [--out FILE|--md-dir DIR]        (--md-dir writes a .md file named after the page)

Output: JSON on stdout unless --out given. Docs: https://api-docs.deepseek.com/zh-cn/guides/search/
Billing: 5 CNY / 1000 successful requests per API. Retries: 408/429/5xx (3 attempts, backoff); 4xx no retry.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://api.deepseek.com/v1/tools"
UA = "design-md-skill/0.1 (+python-urllib)"
SK_RE = re.compile(r"sk-[A-Za-z0-9_-]{4,}")  # defensive masking


def mask(text: str) -> str:
    return SK_RE.sub("sk-***", text)


def read_key_file(path: Path) -> str:
    """Read a key file tolerating UTF-8 (BOM) and UTF-16.

    Windows 常见坑：记事本/某些终端会把纯文本存成 UTF-16（首两字节 FF FE / FE FF），
    或 PowerShell 5.1 的 `>` 重定向产生 UTF-16 LE（无 BOM，ASCII 字符间隔 \\x00）。
    这里按字节特征探测，避免 UnicodeDecodeError。
    """
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16").strip()  # UTF-16 with BOM
    if b"\x00" in raw[:64]:  # UTF-16 without BOM (heuristic: NULs among ASCII)
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                s = raw.decode(enc).strip()
                if s and all(32 <= ord(c) < 127 for c in s):
                    return s
            except UnicodeDecodeError:
                pass
    return raw.decode("utf-8-sig").strip()


def find_key(key_file: str | None) -> tuple[str | None, str]:
    """Return (key, human-readable source). Never prints the key itself."""
    if key_file:
        p = Path(key_file).expanduser()
        if p.is_file():
            return read_key_file(p), f"--key-file {p}"
        return None, f"--key-file {p} (not found)"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"].strip(), "env DEEPSEEK_API_KEY"
    env_file = os.environ.get("DEEPSEEK_API_KEY_FILE")
    if env_file:
        p = Path(env_file).expanduser()
        if p.is_file():
            return read_key_file(p), f"env DEEPSEEK_API_KEY_FILE -> {p}"
    default = Path.home() / ".deepseek" / "api_key"
    if default.is_file():
        return read_key_file(default), f"key file {default}"
    return None, (
        "not found. Set it up in your own terminal (key never echoed here):\n"
        '  mkdir "%USERPROFILE%\\.deepseek" 2>nul\n'
        '  notepad "%USERPROFILE%\\.deepseek\\api_key"   # paste key, save\n'
        "  (or set env DEEPSEEK_API_KEY / DEEPSEEK_API_KEY_FILE)"
    )


RETRY_STATUS = {408, 429, 500, 502, 503, 504}


def call(endpoint: str, payload: dict, key: str, attempts: int = 3) -> dict:
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for i in range(attempts):
        req = urllib.request.Request(
            f"{BASE}/{endpoint}",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": UA,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            if e.code in RETRY_STATUS and i < attempts - 1:
                last_err = f"HTTP {e.code}: {body}"
                time.sleep(2 * (3**i) / 2)
                continue
            raise RuntimeError(f"HTTP {e.code}: {mask(body)}") from None
        except Exception as e:  # noqa: BLE001
            if i < attempts - 1:
                last_err = str(e)
                time.sleep(2 * (3**i) / 2)
                continue
            raise RuntimeError(mask(str(e))) from None
    raise RuntimeError(mask(str(last_err)))


def print_or_write(obj: dict, out: str | None):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"written: {out}  ({len(text)} chars)")
    else:
        print(text)


def cmd_check(key: str, source: str) -> int:
    try:
        res = call("search", {"query": "design tokens", "count": 1}, key)
        n = len(res.get("results", []))
        print(f"key OK (source: {source}) — minimal search returned {n} result(s).")
        return 0
    except RuntimeError as e:
        print(f"key found ({source}) but request failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="DeepSeek Search/Fetch helper (key never echoed)")
    ap.add_argument("--key-file", help="path to a file containing only the API key")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="verify key works (1 minimal request)")

    ps = sub.add_parser("search", help="web search")
    ps.add_argument("--query", required=True)
    ps.add_argument("--count", type=int, default=10)
    ps.add_argument("--need-content", action="store_true")
    ps.add_argument("--ori-question")
    ps.add_argument("--out")

    pf = sub.add_parser("fetch", help="fetch a URL as Markdown")
    pf.add_argument("--url", required=True)
    pf.add_argument("--out")
    pf.add_argument("--md-dir", help="write <md-dir>/<slug>.md instead of stdout")

    args = ap.parse_args()
    key, source = find_key(args.key_file)
    if not key:
        print(f"DeepSeek key {source}", file=sys.stderr)
        return 2

    if args.cmd == "check":
        return cmd_check(key, source)

    if args.cmd == "search":
        payload = {"query": args.query, "count": max(1, min(50, args.count))}
        if args.need_content:
            payload["need_content"] = True
        if args.ori_question:
            payload["ori_question"] = args.ori_question
        try:
            res = call("search", payload, key)
        except RuntimeError as e:
            print(f"search failed: {e}", file=sys.stderr)
            return 1
        results = res.get("results", [])
        print(f"# {len(results)} result(s) via {source}", file=sys.stderr)
        print_or_write(res, args.out)
        return 0

    # fetch
    try:
        res = call("fetch", {"url": args.url}, key)
    except RuntimeError as e:
        print(f"fetch failed: {e}", file=sys.stderr)
        return 1
    if args.md_dir:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", args.url.rstrip("/").split("/")[-1] or "page")[:60]
        out_file = Path(args.md_dir) / f"{slug}.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        title = res.get("title", "")
        out_file.write_text(f"# {title}\n\n> source: {args.url}\n\n" + res.get("content", ""), encoding="utf-8")
        print(f"written: {out_file}  (title: {title})")
    else:
        print_or_write(res, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
