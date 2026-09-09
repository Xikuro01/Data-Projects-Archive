"""
카디널형(중앙집중) vs 대지인형(분산) AI NPC 아키텍처
비용/속도, 그리고 '유저마다 다른 경험' 두 축을 검증. 배경·시행착오는 README 참고.

[4차 뒤집힘] 최초 버전은 서버를 "이론적 최소치(여유 0%)"로 배정해
대지인형이 100명부터 붕괴한다는 결과를 얻었으나, 재검토 결과 이는
현실적인 서버 운영 관례(여유를 두고 증설)와 다른 가정에서 나온
아티팩트였음이 드러남. 아래 [1]에서 두 가정을 나란히 비교.

[고지] 아래 상수(비용, 처리량, 목표 가동률 등)는 실데이터가 아닌
가상 예시값을 바탕으로 한 시뮬레이션이며, 코드 작성 과정에는
Anthropic Claude를 작업 도구로 활용함 — 자세한 내용은 README 참고.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
np.random.seed(42)

MAX_LATENCY = 2.0          # 실시간 응답 허용 한계(초)
COST_PER_INFER = 0.0005    # sLLM 1회 추론 비용(USD, 예시)
THROUGHPUT = 20            # 서버 1대가 초당 처리 가능한 추론 수(예시)
SERVER_COST_HR = 2.0
TOKENS_PER_NPC = 200       # 카디널형: NPC 1명 상태를 표현하는 토큰 수(예시)
CTX_LIMIT = 200_000        # LLM 컨텍스트 한도(예시)
TARGET_UTIL = 0.8          # 현실적 서버 운영 가정: 목표 가동률 80% (여유를 두고 증설)


def distributed_latency(n, tiered=False, active_ratio=0.08, target_util=TARGET_UTIL):
    """대지인형: NPC마다 개별 추론.
    tiered=True면 활성 NPC만 자주 반응.
    target_util=1.0은 "여유 없이 이론적 최소 서버 수로 배정"한 최초 버전 가정,
    target_util=0.8(기본값)은 현실적인 여유를 둔 배정."""
    if tiered:
        n_active = max(1, round(n * active_ratio))
        calls = n_active / 5 + (n - n_active) / 60
    else:
        calls = n / 5  # 5초 주기
    servers = max(1, np.ceil(calls / (THROUGHPUT * target_util)))
    rho = min(calls / (servers * THROUGHPUT), 0.99)
    latency = (1 / THROUGHPUT) * rho / (1 - rho)  # 대기행렬(M/M/1) 근사
    return latency, servers * SERVER_COST_HR


def cardinal_latency(n, tiered=False, active_ratio=0.08):
    """카디널형: 전체 NPC 상태를 하나의 컨텍스트로 묶어 처리."""
    if tiered:
        n_active = max(1, round(n * active_ratio))
        tokens = n_active * TOKENS_PER_NPC + (n - n_active) * TOKENS_PER_NPC * 0.15
    else:
        tokens = n * TOKENS_PER_NPC
    latency = 0.3 + tokens * 0.00002
    return latency, tokens * 0.000003 * (3600 / 5)


def find_breakdown(fn, counts, **kwargs):
    for n in counts:
        latency, _ = fn(n, **kwargs)
        if latency > MAX_LATENCY:
            return n
    return f"{counts[-1]}+"


counts = [5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]

print("[1] 비용/속도 한계선 — 여유 0% 가정 vs 현실적 여유(80%) 가정 비교")
print(f"  [여유 0%, 최초 버전 가정] 대지인형 - 기본: "
      f"{find_breakdown(distributed_latency, counts, target_util=1.0)}명 / "
      f"계층화: {find_breakdown(distributed_latency, counts, tiered=True, target_util=1.0)}명")
print(f"  [현실적 여유 80%]        대지인형 - 기본: "
      f"{find_breakdown(distributed_latency, counts)}명 / "
      f"계층화: {find_breakdown(distributed_latency, counts, tiered=True)}명")
print(f"  카디널형(여유 개념 없음, 컨텍스트 크기로 결정) - 기본: "
      f"{find_breakdown(cardinal_latency, counts)}명 / "
      f"계층화: {find_breakdown(cardinal_latency, counts, tiered=True)}명")

# 왜 이렇게 갈리는지: 목표 가동률 u로 서버를 유지하면 calls가 아무리 커져도
# rho -> u로 수렴하고, latency는 스케일과 무관한 상수 (1/처리량)*u/(1-u)에 수렴함.
# 이 상수가 MAX_LATENCY를 넘으려면 u가 아래 임계치를 넘어야 함:
u_threshold = (MAX_LATENCY * THROUGHPUT) / (1 + MAX_LATENCY * THROUGHPUT)
print(f"\n  [분석] 목표 가동률 u가 {u_threshold:.1%}를 넘지 않는 한, 대지인형은 "
      f"이론상 어떤 규모에서도 latency로는 붕괴하지 않음(서버를 계속 늘릴 수 있다는 전제 하에).")
print(f"  최초 버전의 '100명 붕괴'는 바로 u=100%(여유 0%)라는 극단적 가정 때문이었음.")
print(f"  → 현실적 가정에서는 대지인형의 실질적 한계가 '속도'가 아니라 '서버비용의 선형 증가'로 바뀜.")


def diversity_simulation(n_players=300, n_turns=30, pull_to_mean=0.7):
    """카디널형(표준반응으로 수렴) vs 대지인형(경로의존적 랜덤워크)."""
    c_std, d_std = [], []
    c_state = np.zeros(n_players)
    d_state = np.zeros(n_players)
    for _ in range(n_turns):
        player_input = np.random.normal(0, 1, n_players)
        c_state = (1 - pull_to_mean) * c_state + 0.3 * player_input
        d_state = d_state + player_input
        c_std.append(c_state.std())
        d_std.append(d_state.std())
    return c_std, d_std


c_std, d_std = diversity_simulation()
print(f"\n[2] 유저 간 경험 편차(30턴 후) — 카디널형: {c_std[-1]:.2f} / 대지인형: {d_std[-1]:.2f}")
print(f"  (대지인형 이론값 sqrt(30)={np.sqrt(30):.2f} — 랜덤워크 공식과 근접해 시뮬레이션 검증됨)")

# 시각화
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

n_grid = np.unique(np.round(np.logspace(np.log10(5), np.log10(5000), 250)).astype(int))
lat_naive = [distributed_latency(n, target_util=1.0)[0] for n in n_grid]
lat_real = [distributed_latency(n)[0] for n in n_grid]
lat_card = [cardinal_latency(n)[0] for n in n_grid]

axes[0].plot(n_grid, lat_naive, color="#e74c3c", lw=1, alpha=0.8, label="대지인(여유 0%, 최초 가정)")
axes[0].plot(n_grid, lat_real, color="#2ecc71", lw=2, label="대지인(여유 80%, 현실적 가정)")
axes[0].plot(n_grid, lat_card, color="#2980b9", lw=2, label="카디널(기본)")
axes[0].axhline(MAX_LATENCY, color="gray", ls="--", lw=1, label="한계(2초)")
axes[0].set_xscale("log")
axes[0].set_xlabel("NPC 수")
axes[0].set_ylabel("지연시간(초)")
axes[0].set_title("서버 배정 가정에 따른 지연시간 변화")
axes[0].legend(fontsize=8)

axes[1].plot(range(1, 31), c_std, label="카디널형", color="#2980b9")
axes[1].plot(range(1, 31), d_std, label="대지인형", color="#e74c3c")
axes[1].set_xlabel("상호작용 누적 횟수")
axes[1].set_ylabel("유저 간 결과 편차")
axes[1].set_title("경험 다양성 비교")
axes[1].legend()

plt.tight_layout()
plt.savefig("/home/claude/work/ai_npc_architecture_analysis.png", dpi=150)
print("\n[차트 저장 완료] ai_npc_architecture_analysis.png")

print("""
[결론] 서버를 현실적인 여유(목표 가동률 80%)를 두고 운영한다고 가정하면,
대지인형은 테스트한 규모(5000명)까지 '속도'로는 붕괴하지 않고, 실질적
한계는 서버비용의 선형 증가로 옮겨감. 반면 카디널형은 컨텍스트 크기
자체가 늘어나는 구조라 여유의 개념이 없고, 500명 안팎에서 실제로
속도 한계에 부딪힘. 경험 다양성 면에서는 여전히 대지인형이 우세하며,
카디널형의 '수렴하는 성질'은 일관성·통제력이 필요한 영역(세계관 큰
흐름)에서 강점이 되므로, 하이브리드 구조가 현재 기술 기준 현실적임.
""")
