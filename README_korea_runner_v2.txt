Korea Runner V2 적용 방법

이번 오류의 정확한 원인:
- Naver mobile API 자체는 작동했습니다.
- 하지만 KOSPI 200개 요청에서 1~2페이지 합계가 195개 고유 종목만 나왔습니다.
- 기존 V1은 200개 미만이면 즉시 실패하도록 되어 있었습니다.
- 이후 pykrx, Naver desktop, cache fallback도 실패해서 Actions가 종료됐습니다.

수정:
1. korea_runner_v2.py를 다운로드합니다.
2. GitHub 저장소 루트의 기존 korea_runner.py를 삭제/교체합니다.
3. 파일 이름은 반드시 korea_runner.py 로 맞춥니다.
4. pages.yml은 이번에는 수정할 필요 없습니다.
5. Commit 후 Actions > Run workflow를 다시 실행합니다.

V2 동작:
- KOSPI 200 요청이면 2페이지만 보고 끝내지 않고 최대 6페이지까지 추가 조회합니다.
- 페이지 경계 중복 때문에 195개만 모여도 뒤 페이지에서 부족분을 계속 채웁니다.
- 그래도 소폭 부족할 경우 90% 이상이면 전체 workflow를 죽이지 않고 진행합니다.
- 성공한 목록은 state/korea_universe.json에 캐시됩니다.

정상 로그 예시:
[universe] trying Naver mobile JSON V2: KOSPI
[universe] Naver KOSPI page 1: +100 unique, total=100/200
[universe] Naver KOSPI page 2: +95 unique, total=195/200
[universe] Naver KOSPI page 3: +5 unique, total=200/200
[universe] Naver mobile OK KOSPI: 200/200
