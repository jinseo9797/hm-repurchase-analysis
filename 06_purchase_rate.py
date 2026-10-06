from pathlib import Path
import pandas as pd

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
if customers["customer_id"].isna().any():
    raise ValueError("고객 ID에 결측치가 있습니다.")

if customers["customer_id"].duplicated().any():
    raise ValueError("고객 ID가 중복되어 있습니다.")

if customers["first_purchase_date"].isna().any():
    raise ValueError("첫 관측 구매일에 결측치가 있습니다.")

if customers["eligible_30d"].isna().any():
    raise ValueError("관측 가능 여부에 결측치가 있습니다.")

# 거래의 고객 ID를 첫 관측 구매일로 바꿔 찾기 위한 목록
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
        first_dates = chunk["customer_id"].map(first_date_lookup)

        if first_dates.isna().any():
            raise ValueError("첫 관측 구매일을 찾지 못한 고객이 있습니다.")

        # 첫 관측 구매일로부터 며칠 뒤의 거래인지 계산
        days_since_first = (purchase_dates - first_dates).dt.days

        if (days_since_first < 0).any():
            raise ValueError("첫 관측 구매일보다 이른 거래가 있습니다.")

        # 첫날은 제외하고 1~30일째 구매만 선택
        is_repurchase = days_since_first.between(1, 30)

        repurchased_ids.update(
            chunk.loc[is_repurchase, "customer_id"]
        )

        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 확인 완료", flush=True)

# 30일 관측 가능한 고객만 최종 분석표에 포함
result = customers.loc[customers["eligible_30d"]].copy()

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