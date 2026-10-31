# 월별 재구매율과 분석 고객 수 시각화
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = (
    BASE_DIR / "data" / "processed" / "monthly_repurchase_30d.csv"
)

OUTPUT_DIR = BASE_DIR / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

monthly = pd.read_csv(
    INPUT_PATH,
    dtype={"cohort_month": "string"},
)

monthly = monthly.sort_values("cohort_month").reset_index(drop=True)

print(monthly.to_string(index=False))

# 한글 표시용 폰트 (Windows)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

fig, axes = plt.subplots(
    nrows=2,
    ncols=1,
    figsize=(13, 9),
    sharex=True,
)

rate_ax = axes[0]
count_ax = axes[1]

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

count_ax.ticklabel_format(axis="y", style="plain")

count_ax.tick_params(axis="x", labelrotation=60)

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

output_path = OUTPUT_DIR / "monthly_repurchase_30d.png"

fig.savefig(
    output_path,
    dpi=150,
    bbox_inches="tight",
)

print(f"\n그래프 저장 완료: {output_path}")

plt.show()
