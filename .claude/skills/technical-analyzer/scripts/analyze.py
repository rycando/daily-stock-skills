#!/usr/bin/env python3
"""BNF-style technical analysis for KRX tickers.

Computes:
- 25-day disparity (이격도): close / MA25 * 100
- MA5 / MA20 / MA60 position
- Volume surge vs 20-day average
- Simple BNF oversold/overbought signal

Usage:
    python analyze.py --tickers 005930,000660 --out docs/2026-04-14/technical-analysis.md

Requires: pykrx
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pykrx import stock
except ImportError:
    sys.stderr.write("pykrx not installed. Run: pip install pykrx\n")
    sys.exit(2)


def _recent_trading_day(today: datetime, probe_ticker: str = "005930") -> str:
    start = (today - timedelta(days=10)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start, end, probe_ticker)
    if df.empty:
        raise RuntimeError("no recent trading day")
    return df.index[-1].strftime("%Y%m%d")


def analyze_ticker(ticker: str, end_ymd: str) -> dict:
    start = (datetime.strptime(end_ymd, "%Y%m%d") - timedelta(days=120)).strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start, end_ymd, ticker)
    if df.empty or len(df) < 25:
        return {"ticker": ticker, "error": "insufficient history"}

    closes = df["종가"].astype(float)
    vols = df["거래량"].astype(float)
    last_close = float(closes.iloc[-1])

    ma5 = float(closes.tail(5).mean())
    ma20 = float(closes.tail(20).mean())
    ma25 = float(closes.tail(25).mean())
    ma60 = float(closes.tail(60).mean()) if len(closes) >= 60 else float("nan")

    disparity_25 = last_close / ma25 * 100 if ma25 else 0.0
    vol_avg20 = float(vols.tail(20).mean())
    vol_ratio = float(vols.iloc[-1]) / vol_avg20 if vol_avg20 else 0.0

    # BNF signals — BNF 본인의 규칙은 공개된 게 단편적이지만, 통상적인 해석:
    #   disparity_25 <= 80 → 강한 과매도 (매수 후보)
    #   disparity_25 <= 85 → 과매도
    #   disparity_25 >= 115 → 과매수 (매도/숏 후보)
    #   disparity_25 >= 110 → 과매수 경고
    if disparity_25 <= 80:
        bnf_signal = "강한 과매도 (BNF 매수 후보)"
        bnf_score = 2
    elif disparity_25 <= 85:
        bnf_signal = "과매도"
        bnf_score = 1
    elif disparity_25 >= 115:
        bnf_signal = "강한 과매수 (경계)"
        bnf_score = -2
    elif disparity_25 >= 110:
        bnf_signal = "과매수"
        bnf_score = -1
    else:
        bnf_signal = "중립"
        bnf_score = 0

    ma_position = []
    if last_close > ma5:
        ma_position.append("종가>MA5")
    if last_close > ma20:
        ma_position.append("종가>MA20")
    if ma5 > ma20:
        ma_position.append("MA5>MA20 (단기 상승)")
    else:
        ma_position.append("MA5<MA20 (단기 하락)")

    return {
        "ticker": ticker,
        "name": stock.get_market_ticker_name(ticker),
        "close": last_close,
        "ma5": ma5,
        "ma20": ma20,
        "ma25": ma25,
        "ma60": ma60,
        "disparity_25": disparity_25,
        "vol_ratio": vol_ratio,
        "bnf_signal": bnf_signal,
        "bnf_score": bnf_score,
        "ma_position": ma_position,
    }


def render(date_str: str, rows: list[dict]) -> str:
    out = [f"# 기술적 분석 (BNF 기반) — {date_str}", ""]
    for r in rows:
        if "error" in r:
            out.append(f"## {r['ticker']} — 오류: {r['error']}")
            out.append("")
            continue
        out.append(f"## {r['name']} ({r['ticker']})")
        out.append(f"- 종가: {r['close']:,.0f}")
        out.append(f"- 25일 이격도: **{r['disparity_25']:.2f}** → {r['bnf_signal']}")
        out.append(f"- BNF 점수: **{r['bnf_score']:+d}** (범위 −2..+2)")
        out.append(
            f"- 이평선: MA5 {r['ma5']:,.0f} / MA20 {r['ma20']:,.0f} / MA60 {r['ma60']:,.0f}"
        )
        out.append(f"- 이평 포지션: {', '.join(r['ma_position'])}")
        out.append(f"- 거래량/20일평균: **{r['vol_ratio']:.2f}x**")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    end_ymd = _recent_trading_day(datetime.now())
    date_str = datetime.strptime(end_ymd, "%Y%m%d").strftime("%Y-%m-%d")

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    rows = [analyze_ticker(t, end_ymd) for t in tickers]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(date_str, rows), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
