# 고객·상품 ID의 결측과 중복 확인
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"

targets = [
    ("customers.csv", "customer_id"),
    ("articles.csv", "article_id"),
]

for file_name, key_column in targets:
    file_path = RAW_DIR / file_name

    df = pd.read_csv(
        file_path,
        usecols=[key_column],
        dtype="string",
    )

    ids = df[key_column]

    missing_count = int(ids.isna().sum())

    valid_ids = ids.dropna()

    unique_count = valid_ids.nunique()
    # 같은 ID의 첫 행은 중복 건수에서 제외
    duplicate_count = int(valid_ids.duplicated().sum())
    
    print(f"\n=== {file_name} ID 점검 ===")
    print(f"전체 행 수: {len(df):,}")
    print(f"ID 결측치: {missing_count:,}")
    print(f"고유 ID 수: {unique_count:,}")
    print(f"중복 ID 초과 행 수: {duplicate_count:,}")

    if duplicate_count > 0:
        duplicate_ids = valid_ids[
            valid_ids.duplicated(keep=False)
        ]

        print("\n중복된 ID 샘플:")
        print(duplicate_ids.head(10).to_string(index=False))

    if missing_count == 0 and duplicate_count == 0:
        print("판정: ID 결측·중복 검사 통과")
    else:
        print("판정: JOIN 전에 원인 확인 필요")
