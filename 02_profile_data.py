# 02_profile_data.py
# 목적: 전체 거래 행 수·결측·날짜·가격 검사
# 입력: transactions_train.csv
# 출력: 화면 출력
# 실행: 프로젝트 최상위에서 python 02_profile_data.py
#
# [읽는 순서] 아래 SQL로 전체 흐름을 이해한 뒤 Python 본문을 읽으세요.
# SQL은 MySQL 8 기준의 설명용 예시이며 이 Python 파일에서 실행되지 않습니다.
# CSV를 같은 이름의 테이블로 적재하고 날짜·키·불리언 타입을 맞췄다고 가정합니다.
# 앞 단계(01~04)의 검증 결과에 문제가 있으면 원인을 해결한 뒤 분석을 진행하세요.
#
# -- 날짜·가격 변환 검사는 아래 Python에서 먼저 수행합니다.
# -- 아래 SQL은 t_dat가 DATE, price가 숫자 타입으로 검증된 이후의 예시입니다.
# SELECT COUNT(*) AS total_rows,
#        MIN(t_dat) AS min_date, MAX(t_dat) AS max_date,
#        SUM(CASE WHEN t_dat IS NULL THEN 1 ELSE 0 END) AS missing_date,
#        SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS missing_customer,
#        SUM(CASE WHEN article_id IS NULL THEN 1 ELSE 0 END) AS missing_article,
#        SUM(CASE WHEN price IS NULL THEN 1 ELSE 0 END) AS missing_price,
#        SUM(CASE WHEN sales_channel_id IS NULL THEN 1 ELSE 0 END) AS missing_channel,
#        SUM(CASE WHEN price < 0 THEN 1 ELSE 0 END) AS negative_price,
#        SUM(CASE WHEN price = 0 THEN 1 ELSE 0 END) AS zero_price
# FROM transactions_train;
# -- CSV의 빈 값은 SQL의 NULL에 대응한다고 가정합니다.
# -- 문자열의 날짜·숫자 변환 오류 처리는 DB별로 달라 별도 Python 검사로 설명합니다.

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR / "data" / "raw" / "transactions_train.csv"

total_rows = 0
missing_counts = None

min_date = None
max_date = None

invalid_date_count = 0
invalid_price_count = 0
negative_price_count = 0
zero_price_count = 0

# 파일을 한 번에 100,000행씩 읽기
with pd.read_csv(
    file_path,
    dtype="string",
    chunksize=100_000,
) as reader:

    for chunk_number, chunk in enumerate(reader, start=1):
        # len(chunk)는 이번 청크 행 수. +=로 전체 행 수에 더합니다.
        total_rows += len(chunk)

        # 컬럼별 결측치 개수를 누적
        # isna(): 각 칸을 결측 여부 True/False로 변환합니다.
        # sum(): 열별로 True(1)를 더해 결측 개수 Series를 만듭니다.
        chunk_missing = chunk.isna().sum()

        if missing_counts is None:
            missing_counts = chunk_missing
        else:
            # 두 Series는 열 이름(인덱스)을 기준으로 같은 항목끼리 더해집니다.
            missing_counts = missing_counts + chunk_missing

        # 날짜 변환: 변환할 수 없는 값은 NaT
        # errors="coerce": 잘못된 날짜는 NaT(날짜 결측)로 바꿔 개수를 셉니다.
        # 05부터는 검증된 데이터를 쓰므로 errors="raise"로 오류 시 중단합니다.
        dates = pd.to_datetime(
            chunk["t_dat"],
            format="%Y-%m-%d",
            errors="coerce",
        )

        # 원래 결측치였던 값과 형식 오류를 구분
        # notna() & isna(): 원래 값은 있었지만 날짜 변환 후 사라진 값만 셉니다.
        # 원래부터 비어 있던 값과 변환 오류를 중복해서 세지 않습니다.
        invalid_date_count += int(
            (chunk["t_dat"].notna() & dates.isna()).sum()
        )

        chunk_min = dates.min()
        chunk_max = dates.max()

        if pd.notna(chunk_min):
            if min_date is None or chunk_min < min_date:
                min_date = chunk_min

        if pd.notna(chunk_max):
            if max_date is None or chunk_max > max_date:
                max_date = chunk_max

        # 가격을 숫자로 변환
        # to_numeric: 숫자 문자열을 수치로 변환. 변환 불가 값은 결측으로 바꿉니다.
        prices = pd.to_numeric(
            chunk["price"],
            errors="coerce",
        )

        invalid_price_count += int(
            (chunk["price"].notna() & prices.isna()).sum()
        )

        negative_price_count += int((prices < 0).sum())
        zero_price_count += int((prices == 0).sum())

        # 10개 묶음마다 진행 상황 출력
        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 확인 완료", flush=True)

print("\n=== 거래 데이터 점검 결과 ===")
print(f"전체 행 수: {total_rows:,}")

print(
    "시작일:",
    min_date.date() if min_date is not None else "유효한 날짜 없음",
)
print(
    "종료일:",
    max_date.date() if max_date is not None else "유효한 날짜 없음",
)

print("\n컬럼별 결측치:")
print(missing_counts)

print(f"\n날짜 형식 오류: {invalid_date_count:,}건")
print(f"가격 숫자 변환 오류: {invalid_price_count:,}건")
print(f"음수 가격: {negative_price_count:,}건")
print(f"0인 가격: {zero_price_count:,}건")
