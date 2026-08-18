# 적용 방법

이번 버전은 Position Management를 한국 스크리너 본문에서 분리합니다.

업로드:
- `position_manager.py` → 레포 루트
- `position_build_page.py` → 레포 루트
- `nav_patch.py` → 레포 루트
- `pages.yml` → `.github/workflows/pages.yml` 교체

기존에 올렸던 `position_page_patch.py`는 삭제하거나 사용하지 않아도 됩니다.

Actions를 다시 실행하면 주소:
- 한국: `/daily-kospi-signal-results/`
- 미국: `/daily-kospi-signal-results/us/`
- 포지션 관리: `/daily-kospi-signal-results/position/`

세 페이지 상단에서 서로 이동할 수 있습니다.
