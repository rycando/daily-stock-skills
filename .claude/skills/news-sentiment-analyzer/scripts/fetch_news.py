#!/usr/bin/env python3
"""Fetch recent Korean market news headlines via RSS and print as markdown bullets.

Usage:
    python fetch_news.py --query "삼성전자" --limit 15

The script does NOT classify sentiment — it produces a clean headline list
that Claude then reads back and analyzes.
"""
from __future__ import annotations

import argparse
import html
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime


_MARKET_Q = urllib.parse.quote("코스피 OR 코스닥 OR 증시")
FEEDS = {
    "google_kr": "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko",
    "google_market": f"https://news.google.com/rss/search?q={_MARKET_Q}&hl=ko&gl=KR&ceid=KR:ko",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_rss(xml_text: str, limit: int) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source_el = item.find("{http://news.google.com/}source") or item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else ""
        items.append(
            {
                "title": html.unescape(title),
                "link": link,
                "pub": pub,
                "source": source,
            }
        )
        if len(items) >= limit:
            break
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="", help="search keyword; empty = general market feed")
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    if args.query:
        url = FEEDS["google_kr"].format(q=urllib.parse.quote(args.query))
    else:
        url = FEEDS["google_market"]

    try:
        xml_text = fetch(url)
    except Exception as e:
        sys.stderr.write(f"fetch failed: {e}\n")
        return 2

    items = parse_rss(xml_text, args.limit)
    label = args.query or "시장 전반"
    print(f"### {label} (수집 {datetime.now():%H:%M}, {len(items)}건)")
    for it in items:
        src = f" — {it['source']}" if it["source"] else ""
        print(f"- {it['title']}{src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
