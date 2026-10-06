from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

# 결과를 저장할 폴더 생성
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 고객별 첫 관측 구매일을 누적할 변수
first_dates = None
last_date = None
total_rows = 0

with pd.read_csv(
    RAW_DIR / "transactions_train.csv",
    usecols=["customer_id", "t_dat"],
    dtype="string",
    chunksize=100_000,
) as reader:

    for chunk_number, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        chunk["t_dat"] = pd.to_datetime(
            chunk["t_dat"],
            format="%Y-%m-%d",
            errors="raise",
        )

        # 이번 묶음에서 고객별 가장 이른 구매일
        chunk_first = chunk.groupby("customer_id")["t_dat"].min()

        if first_dates is None:
            first_dates = chunk_first
        else:
            # 기존 결과와 이번 결과를 합친 뒤,
            # 같은 고객의 날짜 중 가장 이른 날짜만 남기기
            combined = pd.concat([first_dates, chunk_first])
            first_dates = combined.groupby(level=0).min()

        # 전체 데이터의 마지막 구매일도 확인
        chunk_last = chunk["t_dat"].max()

        if last_date is None or chunk_last > last_date:
            last_date = chunk_last

        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 처리 완료", flush=True)

if first_dates is None or first_dates.empty:
    raise ValueError("분석할 거래 데이터가 없습니다.")

# 고객별 한 행짜리 표로 변환
result = first_dates.rename("first_purchase_date").reset_index()

# 30일을 온전히 관측할 수 있는 마지막 첫 구매일
cutoff_date = last_date - pd.Timedelta(days=30)

result["eligible_30d"] = (
    result["first_purchase_date"] <= cutoff_date
)

# 결과 저장
output_path = OUTPUT_DIR / "customer_first_purchase.csv"

result.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
)

eligible_count = int(result["eligible_30d"].sum())

print("\n=== 고객별 첫 관측 구매일 계산 완료 ===")
print(f"처리한 거래 행 수: {total_rows:,}")
print(f"거래에 등장한 고객 수: {len(result):,}")
print(f"데이터 마지막 날짜: {last_date.date()}")
print(f"30일 관측 가능 기준일: {cutoff_date.date()}")
print(f"분석 대상 고객 수: {eligible_count:,}")
print(f"관측 기간 부족 고객 수: {len(result) - eligible_count:,}")

print("\n결과 샘플:")
print(result.head(10).to_string(index=False))

print(f"\n저장 위치: {output_path}")