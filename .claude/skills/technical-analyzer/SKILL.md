---
name: technical-analyzer
description: Run BNF-style technical analysis on KRX tickers — 25-day disparity (이격도), moving-average position, and volume surge — and emit a dated markdown report with a per-ticker signal score. Use when the daily-stock-analyzer orchestrator needs the technical slice of the pipeline, or when the user asks "BNF 이격도 확인해줘" / "25일 이격도로 과매도 종목 찾아줘".
---

# Technical Analyzer (BNF style)

Produces the *technical* slice of the daily pipeline using BNF's trademark oversold-reversal heuristic (25-day disparity) combined with MA5/MA20/MA60 alignment and volume surge.

## Usage

1. Resolve watchlist tickers (caller or `.claude/skills/daily-stock-analyzer/assets/watchlist.json`).
2. Run:
   ```bash
   python .claude/skills/technical-analyzer/scripts/analyze.py \
     --tickers 005930,000660 \
     --out docs/$(date +%Y-%m-%d)/technical-analysis.md
   ```
3. Read the output back to confirm and extract each ticker's `BNF 점수`.
4. If `pykrx` missing → instruct `pip install pykrx` and stop.

## Scoring meaning (for orchestrator weighting)

| Score | Meaning                   | BNF heuristic                              |
|-------|---------------------------|--------------------------------------------|
| +2    | 강한 매수 시그널          | 25일 이격도 ≤ 80                           |
| +1    | 매수 시그널               | 25일 이격도 ≤ 85                           |
| 0     | 중립                      | 85 < 이격도 < 110                          |
| −1    | 매도 경고                 | 25일 이격도 ≥ 110                          |
| −2    | 강한 매도 경고            | 25일 이격도 ≥ 115                          |

**Important caveat**: BNF's real trading was intraday/short-term. These thresholds are simplified proxies — the orchestrator should combine this with volume ratio (>2x is a real breakout signal) and MA alignment, not treat BNF score as gospel.

## Output schema

```markdown
# 기술적 분석 (BNF 기반) — YYYY-MM-DD

## 삼성전자 (005930)
- 종가: ...
- 25일 이격도: X.XX → {label}
- BNF 점수: ±N
- 이평선: MA5 / MA20 / MA60
- 이평 포지션: ...
- 거래량/20일평균: X.Xx
```

## Non-goals

- No fundamental analysis (PER, PBR, earnings).
- No portfolio sizing or stop-loss calculation.
- No news or sentiment input — purely price/volume math.
