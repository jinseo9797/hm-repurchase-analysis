from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# 고객당 한 행으로 정리된 분석 결과 읽기
df = pd.read_csv(
    PROCESSED_DIR / "customer_repurchase_30d.csv",
    dtype={
        "customer_id": "string",
        "repurchased_30d": "boolean",
    },
    parse_dates=["first_purchase_date"],
)

# 집계 전 확인
if df["customer_id"].isna().any():
    raise ValueError("고객 ID에 결측치가 있습니다.")

if df["customer_id"].duplicated().any():
    raise ValueError("고객당 한 행이어야 합니다.")

if df["first_purchase_date"].isna().any():
    raise ValueError("첫 관측 구매일에 결측치가 있습니다.")

if df["repurchased_30d"].isna().any():
    raise ValueError("재구매 여부에 결측치가 있습니다.")

# 2020-08-15 같은 날짜를 '2020-08' 문자열로 변환
df["cohort_month"] = df["first_purchase_date"].dt.strftime("%Y-%m")

# 첫 관측 구매 월별 고객 수와 재구매 고객 수
monthly = (
    df.groupby("cohort_month")
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
    .reset_index()
    .sort_values("cohort_month")
)

# 월별 재구매율
monthly["repurchase_rate_pct"] = (
    monthly["repurchased_count"]
    / monthly["customer_count"]
    * 100
).round(2)

# 전체 재구매율: 월별 비율의 단순 평균으로 계산하지 않기
overall_rate = (
    monthly["repurchased_count"].sum()
    / monthly["customer_count"].sum()
    * 100
)

output_path = PROCESSED_DIR / "monthly_repurchase_30d.csv"
monthly.to_csv(output_path, index=False, encoding="utf-8-sig")

print("\n=== 첫 관측 구매 월별 30일 재구매율 ===")
print(monthly.to_string(index=False))

print(f"\n전체 분석 대상 고객 수: {monthly['customer_count'].sum():,}")
print(f"전체 30일 재구매율: {overall_rate:.2f}%")
print(f"\n저장 위치: {output_path}")


# 데이터 시작 월인 2018년 9월 코호트를 제외한 비교
after_start_month = df.loc[
    df["first_purchase_date"] >= pd.Timestamp("2018-10-01")
]

print("\n=== 시작 월을 제외한 비교 ===")
print(f"고객 수: {len(after_start_month):,}")

if len(after_start_month) > 0:
    comparison_rate = after_start_month["repurchased_30d"].mean() * 100
    print(f"30일 재구매율: {comparison_rate:.2f}%")

print("\n=== 처음 3개 월의 집계 ===")
print(monthly.head(3).to_string(index=False))

# 첫 관측 구매일이 2019년 이후인 고객만 선택
from_2019 = df.loc[
    df["first_purchase_date"] >= pd.Timestamp("2019-01-01")
]

print("\n=== 2019년 이후 첫 관측 구매 고객 ===")
print(f"고객 수: {len(from_2019):,}")

if len(from_2019) > 0:
    rate_2019 = from_2019["repurchased_30d"].mean() * 100
    print(f"30일 재구매율: {rate_2019:.2f}%")