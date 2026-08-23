# Alpha + Institutional Risk Engine (V3)

이 버전은 기존 CCI/DMI/ADX/Supertrend/Flow/Relative Strength 기반 **Alpha 엔진**을 유지하면서, 공개적으로 널리 쓰이는 기관형 리스크 지표를 추가한 통합 버전입니다.

## 중요한 구분

Goldman Sachs의 공개 `gs-quant` 프로젝트는 정량 전략/리스크 분석용 Python 툴킷이지만, Goldman Sachs API/Marquee 데이터 접근은 별도 client id/secret이 필요합니다. 이 저장소는 해당 인증에 의존하지 않도록 Yahoo Finance/기존 데이터 파이프라인 위에서 동작하는 로컬 리스크 계산식을 사용합니다.

즉, Goldman Sachs의 비공개 내부 모델을 복제한 것이 아니며, `gs-quant`가 지향하는 **Alpha와 Risk를 분리해 분석하고 리스크 조정 결과를 산출하는 워크플로**를 개인용 스크리너에 맞게 구현했습니다.

## 새로 추가된 값

- `vol60_ann_pct`: 최근 60거래일 연환산 변동성
- `beta120`: 최근 120거래일 시장 베타
  - 한국: KOSPI 종목은 KOSPI, KOSDAQ 종목은 KOSDAQ
  - 미국: S&P 500 편입 종목은 S&P 500, NDX-only 종목은 NASDAQ-100
- `mdd120_pct`: 최근 120거래일 최대낙폭
- `var95_60_pct`: 최근 60거래일 Historical 95% 1-day VaR (손실 크기를 양수 %로 표시)
- `es95_60_pct`: Historical 95% Expected Shortfall
- `risk_quality_score`: 0~100, **높을수록 안정적**
- `risk_score`: 0~100, **높을수록 위험** (기존 UI 호환)
- `final_quant_score`: `Alpha 70% + Risk Quality 30%`
- `model_weight_pct`: 변동성/신호 단계/시장 Regime을 반영한 독립 종목 모델 비중

## Risk Quality 구성

초기 버전은 미래 데이터에 피팅하지 않은 투명한 규칙 기반 점수입니다.

- 60D 연환산 변동성: 30%
- 120D Beta: 20%
- 120D MDD: 25%
- 95% Historical VaR: 15%
- 95% Expected Shortfall: 10%

임계값은 `quant_risk.py`에서 확인·수정할 수 있습니다. 추후에는 walk-forward 백테스트로 보정하는 것을 권장합니다.

## Model Size

`model_weight_pct`는 개인 계좌를 직접 최적화한 비중이 아닙니다. 계좌 규모, 기존 보유종목, 종목 간 상관관계, 레버리지, 세금은 모르는 상태이므로 **독립 종목 위험예산 참고값**으로만 사용합니다.

기본 구조:

1. 60D 변동성 역수 기반 위험예산
2. Alpha 강도 반영
3. Risk Quality 반영
4. `CONFIRMED > FRESH > EARLY > RANK(0%)` 단계 조절
5. `RISK-ON > NEUTRAL > RISK-OFF` 조절
6. 단일 종목 최대 15%

## 페이지 변경

한국/미국 페이지 모두 다음 항목을 표시합니다.

- Alpha Score
- Final Quant Score
- Risk Quality
- Risk Level
- Model Size
- Beta 120D
- MDD 120D
- VaR95
- ES95
- 60D Volatility

Top 60 정렬도 단순 Alpha가 아니라 `Final Quant Score` 우선으로 변경됩니다.

## 실행

기존 GitHub Actions 흐름은 유지됩니다.

```bash
python scanner.py
python build_page.py
python us_scanner.py
python us_build_page.py
```

새로운 패키지 의존성은 없습니다. 기존 `numpy`, `pandas`만으로 Risk Engine이 계산됩니다.
