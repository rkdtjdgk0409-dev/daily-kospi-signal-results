# Korea Equity Alpha Screener V2.4 — Close Refresh + Mobile

V2.3 Supertrend + Entry Score를 유지하면서 **장 마감 후 자동 업데이트**, **NXT 미사용 안내**, **페이지 내 최신 배포본 확인 버튼**, **모바일 카드형 표**를 추가한 버전입니다.

## 핵심 변경

- KRX 정규장 종료 후 **15:50 KST** 1차 자동 실행
- 일봉 데이터 게시 지연 대응용 **16:20 KST** 2차 보정 실행
- 스캐너는 기존처럼 Yahoo Finance의 `.KS` / `.KQ` 일봉을 사용하고 NXT API/데이터는 조회하지 않음
- `generated_at`을 GitHub 서버 UTC가 아니라 **Asia/Seoul(KST)** 로 기록
- 마감 직후 종목별 일봉 게시 시점 차이 때문에 서로 다른 날짜가 섞이지 않도록 **종가 날짜 정렬(close-date alignment)** 적용
- 화면 우측 상단 **↻ 최신 데이터** 버튼 추가
  - 토큰 없이 안전하게 최신 GitHub Pages 배포본을 `no-store` 방식으로 조회
  - 새로운 배포본이 있으면 자동으로 페이지 교체
  - 이미 최신이면 상태 메시지만 표시
- 페이지를 켜 둔 상태에서도 **5분마다** 최신 배포본 확인
- 700px 이하 모바일 화면에서 신호/Top 60 표를 카드형으로 전환
- 모바일에서는 우측 상단 새로고침 버튼을 원형 아이콘으로 축소

## 중요한 제한

GitHub Pages는 정적 페이지이므로 브라우저의 버튼이 GitHub Actions 자체를 직접 재실행하도록 만들려면 인증 토큰을 노출해야 합니다. 이 버전은 안전하게 다음 구조를 사용합니다.

1. GitHub Actions가 15:50 / 16:20 KST에 실제 스캐너와 지표를 재계산
2. GitHub Pages에 새 HTML을 배포
3. 페이지의 `↻ 최신 데이터` 버튼은 새 배포본 존재 여부를 캐시 없이 확인하고 새 버전이면 즉시 전환

## GitHub에서 교체할 파일

1. `scanner.py`
2. `build_page.py`
3. `.github/workflows/pages.yml`
4. `requirements.txt`

업로드 후 **Actions → Daily Korea Alpha Screener V2.4 Close Refresh + Mobile → Run workflow**를 한 번 실행하면 됩니다. 이후 평일 자동 실행됩니다.
