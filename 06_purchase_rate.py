# 06_purchase_rate.py
# 목적: 고객별 30일 재구매 여부와 전체 재구매율 계산
# 입력: 05 결과, transactions_train.csv
# 출력: data/processed/customer_repurchase_30d.csv
# 실행: 프로젝트 최상위에서 python 06_purchase_rate.py
#
# -- 첫날(0일)은 제외하고 1~30일(양 끝 포함)의 구매 존재 여부를 봅니다.
# WITH customer_result AS (
#     SELECT c.customer_id, c.first_purchase_date, c.eligible_30d,
#            EXISTS (
#                SELECT 1 FROM transactions_train t
#                WHERE t.customer_id = c.customer_id
#                  AND DATEDIFF(t.t_dat, c.first_purchase_date) BETWEEN 1 AND 30
#            ) AS repurchased_30d
#     FROM customer_first_purchase c
#     WHERE c.eligible_30d = TRUE
# )
# SELECT * FROM customer_result;
# -- 위 결과를 customer_repurchase_30d로 저장했다고 가정한 집계:
# SELECT COUNT(*) AS customer_count,
#        SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END) AS repurchased_count,
#        100.0 * SUM(CASE WHEN repurchased_30d = TRUE THEN 1 ELSE 0 END)
#              / NULLIF(COUNT(*), 0) AS repurchase_rate_pct
# FROM customer_repurchase_30d;
# -- JOIN 후 거래 행을 COUNT하면 여러 번 구매한 고객이 중복 집계될 수 있습니다.
# -- EXISTS는 구매가 한 번이든 여러 번이든 고객당 TRUE 하나만 반환합니다.

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

# 이전 단계에서 저장한 고객별 첫 관측 구매일
customers = pd.read_csv(
    OUTPUT_DIR / "customer_first_purchase.csv",
    dtype={
        "customer_id": "string",
        "eligible_30d": "boolean",
    },
    parse_dates=["first_purchase_date"],
)

# 연결 기준에 문제가 있으면 중단
# isna()는 결측 여부, any()는 하나라도 True인지 확인합니다.
# SQL: WHERE 컬럼 IS NULL에 해당하는 행이 있으면 중단합니다.
for column in ['customer_id', 'first_purchase_date', 'eligible_30d']:
    if customers[column].isna().any():
        raise ValueError(f"{column}에 결측치가 있습니다.")

if customers["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")

# 거래의 고객 ID를 첫 관측 구매일로 바꿔 찾기 위한 목록
# set_index로 고객 ID를 조회 키로 사용합니다. 다음 map으로 날짜 한 열을 연결합니다.
# SQL JOIN은 여러 열을 붙일 때, 여기의 map은 한 값을 찾을 때 대응됩니다.
first_date_lookup = customers.set_index(
    "customer_id"
)["first_purchase_date"]

# 재구매한 고객 ID를 중복 없이 보관
repurchased_ids = set()
total_rows = 0

with pd.read_csv(
    RAW_DIR / "transactions_train.csv",
    usecols=["customer_id", "t_dat"],
    dtype="string",
    chunksize=100_000,
) as reader:

    for chunk_number, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        purchase_dates = pd.to_datetime(
            chunk["t_dat"],
            format="%Y-%m-%d",
            errors="raise",
        )

        # 각 거래에 해당 고객의 첫 관측 구매일 연결
        # 고객별 첫 구매일을 각 거래 행에 매핑합니다. 반환값은 거래와 같은 길이의 Series입니다.
        first_dates = chunk["customer_id"].map(first_date_lookup)

        if first_dates.isna().any():
            raise ValueError("첫 관측 구매일을 찾지 못한 고객이 있습니다.")

        # 첫 관측 구매일로부터 며칠 뒤의 거래인지 계산
        # 날짜 빼기의 결과는 시간 간격. dt.days로 일수만 추출합니다. SQL DATEDIFF.
        days_since_first = (purchase_dates - first_dates).dt.days

        if (days_since_first < 0).any():
            raise ValueError("첫 관측 구매일보다 이른 거래가 있습니다.")

        # 첫날은 제외하고 1~30일째 구매만 선택
        # between(1, 30)은 양 끝 포함. 첫날 0일은 제외하고 30일째까지 인정합니다.
        is_repurchase = days_since_first.between(1, 30)

        # SQL SELECT DISTINCT customer_id ... WHERE 날짜 차이 BETWEEN 1 AND 30.
        # 청크가 달라도 같은 고객을 한 번만 세도록 set에 누적합니다.
        repurchased_ids.update(
            chunk.loc[is_repurchase, "customer_id"]
        )

        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 확인 완료", flush=True)

# 30일 관측 가능한 고객만 최종 분석표에 포함
# loc[조건]은 WHERE처럼 행 선택. copy()는 이후 열을 추가할 별도 표를 만듭니다.
result = customers.loc[customers["eligible_30d"]].copy()

# isin은 EXISTS와 같은 목적: 재구매 집합에 있으면 True, 없으면 False.
result["repurchased_30d"] = result["customer_id"].isin(
    repurchased_ids
)

eligible_count = len(result)

if eligible_count == 0:
    raise ValueError("30일 관측 가능한 고객이 없습니다.")

repurchased_count = int(result["repurchased_30d"].sum())
not_repurchased_count = eligible_count - repurchased_count

repurchase_rate = repurchased_count / eligible_count * 100

# 이후 고객군별 분석에 사용할 결과 저장
output_path = OUTPUT_DIR / "customer_repurchase_30d.csv"

result.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
)

print("\n=== 30일 재구매율 계산 결과 ===")
print(f"처리한 거래 행 수: {total_rows:,}")
print(f"분석 대상 고객 수: {eligible_count:,}")
print(f"30일 이내 재구매 고객 수: {repurchased_count:,}")
print(f"30일 이내 재구매하지 않은 고객 수: {not_repurchased_count:,}")
print(f"30일 재구매율: {repurchase_rate:.2f}%")
print(f"\n저장 위치: {output_path}")
