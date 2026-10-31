# 원본 CSV 구조와 샘플 확인
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

RAW_DIR = BASE_DIR / "data" / "raw"

file_names = [
    "articles.csv",
    "customers.csv",
    "transactions_train.csv",
]

for file_name in file_names:
    file_path = RAW_DIR / file_name

    print(f"\n{'=' * 60}")
    print(f"파일: {file_name}")

    if not file_path.is_file():
        print(f"파일을 찾을 수 없습니다: {file_path}")
        continue

    sample = pd.read_csv(
        file_path,
        nrows=5,
        dtype="string",
    )

    print("\n컬럼 목록:")
    print(sample.columns.tolist())

    print("\n앞 5행:")
    print(sample.to_string(index=False))
