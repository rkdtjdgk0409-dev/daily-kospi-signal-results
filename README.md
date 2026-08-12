# KOSPI Signal Screener → GitHub Pages → Notion Embed

Notion 토큰은 필요 없습니다.

구조:
GitHub Actions → 조건검색 → HTML 생성 → GitHub Pages 배포 → Notion /embed

## 설정
1. ZIP 내용을 저장소 루트에 업로드
2. GitHub 저장소 → Settings → Pages
3. Build and deployment → Source → **GitHub Actions**
4. Actions → `Daily KOSPI Screener + GitHub Pages` → Run workflow
5. deploy job 완료 후 표시되는 GitHub Pages URL 확인
6. Notion에서 `/embed` → 해당 URL 붙여넣기

보통 URL:
`https://<github아이디>.github.io/<저장소이름>/`

## 자동 실행
평일 한국시간 16:40에 실행되도록 설정되어 있습니다.

## 화면
Notion 임베드 페이지에는:
- 신규 매수 신호
- 상승추세 유지 종목 상위 30개
- 종가 / 등락률 / CCI / +DI / -DI / ADX / CVD / 점수

만 표시됩니다.

GitHub Secrets 및 NOTION_TOKEN은 전혀 사용하지 않습니다.
