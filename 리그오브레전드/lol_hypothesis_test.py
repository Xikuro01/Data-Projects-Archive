"""
포지션(+라인전 여부) 그룹별 적진 사망 비율이 가설(도메인 지식)이
제시한 방향과 통계적으로 유의미하게 일치하는지 검정.

[검정 선택 이유]
표본이 그룹당 36~38개로 작고, 각 표본이 '비율(0~1)'이라 정규분포를
가정하기 어려움 → 정규성 가정이 필요 없는 비모수 검정(Kruskal-Wallis,
Mann-Whitney U) 사용.
"""
import sqlite3
import pandas as pd
from scipy import stats

conn = sqlite3.connect("/home/claude/lol_analytics.db")
df = pd.read_sql("SELECT player_group, enemy_death_rate FROM player_stats_real", conn)
conn.close()

# ---------------------------------------------------------------
# 1. 전체 그룹 간 차이 검정 (Kruskal-Wallis) — "7개 그룹이 정말 서로 다른가?"
# ---------------------------------------------------------------
groups = [g["enemy_death_rate"].values for _, g in df.groupby("player_group")]
h, p_overall = stats.kruskal(*groups)
print("=" * 70)
print("[1] 전체 그룹 간 차이 (Kruskal-Wallis)")
print("=" * 70)
print(f"H = {h:.3f}, p = {p_overall:.4f}")
print("→ 유의함(p<0.05)" if p_overall < 0.05 else "→ 유의하지 않음(p>=0.05)")

# ---------------------------------------------------------------
# 2. 가설이 예측한 핵심 방향성 각각을 개별 검정 (Mann-Whitney U, one-sided)
# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("[2] 가설별 개별 방향 검정 (Mann-Whitney U, one-sided)")
print("=" * 70)

pairs = [
    ("BOTTOM", "TOP-라인전이후", "ADC가 라인전이후 TOP보다 적진사망이 적어야 함"),
    ("BOTTOM", "MIDDLE-라인전이후", "ADC가 라인전이후 MID보다 적진사망이 적어야 함"),
    ("TOP-라인전", "TOP-라인전이후", "TOP은 라인전이후 적진사망이 늘어야 함"),
    ("MIDDLE-라인전", "MIDDLE-라인전이후", "MID는 라인전이후 적진사망이 늘어야 함"),
]

for a, b, desc in pairs:
    ga = df[df["player_group"] == a]["enemy_death_rate"]
    gb = df[df["player_group"] == b]["enemy_death_rate"]
    u, p = stats.mannwhitneyu(ga, gb, alternative="less")
    flag = "유의함" if p < 0.05 else "유의하지 않음"
    print(f"- {desc}")
    print(f"  {a}(n={len(ga)}) < {b}(n={len(gb)}) : p = {p:.4f} → {flag}")

print("""
[해석]
전체 검정(Kruskal-Wallis)은 유의하지 않아, 7개 그룹이 통계적으로
뚜렷이 다르다고 확정할 수 없음. 개별 방향 검정에서도 대부분
p>=0.05로, 가설이 예측한 방향과 '경향은 일치'하지만 이 표본
크기(20경기)로는 통계적으로 확정 짓기엔 검정력이 부족함.
표본을 확대하면 유의성이 확보될 가능성이 있는지가 다음 과제.
""")
