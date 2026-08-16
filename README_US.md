# US Equity Alpha Screener — S&P 500 + NASDAQ-100

기존 한국 시장 스크리너와 동일한 기술적 모델을 미국 시장에 적용한 GitHub Pages 하위 페이지입니다.

- 페이지: `https://rkdtjdgk0409-dev.github.io/daily-kospi-signal-results/us/`
- 유니버스: 현재 S&P 500과 NASDAQ-100 구성종목의 합집합
- 중복 편입: 한 종목으로 분석하되 두 지수 소속과 각 지수 내 순위를 함께 표시
- 모델: CCI(9), DMI/ADX(14), Supertrend(10, 3.0), Flow 프록시, 상대강도, 변동성 위험
- 신호: `CONFIRMED`, `FRESH`, `EARLY`, Alpha Top 60
- 가격: Yahoo Finance 미국 정규장 조정 일봉
- 자동 실행: 기존 KRX 마감 실행과 미국 마감 후 22:05 UTC 실행

## 구성종목 자동 추적

`us_scanner.py`는 실행할 때마다 최신 구성종목을 조회하고 `state/us_universe.json`의 마지막 검증 스냅샷과 비교합니다.

1. S&P 500은 Wikipedia 구성종목 표를 읽습니다.
2. NASDAQ-100은 Nasdaq 공식 구성종목 API를 사용합니다.
3. S&P 500은 490~515개, NASDAQ-100은 95~110개 범위를 벗어나면 결과를 거부합니다.
4. 한 번에 30개를 초과하는 대량 교체는 파싱 오류 가능성이 높다고 보고 거부합니다.
5. 모든 실시간 소스가 실패하면 마지막 검증 스냅샷을 유지합니다.
6. 실제 편입·편출이 발견된 경우에만 상태 파일에 이력을 추가하고 GitHub Actions가 커밋합니다.

이 구조로 일시적인 웹페이지 형식 변경이 수백 종목의 허위 편출로 표시되는 것을 막습니다.

## 파일

- `us_scanner.py`: 유니버스 수집, 변경 추적, 가격 수집, 신호 계산
- `us_build_page.py`: 반응형 미국 시장 페이지 생성
- `state/us_universe.json`: 첫 성공 실행 후 생성되는 검증 스냅샷과 변경 이력
- `us_results/`: Actions artifact에 30일간 보관되는 CSV/JSON 결과
- `docs/us/index.html`: 배포 시 생성되는 미국 시장 페이지

## 수동 실행

저장소의 **Actions → Daily Korea + US Equity Alpha Screeners → Run workflow**를 누르면 한국판과 미국판이 함께 다시 계산됩니다.

> 정적 GitHub Pages이므로 페이지의 `↻ 최신 데이터` 버튼은 계산을 직접 실행하지 않습니다. 새 배포본이 있는지 캐시 없이 확인하고, 새 버전이면 화면을 교체합니다.
