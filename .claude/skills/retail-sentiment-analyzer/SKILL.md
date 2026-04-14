---
name: retail-sentiment-analyzer
description: Scrape Naver Finance 종목토론실 (retail investor discussion board) post titles for each watchlist ticker, then classify the crowd mood (탐욕/공포/혼조) with concrete evidence. Use when the daily-stock-analyzer orchestrator needs a read on 개미 sentiment, or when the user asks "종토방 분위기 어때?" / "개미들 심리 분석해줘".
---

# Retail Sentiment Analyzer

Produces the *crowd-psychology* slice of the daily pipeline — what retail investors are posting on Naver Finance boards for each watchlist ticker.

## Usage

1. Resolve watchlist tickers (caller-supplied or `.claude/skills/daily-stock-analyzer/assets/watchlist.json`).
2. For each ticker, fetch 1–3 pages of board titles:
   ```bash
   python .claude/skills/retail-sentiment-analyzer/scripts/fetch_board.py \
     --ticker 005930 --pages 2 > /tmp/board_005930.md
   ```
3. Read each collected file and classify according to the **Rubric** below. Only use titles actually present in the file.
4. Write `docs/<YYYY-MM-DD>/retail-sentiment.md` using the **Output schema**.
5. If the script exits non-zero (e.g., Naver changed markup, rate limit), record that ticker as `status: unavailable` in the output and continue. Do not fabricate posts.

## Ethical and legal notes

- Titles only. Do not scrape full post bodies or user IDs.
- Respect rate: 1 request/second. Default `--pages 2` is usually sufficient.
- This is personal analysis use only — do not redistribute scraped content.

## Rubric

Classify per ticker on a 5-level scale:

| Score | Label         | Signal patterns                                              |
|-------|---------------|--------------------------------------------------------------|
| +2    | 과열 탐욕     | "가즈아", "10만원 간다", 목표가 자화자찬, 차익 자랑         |
| +1    | 긍정          | 관망 + 기대, 호재 공유, 매수 인증                            |
| 0     | 혼조          | 의견 양분, 방향성 없음                                       |
| −1    | 불안          | "조정", "손절 고민", 호재 부재 불평                          |
| −2    | 공포          | "폭락", "물렸다", "탈출", 욕설 비중 증가                     |

**Contrarian note for the orchestrator**: extreme retail sentiment (+2 or −2) often correlates with short-term reversal — flag this explicitly in the output so the orchestrator can weight it accordingly.

Cite **3–5 post titles as evidence** per ticker. No evidence → no score.

## Output schema

```markdown
# 개미 심리 분석 — YYYY-MM-DD

## 삼성전자 (005930)
- **점수**: {-2..+2}
- **라벨**: 과열 탐욕 / 긍정 / 혼조 / 불안 / 공포
- **키워드**: 3–6개의 반복 키워드
- **대표 게시글**:
  - "..."
  - "..."
- **컨트라리언 경고**: (점수가 ±2일 때만) 단기 역행 가능성 코멘트

## [다음 종목...]
```

## Non-goals

- No price prediction, no buy/sell verdict.
- No full-text scraping, no user profiling.
- No upvote/comment counts (script only collects titles).
