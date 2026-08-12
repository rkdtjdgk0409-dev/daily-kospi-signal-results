# KOSPI Signal Screener → Notion 일반 페이지 자동 갱신

이 프로젝트는 데이터베이스를 만들지 않습니다.

GitHub Actions가 평일 장 마감 후 KOSPI 시가총액 상위 200개 종목을 분석하고,
조건을 만족하는 종목만 **하나의 Notion 일반 페이지 본문**에 표로 표시합니다.

## 기본 매수조건

```text
CCI(9) 0선 상향돌파
AND
+DI > -DI
AND
ADX(14) >= 20
```

CVD Proxy는 강제 진입조건이 아니라 랭킹/확인용입니다.

## Notion 페이지에는 무엇이 표시되나

1. 기준일 / 업데이트 시간
2. 오늘 신규 매수신호 종목
3. 현재 상승추세 유지 종목 상위 30개
4. 종가, CCI, +DI, -DI, ADX, CVD 확인, signal score
5. 지표 해석

조건에 맞지 않는 전체 200개 종목은 Notion 페이지에 표시하지 않습니다.

---

# 1. Notion에서 빈 페이지 만들기

Notion에서 일반 페이지를 하나 만드세요.

예시 제목:

```text
KOSPI CCI + DMI Signal
```

페이지 안의 본문은 비워두는 것을 권장합니다.
GitHub가 실행될 때 페이지 본문 전체를 자동으로 교체합니다.

---

# 2. Notion Integration 만들기

Notion 개발자 페이지에서 Internal Integration을 만들고
페이지 내용을 수정할 수 있는 권한(Update content)을 허용합니다.

Integration Secret을 복사합니다.

GitHub에는 다음 이름으로 저장합니다.

```text
NOTION_TOKEN
```

---

# 3. 만든 페이지를 Integration과 연결

Notion의 `KOSPI CCI + DMI Signal` 페이지에서 연결/Connections 메뉴를 열고,
방금 만든 Integration이 해당 페이지에 접근할 수 있도록 연결합니다.

이 과정이 빠지면 보통 403 또는 object_not_found 오류가 발생합니다.

---

# 4. NOTION_PAGE_ID 확인

Notion 페이지 URL은 보통 마지막에 긴 ID가 있습니다.

예:

```text
https://www.notion.so/KOSPI-Signal-0123456789abcdef0123456789abcdef
```

이 경우:

```text
0123456789abcdef0123456789abcdef
```

부분이 PAGE ID입니다.

URL 전체를 Secret에 넣어도 스크립트가 어느 정도 처리하지만,
가급적 raw page ID를 넣는 것을 권장합니다.

GitHub Secret 이름:

```text
NOTION_PAGE_ID
```

---

# 5. GitHub Secrets 등록

GitHub 저장소:

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

두 개를 만듭니다.

```text
NOTION_TOKEN
NOTION_PAGE_ID
```

---

# 6. 파일 업로드

ZIP 안의 파일을 저장소 루트에 그대로 올립니다.

```text
scanner.py
notion_publish.py
requirements.txt
.github/workflows/daily_screener_notion.yml
```

---

# 7. 실행

GitHub:

```text
Actions
→ Daily KOSPI Signal Screener + Notion Page
→ Run workflow
```

성공하면 Notion 페이지 본문이 자동으로 바뀝니다.

---

# 자동 실행 시간

GitHub cron:

```text
40 7 * * 1-5
```

UTC 기준이므로 한국시간 평일 16:40입니다.

GitHub Actions scheduled workflow는 정확히 16:40:00에 시작된다고 보장되지는 않으며
몇 분 정도 지연될 수 있습니다.

---

# 결과 파일

GitHub Artifact에도 아래 결과를 저장합니다.

```text
results/latest_buy_signals.csv
results/latest_active_trends.csv
results/latest_all_scored.csv
results/summary.json
results/notion_preview.md
```

`notion_preview.md`는 실제 Notion으로 보낸 내용을 확인하는 용도입니다.

---

# Notion 오류별 확인

## 401 Unauthorized

`NOTION_TOKEN`이 잘못되었거나 만료/삭제된 Integration 토큰인지 확인합니다.

## 403 Forbidden

Integration에 페이지 편집 권한이 없거나 Update content capability가 없는 경우가 많습니다.

## 404 / object_not_found

해당 Notion 페이지를 Integration과 연결하지 않았거나
`NOTION_PAGE_ID`가 잘못된 경우가 많습니다.

---

# 주의

Notion 페이지 본문을 매 실행마다 `replace_content` 방식으로 갱신합니다.
따라서 이 페이지에 직접 작성한 별도 메모는 다음 자동 실행 때 사라질 수 있습니다.

별도 메모가 필요하면 이 자동 페이지의 하위 페이지나 다른 페이지에 작성하는 것을 권장합니다.
