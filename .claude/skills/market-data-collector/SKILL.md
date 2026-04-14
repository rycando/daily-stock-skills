---
name: market-data-collector
description: Collect Korean stock market data (KOSPI/KOSDAQ indices, investor net-buy flows, per-ticker OHLCV and moving averages) via pykrx and emit a dated markdown report. Use when the daily-stock-analyzer orchestrator (or user) needs today's quantitative market snapshot for a watchlist of KRX tickers. Invoke for requests like "오늘 시장 데이터 수집해줘" or "KOSPI 지수와 삼성전자 시세 정리해줘".
---

# Market Data Collector

Gathers the *quantitative* slice of the daily analysis pipeline. Does not interpret — interpretation happens downstream in `technical-analyzer` and `daily-stock-analyzer`.

## Usage

1. Determine the watchlist. If the caller supplied tickers, use them. Otherwise read `.claude/skills/daily-stock-analyzer/assets/watchlist.json` and use its `tickers` array.
2. Determine output path. Default: `docs/<YYYY-MM-DD>/market-data.md` relative to the project root.
3. Run the collector:
   ```bash
   python .claude/skills/market-data-collector/scripts/collect.py \
     --tickers 005930,000660 \
     --out docs/$(date +%Y-%m-%d)/market-data.md
   ```
4. If `pykrx` is missing, instruct the user to `pip install pykrx` and stop. Do not fall back to scraping.
5. Read the emitted file back and confirm it landed (line count + ticker count).

## Output schema

The script writes sections in this exact order — downstream skills depend on it:

- `# 국내 시장 데이터 — YYYY-MM-DD`
- `## 지수` (KOSPI, KOSDAQ: close, change %, volume)
- `## 투자자별 순매수` (외국인 / 기관합계 / 개인, KRW)
- `## 종목별` (one `###` subsection per ticker: 종가, 거래량, 20일 평균 대비, 5/20일 이평)

Do not rewrite or reorder — the orchestrator relies on these exact headings.

## KRX 인증 (투자자 수급 데이터 활성화)

기본 실행 시 경고가 뜹니다:

```
KRX 로그인 실패: KRX_ID 또는 KRX_PW 환경 변수가 설정되지 않았습니다.
```

이 경고가 있으면:
- ✅ **작동하는 것**: 지수(Naver 스크래핑), 종목 OHLCV/이평(pykrx의 Naver 폴백 경로)
- ❌ **작동 안 하는 것**: 투자자별 순매수 (외국인/기관/개인) — KRX 정보데이터시스템 API 요구

수급 데이터를 켜려면 **KRX 정보데이터시스템**(http://data.krx.co.kr) 계정으로 환경변수를 설정합니다. 설정 위치는 사용 컨텍스트에 따라 다름:

### 옵션 A — 셸 프로필 (가장 단순, 로컬 수동 실행)

`~/.zshrc`에 다음 2줄 추가:

```bash
export KRX_ID="your_krx_id"
export KRX_PW="your_krx_password"
```

적용: `source ~/.zshrc`. 이후 새 터미널에서 `python .../collect.py ...` 실행 시 경고 사라짐.

### 옵션 B — 프로젝트 `.env` (프로젝트별 격리, 권장)

프로젝트 루트에 `.env` 파일:

```env
KRX_ID=your_krx_id
KRX_PW=your_krx_password
```

그리고 `.gitignore`에 `.env` 포함 필수. 스크립트 실행 시 `set -a; source .env; set +a; python .../collect.py ...` 또는 `direnv` 사용.

### 옵션 C — Claude Code `settings.json` (크론/스케줄 실행 시 권장)

이 스킬이 `/schedule` 나 cron을 통해 백그라운드로 실행될 때는 셸 프로필이 로드되지 않을 수 있습니다. Claude Code 세션 환경변수에 넣으려면 `.claude/settings.json`(프로젝트) 또는 `~/.claude/settings.json`(글로벌)에:

```json
{
  "env": {
    "KRX_ID": "your_krx_id",
    "KRX_PW": "your_krx_password"
  }
}
```

⚠️ 프로젝트 settings.json을 git에 올리는 경우 `.claude/settings.local.json`에 넣으세요 (local은 git ignore 대상). `/update-config` 스킬로 추가 가능.

### 검증

설정 후 테스트:

```bash
python3 -c "
from pykrx import stock
df = stock.get_market_trading_value_by_investor('20260414','20260414','KOSPI')
print(df)
"
```

"KRX 로그인 실패" 경고가 안 뜨고 외국인/기관/개인 행이 출력되면 성공. 성공하면 `collect.py`의 `collect_investor_flow()` 함수를 KRX 경로로 복구할 수 있습니다 (현재는 degrade 처리됨 — `_scrape_naver_index` 아래 주석 참고).

## Non-goals

- No sentiment, no buy/sell recommendation, no narrative.
- Daily bars only — no intraday ticks.
- If the market is closed today, the script automatically falls back to the most recent trading day within the last 7 days.
