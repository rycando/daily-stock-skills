#!/usr/bin/env python3
"""Scrape Naver Finance 종목토론실 (discussion board) titles for one ticker.

Usage:
    python fetch_board.py --ticker 005930 --pages 2

Prints markdown bullets. Robust to minor HTML changes, but if Naver changes
markup significantly the script will emit a warning and exit non-zero.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from html import unescape

BOARD_URL = "https://finance.naver.com/item/board.naver?code={ticker}&page={page}"

TITLE_RE = re.compile(
    r'<td class="title"[^>]*>.*?<a[^>]*title="([^"]+)"', re.DOTALL
)
DATE_RE = re.compile(r'<span class="tah p10 gray03">([^<]+)</span>')


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.naver.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    # Naver serves euc-kr
    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse(html_text: str) -> list[dict]:
    rows = []
    titles = TITLE_RE.findall(html_text)
    dates = DATE_RE.findall(html_text)
    for i, title in enumerate(titles):
        rows.append(
            {
                "title": unescape(title).strip(),
                "date": dates[i].strip() if i < len(dates) else "",
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--pages", type=int, default=2)
    args = ap.parse_args()

    all_rows = []
    for page in range(1, args.pages + 1):
        try:
            html_text = fetch(BOARD_URL.format(ticker=args.ticker, page=page))
        except Exception as e:
            sys.stderr.write(f"page {page} failed: {e}\n")
            continue
        rows = parse(html_text)
        if not rows:
            sys.stderr.write(f"WARN: no rows parsed on page {page} — markup may have changed\n")
            continue
        all_rows.extend(rows)

    if not all_rows:
        sys.stderr.write("no posts collected\n")
        return 2

    print(f"### 종목토론실 {args.ticker} ({len(all_rows)}건)")
    for r in all_rows:
        meta = f" [{r['date']}]" if r["date"] else ""
        print(f"- {r['title']}{meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
