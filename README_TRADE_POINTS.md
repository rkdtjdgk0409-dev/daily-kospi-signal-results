# Price Structure V4 — 매수 가격 포인트 + 구조 손절선

한국/미국 Price Structure 페이지에 실행(Execution) 레이어를 추가합니다.
기존 익절 목표 1/2 로직은 그대로 유지하고, 신규로 아래를 계산/표시합니다.

## 새 출력

- `execution_plan.status`: 현재 진입 상태
- `preferred_low`, `preferred_high`: 현재 구조에서 우선하는 매수 범위
- `buy_zone_low`, `buy_zone_high`: 눌림 매수 구간
- `breakout_buy`: 돌파 확인 매수 가격
- `stop`: 구조 손절선
- `risk_pct`: 우선 진입 기준 예상 손절폭
- `to_buy_pct`: 현재가에서 눌림 매수 중간값까지 거리
- `to_breakout_pct`: 현재가에서 돌파 확인선까지 거리
- `reasons`: 매수/손절 가격 산출 근거

## 눌림 매수 가격

우선순위:
1. Elliott/Fibonacci 파동 `entry_zone`
2. 지지/거래량 매물대
3. 상승 평행채널 하단

서로 겹치면 교집합을 사용해 합류(confluence)가 높은 가격대를 좁힙니다.

## 돌파 매수 가격

우선순위:
1. 파동 시나리오의 `confirm_price`
2. 저항 매물대 상단 + ATR 버퍼
3. 하락 평행채널 상단 + ATR 버퍼

이미 돌파 가격에서 너무 멀어진 경우 `추격 금지 · 리테스트 대기`로 표시합니다.

## 손절선

다음 구조적 무효화 후보 가운데 현재 진입 기준에 가장 가까운 유효 가격을 사용합니다.

- 기존 support/swing 기반 stop
- 파동 시나리오 invalidation
- 핵심 지지 매물대 하단 - ATR buffer
- 상승채널 하단 - ATR buffer
- 매수 합류구간 하단 - ATR buffer

단, 잡음 손절을 줄이기 위해 진입 기준과 최소 0.70 ATR 간격을 둡니다.

## 페이지 표시

상세 카드:
- 매수 상태
- 우선 매수
- 눌림 매수
- 돌파 매수
- 손절선
- 예상 손절폭
- 현재→눌림 거리
- 현재→돌파 거리
- 판단/근거/손절 근거

차트:
- `BUY ZONE`: 눌림 매수 영역
- `BUY TRIGGER`: 돌파 매수 확인선
- `STOP`: 구조 손절선
- `매매포인트` 토글로 on/off

한국과 미국 페이지에 동일하게 적용됩니다.
