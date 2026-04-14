#!/usr/bin/env python3
"""Collect Korean market data via pykrx and emit a markdown report.

Usage:
    python collect.py --tickers 005930,000660 --out docs/2026-04-14/market-data.md

Requires: pykrx  (pip install pykrx)
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pykrx import stock
except ImportError:
    sys.stderr.write("pykrx not installed. Run: pip install pykrx\n")
    sys.exit(2)


NAVER_INDEX = {
    "KOSPI": "https://finance.naver.com/sise/sise_index.naver?code=KOSPI",
    "KOSDAQ": "https://finance.naver.com/sise/sise_index.naver?code=KOSDAQ",
}


def _scrape_naver_index(label: str) -> dict | None:
    url = NAVER_INDEX.get(label)
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("euc-kr", errors="replace")
    except Exception:
        return None
    now = re.search(r'id="now_value">([\d,.]+)', html)
    change = re.search(r'id="change_value_and_rate"[^>]*><span>([\d,.\-+]+)</span>\s*([+\-]?[\d.]+%)', html)
    blind = re.search(r'<span class="blind">(상승|하락|보합)</span>', html)
    if not now:
        return None
    close = float(now.group(1).replace(",", ""))
    chg_val = change.group(1) if change else "0"
    chg_pct = change.group(2) if change else "0.00%"
    direction = blind.group(1) if blind else ""
    sign = "+" if direction == "상승" else ("-" if direction == "하락" else "")
    return {
        "close": close,
        "change_val": f"{sign}{chg_val}",
        "change_pct": f"{sign}{chg_pct}" if sign and not chg_pct.startswith(("+", "-")) else chg_pct,
    }


def _fmt_pct(a: float, b: float) -> str:
    if b == 0:
        return "n/a"
    return f"{(a - b) / b * 100:+.2f}%"


def _recent_trading_day(today: datetime, probe_ticker: str = "005930") -> str:
    """Use a liquid ticker's OHLCV (Naver-backed in pykrx) to find the last trading day."""
    start = (today - timedelta(days=10)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start, end, probe_ticker)
    if df.empty:
        raise RuntimeError("No recent trading day found within 10 days")
    last = df.index[-1]
    return last.strftime("%Y%m%d")


def collect_index(today_ymd: str, prev_ymd: str) -> dict:
    out = {}
    for label in ("KOSPI", "KOSDAQ"):
        data = _scrape_naver_index(label)
        if data:
            out[label] = data
    return out


def collect_investor_flow(today_ymd: str) -> dict:
    # KRX investor flow now requires login; skipped until a Naver-based fallback is added.
    return {"error": "KRX investor flow requires login; not collected"}


def collect_ticker(ticker: str, today_ymd: str) -> dict:
    start = (datetime.strptime(today_ymd, "%Y%m%d") - timedelta(days=40)).strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start, today_ymd, ticker)
    if df.empty:
        return {"ticker": ticker, "error": "no data"}
    name = stock.get_market_ticker_name(ticker)
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    ma5 = float(df["종가"].tail(5).mean())
    ma20 = float(df["종가"].tail(20).mean())
    avg_vol20 = float(df["거래량"].tail(20).mean())
    return {
        "ticker": ticker,
        "name": name,
        "close": float(last["종가"]),
        "prev_close": float(prev["종가"]),
        "change_pct": _fmt_pct(float(last["종가"]), float(prev["종가"])),
        "volume": int(last["거래량"]),
        "avg_volume_20d": int(avg_vol20),
        "volume_ratio": float(last["거래량"]) / avg_vol20 if avg_vol20 else 0.0,
        "ma5": ma5,
        "ma20": ma20,
    }


def render_markdown(date_str: str, indices: dict, flow: dict, tickers: list[dict]) -> str:
    lines = [f"# 국내 시장 데이터 — {date_str}", ""]
    lines.append("## 지수")
    if indices:
        for k, v in indices.items():
            lines.append(f"- **{k}**: {v['close']:.2f} (전일대비 {v['change_val']}, {v['change_pct']})")
    else:
        lines.append("- 수집 실패")
    lines.append("")
    lines.append("## 투자자별 순매수 (KOSPI, 원)")
    if flow and "error" not in flow:
        for k, v in flow.items():
            lines.append(f"- **{k}**: {v:+,}")
    else:
        lines.append(f"- 수집 실패: {flow.get('error', 'unknown')}")
    lines.append("")
    lines.append("## 종목별")
    for t in tickers:
        if "error" in t:
            lines.append(f"### {t['ticker']} — 오류: {t['error']}")
            continue
        lines.append(f"### {t['name']} ({t['ticker']})")
        lines.append(f"- 종가: {t['close']:,.0f} ({t['change_pct']})")
        lines.append(f"- 거래량: {t['volume']:,} (20일 평균 대비 {t['volume_ratio']:.2f}x)")
        lines.append(f"- 5일 이평: {t['ma5']:,.0f}  /  20일 이평: {t['ma20']:,.0f}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", required=True, help="comma-separated 6-digit tickers")
    ap.add_argument("--out", required=True, help="output markdown path")
    args = ap.parse_args()

    today_ymd = _recent_trading_day(datetime.now())
    prev_ymd = (datetime.strptime(today_ymd, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")
    date_str = datetime.strptime(today_ymd, "%Y%m%d").strftime("%Y-%m-%d")

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    indices = collect_index(today_ymd, prev_ymd)
    flow = collect_investor_flow(today_ymd)
    rows = [collect_ticker(t, today_ymd) for t in tickers]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown(date_str, indices, flow, rows), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
