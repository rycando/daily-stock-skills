# daily-stock-skills

매일 아침 한국 주식 시장을 자동 분석하는 [Claude Code](https://claude.com/claude-code) 스킬 번들입니다. 와치리스트 종목에 대해 시장 데이터·기술적 지표·뉴스·종토방 심리를 모은 뒤, 가중치 기반으로 매수/매도 *보조* 판단을 생성합니다.

> ⚠️ 본 도구는 분석 보조용입니다. 투자 권유가 아니며, 실제 매매는 사용자 본인의 판단과 책임하에 진행해야 합니다.

## 구성

오케스트레이터 1개 + 서브스킬 4개:

| 스킬 | 역할 |
|---|---|
| `daily-stock-analyzer` | 오케스트레이터 — 4개 서브스킬을 호출하고 가중합으로 최종 판단 |
| `market-data-collector` | KOSPI/KOSDAQ 지수, 종목 OHLCV, 이평선 (pykrx + Naver) |
| `technical-analyzer` | BNF 25일 이격도 기반 과매수/과매도 시그널 |
| `news-sentiment-analyzer` | Google News RSS 기반 시장/종목 뉴스 감성 |
| `retail-sentiment-analyzer` | 네이버 금융 종목토론실 개미 심리 + 컨트라리언 룰 |

## 점수 합성

각 서브스킬이 −2..+2 점수를 산출하고 오케스트레이터가 가중합을 계산합니다.

| 출처 | 가중치 |
|---|---|
| 기술적 (BNF) | 0.40 |
| 시장/수급 | 0.20 |
| 뉴스 심리 | 0.25 |
| 개미 심리 | 0.15 (±2일 때 컨트라리언 반전) |

총점 → 판단:

| 총점 | 판단 |
|---|---|
| ≥ +1.2 | 강한 매수 (assist) |
| +0.5 ~ +1.19 | 매수 (assist) |
| −0.49 ~ +0.49 | 관망 |
| −1.19 ~ −0.5 | 축소 (assist) |
| ≤ −1.2 | 강한 축소 (assist) |

## 설치

```bash
git clone https://github.com/rycando/daily-stock-skills.git
cd daily-stock-skills
pip install pykrx

# 와치리스트 편집
$EDITOR .claude/skills/daily-stock-analyzer/assets/watchlist.json
```

이 디렉토리에서 Claude Code를 실행하면 5개 스킬이 자동 발견됩니다.

## 사용

Claude Code에서:

```
/daily-stock-analyzer
```

또는 자연어:

> 오늘 시장 분석해줘

산출물은 `docs/YYYY-MM-DD/` 아래 5개 마크다운으로 떨어집니다:

```
docs/YYYY-MM-DD/
├── market-data.md
├── technical-analysis.md
├── news-sentiment.md
├── retail-sentiment.md
└── decision.md       ← 최종 판단
```

## 자동화 (크론)

장 시작 전 매일 08:30 KST 자동 실행:

```
/schedule
# cron: 30 8 * * 1-5
# command: /daily-stock-analyzer
```

## KRX 인증 (선택)

기본 동작 시 투자자별 순매수(외국인/기관/개인) 데이터는 KRX 정보데이터시스템 로그인 요구로 누락됩니다 (`market-data: partial`). 활성화하려면 [KRX 정보데이터시스템](http://data.krx.co.kr) 계정으로 환경변수 설정:

```json
// .claude/settings.local.json (git ignore 됨)
{
  "env": {
    "KRX_ID": "your_krx_id",
    "KRX_PW": "your_krx_password"
  }
}
```

자세한 설정 옵션은 `.claude/skills/market-data-collector/SKILL.md`의 KRX 인증 섹션 참고.

## 의존성

- Python 3.10+
- `pykrx` (시세 수집)
- 표준 라이브러리만 사용 (urllib, re, xml.etree)

## 라이선스

MIT
