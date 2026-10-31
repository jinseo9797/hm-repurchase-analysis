# 2020년 3~5월 채널별 거래 기록 재확인
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "data" / "raw" / "transactions_train.csv"
OUTPUT_PATH = (
    BASE_DIR / "data" / "processed" / "monthly_channel_activity.csv"
)

# 거래가 없는 월·채널 조합도 0으로 출력
counts = {
    ("2020-03", "1"): 0,
    ("2020-03", "2"): 0,
    ("2020-04", "1"): 0,
    ("2020-04", "2"): 0,
    ("2020-05", "1"): 0,
    ("2020-05", "2"): 0,
}

reader = pd.read_csv(
    INPUT_PATH,
    usecols=["t_dat", "sales_channel_id"],
    dtype={"sales_channel_id": "string"},
    parse_dates=["t_dat"],
    chunksize=100_000,
)

for chunk_number, chunk in enumerate(reader, start=1):

    selected = chunk.loc[
        (chunk["t_dat"] >= "2020-03-01")
        & (chunk["t_dat"] < "2020-06-01")
    ].copy()

    if not selected["sales_channel_id"].isin(["1", "2"]).all():
        raise ValueError("대상 기간에 채널 1, 2 이외의 값 또는 결측치가 있습니다.")

    selected["purchase_month"] = (
        selected["t_dat"].dt.strftime("%Y-%m")
    )

    chunk_counts = selected.groupby(
        ["purchase_month", "sales_channel_id"]
    ).size()

    for key, row_count in chunk_counts.items():
        counts[key] += int(row_count)

    if chunk_number % 50 == 0:
        print(f"{chunk_number:,}개 청크 처리 완료")

rows = []

for (month, channel), row_count in counts.items():
    rows.append({
        "purchase_month": month,
        "sales_channel_id": channel,
        "transaction_row_count": row_count,
    })

result = pd.DataFrame(rows)

result = result.sort_values(
    ["purchase_month", "sales_channel_id"]
)

print("\n=== 월별·채널별 거래 행 수 ===")
print(result.to_string(index=False))

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

result.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)

print(f"\n저장 완료: {OUTPUT_PATH}")
