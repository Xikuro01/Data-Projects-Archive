"""
팰월드: 진행 단계별 이탈 지점 분석 (기초 버전)
==================================================================
[기존 접근과의 차이]
- 기존: "선택적 방향성 퀘스트를 넣자" (콘텐츠 기획 아이디어)
- 재설계: "어느 진행 구간에서 유저가 가장 많이 이탈하는가?"를
  먼저 데이터로 특정한 뒤, 그 구간에 콘텐츠를 배치해야 한다는
  근거를 세우는 방식

[방법론]
- 실제 세션 로그가 없을 때 흔히 쓰는 대체 지표(프록시)로
  '도전과제(Achievement) 달성률'을 사용
  → 도전과제는 보통 진행 단계 순서대로 설계되므로, 단계별
    달성률 하락폭이 클수록 그 구간에서 이탈이 많았다는 신호로 해석 가능
- 복잡한 통계 없이 "단계 간 하락폭(%)"만 비교해도 이탈 구간을
  특정하기에 충분하므로, 가장 단순한 방법을 선택함

[중요 - 데이터 관련 고지]
이 환경은 외부 네트워크가 차단되어 있어 실제 SteamSpy/Steam API를
호출할 수 없습니다. 아래 데이터는 실제 API 응답과 유사한 형태로
구성한 가상 데이터입니다. 실제 사용 시에는 데이터 로드 부분만
실제 API 호출로 교체하면 분석 로직은 그대로 재사용 가능합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False


# =====================================================================
# 1. (임시) 가상 도전과제 달성률 데이터 — 실제 사용 시 API 응답으로 교체
# =====================================================================
def load_mock_achievement_data():
    # 진행 순서대로 정렬된 도전과제와 전체 유저 중 달성 비율(%) (가정치)
    return pd.DataFrame([
        {"stage": "1. 첫 팰 포획",        "order": 1, "achievement_rate": 92.0},
        {"stage": "2. 첫 베이스 건설",     "order": 2, "achievement_rate": 78.0},
        {"stage": "3. 첫 보스 처치",       "order": 3, "achievement_rate": 55.0},
        {"stage": "4. 중반 기술 트리 해금", "order": 4, "achievement_rate": 31.0},
        {"stage": "5. 후반 지역 도달",     "order": 5, "achievement_rate": 12.0},
        {"stage": "6. 엔드콘텐츠 진입",     "order": 6, "achievement_rate": 6.0},
    ])


df = load_mock_achievement_data().sort_values("order")

# =====================================================================
# 2. 단계 간 하락폭(%) 계산 — 이탈이 가장 큰 구간을 찾는 핵심 로직
# =====================================================================
df["직전 대비 하락폭(%p)"] = -df["achievement_rate"].diff()

print("=" * 60)
print("[1] 진행 단계별 달성률 및 하락폭")
print("=" * 60)
print(df[["stage", "achievement_rate", "직전 대비 하락폭(%p)"]].to_string(index=False))

biggest_drop = df.loc[df["직전 대비 하락폭(%p)"].idxmax()]
print(f"\n가장 큰 하락 구간: {biggest_drop['stage']} "
      f"(직전 단계 대비 {biggest_drop['직전 대비 하락폭(%p)']:.1f}%p 하락)")

# =====================================================================
# 3. 시각화 — 퍼널(funnel) 형태로 진행 단계별 달성률 표시
# =====================================================================
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(df["stage"], df["achievement_rate"], color="#3498db")
# 가장 큰 하락 구간 강조
max_idx = df["직전 대비 하락폭(%p)"].idxmax()
bars[list(df.index).index(max_idx)].set_color("#e74c3c")

ax.set_ylabel("도전과제 달성률 (%)")
ax.set_title("진행 단계별 도전과제 달성률\n(빨강 = 가장 큰 하락 구간)")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig("/home/claude/palworld_stage_dropoff.png", dpi=150)
print("\n[차트 저장 완료] palworld_stage_dropoff.png")

# =====================================================================
# 4. 결론
# =====================================================================
print("\n" + "=" * 60)
print("[결론]")
print("=" * 60)
print(f"""
- '{biggest_drop['stage']}' 구간에서 하락폭이 가장 커, 이 구간이
  유저가 목표를 잃고 이탈할 가능성이 가장 높은 지점으로 추정됨
- 이 구간에 선택적 방향성 퀘스트를 배치하면, "막연히 재밌을 것 같다"가
  아니라 "가장 이탈이 많은 지점을 데이터로 특정해 배치했다"는
  근거 있는 제안이 됨
- 한계: 도전과제 달성률은 실제 세션 단위 이탈률보다 거친(coarse) 지표이므로,
  실제 적용 전 정밀한 로그 기반 검증이 필요함
""")
