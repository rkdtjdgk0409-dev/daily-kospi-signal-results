# Korea Equity Alpha Screener V2.1 — Signal Ladder

V2의 Alpha/Trend/Momentum/Flow/RS/Risk/Regime 구조는 유지하면서, 신규 매수 신호가 지나치게 적어지는 문제를 줄이기 위해 진입 후보를 3단계로 분리한 버전입니다.

## 교체할 파일

1. 저장소 루트 `scanner.py`
2. 저장소 루트 `build_page.py`
3. `.github/workflows/pages.yml`
4. `requirements.txt`는 기존과 동일하지만 함께 업로드해도 됩니다.

교체 후 GitHub에서 **Actions → Daily Korea Alpha Screener V2.1 + GitHub Pages → Run workflow**를 실행하세요.

## Alpha Score

기존 V2와 동일합니다.

- Trend 30%
- Momentum 25%
- Flow 20%
- Relative Strength 25%

Risk와 Market Regime은 Alpha에서 분리합니다.

## 왜 V2.1에서 임계값을 다시 조정했나

V2 Alpha는 CCI 돌파 초기와 DMI/ADX 추세 형성 초기에 Trend/Momentum 점수가 아직 충분히 높지 않을 수 있습니다. 이 상태에서 `Alpha >= 70 + 최근 2일 CCI 돌파 + ADX >= 20 + Flow >= 50`을 모두 Hard Filter로 걸면 Alpha 안에서 이미 평가한 조건을 다시 한 번 거르는 셈이라 신규 신호가 매우 적어질 수 있습니다.

따라서 V2.1은 엄격한 확정 신호는 유지하면서 초기 후보를 별도 단계로 보여줍니다.

## 1) CONFIRMED BUY

기본값:

- Alpha >= 75
- CCI 0선 상향돌파가 오늘 또는 직전 거래일 (`cross_age <= 1`)
- 현재 CCI > 0
- +DI > -DI
- ADX >= 20
- Flow >= 50

가장 확정성이 높은 대신 신호 빈도는 낮습니다.

## 2) FRESH BUY

기본값:

- Alpha >= 60
- CCI 0선 상향돌파가 최근 3거래일 이내
- 현재 CCI > 0
- +DI > -DI
- Flow >= 40
- ADX >= 20은 Hard Filter에서 제거

Trend Score 안에서 DMI 방향/ADX 강도/ADX 가속도를 이미 평가하므로, Fresh 단계에서는 ADX 20 필터를 다시 강제하지 않습니다. 추세가 막 생기기 시작하는 종목을 포착하는 단계입니다.

Confirmed 조건을 만족한 종목은 Fresh에 중복 표시하지 않습니다.

## 3) EARLY SETUP

기본값:

- Alpha >= 50
- -30 < CCI <= 0
- CCI 3거래일 변화량 >= +25
- +DI / -DI >= 0.85
- Flow >= 40
- RS >= 50

CCI가 아직 0선을 넘지 않았지만 빠르게 접근하고 있고, DMI가 상향 교차에 가까우며, 거래 흐름과 상대강도가 약하지 않은 종목을 선행 감시합니다.

### Early Alpha 기준이 50인 이유

돌파 전에는 CCI Level/Freshness 점수가 낮고 +DI가 -DI보다 아직 충분히 크지 않을 수 있어 Alpha 자체가 구조적으로 낮습니다. Early까지 60~70을 요구하면 이 단계가 다시 거의 비게 됩니다. 대신 RS >= 50, Flow >= 40, DMI Ratio >= 0.85, CCI acceleration 조건을 함께 요구해 품질을 보완합니다.

## Setup 등급

- `A+`: Confirmed + Alpha >= 85 + RS >= 80 + Flow >= 65 + RISK-ON
- `A`: Confirmed
- `B`: Fresh
- `EARLY`: Early Setup
- `WATCH`: Alpha >= 60이지만 위 진입 단계에는 미포함

## 생성 CSV

- `latest_all_scored.csv`
- `latest_buy_signals.csv` — Confirmed + Fresh 합본(기존 호환용)
- `latest_confirmed_buy.csv`
- `latest_fresh_buy.csv`
- `latest_early_setups.csv`
- `latest_active_trends.csv`
- `latest_top_alpha.csv`
- `summary.json`
- `universe.csv`

## 다음 검증 포인트

이 임계값은 최종 최적값이 아니라 논리적으로 조정한 기본값입니다. 이후 백테스트에서 단계별로 아래를 비교하는 것이 좋습니다.

- 일평균 신호 수
- 1일 / 5일 / 10일 Forward Return
- 승률
- Profit Factor
- MDD
- 평균 보유기간
- Turnover
- 거래비용 반영 후 성과

특히 Confirmed / Fresh / Early가 순서대로 기대수익과 신뢰도에서 실제 차이를 보이는지 검증해야 합니다.
