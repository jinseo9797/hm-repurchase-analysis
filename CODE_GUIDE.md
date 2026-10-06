# SQL과 함께 읽는 H&M 분석 코드

## 적용 방법

1. 기존 프로젝트를 Git으로 커밋하거나 Python 파일을 별도 폴더에 백업합니다.
2. 이 묶음의 01~10 Python 파일을 기존 프로젝트 최상위의 같은 이름 파일과 교체합니다.
3. data/raw와 data/processed의 기존 파일은 유지합니다. ZIP에는 원본 데이터가 없습니다.
4. 필요하면 CODE_GUIDE.md도 프로젝트 최상위에 복사합니다. 기존 README를 대체하지 않습니다.
5. 프로젝트 가상환경에서 기존과 같은 번호순으로 실행합니다.

## 어떻게 읽으면 좋을까요?

각 파일의 처음에는 목적·입력·출력과 MySQL 8 기준 설명용 SQL이 있습니다.
먼저 SQL로 전체 작업을 이해한 뒤 Python의 해당 구문을 읽으세요.
SQL은 모두 # 주석이며 실행하지 않습니다. CSV를 테이블로 적재하는 기능도 추가하지 않았습니다.
SQL에서 날짜는 DATE, 재구매 여부는 TRUE/FALSE, ID는 문자열이라고 가정합니다.
CSV의 빈 값 처리와 SQL의 빈 문자열/NULL 처리는 완전히 같지 않으므로 입력 규칙을 맞춰야 합니다.

| 파일 | SQL 핵심 | Python 핵심 |
|---|---|---|
| 01 | SELECT, LIMIT | read_csv, nrows, dtype |
| 02 | COUNT, MIN/MAX, CASE WHEN | isna, to_datetime, to_numeric, 청크 누적 |
| 03 | COUNT(DISTINCT), HAVING | dropna, nunique, duplicated |
| 04 | LEFT JOIN, IS NULL, OR | isin, ~, 집합에 예시 ID 누적 |
| 05 | GROUP BY, MIN, DATE_SUB | concat, groupby(level=0), Timedelta |
| 06 | EXISTS, DATEDIFF, BETWEEN | map, dt.days, between, set.update |
| 07 | DATE_FORMAT, GROUP BY, AVG | strftime, agg, mean |
| 08 | SELECT, ORDER BY | sort_values, Matplotlib |
| 09 | JOIN, COUNT(DISTINCT), CASE | 첫날 선택, 채널 집합, 조건별 값 지정 |
| 10 | CROSS JOIN, LEFT JOIN, COALESCE | 튜플 키 딕셔너리, items, += |

## 바꾼 부분

- 06·07: 반복되던 결측 검사를 컬럼별 for문으로 정리했습니다. 결측 또는 중복이면 여전히 중단합니다.
- 09: any().any() 대신 컬럼별 결측 검사로 변경했습니다. 오류 메시지에 해당 컬럼이 나옵니다.
- 07·09: groupby(as_index=False)로 그룹 기준을 일반 열로 유지해 reset_index()를 생략했습니다.
- 09: eq()를 익숙한 == 비교로 변경했습니다.
- 10: 끝에 있던 SQL 문자열을 상단 # 주석으로 옮겼습니다. 거래가 없는 조합을 0으로 표시하는 SQL도 추가했습니다.
- 10: 분석 대상 기간의 채널 결측·예상 외 값은 명확한 오류로 알리고 저장 폴더가 없으면 생성합니다.
- 파일 이름, 정상 입력에서의 계산 기준, 결과 CSV 이름과 컬럼은 유지했습니다.

코드의 줄 수는 주석 때문에 늘었습니다. 실행 흐름은 줄이고, 설명은 늘린 버전입니다.
공통 함수·클래스·별도 모듈은 추가하지 않아 각 파일을 위에서 아래로 읽을 수 있습니다.

## 꼭 유지한 계산 기준

- 첫 관측 구매는 데이터에서 처음 보인 구매입니다. 실제 신규 고객으로 단정하지 않습니다.
- 재구매는 첫날을 제외한 1~30일, 양 끝 포함입니다. 채널과 관계없이 인정합니다.
- 데이터 마지막 날짜까지 30일을 관찰할 수 있는 고객만 분모에 포함합니다.
- 09의 both는 첫 관측 구매일에 두 채널을 사용했다는 뜻입니다.
- 거래 행 수는 주문 수가 아닙니다. 중복처럼 보이는 원본 거래도 임의로 지우지 않습니다.
- 월별 비율의 단순 평균을 전체 재구매율로 쓰지 않습니다.
- 채널 1·2의 실제 의미는 공식 정의 확인 전까지 번호로 유지합니다.

## 왜 더 줄이지 않았나요?

05의 concat 후 groupby(level=0).min()은 같은 고객이 여러 청크에 등장할 때 가장 이른 날짜를 유지합니다.
06·09의 set은 청크가 달라도 같은 고객을 한 번만 보관합니다.
단순 덮어쓰기나 청크별 고유 고객 수의 합산으로 바꾸면 결과가 틀릴 수 있어 유지했습니다.

08은 Windows의 Malgun Gothic 폰트를 사용합니다. 다른 OS에서는 설치된 한글 폰트로 바꿔야 합니다.

## 검증 범위

- Python 파일 10개 문법 검사 통과.
- 작은 가상 데이터에서 원본 10개와 수정본 10개를 각각 실행했습니다.
- 검증 중에만 청크 크기를 3행으로 줄여 같은 고객이 서로 다른 청크에 등장하도록 했습니다.
- 생성된 CSV 7개의 값·행 순서·컬럼이 원본과 일치했습니다.
- 같은 날, 1일째, 30일째, 31일째 구매, 관찰 기간 기준일과 그 다음 날,
  첫날 두 채널 이용, 거래가 없는 월·채널의 0행 표시를 확인했습니다.
- 그래프 스크립트는 화면 없는 방식으로 실행을 확인했습니다.
- 3.4GB H&M 원본은 제공되지 않았으므로 전체 실데이터를 재실행한 검증은 아닙니다.
- SQL은 설명용이며 실제 MySQL 서버에서 실행 검증하지 않았습니다.

## GitHub에 반영

프로젝트 최상위에서 변경 내용을 확인한 뒤 실행하세요.

```powershell
git diff --stat
git add -- *.py
# 이 안내 파일도 복사했다면 실행:
git add CODE_GUIDE.md
git commit -m "Clarify analysis code with SQL examples and pandas comments"
git push
```
