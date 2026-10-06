# 07_monthly_cohort.py
# 목적: 첫 관측 구매 월별 재구매율과 기간별 비교
# 입력: 06 결과
# 출력: data/processed/monthly_repurchase_30d.csv
# 실행: 프로젝트 최상위에서 python 07_monthly_cohort.py
#
# SELECT DATE_FORMAT(first_purchase_date, '%Y-%m') AS cohort_month,
#        COUNT(*) AS customer_count,
#        SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END) AS repurchased_count,
#        ROUND(100.0 * SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END)
#                    / COUNT(*), 2) AS repurchase_rate_pct
# FROM customer_repurchase_30d
# GROUP BY DATE_FORMAT(first_purchase_date, '%Y-%m')
# ORDER BY cohort_month;
# -- 전체 비율은 고객 수로 가중되어야 합니다. 월별 퍼센트의 단순 평균은 다릅니다.
# SELECT 100.0 * SUM(repurchased_count) / SUM(customer_count) AS overall_rate
# FROM monthly_repurchase_30d;
# -- 관측 시작 월을 제외한 비교:
# SELECT COUNT(*) AS customer_count,
#        100.0 * AVG(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END) AS rate
# FROM customer_repurchase_30d
# WHERE first_purchase_date >= '2018-10-01';
# -- 2019년 이후 비교는 위 WHERE 날짜를 '2019-01-01'로 바꿉니다.
# -- 실제 신규 고객을 골라낸 결과가 아니라 분석 대상 기간을 바꾼 비교입니다.

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
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
# isna()는 결측 여부, any()는 하나라도 True인지 확인합니다.
# SQL: WHERE 컬럼 IS NULL에 해당하는 행이 있으면 중단합니다.
for column in ['customer_id', 'first_purchase_date', 'repurchased_30d']:
    if df[column].isna().any():
        raise ValueError(f"{column}에 결측치가 있습니다.")

if df["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")

# 2020-08-15 같은 날짜를 '2020-08' 문자열로 변환
# dt는 날짜 Series의 기능에 접근합니다. strftime은 날짜를 지정 형식의 문자열로 바꿉니다.
# SQL DATE_FORMAT(first_purchase_date, "%Y-%m"). 코호트는 같은 시기에 묶인 고객군입니다.
df["cohort_month"] = df["first_purchase_date"].dt.strftime("%Y-%m")

# 첫 관측 구매 월별 고객 수와 재구매 고객 수
# agg의 새열=(원래열, 집계함수): size는 COUNT(*), sum은 True의 개수입니다.
# as_index=False는 GROUP BY 기준 열을 일반 컬럼으로 유지합니다.
monthly = (
    df.groupby("cohort_month", as_index=False)
    .agg(
        customer_count=("customer_id", "size"),
        repurchased_count=("repurchased_30d", "sum"),
    )
    .sort_values("cohort_month")
)

# 월별 재구매율
monthly["repurchase_rate_pct"] = (
    monthly["repurchased_count"]
    / monthly["customer_count"]
    * 100
).round(2)

# 전체 재구매율: 월별 비율의 단순 평균으로 계산하지 않기
# 예: 고객 10명인 월과 1,000명인 월의 비율을 동일 비중으로 평균내면 안 됩니다.
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
    # 결측 검사를 통과했으므로 mean()은 True 수 / 전체 고객 수입니다. SQL AVG(CASE...).
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
