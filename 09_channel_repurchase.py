# 첫 관측 구매일의 이용 채널별 재구매율 비교
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

customers = pd.read_csv(
    PROCESSED_DIR / "customer_repurchase_30d.csv",
    dtype={
        "customer_id": "string",
        "repurchased_30d": "boolean",
    },
    parse_dates=["first_purchase_date"],
)

required_columns = [
    "customer_id",
    "first_purchase_date",
    "repurchased_30d",
]

for column in required_columns:
    if customers[column].isna().any():
        raise ValueError(f"{column}에 결측치가 있습니다.")

if customers["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")

first_date_lookup = customers.set_index(
    "customer_id"
)["first_purchase_date"]

# 첫날 여러 거래가 있어도 고객 ID는 중복 없이 보관
channel_1_ids = set()
channel_2_ids = set()

reader = pd.read_csv(
    RAW_DIR / "transactions_train.csv",
    usecols=["t_dat", "customer_id", "sales_channel_id"],
    dtype={
        "customer_id": "string",
        "sales_channel_id": "string",
    },
    parse_dates=["t_dat"],
    chunksize=100_000,
)

for chunk_number, chunk in enumerate(reader, start=1):

    if not chunk["sales_channel_id"].isin(["1", "2"]).all():
        raise ValueError("채널 1, 2 이외의 값 또는 결측치가 있습니다.")

    mapped_first_date = chunk["customer_id"].map(first_date_lookup)

    # 분석 대상 고객의 첫 관측 구매일 거래만 사용
    first_day = chunk.loc[
        chunk["t_dat"] == mapped_first_date
    ]

    channel_1_ids.update(
        first_day.loc[
            first_day["sales_channel_id"] == "1",
            "customer_id",
        ]
    )

    channel_2_ids.update(
        first_day.loc[
            first_day["sales_channel_id"] == "2",
            "customer_id",
        ]
    )

    if chunk_number % 50 == 0:
        print(f"{chunk_number:,}개 청크 처리 완료")

used_channel_1 = customers["customer_id"].isin(channel_1_ids)
used_channel_2 = customers["customer_id"].isin(channel_2_ids)

if not (used_channel_1 | used_channel_2).all():
    raise ValueError("첫 구매일 채널을 찾지 못한 고객이 있습니다.")

# 첫날 두 채널을 모두 이용한 고객은 별도 분류
customers["first_day_channel"] = pd.Series(
    pd.NA,
    index=customers.index,
    dtype="string",
)

customers.loc[
    used_channel_1 & ~used_channel_2,
    "first_day_channel",
] = "channel_1"

customers.loc[
    used_channel_2 & ~used_channel_1,
    "first_day_channel",
] = "channel_2"

customers.loc[
    used_channel_1 & used_channel_2,
    "first_day_channel",
] = "both"

summary = (
    customers.groupby("first_day_channel", as_index=False)
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
)

summary["repurchase_rate_pct"] = (
    summary["repurchased_count"]
    / summary["customer_count"]
    * 100
).round(2)

customers["cohort_month"] = (
    customers["first_purchase_date"].dt.strftime("%Y-%m")
)

monthly_summary = (
    customers.groupby(["cohort_month", "first_day_channel"], as_index=False)
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
)

monthly_summary["repurchase_rate_pct"] = (
    monthly_summary["repurchased_count"]
    / monthly_summary["customer_count"]
    * 100
).round(2)

customers.to_csv(
    PROCESSED_DIR / "customer_repurchase_30d_with_channel.csv",
    index=False,
    encoding="utf-8-sig",
)

summary.to_csv(
    PROCESSED_DIR / "channel_repurchase_30d.csv",
    index=False,
    encoding="utf-8-sig",
)

monthly_summary.to_csv(
    PROCESSED_DIR / "monthly_channel_repurchase_30d.csv",
    index=False,
    encoding="utf-8-sig",
)

print("\n=== 첫 구매일 채널별 30일 재구매율 ===")
print(summary.to_string(index=False))

print(f"\n전체 분석 고객 수: {len(customers):,}")
print(f"채널별 고객 수 합계: {summary['customer_count'].sum():,}")

print("\n=== 2020년 4~5월 채널별 비교 ===")
print(
    monthly_summary.loc[
        monthly_summary["cohort_month"].isin(["2020-04", "2020-05"])
    ].to_string(index=False)
)

print("\n저장 완료")
