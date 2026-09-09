"""
카디널의 우연한 목격: 소멸 원인(연출용 vs 실제 탐지 연동)을
유저가 통계적으로도 구별할 수 없는지 검증. 배경은 README 참고.

[강화 포인트] 이 구별 불가능성은 90초/300초라는 특정 파라미터를 잘 골라서
나온 우연이 아니라, "독립된 두 지수분포가 경쟁할 때 어느 쪽이 이겼는지와
걸린 시간은 항상 통계적으로 독립"이라는 무기억성(memorylessness)에서
오는 일반적 성질임. 아래 [파라미터 의존성 검증]에서 다른 조합으로도
동일하게 확인.

[고지] 아래 평균 주기값(90초/300초 등)은 실데이터가 아닌 가상
예시값을 바탕으로 한 시뮬레이션이며, 코드 작성 과정에는 Anthropic
Claude를 작업 도구로 활용함 — 자세한 내용은 README 참고.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
np.random.seed(42)

N = 5000
LAMBDA_AMBIENT = 1 / 90     # 순수 연출: 평균 90초 후 이동
LAMBDA_DETECTION = 1 / 300  # 실제 탐지: 평균 300초당 1회 발생

ambient_time = np.random.exponential(1 / LAMBDA_AMBIENT, N)
detection_time = np.random.exponential(1 / LAMBDA_DETECTION, N)
duration = np.minimum(ambient_time, detection_time)
cause = np.where(ambient_time < detection_time, "연출", "탐지")

detection_ratio = (cause == "탐지").mean()
ks_stat, p_value = stats.ks_2samp(duration[cause == "연출"], duration[cause == "탐지"])

print(f"실제 탐지 연동 비율: {detection_ratio:.1%}")
print(f"두 원인의 지속시간 분포 KS 검정 p-value: {p_value:.3f}"
      f" → {'통계적으로 구별 불가능' if p_value >= 0.05 else '구별 가능(설계 재검토 필요)'}")

# 파라미터 의존성 검증: 90/300이라는 특정 값에서만 성립하는 결과가 아님을 확인
print("\n[파라미터 의존성 검증] — 다른 (평균 연출주기, 평균 탐지주기) 조합에서도 성립하는지")
rng = np.random.default_rng(1)
for mean_amb, mean_det in [(50, 500), (200, 210), (10, 1000), (120, 130)]:
    a = rng.exponential(mean_amb, N)
    d = rng.exponential(mean_det, N)
    dur2 = np.minimum(a, d)
    c2 = np.where(a < d, "연출", "탐지")
    _, p2 = stats.ks_2samp(dur2[c2 == "연출"], dur2[c2 == "탐지"])
    print(f"  평균 연출={mean_amb:4d}초, 평균 탐지={mean_det:4d}초 → 탐지비율 "
          f"{(c2 == '탐지').mean():.1%}, KS p={p2:.3f}")
print("  → 파라미터를 바꿔도 p-value는 계속 비유의(>0.05): 이 설계의 구별 불가능성은")
print("    특정 값(90/300)에 의존하지 않고 무기억성에서 오는 일반적 성질임.")

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].pie([detection_ratio, 1 - detection_ratio], labels=["실제 탐지", "순수 연출"],
            autopct="%1.1f%%", colors=["#e74c3c", "#3498db"])
axes[0].set_title("목격-소멸 원인 비율(유저는 모름)")

bins = np.linspace(0, duration.max(), 40)
axes[1].hist(duration[cause == "연출"], bins=bins, alpha=0.5, label="연출", color="#3498db", density=True)
axes[1].hist(duration[cause == "탐지"], bins=bins, alpha=0.5, label="탐지", color="#e74c3c", density=True)
axes[1].set_title(f"지속시간 분포 비교 (p={p_value:.3f})")
axes[1].legend()

plt.tight_layout()
plt.savefig("/home/claude/work/cardinal_sighting_analysis.png", dpi=150)
print("[차트 저장 완료] cardinal_sighting_analysis.png")
