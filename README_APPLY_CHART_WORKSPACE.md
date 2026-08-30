# 차트구조 워크스페이스 패치 적용법

기존 GitHub Actions 흐름은 그대로 사용합니다. `.github/workflows/pages.yml` 수정은 필요 없습니다.

## 업로드할 파일

루트에 아래 3개 파일을 넣습니다.

1. `price_structure_workspace.py` — 새로 추가
2. `price_structure_build_page.py` — 기존 파일 교체
3. `us_price_structure_build_page.py` — 기존 파일 교체

## 변경 결과

### 한국 차트구조
- `/price-structure/` : **종목 스캔 전용 페이지**
- `/price-structure/stock.html?ticker=005930` : 종목별 독립 차트 워크스페이스

### 미국 차트구조
- `/us-price-structure/` : **종목 스캔 전용 페이지**
- `/us-price-structure/stock.html?ticker=AAPL` : 종목별 독립 차트 워크스페이스

## 종목 상세 페이지 구조

- 왼쪽: 큰 캔들 차트
  - 매물대 ON/OFF
  - 파동 ON/OFF
  - 채널 ON/OFF
  - 매매포인트 ON/OFF
  - 예상경로 ON/OFF
  - Fibonacci ON/OFF
  - 3M / 6M / 1Y / 전체 범위 전환
- 오른쪽: 매매포인트 분석 상태
  - 현재가 / 등급 / 종합점수
  - 우선매수 / 눌림매수 / 돌파매수
  - 손절선 / 예상손절폭
  - 지지·저항 / 평행채널 / 파동 신뢰도
  - 구조 시나리오 / 판단 구성

## 적용 후

GitHub `Actions` → `Daily Korea + US Equity Alpha Screeners` → `Run workflow`를 한 번 실행합니다.
Pages 빌드가 끝나면 기존 차트구조 링크는 자동으로 새 스캔 페이지를 가리킵니다.
