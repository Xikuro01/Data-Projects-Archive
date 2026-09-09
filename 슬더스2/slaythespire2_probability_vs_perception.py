"""
슬더스2 확률 검증
가설1: 카드가 덱에 '있다'는 건 알아도 '위치'는 모름 → 드로우까지 걸리는 턴수
가설2: 초반 스타터 덱 재정립 시, 새 패가 이전 패와 겹치는 비율(카드 이름 기준)
(배경·검증 과정은 README 참고)
"""

import random
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
random.seed(42)
np.random.seed(42)


def turns_to_draw(deck_size, hand_size=5, trials=10000):
    position = np.random.randint(1, deck_size + 1, trials)
    return np.ceil(position / hand_size).mean()


def overlap_rate(deck, hand_size=5, trials=10000):
    cards = [name for name, n in deck.items() for _ in range(n)]
    hits = []
    for _ in range(trials):
        random.shuffle(cards)
        before = cards[:hand_size]
        pool = before + cards[hand_size:]
        random.shuffle(pool)
        after = pool[:hand_size]
        hits.append(sum((Counter(before) & Counter(after)).values()) / hand_size)
    return np.mean(hits)


STARTER_DECKS = {
    "아이언클레드": {"타격": 5, "수비": 4, "강타": 1},
    "사일런트": {"타격": 5, "수비": 5, "무력화": 1, "생존자": 1},
    "리젠트": {"타격": 4, "수비": 4, "별똥별": 1, "추앙": 1},
    "네크로바인드": {"타격": 4, "수비": 4, "호위": 1, "풀어놓기": 1},
    "디펙트": {"타격": 4, "수비": 4, "파지직": 1, "이중시전": 1},
}

deck_sizes = [10, 15, 20, 25]
avg_turns = [turns_to_draw(s) for s in deck_sizes]
overlap = {name: overlap_rate(deck) for name, deck in STARTER_DECKS.items()}

print("가설1 - 덱 크기별 평균 드로우 턴:", dict(zip(deck_sizes, [round(float(t), 1) for t in avg_turns])))
print("가설2 - 캐릭터별 재정립 겹침률:", {k: f"{v:.0%}" for k, v in overlap.items()})
print(f"→ 평균 {np.mean(list(overlap.values())):.0%} (체감 80%와 근접)")

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].bar([str(s) for s in deck_sizes], avg_turns, color="#3498db")
ax[0].set_title("가설1: 덱 크기별 평균 드로우 턴")
ax[1].bar(overlap.keys(), [v * 100 for v in overlap.values()], color="#2ecc71")
ax[1].axhline(80, color="gray", linestyle="--")
ax[1].set_title("가설2: 캐릭터별 겹침률(%)")
plt.setp(ax[1].get_xticklabels(), rotation=20, ha="right")
plt.tight_layout()
plt.savefig("/home/claude/slaythespire2_probability_vs_perception.png", dpi=150)
