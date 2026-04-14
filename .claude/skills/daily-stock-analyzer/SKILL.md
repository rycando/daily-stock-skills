---
name: daily-stock-analyzer
description: Orchestrate a daily pre-market Korean stock analysis pipeline — collects market data, news sentiment, retail board sentiment, and BNF-style technical signals for a watchlist, then synthesizes per-ticker buy/hold/sell *assist* verdicts with weighted scoring and concrete evidence. Use every trading day around 08:30 KST (or on demand) for requests like "오늘 시장 분석해줘", "와치리스트 종목 매수매도 판단 도와줘", or when scheduled via cron/`/schedule`.
---

# Daily Stock Analyzer (Orchestrator)

Single entry point that runs four sub-skills, writes their outputs into `docs/<YYYY-MM-DD>/`, and produces a final **decision.md** with weighted scores and evidence per ticker.

This skill *assists* — it never autonomously trades. The final verdict is a recommendation with explicit confidence, not a command.

## Pipeline

```
watchlist.json
      │
      ├─► market-data-collector      → docs/YYYY-MM-DD/market-data.md
      ├─► technical-analyzer          → docs/YYYY-MM-DD/technical-analysis.md
      ├─► news-sentiment-analyzer     → docs/YYYY-MM-DD/news-sentiment.md
      ├─► retail-sentiment-analyzer   → docs/YYYY-MM-DD/retail-sentiment.md
      │
      └─► (this skill) synthesize     → docs/YYYY-MM-DD/decision.md
```

Sub-skills can run in parallel — they write to disjoint output files. Launch them in a single tool-use batch when possible.

## Execution steps

1. **Load watchlist** from `assets/watchlist.json`. Extract tickers and Korean names.
2. **Prep output dir**: `mkdir -p docs/$(date +%Y-%m-%d)`.
3. **Run the four sub-skills**. Delegate to each via the Skill tool (or run their scripts directly if invoked as a cron job):
   - `market-data-collector` — market-data.md
   - `technical-analyzer` — technical-analysis.md
   - `news-sentiment-analyzer` — news-sentiment.md
   - `retail-sentiment-analyzer` — retail-sentiment.md

   If any one fails, record the failure in decision.md's `data_quality` section and proceed with the remainder. Partial > nothing.

4. **Read all four outputs back**. Do not skip — synthesis requires the actual content.

5. **Synthesize decision.md** using the rubric below.

## Scoring rubric

Each sub-skill contributes a score in the range `−2..+2`. The orchestrator computes a weighted sum per ticker:

| Source              | Weight | Rationale                                             |
|---------------------|--------|-------------------------------------------------------|
| technical (BNF)     | 0.40   | Most objective, quantitative, repeatable              |
| market data (flow)  | 0.20   | Foreigner/institution flow is a real liquidity signal |
| news sentiment      | 0.25   | Narrative moves price short-term                      |
| retail sentiment    | 0.15   | Contrarian signal at extremes (flip sign at ±2)       |

**Retail contrarian rule**: if retail_sentiment is +2 (과열 탐욕), treat it as −1 in the weighted sum. If −2 (공포), treat it as +1. Log the flip in the evidence.

**Market-data score derivation**: the market-data.md file contains numbers, not a score. The orchestrator derives a ticker's market-data score from:
- `+1` if foreign + institution net-buy on the ticker's index are both positive
- `−1` if both negative
- `0` otherwise
- Add `+1` if ticker's volume ratio ≥ 2.0 (real breakout), `−1` if ≤ 0.5 (stagnation)
- Clamp to `[−2, +2]`

**Weighted total → verdict**:

| Total         | Verdict         | Confidence |
|---------------|-----------------|------------|
| ≥ +1.2        | Strong Buy*     | 강한 매수  |
| +0.5 to +1.19 | Buy*            | 매수       |
| −0.49 to +0.49| Hold/Neutral    | 관망       |
| −1.19 to −0.5 | Reduce*         | 축소       |
| ≤ −1.2        | Strong Reduce*  | 강한 축소  |

*"Buy/Reduce" is an *assist* recommendation — the human user makes the actual trade decision.

## decision.md schema

```markdown
# 매수/매도 판단 — YYYY-MM-DD

## 데이터 품질
- market-data: ok | partial | failed
- technical: ok | partial | failed
- news: ok | partial | failed
- retail: ok | partial | failed

## 시장 전반 요약
- 2–4 문장. 오늘 시장 분위기 총평 (지수, 수급, 뉴스 테마).

## 종목별 판단

### 삼성전자 (005930)
- **종합 점수**: +1.35
- **판단**: Strong Buy (강한 매수, assist)
- **구성**:
  - 기술적 (BNF): +2  × 0.40 = +0.80  — 25일 이격도 82, 과매도 진입
  - 시장/수급: +1  × 0.20 = +0.20  — 외국인/기관 동반 순매수, 거래량 2.3x
  - 뉴스: +1     × 0.25 = +0.25  — HBM 호재 헤드라인 3건
  - 개미 심리: +2 → 컨트라리언 전환 −1 × 0.15 = −0.15  — "가즈아" 과열
- **주요 리스크**: 단기 과열 유의, 뉴스 기반 급등
- **근거 파일**:
  - docs/YYYY-MM-DD/market-data.md
  - docs/YYYY-MM-DD/technical-analysis.md
  - docs/YYYY-MM-DD/news-sentiment.md
  - docs/YYYY-MM-DD/retail-sentiment.md

### [다음 종목...]

## 면책
본 리포트는 분석 보조 자료이며 투자 권유가 아닙니다. 실제 매매는 사용자 본인의 판단과 책임으로 진행되어야 합니다.
```

## KRX 인증 설정

`market-data: partial` 상태가 계속 나오면 투자자별 순매수(외국인/기관/개인) 데이터가 누락된 것입니다. 이는 KRX 정보데이터시스템 API 로그인 요구 때문으로, `KRX_ID` / `KRX_PW` 환경변수 설정이 필요합니다.

**설정 위치**: `.claude/skills/market-data-collector/SKILL.md`의 "KRX 인증" 섹션 참고 — 셸 프로필 / `.env` / `.claude/settings.local.json` 3가지 옵션 안내.

크론(`/schedule`)으로 자동 실행하는 경우는 반드시 **옵션 C (`.claude/settings.local.json`)**를 사용하세요. 셸 프로필 기반 환경변수는 백그라운드 실행 시 로드되지 않습니다.

## Cron / schedule integration

Intended for daily 08:30 KST execution (pre-market). When scheduled, the trigger prompt should be:

```
/skill daily-stock-analyzer
```

or via `/schedule` → cron `30 8 * * 1-5` (Mon–Fri).

## Non-goals

- No automated order placement.
- No position sizing or stop-loss calculation (add a sizing skill later if needed).
- No backtest or historical verdict grading (a future `decision-journal` skill could handle that).
- No single-point verdict without per-source evidence — if any sub-skill's score lacks evidence, mark the overall as `관망` and explain.
