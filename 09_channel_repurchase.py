from pathlib import Path

import pandas as pd


# 1. 경로 설정
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


# 2. 30일 관찰 기간을 확보한 고객 데이터 읽기
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

if customers[required_columns].isna().any().any():
    raise ValueError("분석에 필요한 고객 정보에 결측치가 있습니다.")

if customers["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")


# 3. 고객 ID로 첫 구매일을 찾기 위한 Series
first_date_lookup = customers.set_index(
    "customer_id"
)["first_purchase_date"]


# 4. 첫 구매일에 각 채널을 이용한 고객 ID를 저장
channel_1_ids = set()
channel_2_ids = set()


# 5. 거래 원본을 나누어 읽기
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

    # 예상한 채널 값인지 확인
    if not chunk["sales_channel_id"].isin(["1", "2"]).all():
        raise ValueError("채널 1, 2 이외의 값 또는 결측치가 있습니다.")

    # 각 거래에 해당 고객의 첫 구매일을 연결
    mapped_first_date = chunk["customer_id"].map(first_date_lookup)

    # 분석 대상 고객의 첫 구매일 거래만 선택
    first_day = chunk.loc[
        chunk["t_dat"].eq(mapped_first_date)
    ]

    # 첫 구매일에 채널 1을 이용한 고객
    channel_1_ids.update(
        first_day.loc[
            first_day["sales_channel_id"].eq("1"),
            "customer_id",
        ]
    )

    # 첫 구매일에 채널 2를 이용한 고객
    channel_2_ids.update(
        first_day.loc[
            first_day["sales_channel_id"].eq("2"),
            "customer_id",
        ]
    )

    if chunk_number % 50 == 0:
        print(f"{chunk_number:,}개 청크 처리 완료")


# 6. 고객별 첫 구매일 채널 분류
used_channel_1 = customers["customer_id"].isin(channel_1_ids)
used_channel_2 = customers["customer_id"].isin(channel_2_ids)

if not (used_channel_1 | used_channel_2).all():
    raise ValueError("첫 구매일 채널을 찾지 못한 고객이 있습니다.")

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


# 7. 채널별 재구매율 집계
summary = (
    customers.groupby("first_day_channel")
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
    .reset_index()
)

summary["repurchase_rate_pct"] = (
    summary["repurchased_count"]
    / summary["customer_count"]
    * 100
).round(2)


# 8. 월별·채널별 재구매율도 함께 집계
customers["cohort_month"] = (
    customers["first_purchase_date"].dt.strftime("%Y-%m")
)

monthly_summary = (
    customers.groupby(["cohort_month", "first_day_channel"])
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
    .reset_index()
)

monthly_summary["repurchase_rate_pct"] = (
    monthly_summary["repurchased_count"]
    / monthly_summary["customer_count"]
    * 100
).round(2)


# 9. 결과 저장
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


# 10. 결과 출력
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