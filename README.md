# Daily KOSPI CCI + DMI Signal Screener

키움증권 조건검색처럼 매일 조건을 만족하는 종목을 찾아 CSV로 출력합니다.

## 기본 유니버스
이전 백테스트와 동일하게 **현재 KOSPI 시가총액 상위 200개**입니다.
- 1순위: pykrx/KRX
- 실패 시: 네이버 금융 KOSPI 시가총액 순위 fallback

## 신규 매수 조건
- CCI(9)가 0선을 상향 돌파
- +DI > -DI
- ADX(14) >= 20

CVD Proxy는 강제 필터가 아니라 랭킹/확인용입니다.

## 결과
- `results/latest_buy_signals.csv`: 오늘 새로 매수 신호가 난 종목
- `results/latest_active_trends.csv`: 현재 상승 추세 조건을 유지 중인 종목
- `results/latest_exit_signals.csv`: CCI 0선 하향돌파 또는 -DI > +DI 종목
- `results/latest_all_scored.csv`: 전체 200종목 지표/점수
- `results/summary.json`: 실행 요약

## 자동 실행
GitHub Actions가 평일 16:40 KST에 실행됩니다. GitHub cron은 UTC 기준이므로 `40 7 * * 1-5`입니다.
실행 완료 후 Actions의 Artifact `daily-kospi-signal-results`를 받으면 됩니다.

## 수동 실행
Actions → `Daily KOSPI Signal Screener` → `Run workflow`

## 로컬 실행
```bash
pip install -r requirements.txt
python scanner.py
```

## CVD 주의
일봉 OHLCV만으로 실제 bid/ask CVD는 계산할 수 없으므로 `Volume × sign(Close-Open)` 누적값을 proxy로 씁니다.
