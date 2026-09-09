"""
대지인형: NPC 관계망을 통한 소문 전파(독립 전파 모델).
전파확률 가정에 따라 결과가 얼마나 달라지는지까지 함께 검증
(최초엔 0.35로 가정해 "99% 도달"을 얻었으나 근거 없는 값이었음 — README 참고).

대표 사례는 민감도 검증에 실제로 사용한 세 값(0.35/0.15/0.05) 중 하나인
0.15를 그대로 사용하고, 그 설정에서의 평균 도달(123명)에 가장 가까운
시드(1)를 골라 "우연히 극단적으로 잘 나온 사례"가 아니라 전형적인
사례를 보여주도록 함.

[고지] 아래 관계망·전파확률 값은 실데이터가 아닌 가상 예시값을
바탕으로 한 시뮬레이션이며, 코드 작성 과정에는 Anthropic Claude를
작업 도구로 활용함 — 자세한 내용은 README 참고.
"""
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
np.random.seed(42)
random.seed(42)

N_NPCS, AVG_DEGREE = 150, 5
DECAY_PER_HOP, TIME_DECAY, MIN_STRENGTH = 0.7, 0.9, 0.05


def build_graph(seed):
    rng = np.random.default_rng(seed)
    p = AVG_DEGREE / (N_NPCS - 1)
    adj = {i: set() for i in range(N_NPCS)}
    for i in range(N_NPCS):
        for j in range(i + 1, N_NPCS):
            if rng.random() < p:
                adj[i].add(j); adj[j].add(i)
    return adj, rng


def simulate(adj, rng, spread_prob, days=30):
    strength = {0: 1.0}
    for _ in range(days):
        new_s = dict(strength)
        for npc, s in list(strength.items()):
            if s < MIN_STRENGTH:
                continue
            for nb in adj[npc]:
                if nb not in new_s and rng.random() < spread_prob:
                    new_s[nb] = s * DECAY_PER_HOP
        for npc in new_s:
            new_s[npc] *= TIME_DECAY
        strength = new_s
    return strength


# 전파확률 민감도 (단일 확정값이 아님을 확인)
print("[전파확률별 도달 범위 — 시드 20개 평균]")
sensitivity = {}
for sp in [0.35, 0.15, 0.05]:
    reach = [len(simulate(*build_graph(seed), sp)) for seed in range(20)]
    sensitivity[sp] = reach
    print(f"  전파확률 {sp}: 평균 {np.mean(reach):.0f}명 ({np.mean(reach)/N_NPCS:.0%}), "
          f"표준편차 {np.std(reach):.0f}, 범위 {min(reach)}~{max(reach)}명 "
          f"({min(reach)/N_NPCS:.0%}~{max(reach)/N_NPCS:.0%})")

# 대표 사례 시각화 — 민감도 검증에 실제로 쓴 값(0.15)을, 그 값의 평균에
# 가장 가까운 시드(1)로 시각화 (극단값을 대표사례로 고르지 않도록)
adj, rng = build_graph(seed=1)
strength = simulate(adj, rng, spread_prob=0.15)
print(f"\n대표 사례(전파확률 0.15, 해당 설정의 평균에 근접한 시드): "
      f"최종 도달 {len(strength)}명 / {N_NPCS}명")

fig, ax = plt.subplots(figsize=(6, 4.5))
ax.hist(list(strength.values()), bins=20, color="#2ecc71")
ax.set_xlabel("최종 인상 강도")
ax.set_ylabel("NPC 수")
ax.set_title("소문 도달 후 잔존 인상 강도 분포")
plt.tight_layout()
plt.savefig("/home/claude/work/gossip_propagation_analysis.png", dpi=150)
print("[차트 저장 완료] gossip_propagation_analysis.png")
