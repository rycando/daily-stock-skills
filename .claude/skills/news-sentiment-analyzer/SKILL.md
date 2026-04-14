---
name: news-sentiment-analyzer
description: Fetch recent Korean market and per-ticker news headlines from Google News RSS, then score overall market mood and per-ticker news tone into a dated markdown report. Use when the daily-stock-analyzer orchestrator needs today's news-based sentiment signal for the watchlist, or when the user asks "오늘 뉴스 분위기 분석해줘" / "시장 분위기 뉴스로 정리해줘".
---

# News Sentiment Analyzer

Produces the *qualitative narrative* slice of the daily pipeline: what does today's news flow say about the market and each watchlist ticker.

## Usage

1. Resolve watchlist. Use supplied tickers or read `.claude/skills/daily-stock-analyzer/assets/watchlist.json`. Each entry must include `ticker` and `name` (Korean) — the Korean name is the search key, not the numeric ticker.
2. Create `docs/<YYYY-MM-DD>/` if missing.
3. Fetch headlines for (a) the overall market and (b) each ticker:
   ```bash
   python .claude/skills/news-sentiment-analyzer/scripts/fetch_news.py --limit 20 > /tmp/news_market.md
   python .claude/skills/news-sentiment-analyzer/scripts/fetch_news.py --query "삼성전자" --limit 15 > /tmp/news_005930.md
   ```
4. Read every collected file and classify each according to the **Scoring rubric** below. Do not invent headlines — only score what was actually fetched.
5. Write `docs/<YYYY-MM-DD>/news-sentiment.md` using the **Output schema**.
6. If a fetch fails (network, feed empty), record `status: partial` in the front matter and proceed with what you have. Never hallucinate headlines.

## Scoring rubric

Score each bucket (market + each ticker) on a discrete scale:

| Score | Label         | Meaning                                                    |
|-------|---------------|------------------------------------------------------------|
| +2    | strongly positive | clear earnings beats, favorable regulatory news, upgrades |
| +1    | positive      | generally constructive tone, mild good news               |
| 0     | neutral       | mixed or no directional signal                            |
| −1    | negative      | downgrades, soft guidance, concerning macro               |
| −2    | strongly negative | litigation, scandal, earnings miss, sanctions            |

Always justify with **2–4 concrete headlines as evidence**. A score without cited headlines is invalid.

## Output schema

```markdown
# 뉴스 심리 분석 — YYYY-MM-DD

## 시장 전반
- **점수**: {-2..+2}
- **핵심 테마**: 3개 이하의 불릿
- **근거 헤드라인**:
  - ...

## 종목별

### 삼성전자 (005930)
- **점수**: {-2..+2}
- **요약**: 1–2문장
- **근거 헤드라인**:
  - ...
```

Keep it tight — the orchestrator reads this whole file.

## Non-goals

- No price targets, no buy/sell calls.
- No paraphrased or synthesized "news" — only score real fetched headlines.
- No translation of headlines into English.
