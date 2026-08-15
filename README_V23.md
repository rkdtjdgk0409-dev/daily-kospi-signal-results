# Korea Equity Alpha Screener V2.3 — Supertrend + Entry Score

V2.2 Searchable Universe를 기반으로 Supertrend를 추가한 버전입니다.
이번 변경은 요청에 따라 별도의 백테스트 최적화 없이, 지표 역할 중복과 신호 빈도를 고려해 구조적으로 설계했습니다.

## 핵심 설계

### 1. Supertrend 기본값
- ATR Period: 10
- Factor: 3.0
- Wilder ATR 기반
- 현재 상승 추세: `GOOD`
- 현재 하락 추세: `BAD`

종목 검색 상세 카드와 각 신호/Top 60 테이블에 표시됩니다.
- `GOOD` = 초록색
- `BAD` = 빨간색

### 2. Supertrend는 Alpha에 별도 5번째 팩터로 추가하지 않음
기존 Alpha 구조를 유지합니다.
- Trend 30%
- Momentum 25%
- Flow 20%
- Relative Strength 25%

Supertrend는 Trend 30점 내부에 포함합니다.

Trend 내부 비중:
- DMI 방향: 35%
- ADX 강도: 30%
- ADX 가속: 10%
- Supertrend: 25%

이렇게 한 이유는 DMI/ADX/Supertrend가 모두 추세 정보를 포함하기 때문에 별도 Alpha 팩터로 추가하면 추세를 이중 계산할 가능성이 있기 때문입니다.

### 3. Entry Score 추가
Alpha Score는 '종목의 현재 기술적 강도', Entry Score는 '지금 진입하기 좋은가'를 구분합니다.

Entry Score:
- CCI 신호 신선도: 30%
- Supertrend: 25%
- DMI/ADX: 20%
- Flow: 15%
- 과열/가격 이격: 10%

Supertrend가 GOOD이고 최근 Bull 전환일수록 유리합니다. 반대로 CCI가 과열되거나 가격이 Supertrend에서 ATR 기준으로 너무 멀리 떨어지면 Entry Score를 낮춥니다.

## Signal Ladder

### CONFIRMED BUY
- Alpha >= 75
- Entry >= 70
- CCI Cross <= 1D
- CCI > 0
- +DI > -DI
- ADX >= 20
- Flow >= 50
- **Supertrend = GOOD 필수**

가장 엄격한 확정 신호에서만 Supertrend를 Hard Filter로 사용합니다.

### FRESH BUY
- Alpha >= 60
- Entry >= 60
- CCI Cross <= 3D
- CCI > 0
- +DI > -DI
- Flow >= 40
- Supertrend GOOD를 Hard Filter로 강제하지 않음

Supertrend가 아직 BAD여도 바로 제외하지 않고 Entry Score에서 감점합니다. CCI/DMI가 먼저 움직이고 Supertrend가 뒤늦게 전환되는 초기 추세를 놓치지 않기 위한 구조입니다.

### EARLY SETUP
- Alpha >= 50
- Entry >= 45
- -30 < CCI <= 0
- CCI 3D Delta >= 25
- +DI / -DI >= 0.85
- Flow >= 40
- RS >= 50

## 종목 상세에서 새로 보이는 값
- `Supertrend GOOD/BAD`
- `ST Flip`: 현재 추세 방향으로 전환된 시점
- `ST Dist / ATR`: 현재가와 Supertrend 선의 거리를 ATR 배수로 표시
- `Entry Score`

## GitHub에서 교체할 파일
1. `scanner.py`
2. `build_page.py`
3. `.github/workflows/pages.yml`
4. `requirements.txt`

업로드 후 GitHub에서:
`Actions → Daily Korea Alpha Screener V2.3 Supertrend + GitHub Pages → Run workflow`

기존 GitHub Pages 설정은 그대로 사용할 수 있습니다.
