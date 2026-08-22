# Price Structure Scanner — GitHub 적용 파일

기존 CCI/DMI/SAR/Supertrend 스크리너와 별도로 동작하는 **Price Action / Market Structure Scanner**입니다.

## 구현 범위

- Confirmed Pivot High / Low (오른쪽 확인 봉 이후에만 확정)
- HH/HL/LH/LL 시장 구조
- 일봉 OHLCV 기반 근사 Volume Profile: POC / HVN / LVN
- 다중 기간(60/120/250일) 매물대 클러스터링
- Support / Resistance Zone 및 강도
- Descending Trendline Breakout / Ascending Trendline Breakdown
- Ascending / Descending / Symmetrical Triangle
- ATR/거래량 기반 Compression
- Breakout Ready
- Resistance Breakout
- Support Bounce
- Breakout Retest
- Failed Breakout / Failed Breakdown
- Breakout Quality 0~100
- KOSPI/KOSDAQ 대비 20일 Relative Strength
- 시장 Regime(Risk On / Neutral / Risk Off)
- Entry / Invalidation / Target / R-R
- Hard Filter + A+~D 등급
- 모바일 대응 GitHub Pages 대시보드 및 종목 검색
- 종목 클릭 시 캔들 + 지지/저항 Zone + 추세선 + 삼각수렴 표시

## 업로드할 파일

새 파일:

- `price_structure_engine.py`
- `price_structure_scanner.py`
- `price_structure_build_page.py`
- `price_structure_config.json`
- `selftest_price_structure.py`
- `README_PRICE_STRUCTURE.md`

교체 파일:

- `.github/workflows/pages.yml`
- `nav_patch.py`

`requirements.txt`는 현재 레포의 numpy/pandas/yfinance/pykrx/requests/beautifulsoup4 구성으로 충분해서 수정하지 않습니다.

## 실행 흐름

```bash
python price_structure_scanner.py --kospi-n 200 --kosdaq-n 150
python price_structure_build_page.py
python nav_patch.py
```

결과:

- `price_structure_results/summary.json`
- `price_structure_results/summary.csv`
- `price_structure_results/details/*.json`
- `docs/price-structure/index.html`

GitHub Actions에서는 위 과정을 자동 실행하며 Pages에 `/price-structure/`가 추가됩니다.

## 가장 먼저 조정할 설정

모든 주요 임계값은 `price_structure_config.json`에서 변경합니다.

- `pivot_left`, `pivot_right`: Pivot 민감도
- `pivot_min_prominence_atr`: 의미 없는 작은 Swing 제거
- `breakout_buffer_atr`: 가짜 돌파 방지용 종가 여유폭
- `trendline_min_quality`: 추세선 최소 품질
- `breakout_ready_max_atr`: 돌파 임박으로 볼 최대 거리
- `rvol_good`, `rvol_strong`: 상대 거래량 기준
- `triangle_ideal_progress_low/high`: 삼각수렴 이상적 돌파 진행 구간
- `min_rr`: 최소 손익비
- `min_breakout_quality`: 확정 돌파 최소 품질
- `min_final_trade_score`: Hard Filter 최소 종합 점수

## 중요한 제한

### Volume Profile
일봉 OHLCV에는 가격별 실제 체결량이 없으므로 각 일봉의 거래량을 고가~저가 구간에 분배해 근사합니다. 따라서 증권사/TradingView의 intraday Volume-at-Price와 완전히 같지 않습니다.

### Pivot / Look-ahead
Pivot High/Low는 미래 `pivot_right`개 봉이 완성된 뒤에만 확정되는 방식입니다. 이후 별도 백테스트를 만들 때도 `confirmed_x` 이전 시점에 해당 Pivot을 사용하면 안 됩니다.

### 점수
A+/A는 자동 매수 명령이 아닙니다. `hard_filter_pass`, Breakout Quality, R/R, 다음 저항까지의 공간을 함께 보도록 설계했습니다.

## 권장 다음 단계

V1 성능을 실제 데이터로 기록한 뒤 Setup별로 다음을 백테스트하는 것이 좋습니다.

- 5/10/20 거래일 Forward Return
- Win Rate
- MFE / MAE
- False Breakout Rate
- 평균 R multiple
- Score bucket별 성과(50~59, 60~69, 70~79, 80~89, 90+)

이 결과로 `price_structure_config.json`의 임계값을 조정하면 됩니다.
