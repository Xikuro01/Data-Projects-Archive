"""
롤 사망 위치 기반 트롤 탐지 — 포지션별 '적진 사망'의 정상 기준이
다르다는 도메인 지식을 반영한 버전
==================================================================
[프로젝트 주도자 노트 — 도메인 지식 반영]
'적 진영에서 죽었다'는 신호를 모든 포지션에 같은 기준으로 적용하면
오탐이 생김. 실제 플레이 특성상:

  - 정글/서포터: 라인이라는 제약이 적어 시야 장악, 카운터정글, 적진
    침투 등으로 적진에서 죽는 일이 원래도 잦음 (상대 노림수에 당하는
    것도 정상적인 플레이의 일부)
  - 탑/미드: 라인전(대략 초반 15분) 동안은 적진에 있을 이유가 없지만,
    라인전 이후 사이드 운영/로밍이 늘면서 적진 교전 사망이 자연스러워짐
  - 원딜: 팀 자원이 집중되고 라인 제약이 가장 커서, 적진에서 죽는
    일 자체가 상대적으로 드묾 → 같은 '적진 사망'도 원딜에게는 더
    이례적인 신호

즉 '적진 사망'을 전체 유저 기준 하나로 판단하지 않고, 포지션(및
탑/미드는 라인전 여부)별로 서로 다른 기준선과 비교해야 함.

[AI 협업 노트]
포지션별 기준을 어떻게 나눌지는 본인이 설계, Z-score 계산 및
코드 구현은 Claude(AI) 도움을 받음.

[데이터 고지] 실제 Timeline API 접근 불가로 가상 데이터 사용.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
np.random.seed(42)

LANE_PHASE_CUTOFF = 900  # 15분(초) — 라인전이 사실상 끝나는 시점 (가정)


# =====================================================================
# 1. (임시) 가상 사망 이벤트 생성 — 실제 사용 시 Timeline API로 교체
# =====================================================================
def generate_mock_death_events(n_players=500, deaths_per_player=8):
    positions = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
    # 포지션별 '적진에서 죽는 게 정상인' 기준 확률 (도메인 지식 기반 가정)
    base_enemy_death_rate = {"TOP": 0.20, "JUNGLE": 0.35, "MID": 0.20, "ADC": 0.08, "SUPPORT": 0.30}

    rows = []
    for pid in range(n_players):
        position = np.random.choice(positions)
        is_troll = pid < n_players * 0.03
        for _ in range(deaths_per_player):
            game_time = np.random.uniform(60, 1800)  # 1분~30분 사이 무작위 사망 시점
            rate = base_enemy_death_rate[position]

            # 탑/미드는 라인전 시간대(<15분)엔 적진 사망이 원래 드물어야 함
            if position in ["TOP", "MID"] and game_time < LANE_PHASE_CUTOFF:
                rate *= 0.3

            if is_troll:
                rate = min(rate + 0.35, 0.95)  # 트롤은 포지션과 무관하게 적진 사망 확률 급증

            rows.append({
                "player_id": pid, "position": position, "game_time": game_time,
                "died_in_enemy_territory": np.random.random() < rate,
                "is_troll_actual": is_troll,
            })
    return pd.DataFrame(rows)


df = generate_mock_death_events()


# =====================================================================
# 2. '적진 사망'을 포지션(+탑/미드는 라인전 여부)별로 그룹 재정의
#    (본인 주도: 어떤 단위로 기준선을 나눠야 하는지 설계)
# =====================================================================
def group_key(row):
    if row["position"] in ["TOP", "MID"]:
        phase = "라인전" if row["game_time"] < LANE_PHASE_CUTOFF else "라인전이후"
        return f"{row['position']}-{phase}"
    return row["position"]


df["group"] = df.apply(group_key, axis=1)

# =====================================================================
# 3. 유저별 '적진 사망 비율' 집계 후, 같은 그룹 내 평균/표준편차로 Z-score
# =====================================================================
player_stats = df.groupby(["player_id", "group"]).agg(
    enemy_death_rate=("died_in_enemy_territory", "mean"),
    is_troll_actual=("is_troll_actual", "first"),
).reset_index()

group_baseline = player_stats.groupby("group")["enemy_death_rate"].agg(["mean", "std"]).reset_index()
group_baseline.columns = ["group", "group_mean", "group_std"]

player_stats = player_stats.merge(group_baseline, on="group")
player_stats["group_std"] = player_stats["group_std"].replace(0, 0.01)  # 0 나눗셈 방지
player_stats["zscore"] = (player_stats["enemy_death_rate"] - player_stats["group_mean"]) / player_stats["group_std"]

Z_THRESHOLD = 2.0
player_stats["flagged_suspect"] = player_stats["zscore"] > Z_THRESHOLD

# =====================================================================
# 4. 성능 검증 — 가상 정답 라벨 대비 (실제 서비스에는 없는 값)
# =====================================================================
tp = ((player_stats["flagged_suspect"]) & (player_stats["is_troll_actual"])).sum()
fp = ((player_stats["flagged_suspect"]) & (~player_stats["is_troll_actual"])).sum()
fn = ((~player_stats["flagged_suspect"]) & (player_stats["is_troll_actual"])).sum()
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0

print("=" * 70)
print("[그룹별(포지션+라인전 여부) 적진 사망 기준선]")
print("=" * 70)
print(group_baseline.round(3).to_string(index=False))

print("\n" + "=" * 70)
print("[탐지 성능]")
print("=" * 70)
print(f"정밀도: {precision:.2f} / 재현율: {recall:.2f}")

# =====================================================================
# 5. 시각화
# =====================================================================
fig, ax = plt.subplots(figsize=(9, 5))
order = group_baseline.sort_values("group_mean")["group"]
values = group_baseline.set_index("group").loc[order, "group_mean"] * 100
ax.bar(order, values, color="#3498db")
ax.set_ylabel("그룹별 평균 적진 사망 비율 (%)")
ax.set_title("포지션(+라인전 여부)별 '정상' 적진 사망 비율 기준선")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig("/home/claude/lol_death_location_by_group.png", dpi=150)
print("\n[차트 저장 완료] lol_death_location_by_group.png")

# =====================================================================
# 6. 결론
# =====================================================================
print("\n" + "=" * 70)
print("[결론]")
print("=" * 70)
print(f"""
- 같은 '적진 사망'이라도 정글/서포터는 원래 비율이 높고(약 30~35%),
  원딜은 원래 비율이 낮으며(약 8%), 탑/미드는 라인전 이후에만
  비율이 높아지는 게 정상이라는 도메인 지식을 그룹 기준선에 반영함
- 전체 통합 기준이 아니라 '같은 그룹끼리' 비교해 이상치를 탐지하므로,
  정글/서포터가 원래 자주 적진에서 죽는 것을 트롤로 오인하거나,
  반대로 원딜의 적진 사망을 과소평가하는 오류를 줄임
- 이 가상 데이터 기준 정밀도 {precision:.0%}, 재현율 {recall:.0%}
- 한계: 라인전 컷오프(15분)와 포지션별 기준 확률은 가정치이며,
  실제 적용 시 실측 데이터로 재보정 필요
""")
