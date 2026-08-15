# Korea Equity Alpha Screener V2.2 — Searchable Universe

V2.1의 Signal Ladder(Confirmed / Fresh / Early)와 Alpha 계산은 그대로 유지하면서, **Top 60 밖 종목도 전체 분석 유니버스에서 검색해 상세 데이터를 볼 수 있는 기능**을 추가한 버전입니다.

## 핵심 추가 기능

### 전체 분석 종목 검색
- 종목명 또는 6자리 종목코드로 검색
- 부분 일치 자동완성
- KOSPI / KOSDAQ 시장 필터
- 방향키 + Enter 또는 마우스로 종목 선택
- Top 60 밖 종목도 조회 가능
- 검색 대상은 `latest_all_scored.csv`에 포함된 **분석 완료 전체 종목**

### 검색 결과 상세 카드
검색한 종목에 대해 아래를 한 화면에서 표시합니다.

- 종가 / 일간 등락률
- 전체 Alpha 순위 / 해당 시장 Alpha 순위 / Top 60 포함 여부
- Signal Tier: CONFIRMED / FRESH / EARLY / RANK
- Setup: A+ / A / B / EARLY / WATCH
- State / Market Regime
- Alpha / Trend / Momentum / Flow / Relative Strength / Risk
- CCI / CCI 3D Δ / CCI Cross
- +DI / -DI / DMI Ratio
- ADX / ADX 3D Δ
- 당일 상대 거래대금(Dollar Vol) / ADV20
- RS20·RS60 초과수익률과 percentile
- ATR% / 20일 연환산 변동성
- MA20 / MA60 위·아래 여부
- Active Trend 여부

## Top 60

기존 **Alpha Ranking Top 60** 표는 그대로 유지합니다. Top 60 표 안의 검색/시장/Alpha 필터는 Top 60 내부에서만 작동하며, 전체 종목 조회는 그 위의 별도 검색 패널을 사용합니다.

## V2.1 Signal Ladder 유지

### CONFIRMED BUY
- Alpha >= 75
- CCI Cross <= 1D
- CCI > 0
- +DI > -DI
- ADX >= 20
- Flow >= 50

### FRESH BUY
- Alpha >= 60
- CCI Cross <= 3D
- CCI > 0
- +DI > -DI
- Flow >= 40
- ADX 20 하드필터 없음

### EARLY SETUP
- Alpha >= 50
- -30 < CCI <= 0
- CCI 3D Δ >= 25
- +DI / -DI >= 0.85
- Flow >= 40
- RS >= 50

## Alpha Score
- Trend 30%
- Momentum 25%
- Flow 20%
- Relative Strength 25%
- Risk와 Market Regime은 Alpha에서 분리

## GitHub에서 교체할 파일

가장 중요한 변경 파일은 **`build_page.py`** 입니다.

전체 버전을 맞추려면 다음을 교체하세요.

1. 저장소 루트 `build_page.py` **(필수)**
2. 저장소 루트 `scanner.py` — 계산식은 V2.1과 동일하고 버전 표기만 V2.2로 변경
3. `.github/workflows/pages.yml` — 워크플로우 표시 이름/아티팩트 이름만 V2.2로 변경
4. `requirements.txt` — 기존과 동일

교체 후 GitHub에서 **Actions → Daily Korea Alpha Screener V2.2 + GitHub Pages → Run workflow**를 실행하세요.

## 구조

`scanner.py`가 `results/latest_all_scored.csv`를 생성하면, `build_page.py`가 전체 종목 데이터를 JSON 형태로 정적 HTML 안에 포함합니다. 따라서 검색할 때 추가 서버/API 요청이 필요하지 않고 GitHub Pages 브라우저 안에서 즉시 검색됩니다.
