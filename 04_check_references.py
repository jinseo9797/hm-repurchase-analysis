# 04_check_references.py
# 목적: 거래의 고객·상품 ID가 기준 테이블에 존재하는지 확인
# 입력: 원본 CSV 3개
# 출력: 화면 출력
# 실행: 프로젝트 최상위에서 python 04_check_references.py
#
# -- 03에서 고객·상품 키가 고유하고 NULL이 없음을 확인한 뒤 실행하는 예시입니다.
# SELECT COUNT(*) AS total_rows,
#        SUM(CASE WHEN c.customer_id IS NULL THEN 1 ELSE 0 END) AS unknown_customer_rows,
#        SUM(CASE WHEN a.article_id IS NULL THEN 1 ELSE 0 END) AS unknown_article_rows,
#        SUM(CASE WHEN c.customer_id IS NULL OR a.article_id IS NULL
#                 THEN 1 ELSE 0 END) AS invalid_rows
# FROM transactions_train t
# LEFT JOIN customers c ON t.customer_id = c.customer_id
# LEFT JOIN articles a ON t.article_id = a.article_id;
# -- OR로 센 invalid_rows는 두 키 모두 잘못된 행도 한 번만 셉니다.
# -- 문제 ID 예시:
# SELECT DISTINCT t.customer_id
# FROM transactions_train t
# LEFT JOIN customers c ON t.customer_id = c.customer_id
# WHERE c.customer_id IS NULL AND t.customer_id IS NOT NULL
# LIMIT 5;

from pathlib import Path
import pandas as pd

# __file__은 현재 스크립트 경로. parent는 그 파일이 있는 프로젝트 폴더입니다.
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"

# 기준 테이블에서 ID만 읽기
customers = pd.read_csv(
    RAW_DIR / "customers.csv",
    usecols=["customer_id"],
    dtype="string",
)

articles = pd.read_csv(
    RAW_DIR / "articles.csv",
    usecols=["article_id"],
    dtype="string",
)

# 반복 조회에 사용할 ID 목록
# Index는 ID를 조회할 때 사용할 1차원 목록입니다. 원본 키 검증은 03에서 수행합니다.
customer_ids = pd.Index(customers["customer_id"])
article_ids = pd.Index(articles["article_id"])

total_rows = 0
unknown_customer_rows = 0
unknown_article_rows = 0
invalid_rows = 0

customer_examples = set()
article_examples = set()

with pd.read_csv(
    RAW_DIR / "transactions_train.csv",
    usecols=["customer_id", "article_id"],
    dtype="string",
    chunksize=100_000,
) as reader:

    for chunk_number, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        # 기준 테이블에 없는 ID인지 확인
        # isin(): 목록에 있으면 True. ~는 NOT이므로 목록에 없는 거래만 True입니다.
        # SQL LEFT JOIN 뒤 WHERE c.customer_id IS NULL에 대응합니다.
        unknown_customer = ~chunk["customer_id"].isin(customer_ids)
        unknown_article = ~chunk["article_id"].isin(article_ids)

        unknown_customer_rows += int(unknown_customer.sum())
        unknown_article_rows += int(unknown_article.sum())

        # 둘 중 하나라도 연결되지 않는 거래 행
        invalid_rows += int(
            (unknown_customer | unknown_article).sum()
        )

        # 문제가 있을 경우 확인할 ID를 최대 5개씩 보관
        if len(customer_examples) < 5:
            examples = chunk.loc[
                unknown_customer, "customer_id"
            ].dropna().unique()

            # set.update(): 여러 값을 중복 없이 집합에 추가합니다.
            # [:5 - len(...)]는 남은 예시 자리만큼 앞에서 선택하는 슬라이싱입니다.
            customer_examples.update(
                examples[:5 - len(customer_examples)]
            )

        if len(article_examples) < 5:
            examples = chunk.loc[
                unknown_article, "article_id"
            ].dropna().unique()

            article_examples.update(
                examples[:5 - len(article_examples)]
            )

        if chunk_number % 10 == 0:
            print(f"현재 {total_rows:,}행 확인 완료", flush=True)

print("\n=== 거래 데이터 연결 검증 ===")
print(f"검사한 거래 행 수: {total_rows:,}")
print(f"고객 정보에 연결되지 않는 거래 행: {unknown_customer_rows:,}")
print(f"상품 정보에 연결되지 않는 거래 행: {unknown_article_rows:,}")
print(f"하나라도 연결되지 않는 거래 행: {invalid_rows:,}")

if customer_examples:
    print("미등록 고객 ID 예시:", sorted(customer_examples))

if article_examples:
    print("미등록 상품 ID 예시:", sorted(article_examples))

if invalid_rows == 0:
    print("판정: 모든 거래의 고객·상품 ID 연결 가능")
else:
    print("판정: 연결되지 않는 ID의 원인 확인 필요")
