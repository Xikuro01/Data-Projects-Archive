"""
팰월드 정식 출시 대비: 콘텐츠 확장에 따른 이탈 리스크와
선택적 방향 제시 퀘스트의 완화 효과 분석 (간결 버전)
==================================================================
[프로젝트 주도자 노트 — 가설은 본인이 직접 설계함]
정식 출시 예고에서 현재보다 훨씬 많은 콘텐츠(지역/시스템/아이템 등)가
추가된다고 밝혀짐에 따라, 콘텐츠 양 증가가 오히려 초중반 구간에서
유저의 방향성 상실로 이어져 이탈이 커질 수 있다는 리스크를 가설로 세움.
이에 대한 대응으로 "반드시 수행해야 하는 필수 퀘스트가 아니라
선택적으로 참고할 수 있는 방향 제시 퀘스트"를 도입하면 이 리스크를
완화할 수 있는지를 검증 대상으로 설정함.

  가설1) 정식 출시로 콘텐츠가 크게 늘어나면, 방향성 상실로 인해
         초중반 이탈률이 현재보다 높아질 것이다
  가설2) 이때 "선택적"(강제성 없는) 방향 제시 퀘스트를 도입하면,
         유저의 자율적 플레이를 해치지 않으면서도 이탈률 증가를
         완화할 수 있을 것이다
         (강제 퀘스트가 아닌 이유: 자유도를 해치는 강제 유도는
          그 자체로 새로운 이탈 요인이 될 수 있기 때문)

[AI 협업 노트]
가설 설계와 어떤 시나리오 3개를 비교할지는 본인이 직접 함. 이를
비교하는 통계 코드와 시각화 구현은 Claude(AI)의 도움을 받아 작성함.
정식 출시가 아직 이뤄지지 않아 실측 데이터가 존재할 수 없는 상황이므로,
아래 수치는 의사결정을 돕기 위한 시나리오 추정치이며 실측이 아님.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
np.random.seed(42)

# =====================================================================
# 1. 시나리오 정의 (본인 주도: 어떤 3가지 상황을 비교할지 설계)
# =====================================================================
# '현재(출시 전)' 이탈률은 이전 팰월드 프로젝트(진행 단계별 도전과제
# 하락폭 분석)에서 확인된 초중반 하락폭을 참고값으로 사용.
# 콘텐츠 확장 시 증가폭 및 퀘스트 완화 효과는 의사결정을 위한 가정치.
BASELINE_CHURN = 0.24                     # 현재(출시 전) 이탈률
CONTENT_EXPANSION_INCREASE = 0.15         # 콘텐츠 확장으로 인한 이탈률 증가분 (가정)
CHURN_AFTER_EXPANSION = BASELINE_CHURN + CONTENT_EXPANSION_INCREASE

# [수정 포인트] '선택적' 퀘스트이므로 전체 유저가 아니라, 실제로 퀘스트를
# 선택한 유저에게만 완화 효과가 적용되어야 함 — 참여율을 별도 변수로 분리
QUEST_ADOPTION_RATE = 0.4                 # 선택 퀘스트를 실제로 수행할 것으로 예상되는 유저 비율 (가정)
MITIGATION_PER_ADOPTER = 0.12             # 퀘스트를 '수행한 유저에 한해서만' 이탈률이 낮아지는 정도 (가정)
# ※ 검증 포인트: 참여율 100%여도 상쇄 비율이 100%를 넘으면 안 되므로
#   MITIGATION_PER_ADOPTER(0.12) < CONTENT_EXPANSION_INCREASE(0.15)로 설정

N = 2000

# =====================================================================
# 2. 시뮬레이션 — 시나리오별 이탈 유저 수 산출
# =====================================================================
# (a) 현재(출시 전)
baseline_churned = np.random.random(N) < BASELINE_CHURN

# (b) 정식출시 후, 퀘스트 미도입 — 전원이 확장으로 인한 증가된 이탈률을 겪음
no_quest_churned = np.random.random(N) < CHURN_AFTER_EXPANSION

# (c) 정식출시 후, 퀘스트 도입 — 참여율만큼만 완화 효과를 받고, 나머지는 그대로
adopted = np.random.random(N) < QUEST_ADOPTION_RATE                      # 누가 퀘스트를 선택했는지
churn_prob_with_option = np.where(adopted, CHURN_AFTER_EXPANSION - MITIGATION_PER_ADOPTER, CHURN_AFTER_EXPANSION)
with_quest_churned = np.random.random(N) < churn_prob_with_option

result_df = pd.DataFrame({
    "시나리오": ["현재(출시 전)", "정식출시 후(퀘스트 미도입)", f"정식출시 후(선택 퀘스트, 참여율 {QUEST_ADOPTION_RATE:.0%})"],
    "실제 집계 이탈률": [baseline_churned.mean(), no_quest_churned.mean(), with_quest_churned.mean()],
    "표본 수": [N, N, N],
})
print("=" * 70)
print("[시나리오별 초중반 이탈률 비교]")
print("=" * 70)
print(result_df.round(3).to_string(index=False))
print(f"\n[참고] 퀘스트 실제 채택 유저 수: {adopted.sum()}명 / 전체 {N}명 (참여율 {adopted.mean():.1%})")

# =====================================================================
# 3. 선택 퀘스트 도입 효과 계산
# =====================================================================
baseline = result_df.loc[0, "실제 집계 이탈률"]  # 현재(출시 전)
before = result_df.loc[1, "실제 집계 이탈률"]    # 정식출시 후, 퀘스트 미도입
after = result_df.loc[2, "실제 집계 이탈률"]     # 정식출시 후, 퀘스트 도입

increase = before - baseline
mitigation = before - after
offset_ratio = (mitigation / increase * 100) if increase != 0 else 0

print("\n" + "=" * 70)
print("[선택 퀘스트 도입 효과]")
print("=" * 70)
print(f"콘텐츠 확장으로 인한 이탈률 증가분   : {increase*100:.1f}%p")
print(f"선택 퀘스트 도입으로 완화된 이탈률   : {mitigation*100:.1f}%p")
print(f"증가분 대비 상쇄 비율                : {offset_ratio:.0f}%")

# =====================================================================
# 3-1. 참여율 민감도 — "선택"이기 때문에 참여율 자체가 설계 레버가 됨
# =====================================================================
print("\n" + "=" * 70)
print("[참여율에 따른 효과 민감도] — 참여율이 낮으면 효과도 비례해 줄어듦")
print("=" * 70)
sens_rows = []
for rate in [0.2, 0.4, 0.6, 0.8]:
    adopted_s = np.random.random(N) < rate
    prob_s = np.where(adopted_s, CHURN_AFTER_EXPANSION - MITIGATION_PER_ADOPTER, CHURN_AFTER_EXPANSION)
    churn_s = (np.random.random(N) < prob_s).mean()
    sens_rows.append({"참여율": f"{rate:.0%}", "예상 이탈률": round(churn_s, 3),
                       "상쇄 비율": f"{(before - churn_s) / increase * 100:.0f}%"})
print(pd.DataFrame(sens_rows).to_string(index=False))

# =====================================================================
# 4. 시각화
# =====================================================================
fig, ax = plt.subplots(figsize=(8, 5))
colors = ["#95a5a6", "#e74c3c", "#2ecc71"]
ax.bar(result_df["시나리오"], result_df["실제 집계 이탈률"] * 100, color=colors)
ax.set_ylabel("초중반 이탈률 (%)")
ax.set_title("정식 출시 콘텐츠 확장과 선택 퀘스트 도입에 따른 이탈률 시나리오")
plt.xticks(rotation=8, ha="right")
plt.tight_layout()
plt.savefig("/home/claude/palworld_full_release_scenario.png", dpi=150)
print("\n[차트 저장 완료] palworld_full_release_scenario.png")

# =====================================================================
# 5. 결론
# =====================================================================
print("\n" + "=" * 70)
print("[결론]")
print("=" * 70)
print(f"""
- 정식 출시로 콘텐츠가 크게 늘어나면, 방향성 상실로 인한 초중반
  이탈률이 현재 대비 {increase*100:.0f}%p 증가할 수 있다는 리스크 시나리오를 설정함
- 이때 "필수가 아닌 선택적" 방향 제시 퀘스트를 도입하면, 그 증가분의
  약 {offset_ratio:.0f}%를 상쇄할 수 있을 것으로 추정됨
- '선택적'으로 설계한 이유: 강제 퀘스트는 유저의 자유도를 해쳐
  오히려 새로운 이탈 요인이 될 수 있으므로, 참고만 가능한 형태가
  리스크가 더 적다고 판단함
- 참여율 민감도 분석 결과, 참여율이 낮으면 효과도 비례해 줄어듦
  → 따라서 실제 구현 시 퀘스트의 발견 용이성(UI 노출, 초반 튜토리얼
  연계 등)이 참여율을 좌우하는 핵심 설계 변수가 됨
- 한계: 정식 출시 전이라 실측 데이터가 존재할 수 없는 상황이므로,
  위 수치는 의사결정을 돕기 위한 시나리오 추정치이며, 실제로는 출시
  후 알파/베타 테스트 단계에서 실측 이탈률로 재검증이 필요함
""")
