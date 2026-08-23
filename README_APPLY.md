# US Price Structure — Wave Structure Upgrade

기존 `daily-kospi-signal-results`의 `/us-price-structure/` 페이지를 유지하면서 분석 메커니즘을
`평행채널 + 지지/저항/매물대 + Elliott-style 파동 후보 + Fibonacci + 돌파/리테스트 + 무효화` 중심으로 바꾸는 패치입니다.

## 바꿀 파일

저장소 루트에서 아래 파일을 그대로 추가/교체합니다.

1. **새 파일 추가**: `price_structure_wave.py`
2. **교체**: `us_price_structure_scanner.py`
3. **교체**: `us_price_structure_build_page.py`
4. **교체**: `us_price_structure_config.json`

기존 `price_structure_engine.py`, `price_structure_channels.py`, `us_scanner.py`, 포지션 관리 페이지 등은 변경하지 않습니다.

## 기존 GitHub Actions 수정 여부

현재 저장소의 `.github/workflows/pages.yml`은 이미 다음 순서로 실행됩니다.

- `python us_scanner.py`
- `python us_price_structure_scanner.py`
- `python us_price_structure_build_page.py`
- `docs/`를 GitHub Pages로 배포

따라서 위 4개 파일만 반영하면 **워크플로 파일을 바꾸지 않아도 기존 스케줄/수동 실행에서 새 페이지가 생성됩니다.**
반영 직후 확인하려면 GitHub → Actions → `Daily Korea + US Equity Alpha Screeners` → `Run workflow`를 한 번 실행합니다.

## 새 분석 상태

- `WAVE2_PULLBACK`: 2파 눌림 · 3파 대기
- `WAVE3_ADVANCE`: 3파 상승 진행
- `WAVE4_PULLBACK`: 4파 조정 · 5파 대기
- `WAVE5_ADVANCE`: 5파 상승 / 연장 구간
- `CHANNEL_REVERSAL`: 하락채널 돌파 · 1파 탐색
- `RESISTANCE_PAUSE`: 저항 앞 숨 고르기
- `BASE_BUILDING`: 바닥/구조 전환 관찰
- `STRUCTURE_RISK`: 구조 훼손 / 리스크

## 메커니즘

1. 기존 엔진에서 확정 Pivot, 매물대/지지·저항, RVOL, 상대강도, 돌파 품질을 계산합니다.
2. 기존 robust-regression 평행채널을 그대로 사용합니다.
3. 확정 Pivot을 L-H-L / L-H-L-H-L로 정리해 상승 0-1-2 / 0-1-2-3-4 후보를 찾습니다.
4. 1파의 38.2/50/61.8/78.6% 되돌림과 1.0/1.272/1.618/2.0 extension을 계산합니다.
5. 지지 매물대와 Fibonacci 눌림 구간의 겹침, 하락채널 돌파, 상대강도, RVOL, R/R을 결합해 신뢰도와 등급을 계산합니다.
6. 각 종목에 `확인 가격`, `무효화 가격`, `목표 1/2`, `예상 경로`를 생성합니다.
7. 기존 실패 돌파/지지 이탈 등 하방 구조 훼손은 파동 시나리오보다 우선하여 `STRUCTURE_RISK` 처리합니다.

## 페이지에서 유지되는 기능

- 기존 다크 UI와 좌측 종목 리스트 / 우측 상세 구조
- 종목 검색, 시장/등급 필터, 정렬
- 모바일 레이아웃
- Plotly 캔들, 휠/핀치 확대·축소, 1M/3M/6M/1Y/전체
- 주말 공백 없는 category 축
- 지지/저항 매물대, POC, 전문 평행채널
- 한국시장/미국시장/포지션관리 네비게이션

## 페이지에 추가되는 표시

- (1)(2)(3)(4) 파동 라벨과 zig-zag
- Fibonacci 되돌림/확장선
- 2파/4파 진입 후보 구간
- 점선 예상 시나리오 경로
- `01 현재 구조` / `02 대응` 요약 카드
- 확인/무효화/목표 가격
- 차트 오버레이 토글: 파동 / Fib / 채널 / 매물대 / 예상경로

> 파동 카운트는 확정적인 미래 예측이 아니라 **조건부 시나리오**입니다. 가격이 무효화 가격을 깨면 해당 파동 가정을 폐기하도록 설계했습니다.
