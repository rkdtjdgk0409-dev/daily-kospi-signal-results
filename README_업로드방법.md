# 바로 업로드하는 방법

아래 3개 파일만 적용하면 됩니다.

1. `position_manager.py`
   - 저장 위치: 레포 최상단(root)
2. `position_page_patch.py`
   - 저장 위치: 레포 최상단(root)
3. `pages.yml`
   - 저장 위치: `.github/workflows/pages.yml`
   - 기존 파일을 이 파일로 교체

그 다음 GitHub → Actions → `Daily Korea + US Equity Alpha Screeners`
→ `Run workflow`를 한 번 실행합니다.

성공하면 기존 GitHub Pages의 한국 스크리너에서
`Early Setup` 아래에 `📍 Position Management`가 바로 표시됩니다.

표시 상태:
- STRONG HOLD
- HOLD
- WATCH
- TAKE PROFIT
- EXIT
- STOP

주요 값:
- 가상 진입일 / 진입가
- 현재가 / 수익률
- Exit Risk 0~100
- Initial Stop
- Trailing Stop
- 최고 종가 / 고점 대비 하락률
- 판단 사유
- Exit Risk 세부 구성

중요:
`state/position_state.json`은 Actions가 자동 생성하고 main 브랜치에 저장합니다.
이 파일이 있기 때문에 다음 날에도 기존 Confirmed Buy 포지션의 진입가와 최고가가 유지됩니다.

주의:
Confirmed Buy가 처음 발생한 날의 종가를 '가상 진입가'로 사용합니다.
실제 본인의 매수가/보유수량과 연동하는 기능은 아직 넣지 않았습니다.
