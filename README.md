# KOSPI 200 + KOSDAQ 150 Signal Screener

기본 유니버스:
- 현재 KOSPI 시가총액 상위 200
- 현재 KOSDAQ 시가총액 상위 150
- 총 최대 350종목

기존 신호 구조는 그대로 유지합니다.

## 신규 매수 신호
CCI(9) 0선 상향돌파
AND +DI > -DI
AND ADX(14) >= 20

CVD Proxy는 필수 진입조건이 아니라 랭킹/확인용입니다.

## KOSDAQ 유동성 필터
기본값:
20일 평균 거래대금 >= 30억원

계산:
20일 평균(Close × Volume)

## GitHub Pages / Notion
1. ZIP 전체를 저장소 루트에 업로드
2. Settings → Pages → Source → GitHub Actions
3. Actions → Daily KOSPI Screener + GitHub Pages → Run workflow
4. 배포 URL을 Notion에서 /embed

Notion Token은 필요 없습니다.

## 수동 실행 옵션
- KOSPI 종목 수
- KOSDAQ 종목 수
- KOSDAQ 20일 평균 거래대금 기준
- CCI 기간
- DMI/ADX 기간
- ADX 최소값
