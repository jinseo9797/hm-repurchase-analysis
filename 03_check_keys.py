# 03_check_keys.py
# 목적: 고객·상품 테이블의 키 결측과 중복 검사
# 입력: customers.csv, articles.csv
# 출력: 화면 출력
# 실행: 프로젝트 최상위에서 python 03_check_keys.py
#
# [읽는 순서] 아래 SQL로 전체 흐름을 이해한 뒤 Python 본문을 읽으세요.
# SQL은 MySQL 8 기준의 설명용 예시이며 이 Python 파일에서 실행되지 않습니다.
# CSV를 같은 이름의 테이블로 적재하고 날짜·키·불리언 타입을 맞췄다고 가정합니다.
# 앞 단계(01~04)의 검증 결과에 문제가 있으면 원인을 해결한 뒤 분석을 진행하세요.
#
# SELECT COUNT(*) AS total_rows,
#        COUNT(*) - COUNT(customer_id) AS missing_count,
#        COUNT(DISTINCT customer_id) AS unique_count,
#        COUNT(customer_id) - COUNT(DISTINCT customer_id) AS duplicate_extra_rows
# FROM customers;
# -- [A, A, A, B]라면 중복 초과 행은 2행입니다. 중복 ID 종류는 1개입니다.
# SELECT customer_id, COUNT(*) AS row_count
# FROM customers
# WHERE customer_id IS NOT NULL
# GROUP BY customer_id
# HAVING COUNT(*) > 1;
# -- articles도 customer_id를 article_id로 바꿔 같은 방법으로 검사합니다.

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"

# 파일명과 확인할 ID 컬럼
targets = [
    ("customers.csv", "customer_id"),
    ("articles.csv", "article_id"),
]

for file_name, key_column in targets:
    file_path = RAW_DIR / file_name

    # 다른 컬럼은 제외하고 ID 컬럼만 읽기
    df = pd.read_csv(
        file_path,
        usecols=[key_column],
        dtype="string",
    )

    ids = df[key_column]

    missing_count = int(ids.isna().sum())

    # 결측치를 제외한 ID로 중복 검사
    # dropna(): NULL에 해당하는 값 제외. SQL WHERE customer_id IS NOT NULL.
    valid_ids = ids.dropna()

    # nunique(): COUNT(DISTINCT ID). duplicated(): 첫 등장 외 반복 행에 True.
    unique_count = valid_ids.nunique()
    duplicate_count = int(valid_ids.duplicated().sum())
    
    # 파일 2개 돌기
    print(f"\n=== {file_name} ID 점검 ===")
    print(f"전체 행 수: {len(df):,}")
    print(f"ID 결측치: {missing_count:,}")
    print(f"고유 ID 수: {unique_count:,}")
    print(f"중복 ID 초과 행 수: {duplicate_count:,}")

    if duplicate_count > 0:
        # keep=False는 첫 등장까지 포함해 중복 ID에 속한 모든 행을 표시합니다.
        duplicate_ids = valid_ids[
            valid_ids.duplicated(keep=False)
        ]

        print("\n중복된 ID 샘플:")
        print(duplicate_ids.head(10).to_string(index=False))

    if missing_count == 0 and duplicate_count == 0:
        print("판정: ID 결측·중복 검사 통과")
    else:
        print("판정: JOIN 전에 원인 확인 필요")
