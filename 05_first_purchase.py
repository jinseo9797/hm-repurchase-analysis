# 05_first_purchase.py
# 목적: 고객별 첫 관측 구매일과 30일 관찰 가능 여부 계산
# 입력: transactions_train.csv
# 출력: data/processed/customer_first_purchase.csv
# 실행: 프로젝트 최상위에서 python 05_first_purchase.py
#
# [읽는 순서] 아래 SQL로 전체 흐름을 이해한 뒤 Python 본문을 읽으세요.
# SQL은 MySQL 8 기준의 설명용 예시이며 이 Python 파일에서 실행되지 않습니다.
# CSV를 같은 이름의 테이블로 적재하고 날짜·키·불리언 타입을 맞췄다고 가정합니다.
# 앞 단계(01~04)의 검증 결과에 문제가 있으면 원인을 해결한 뒤 분석을 진행하세요.
#
# WITH first_dates AS (
#     SELECT customer_id, MIN(t_dat) AS first_purchase_date
#     FROM transactions_train
#     GROUP BY customer_id
# ), last_observation AS (
#     SELECT MAX(t_dat) AS last_date FROM transactions_train
# )
# SELECT f.customer_id, f.first_purchase_date,
#        CASE WHEN f.first_purchase_date <= DATE_SUB(l.last_date, INTERVAL 30 DAY)
#             THEN TRUE ELSE FALSE END AS eligible_30d
# FROM first_dates f
# CROSS JOIN last_observation l;
# -- 결과를 저장한 테이블 이름: customer_first_purchase
# -- 청크 처리: 각 청크의 MIN을 모아 다시 MIN을 구하면 전체 MIN과 같습니다.

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
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
        # SQL SELECT customer_id, MIN(t_dat) ... GROUP BY customer_id.
        # 결과는 인덱스=고객 ID, 값=날짜인 Series입니다.
        chunk_first = chunk.groupby("customer_id")["t_dat"].min()

        if first_dates is None:
            first_dates = chunk_first
        else:
            # 기존 결과와 이번 결과를 합친 뒤,
            # 같은 고객의 날짜 중 가장 이른 날짜만 남기기
            # concat은 두 Series를 세로로 이어 붙입니다(SQL UNION ALL의 개념).
            # 같은 고객이 다른 청크에도 등장하므로 다시 MIN을 구해야 합니다.
            combined = pd.concat([first_dates, chunk_first])
            # level=0은 첫 번째 인덱스인 고객 ID를 기준으로 묶으라는 뜻입니다.
            # 날짜를 단순 덮어쓰면 더 늦은 날짜로 바뀔 수 있어 이 단계가 필요합니다.
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
# rename은 값 열의 이름을 지정하고, reset_index는 고객 ID를 일반 열로 꺼냅니다.
result = first_dates.rename("first_purchase_date").reset_index()

# 30일을 온전히 관측할 수 있는 마지막 첫 구매일
# Timedelta(days=30)는 30일 길이입니다. SQL DATE_SUB(last_date, INTERVAL 30 DAY).
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
