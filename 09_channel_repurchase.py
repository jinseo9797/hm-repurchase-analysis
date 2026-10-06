# 09_channel_repurchase.py
# 목적: 첫 구매일 채널 분류 및 채널별·월별 집계
# 입력: 06 결과, transactions_train.csv
# 출력: data/processed/ 아래 고객별 채널 결과와 집계 CSV 3개
# 실행: 프로젝트 최상위에서 python 09_channel_repurchase.py
#
# -- sales_channel_id는 '1', '2'만 있고 NULL은 없다는 검사를 전제로 합니다.
# WITH first_day_channels AS (
#     SELECT c.customer_id,
#            CASE WHEN COUNT(DISTINCT t.sales_channel_id) = 2 THEN 'both'
#                 WHEN MIN(t.sales_channel_id) = '1' THEN 'channel_1'
#                 ELSE 'channel_2' END AS first_day_channel
#     FROM customer_repurchase_30d c
#     JOIN transactions_train t
#       ON c.customer_id = t.customer_id
#      AND c.first_purchase_date = t.t_dat
#     GROUP BY c.customer_id
# )
# SELECT c.*, f.first_day_channel,
#        DATE_FORMAT(c.first_purchase_date, '%Y-%m') AS cohort_month
# FROM customer_repurchase_30d c
# JOIN first_day_channels f ON c.customer_id = f.customer_id;
# -- 위 결과를 customer_repurchase_30d_with_channel로 저장한 뒤:
# SELECT first_day_channel, COUNT(*) AS customer_count,
#        SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END) AS repurchased_count,
#        ROUND(100.0 * SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END)
#                    / COUNT(*), 2) AS repurchase_rate_pct
# FROM customer_repurchase_30d_with_channel
# GROUP BY first_day_channel;
# -- 월과 채널을 함께 비교:
# SELECT cohort_month, first_day_channel, COUNT(*) AS customer_count,
#        SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END) AS repurchased_count,
#        ROUND(100.0 * SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END)
#                    / COUNT(*), 2) AS repurchase_rate_pct
# FROM customer_repurchase_30d_with_channel
# GROUP BY cohort_month, first_day_channel
# ORDER BY cohort_month, first_day_channel;
# -- both는 첫 관측 구매일에 두 채널을 이용했다는 뜻입니다.
# -- 재구매는 첫날 채널과 관계없이 어느 채널에서든 발생하면 인정합니다.

from pathlib import Path

import pandas as pd


# 1. 경로 설정
# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
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

# 한 컬럼씩 검사하면 any().any()의 이중 집계를 이해하지 않아도 됩니다.
for column in required_columns:
    if customers[column].isna().any():
        raise ValueError(f"{column}에 결측치가 있습니다.")

if customers["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")


# 3. 고객 ID로 첫 구매일을 찾기 위한 Series
# 조회용 Series: 고객 ID → 첫 관측 구매일. 06 결과에는 30일 관찰 가능 고객만 있습니다.
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
    # LEFT JOIN처럼 날짜 연결. 분석 대상 밖의 고객은 NaT가 됩니다.
    # 이 파일에서는 그런 고객이 정상적으로 존재하며 다음 날짜 비교에서 제외됩니다.
    mapped_first_date = chunk["customer_id"].map(first_date_lookup)

    # 분석 대상 고객의 첫 구매일 거래만 선택
    # SQL ON customer_id 일치 AND t.t_dat = c.first_purchase_date와 같은 선택입니다.
    first_day = chunk.loc[
        chunk["t_dat"] == mapped_first_date
    ]

    # 첫 구매일에 채널 1을 이용한 고객
    # loc[행 조건, 컬럼 이름]은 WHERE + SELECT 컬럼에 대응합니다.
    # 첫날 상품을 여러 개 사도 set은 고객 ID를 하나만 보관합니다.
    channel_1_ids.update(
        first_day.loc[
            first_day["sales_channel_id"] == "1",
            "customer_id",
        ]
    )

    # 첫 구매일에 채널 2를 이용한 고객
    channel_2_ids.update(
        first_day.loc[
            first_day["sales_channel_id"] == "2",
            "customer_id",
        ]
    )

    if chunk_number % 50 == 0:
        print(f"{chunk_number:,}개 청크 처리 완료")


# 6. 고객별 첫 구매일 채널 분류
# 채널별 이용 여부를 고객 순서대로 True/False Series로 만듭니다.
# &: AND, |: OR, ~: NOT. Python and/or 대신 pandas의 기호를 씁니다.
used_channel_1 = customers["customer_id"].isin(channel_1_ids)
used_channel_2 = customers["customer_id"].isin(channel_2_ids)

if not (used_channel_1 | used_channel_2).all():
    raise ValueError("첫 구매일 채널을 찾지 못한 고객이 있습니다.")

# 빈 문자열 Series를 고객 인덱스에 맞춰 만든 후 CASE WHEN처럼 조건별 값을 넣습니다.
# pd.NA는 결측값입니다. 아래 세 조건은 서로 겹치지 않고 모든 고객을 분류합니다.
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
# as_index=False: 그룹 기준을 일반 열로 유지. reset_index()를 따로 호출할 필요가 없습니다.
# 고객당 한 행이므로 size가 고객 수이며, sum이 재구매 고객 수입니다.
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


# 8. 월별·채널별 재구매율도 함께 집계
customers["cohort_month"] = (
    customers["first_purchase_date"].dt.strftime("%Y-%m")
)

# SQL GROUP BY cohort_month, first_day_channel: 월과 채널 조합으로 나눕니다.
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
