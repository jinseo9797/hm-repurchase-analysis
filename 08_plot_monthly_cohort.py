from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# 1. 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = (
    BASE_DIR / "data" / "processed" / "monthly_repurchase_30d.csv"
)

OUTPUT_DIR = BASE_DIR / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 2. 월별 집계 결과 읽기
monthly = pd.read_csv(
    INPUT_PATH,
    dtype={"cohort_month": "string"},
)

monthly = monthly.sort_values("cohort_month").reset_index(drop=True)

print(monthly.to_string(index=False))


# 3. Windows 한글 폰트 설정
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# 4. 위아래로 그래프 두 개 만들기
fig, axes = plt.subplots(
    nrows=2,
    ncols=1,
    figsize=(13, 9),
    sharex=True,
)

rate_ax = axes[0]
count_ax = axes[1]


# 5. 위쪽: 월별 30일 재구매율
rate_ax.plot(
    monthly["cohort_month"],
    monthly["repurchase_rate_pct"],
    marker="o",
    color="tab:blue",
    label="월별 재구매율",
)

rate_ax.set_title("첫 관측 구매 월별 30일 재구매율")
rate_ax.set_ylabel("30일 재구매율 (%)")
rate_ax.set_ylim(bottom=0)

rate_ax.grid(axis="y", alpha=0.3)
rate_ax.legend()


# 6. 아래쪽: 월별 분석 대상 고객 수
count_ax.bar(
    monthly["cohort_month"],
    monthly["customer_count"],
    color="tab:gray",
)

count_ax.set_title("월별 분석 대상 고객 수")
count_ax.set_xlabel("첫 관측 구매 월")
count_ax.set_ylabel("고객 수 (명)")

count_ax.grid(axis="y", alpha=0.3)
count_ax.set_axisbelow(True)

# 고객 수를 지수 표기 대신 일반 숫자로 표시
count_ax.ticklabel_format(axis="y", style="plain")

# 월 이름이 겹치지 않도록 회전
count_ax.tick_params(axis="x", labelrotation=60)


# 7. 제목과 해석 시 주의사항
fig.suptitle(
    "H&M 첫 관측 구매 고객군 분석",
    fontsize=16,
)

fig.text(
    0.5,
    0.02,
    "첫 관측 구매 ≠ 실제 신규 구매 | "
    "2018-09: 9/20부터 관측 | "
    "2020-08: 첫 관측 구매일 8/23까지 포함",
    ha="center",
    fontsize=10,
)

fig.tight_layout(rect=(0, 0.07, 1, 0.95))


# 8. 이미지 저장 후 화면에 표시
output_path = OUTPUT_DIR / "monthly_repurchase_30d.png"

fig.savefig(
    output_path,
    dpi=150,
    bbox_inches="tight",
)

print(f"\n그래프 저장 완료: {output_path}")

plt.show()