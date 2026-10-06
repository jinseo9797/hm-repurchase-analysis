from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR / "data" / "raw" / "transactions_train.csv"

total_rows = 0
missing_counts = None

min_date = None
max_date = None

invalid_date_count = 0
invalid_price_count = 0
negative_price_count = 0
zero_price_count = 0

# 파일을 한 번에 100,000행씩 읽기
with pd.read_csv(
    file_path,
    dtype="string",
    chunksize=100_000,
) as reader:

    for chunk_number, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        # 컬럼별 결측치 개수를 누적
        chunk_missing = chunk.isna().sum()

        if missing_counts is None:
            missing_counts = chunk_missing
        else:
            missing_counts = missing_counts + chunk_missing

        # 날짜 변환: 변환할 수 없는 값은 NaT
        dates = pd.to_datetime(
            chunk["t_dat"],
            format="%Y-%m-%d",
            errors="coerce",
        )

        # 원래 결측치였던 값과 형식 오류를 구분
        invalid_date_count += int(
            (chunk["t_dat"].notna() & dates.isna()).sum()
        )

        chunk_min = dates.min()
        chunk_max = dates.max()

        if pd.notna(chunk_min):
            if min_date is None or chunk_min < min_date:
                min_date = chunk_min

        if pd.notna(chunk_max):
            if max_date is None or chunk_max > max_date:
                max_date = chunk_max

        # 가격을 숫자로 변환
        prices = pd.to_numeric(
            chunk["price"],
            errors="coerce",
        )

        invalid_price_count += int(
            (chunk["price"].notna() & prices.isna()).sum()
        )

        negative_price_count += int((prices < 0).sum())
        zero_price_count += int((prices == 0).sum())

        # 10개 묶음마다 진행 상황 출력
        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 확인 완료", flush=True)

print("\n=== 거래 데이터 점검 결과 ===")
print(f"전체 행 수: {total_rows:,}")

print(
    "시작일:",
    min_date.date() if min_date is not None else "유효한 날짜 없음",
)
print(
    "종료일:",
    max_date.date() if max_date is not None else "유효한 날짜 없음",
)

print("\n컬럼별 결측치:")
print(missing_counts)

print(f"\n날짜 형식 오류: {invalid_date_count:,}건")
print(f"가격 숫자 변환 오류: {invalid_price_count:,}건")
print(f"음수 가격: {negative_price_count:,}건")
print(f"0인 가격: {zero_price_count:,}건")