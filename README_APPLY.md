# 한국 Price Structure — 파동/채널 분석 업그레이드

기존 `docs/price-structure/` 페이지의 다크 UI, 검색, KOSPI/KOSDAQ 필터, 모바일 대응,
캔들 줌/핀치, 지지·저항과 평행채널 표시를 유지하면서 분석 메커니즘을 다음 순서로 바꿉니다.

1. 기존 매물대/지지·저항/확정 Pivot/상대강도/RVOL 계산
2. robust regression 기반 평행채널 탐지
3. 하락채널 돌파 또는 구조 전환 확인
4. 확정 Swing으로 0-1-2 / 0-1-2-3-4 파동 후보 탐지
5. 2파 38.2~61.8% 눌림 + 지지 매물대 합류 평가
6. 1파 고점 돌파 시 3파 진행으로 승격
7. 4파 조정/5파 연장, 저항 앞 숨고르기, 구조 훼손 시나리오 분류
8. Fibonacci 되돌림/확장, 확인가, 무효화가, 목표가를 차트에 표시

## 교체/추가 파일

저장소 루트에서 아래 4개 파일을 추가 또는 교체하세요.

- `price_structure_wave.py` (신규, 미국 버전과 동일한 공용 파동 엔진)
- `price_structure_scanner.py` (교체)
- `price_structure_build_page.py` (교체)
- `price_structure_config.json` (교체)

기존 `price_structure_engine.py`, `price_structure_channels.py`, `scanner.py`, `pages.yml`은 그대로 둡니다.
현재 Actions 워크플로가 이미 `price_structure_scanner.py` → `price_structure_build_page.py`를 실행하므로
별도 workflow 수정이 필요하지 않습니다.

## 결과 주소

기존과 동일한 GitHub Pages 경로를 유지합니다.

`/daily-kospi-signal-results/price-structure/`

## 주요 셋업

- `WAVE2_PULLBACK`: 2파 눌림 · 3파 대기
- `WAVE3_ADVANCE`: 3파 상승 진행
- `CHANNEL_REVERSAL`: 하락채널 돌파 · 1파 탐색
- `WAVE4_PULLBACK`: 4파 조정 · 5파 대기
- `WAVE5_ADVANCE`: 5파 상승 / 연장
- `RESISTANCE_PAUSE`: 저항 앞 숨 고르기
- `BASE_BUILDING`: 바닥/구조 전환 관찰
- `STRUCTURE_RISK`: 상승 시나리오 무효화/구조 훼손

파동 번호와 예상경로는 확정 예측이 아니라 조건부 시나리오이며, 각 시나리오에 확인가와 무효화가를 함께 표시합니다.
