# 01_check_data.py
# 목적: 원본 CSV의 컬럼과 앞 5행 확인
# 입력: data/raw/*.csv
# 출력: 화면 출력
# 실행: 프로젝트 최상위에서 python 01_check_data.py
#
# [읽는 순서] 아래 SQL로 전체 흐름을 이해한 뒤 Python 본문을 읽으세요.
# SQL은 MySQL 8 기준의 설명용 예시이며 이 Python 파일에서 실행되지 않습니다.
# CSV를 같은 이름의 테이블로 적재하고 날짜·키·불리언 타입을 맞췄다고 가정합니다.
# 앞 단계(01~04)의 검증 결과에 문제가 있으면 원인을 해결한 뒤 분석을 진행하세요.
#
# -- CSV를 같은 이름의 테이블로 적재했다고 가정합니다.
# SELECT * FROM articles LIMIT 5;
# SELECT * FROM customers LIMIT 5;
# SELECT * FROM transactions_train LIMIT 5;
# -- 컬럼 목록 확인은 DESCRIBE articles; 로 표현할 수 있습니다.
# -- SQL의 LIMIT은 ORDER BY가 없으면 행 순서를 보장하지 않습니다.
# -- Python의 nrows=5는 CSV에 기록된 순서대로 앞 5행을 읽습니다.

from pathlib import Path
import pandas as pd

# 이 Python 파일이 저장된 폴더
# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent

# 원본 CSV가 있는 폴더
RAW_DIR = BASE_DIR / "data" / "raw"

file_names = [
    "articles.csv",
    "customers.csv",
    "transactions_train.csv",
]

# 리스트에 있는 파일 이름을 하나씩 꺼내 같은 작업을 반복합니다.
for file_name in file_names:
    file_path = RAW_DIR / file_name

    print(f"\n{'=' * 60}")
    print(f"파일: {file_name}")

    if not file_path.is_file():
        print(f"파일을 찾을 수 없습니다: {file_path}")
        continue

    # 처음에는 모든 값을 문자열로, 앞 5행만 읽기
    # nrows=5: CSV 앞 5행만 읽음. dtype="string": ID 앞자리 0을 보존합니다.
    sample = pd.read_csv(
        file_path,
        nrows=5,
        dtype="string",
    )

    print("\n컬럼 목록:")
    # columns는 컬럼 이름 목록, tolist()는 Python 리스트로 변환합니다.
    print(sample.columns.tolist())

    print("\n앞 5행:")
    print(sample.to_string(index=False))
