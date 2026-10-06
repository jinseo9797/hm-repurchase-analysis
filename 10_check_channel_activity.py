# 10_check_channel_activity.py
# 목적: 2020년 3~5월 원본 거래의 채널별 활동 확인
# 입력: transactions_train.csv
# 출력: data/processed/monthly_channel_activity.csv
# 실행: 프로젝트 최상위에서 python 10_check_channel_activity.py
#
# -- 기본 집계 (거래가 없는 조합은 결과 행 자체가 나오지 않습니다):
# SELECT DATE_FORMAT(t_dat, '%Y-%m') AS purchase_month,
#        sales_channel_id, COUNT(*) AS transaction_row_count
# FROM transactions_train
# WHERE t_dat >= '2020-03-01' AND t_dat < '2020-06-01'
# GROUP BY DATE_FORMAT(t_dat, '%Y-%m'), sales_channel_id;
# -- Python 코드처럼 거래가 없는 조합도 0으로 표시하려면:
# WITH months AS (
#     SELECT '2020-03' AS purchase_month UNION ALL
#     SELECT '2020-04' UNION ALL SELECT '2020-05'
# ), channels AS (
#     SELECT '1' AS sales_channel_id UNION ALL SELECT '2'
# ), activity AS (
#     SELECT DATE_FORMAT(t_dat, '%Y-%m') AS purchase_month,
#            sales_channel_id, COUNT(*) AS transaction_row_count
#     FROM transactions_train
#     WHERE t_dat >= '2020-03-01' AND t_dat < '2020-06-01'
#     GROUP BY DATE_FORMAT(t_dat, '%Y-%m'), sales_channel_id
# )
# SELECT m.purchase_month, c.sales_channel_id,
#        COALESCE(a.transaction_row_count, 0) AS transaction_row_count
# FROM months m CROSS JOIN channels c
# LEFT JOIN activity a ON a.purchase_month = m.purchase_month
#                    AND a.sales_channel_id = c.sales_channel_id
# ORDER BY m.purchase_month, c.sales_channel_id;
# -- 고객 수나 주문 수가 아닌 상품 거래 기록의 행 수입니다.

from pathlib import Path

import pandas as pd


# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "data" / "raw" / "transactions_train.csv"
OUTPUT_PATH = (
    BASE_DIR / "data" / "processed" / "monthly_channel_activity.csv"
)

# 월별·채널별 거래 행 수를 누적할 공간
# 처음부터 0을 넣어두면 거래가 없는 조합도 출력됩니다.
# 딕셔너리 키는 (월, 채널) 튜플입니다. 모든 조합을 0으로 시작합니다.
# SQL의 months CROSS JOIN channels + LEFT JOIN + COALESCE에 해당합니다.
counts = {
    ("2020-03", "1"): 0,
    ("2020-03", "2"): 0,
    ("2020-04", "1"): 0,
    ("2020-04", "2"): 0,
    ("2020-05", "1"): 0,
    ("2020-05", "2"): 0,
}

reader = pd.read_csv(
    INPUT_PATH,
    usecols=["t_dat", "sales_channel_id"],
    dtype={"sales_channel_id": "string"},
    parse_dates=["t_dat"],
    chunksize=100_000,
)

for chunk_number, chunk in enumerate(reader, start=1):

    # 2020년 3~5월 거래만 선택
    # >= 시작일 AND < 다음 달 시작일: 3월 1일부터 5월 31일까지 선택합니다.
    selected = chunk.loc[
        (chunk["t_dat"] >= "2020-03-01")
        & (chunk["t_dat"] < "2020-06-01")
    ].copy()

    # 예상하지 못한 채널이나 결측을 집계에서 조용히 빠뜨리지 않도록 검사합니다.
    if not selected["sales_channel_id"].isin(["1", "2"]).all():
        raise ValueError("대상 기간에 채널 1, 2 이외의 값 또는 결측치가 있습니다.")

    selected["purchase_month"] = (
        selected["t_dat"].dt.strftime("%Y-%m")
    )

    # 이번 청크의 월별·채널별 행 수
    # groupby(...).size()는 GROUP BY 두 컬럼 + COUNT(*).
    # 결과는 인덱스=(월, 채널), 값=행 수인 Series입니다.
    chunk_counts = selected.groupby(
        ["purchase_month", "sales_channel_id"]
    ).size()

    # 이번 청크의 결과를 누적
    # items()는 (인덱스, 값)을 하나씩 꺼냅니다. key 예: ("2020-03", "1").
    # 여러 청크에서 나온 동일 조합의 행 수를 +=로 더합니다.
    for key, row_count in chunk_counts.items():
        counts[key] += int(row_count)

    if chunk_number % 50 == 0:
        print(f"{chunk_number:,}개 청크 처리 완료")


# 누적한 딕셔너리를 표로 변환
rows = []

# 튜플 (월, 채널)을 두 변수에 나누어 받습니다. 리스트에 행 딕셔너리를 추가합니다.
for (month, channel), row_count in counts.items():
    rows.append({
        "purchase_month": month,
        "sales_channel_id": channel,
        "transaction_row_count": row_count,
    })

# 행 딕셔너리 목록을 표로 변환합니다. 딕셔너리의 키가 컬럼 이름이 됩니다.
result = pd.DataFrame(rows)

result = result.sort_values(
    ["purchase_month", "sales_channel_id"]
)

print("\n=== 월별·채널별 거래 행 수 ===")
print(result.to_string(index=False))

# 저장 폴더가 없으면 생성합니다.
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

result.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig",
)

print(f"\n저장 완료: {OUTPUT_PATH}")
