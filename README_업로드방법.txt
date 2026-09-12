KOSPI/KOSDAQ GitHub Actions 오류 수정 패키지
=============================================

원인
----
기존 scanner.py의 종목 유니버스 수집 순서는
1) pykrx/KRX
2) 네이버 금융 데스크톱 HTML
이었습니다.

현재 Actions 로그에서는 pykrx/KRX 응답 컬럼 오류가 난 뒤,
네이버 HTML fallback도 0종목을 반환하면서 전체 작업이 종료됩니다.

수정 방식
---------
기존 scanner.py, price_structure_scanner.py의 계산 로직은 건드리지 않습니다.

추가 파일:
- korea_runner.py

교체 파일:
- .github/workflows/pages.yml

새 유니버스 수집 순서:
1) 네이버 모바일 JSON 시가총액 API
2) pykrx/KRX
3) 기존 네이버 데스크톱 HTML
4) state/korea_universe.json 캐시

업로드 방법
-----------
1. 압축을 풉니다.
2. korea_runner.py 를 저장소 최상위(root)에 업로드합니다.
   scanner.py와 같은 위치입니다.
3. .github/workflows/pages.yml 을 기존 파일과 교체합니다.
4. Commit 합니다.
5. GitHub > Actions > 해당 workflow > Run workflow 로 수동 실행합니다.

정상 로그 예시
--------------
[universe] trying Naver mobile JSON: KOSPI
[universe] Naver mobile OK KOSPI: 200
[universe] trying Naver mobile JSON: KOSDAQ
[universe] Naver mobile OK KOSDAQ: 150

첫 성공 실행 뒤에는 state/korea_universe.json도 자동 저장됩니다.
그 뒤 외부 유니버스 API가 일시적으로 모두 실패해도 캐시를 마지막 fallback으로 사용할 수 있습니다.

중요
----
requirements.txt는 교체할 필요가 없습니다.
scanner.py 자체도 교체할 필요가 없습니다.
