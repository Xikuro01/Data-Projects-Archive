"""
팰월드: 초중반 구간 선택 퀘스트(자원/티어 유도)의 효과 검증 (간결 버전)
==================================================================
[프로젝트 주도자 노트 — 가설은 본인이 직접 설계함]
필수 퀘스트만으로 기지 내실을 다지는 흐름과 별개로, 다른 NPC가 주는
선택 퀘스트(다음 지역 및 더 높은 티어의 광물/자원으로 유도하는 퀘스트)가
초중반 구간에서 실제로 진행 속도나 정착에 유의미한 영향을 줬는지를
가설로 세움:

  가설) 선택 퀘스트(자원/티어 유도)를 수행한 유저는, 수행하지 않은
        유저보다 다음 지역 진입률이 유의미하게 높을 것이다

[AI 협업 노트]
위 가설과 어떤 지표(다음 지역 진입률)로 검증할지에 대한 설계는 본인이
직접 함. 두 그룹을 비교하는 통계 코드와 시각화 구현은 Claude(AI)의
도움을 받아 작성함. 실제 로그 데이터가 없는 현재 단계이므로, 아래
수치는 가설 검증 "방법론"을 보여주기 위한 가정치이며 실측 데이터가 아님.
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
# 1. (임시) 가상 유저 로그 생성 — 실제 사용 시 실제 진행 로그로 교체
#    (AI 협업 구간: 데이터 구조 설계 및 코드 구현)
# =====================================================================
def generate_mock_progress_log(n=2000):
    did_optional_quest = np.random.choice([True, False], n, p=[0.45, 0.55])
    # 선택 퀘스트 수행 여부에 따른 다음 지역 진입 확률 (가정치)
    base_rate = 0.35
    boost = 0.20
    prob = np.where(did_optional_quest, base_rate + boost, base_rate)
    reached_next_area = np.random.random(n) < prob
    return pd.DataFrame({
        "did_optional_quest": did_optional_quest,
        "reached_next_area": reached_next_area,
    })


df = generate_mock_progress_log()

# =====================================================================
# 2. 그룹 간 비교 (본인 주도 구간: 어떤 두 그룹을 비교할지 설계)
# =====================================================================
group_a = df[df["did_optional_quest"]]["reached_next_area"].mean()    # 선택 퀘스트 수행
group_b = df[~df["did_optional_quest"]]["reached_next_area"].mean()   # 미수행

print("=" * 60)
print("[선택 퀘스트 수행 여부에 따른 다음 지역 진입률]")
print("=" * 60)
print(f"선택 퀘스트 수행 그룹   : {group_a:.1%}  (n={df['did_optional_quest'].sum()})")
print(f"선택 퀘스트 미수행 그룹 : {group_b:.1%}  (n={(~df['did_optional_quest']).sum()})")
print(f"차이                    : {(group_a - group_b) * 100:.1f}%p")

# =====================================================================
# 3. 시각화
# =====================================================================
fig, ax = plt.subplots(figsize=(6, 5))
ax.bar(["선택 퀘스트\n수행", "선택 퀘스트\n미수행"], [group_a * 100, group_b * 100],
       color=["#2ecc71", "#95a5a6"])
ax.set_ylabel("다음 지역 진입률 (%)")
ax.set_title("선택 퀘스트 수행 여부에 따른 진행 속도 비교")
plt.tight_layout()
plt.savefig("/home/claude/palworld_optional_quest.png", dpi=150)
print("\n[차트 저장 완료] palworld_optional_quest.png")

# =====================================================================
# 4. 결론
# =====================================================================
print("\n" + "=" * 60)
print("[결론]")
print("=" * 60)
print(f"""
- 선택 퀘스트를 수행한 그룹의 다음 지역 진입률이 {(group_a - group_b) * 100:.0f}%p 더 높게 나타나,
  '초중반 방향성 안내 퀘스트가 진행에 유의미한 도움을 준다'는
  가설을 검증하는 방법론을 보여줌
- 위 수치는 본인이 세운 가설을 검증하는 절차를 시연하기 위한
  가정치이며, 실제 진행 로그 확보 시 재검증이 필요함
- 한계: '선택 퀘스트를 하는 유저가 애초에 더 적극적인 유저였을
  가능성(선택 편향)'을 배제하지 못함 — 실제 검증 시에는 신규 유저를
  무작위로 두 그룹에 배정하는 A/B 테스트 형태가 이상적임
""")
