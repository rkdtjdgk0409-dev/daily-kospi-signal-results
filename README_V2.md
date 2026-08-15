# Korea Equity Alpha Screener V2

기존 `daily-kospi-signal-results` GitHub Pages 스크리너를 V2 점수 체계로 교체하는 파일입니다.

## 교체할 파일

1. 저장소 루트의 `scanner.py`를 이 폴더의 `scanner.py`로 교체
2. 저장소 루트의 `build_page.py`를 이 폴더의 `build_page.py`로 교체
3. `.github/workflows/pages.yml`을 이 폴더의 동일 경로 파일로 교체
4. `requirements.txt`는 기존과 동일하지만 함께 넣어도 됩니다.

그 다음 GitHub의 **Actions → Daily Korea Alpha Screener + GitHub Pages → Run workflow**를 실행하면 됩니다.

## V2 Alpha Score

- Trend: 30%
  - DMI 방향성
  - ADX 강도(ADX 40 부근에서 포화)
  - 3거래일 ADX 변화
- Momentum: 25%
  - CCI 0선 상향돌파 신선도
  - 3거래일 CCI 변화
  - CCI 과열 제한 레벨 점수
- Flow: 20%
  - 일봉 OHLCV 기반 CVD proxy 5일 기울기
  - CVD proxy vs EMA10
  - 당일 거래대금 / 20일 평균 거래대금
- Relative Strength: 25%
  - KOSPI/KOSDAQ 벤치마크 대비 20일·60일 초과수익률
  - 같은 시장 종목들 안에서 percentile 점수화

모든 하위 점수와 최종 Alpha Score는 0~100 범위입니다.

## Risk

Risk는 Alpha에 섞지 않습니다.

- ATR(14) / Price
- 20일 연환산 실현변동성
- 같은 시장 안에서 percentile 계산
- LOW / MED / HIGH로 별도 표시

## Market Regime

KOSPI와 KOSDAQ을 별도로 계산합니다.

- Index > MA20
- Index > MA60
- MA20 > MA60
- Breadth20 >= 55%
- Breadth60 >= 50%

5개 중 4~5개 만족: `RISK-ON`  
2~3개 만족: `NEUTRAL`  
0~1개 만족: `RISK-OFF`

## 신규 매수 후보

기본 설정은 아래 조건을 모두 만족해야 합니다.

- CCI가 오늘 또는 직전 거래일에 0선을 상향돌파
- 현재 CCI > 0
- +DI > -DI
- ADX >= 20
- Flow Score >= 50
- Alpha Score >= 70

`buy_alpha_threshold`는 GitHub Actions 수동 실행 화면에서 변경할 수 있습니다.

## 생성 결과

`results/`에 다음 파일이 생성됩니다.

- `latest_all_scored.csv`
- `latest_buy_signals.csv`
- `latest_active_trends.csv`
- `latest_top_alpha.csv`
- `summary.json`
- `universe.csv`

GitHub Pages에는 `docs/index.html`이 생성·배포됩니다.
