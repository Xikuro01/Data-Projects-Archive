"""
팰월드: 얼리액세스 vs 1.0 재설계가 플레이 동기 지속시간에 미치는 영향
==================================================================
[프로젝트 주도자 노트 — 본인 플레이 경험에서 나온 가설]
얼리액세스 시절과 현재 1.0을 모두 플레이한 경험을 바탕으로, 1.0에서
확인한 재설계 방향(이동수단 획득시점 지연, 초반 고성능 팰의 후반
재배치, 금지구역 경비의 전투드론 전환, 테크트리 순서·재료 변경,
초반 팰 스펙 소폭 보정)이 실제로 무엇을 노린 것인지 궁금했음.

  가설) 최종급 보상(예: 제트래곤 같은 최상위 이동수단)을 너무 일찍
  얻으면, 그 즉시 해당 진행축(비행 성능 개선)에 대한 동기가 사라짐.
  1.0처럼 이 보상을 지연시키고, 동시에 기존 루트를 재배치해 새로운
  발견 이벤트를 추가하면, 플레이 동기가 더 오래 유지될 것이다.

[검증 방법]
'진행 이정표(milestone)'마다 동기(참신함)가 정점을 찍고 시간이
지나며 감쇠한다고 가정하고, EA 일정과 1.0 일정 각각에서 누적 동기
곡선이 어떻게 달라지는지 시뮬레이션으로 비교함.

[AI 협업 노트]
가설과 실제 변경 사항 확인은 본인이 직접 함. 시뮬레이션 구현은
Claude(AI) 도움을 받음. 이정표 시점·감쇠율은 실제 패치노트에서
확인된 변경 방향을 반영한 가정치이며, 실제 수치가 아님.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

MAX_HOURS = 45
DECAY_RATE = 0.15  # 이정표 이후 동기가 시간당 옅어지는 비율(가정)

# =====================================================================
# 1. EA(얼리액세스) 시절 이정표 일정 — 최종급 보상이 이른 시점에 등장
# =====================================================================
# (시점(시간), 동기 점수, 설명)
EA_MILESTONES = [
    (2, 1.0, "첫 팰 포획"),
    (5, 1.0, "첫 거점 건설"),
    (10, 1.2, "첫 타워보스"),
    (15, 2.5, "제트래곤 획득(비행축 사실상 완결)"),
    # 제트래곤 이후로는 비행 관련 진행축에서 새 이정표가 없음 — 해당 축 소멸
]

# =====================================================================
# 2. 1.0 이정표 일정 — 지연 + 재배치로 이정표 수 자체가 늘어남
# =====================================================================
V1_MILESTONES = [
    (2, 1.0, "첫 팰 포획"),
    (5, 1.0, "첫 거점 건설"),
    (9, 1.1, "재배치된 첫 타워보스(익숙한 위치 아님)"),
    (14, 1.3, "재배치된 필드보스 조우"),
    (18, 1.4, "전투드론 배치 금지구역 첫 돌파"),
    (24, 1.6, "재배치로 뒤로 밀린 고성능 팰 획득"),
    (30, 1.8, "재구성된 테크트리 신규 분기 해금"),
    (36, 2.5, "제트래곤 획득(지연됨)"),
]


def simulate_motivation(milestones, max_hours, decay_rate):
    hours = np.arange(0, max_hours, 0.5)
    motivation = np.zeros_like(hours)
    for (t, spike, _) in milestones:
        contribution = np.where(hours >= t, spike * np.exp(-decay_rate * (hours - t)), 0)
        motivation += contribution
    return hours, motivation


hours_ea, motivation_ea = simulate_motivation(EA_MILESTONES, MAX_HOURS, DECAY_RATE)
hours_v1, motivation_v1 = simulate_motivation(V1_MILESTONES, MAX_HOURS, DECAY_RATE)

auc_ea = np.trapezoid(motivation_ea, hours_ea)
auc_v1 = np.trapezoid(motivation_v1, hours_v1)

# =====================================================================
# 3. "동기가 임계값 이하로 떨어진 뒤 다시 회복 못 하는 시점" 비교
# =====================================================================
THRESHOLD = 0.3


def find_terminal_drop(hours, motivation, threshold):
    below = motivation < threshold
    for i in range(len(below) - 1):
        if below[i] and not any(~below[i:]):  # 이 지점부터 끝까지 계속 임계값 이하
            return hours[i]
    return None


terminal_ea = find_terminal_drop(hours_ea, motivation_ea, THRESHOLD)
terminal_v1 = find_terminal_drop(hours_v1, motivation_v1, THRESHOLD)

terminal_ea_display = f"{terminal_ea}시간" if terminal_ea is not None else f"{MAX_HOURS}시간 이내 미도달"
terminal_v1_display = f"{terminal_v1}시간" if terminal_v1 is not None else f"{MAX_HOURS}시간 이내 미도달"

print("=" * 70)
print("[결과] EA 일정 vs 1.0 일정 — 누적 동기 및 지속시간 비교")
print("=" * 70)
print(f"EA   — 누적 동기(AUC): {auc_ea:.1f}, 동기 소멸 후 회복 없는 시점: {terminal_ea_display}")
print(f"1.0  — 누적 동기(AUC): {auc_v1:.1f}, 동기 소멸 후 회복 없는 시점: {terminal_v1_display}")
print(f"→ 1.0 일정이 EA 대비 누적 동기 {(auc_v1/auc_ea - 1)*100:.0f}% 더 높으며, "
      f"관찰 기간({MAX_HOURS}시간) 내내 동기가 완전히 소멸하지 않음"
      if terminal_v1 is None else
      f"→ 1.0 일정이 EA 대비 누적 동기 {(auc_v1/auc_ea - 1)*100:.0f}%, "
      f"지속시간 {terminal_v1 - terminal_ea:.1f}시간 더 김")

# =====================================================================
# 4. 시각화
# =====================================================================
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(hours_ea, motivation_ea, color="#e74c3c", label="EA 일정(제트래곤 조기 획득)")
ax.plot(hours_v1, motivation_v1, color="#2ecc71", label="1.0 일정(지연 + 재배치)")
ax.axhline(THRESHOLD, color="gray", linestyle="--", label="동기 소멸 임계값")
for t, _, label in EA_MILESTONES:
    ax.axvline(t, color="#e74c3c", alpha=0.15)
for t, _, label in V1_MILESTONES:
    ax.axvline(t, color="#2ecc71", alpha=0.15)
ax.set_xlabel("누적 플레이 시간")
ax.set_ylabel("추정 플레이 동기(참신함) 수준")
ax.set_title("이정표 재배치·지연이 플레이 동기 지속시간에 미치는 영향")
ax.legend()
plt.tight_layout()
plt.savefig("/home/claude/palworld_motivation_curve.png", dpi=150)
print("\n[차트 저장 완료] palworld_motivation_curve.png")

# =====================================================================
# 5. 결론
# =====================================================================
print("\n" + "=" * 70)
print("[결론]")
print("=" * 70)
print(f"""
- 최종급 보상(제트래곤)을 일찍 배치한 EA 일정은, 그 시점 이후
  비행 관련 진행축에서 더 이상 새로운 동기가 발생하지 않아
  {terminal_ea_display} 이후로 동기가 임계값 아래로 떨어진 뒤 회복하지 못함
- 보상을 지연시키고 기존 루트를 재배치해 새로운 발견 이벤트를 추가한
  1.0 일정은, 동일 감쇠 가정 하에서도 누적 동기가 EA 대비
  {(auc_v1/auc_ea - 1)*100:.0f}% 더 높고, 동기 소멸 시점도 더 뒤로 밀림
- 즉 '최종 보상을 늦추는 것' 자체보다, '늦추면서 동시에 그 사이를
  새로운 발견 이벤트로 채우는 것'이 핵심 메커니즘으로 보임 — 단순
  지연만으로는 오히려 그 사이 구간이 지루해질 위험이 있음
- 한계: 이정표 시점·동기 점수·감쇠율은 실제 패치노트에서 확인된
  변경 방향을 참고한 가정치이며, 실제 유저 몰입 데이터로 검증된
  수치가 아님
""")
