"""
[역할 구분 명시] 데이터 생성/적재 전용(Python). 분석 로직은
palworld_review_analysis.sql에 순수 SQL로 작성됨.

[개선점 — 이전 버전과의 차이]
이전 버전은 10개 템플릿을 20번씩 반복해 인위적으로 균형 잡힌(3긍정+3부정)
테스트 데이터였음 — 그래서 결과가 "차이 0.0%p"라는, 실행했다는 사실
외엔 아무 정보도 없는 결과를 냈음. 이번엔:
  1) 카테고리를 3개(위치재배치/테크트리순서/밸런스난이도)로 세분화
  2) 각 카테고리에 서로 다른 '내재된 긍정비율'을 심어서 실제 신호가
     있는 것처럼 생성 (연구자만 아는 정답, 분석 코드는 이걸 모르는 채로
     리뷰 텍스트+투표만 보고 찾아내야 함)
  3) 무작위성을 추가해 100% 예측 가능한 균형이 아니게 만듦
이렇게 해야 "필터링해서 집계하면 진짜로 신호를 찾아내는지"를
의미 있게 검증할 수 있음.

[실행 환경 고지] 네트워크 차단으로 실제 Steam API 호출 불가.
fetch_reviews_from_api()가 실제 사용 시 교체할 함수.
"""

import sqlite3
import requests
import time
import random

DB_PATH = "/home/claude/palworld_reviews.db"
APP_ID = 1623730


def fetch_reviews_from_api(app_id, num_pages=10, language="koreana"):
    """실제 사용 시 이 함수로 교체 — Steam 공식 리뷰 API(키 불필요)"""
    reviews, cursor = [], "*"
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    for _ in range(num_pages):
        params = {"json": 1, "filter": "recent", "language": language,
                  "num_per_page": 100, "cursor": cursor}
        data = requests.get(url, params=params, timeout=10).json()
        if not data.get("reviews"):
            break
        for r in data["reviews"]:
            reviews.append((r["review"], int(r["voted_up"]), r["timestamp_created"]))
        cursor = data.get("cursor", cursor)
        time.sleep(1)
    return reviews


# --- 카테고리별 문구 재료 (긍정/부정 각각 여러 변형) ---
CATEGORY_PHRASES = {
    "위치재배치": {
        "true_positive_rate": 0.68,  # 연구자만 아는 '숨겨진 정답'
        "keyword": "위치",
        "positive": ["필드보스 위치가 바뀌어서 탐색하는 맛이 다시 생겼어요",
                     "보스 위치 재배치 덕분에 루트를 새로 짜는 재미가 있음",
                     "위치가 달라지니 익숙했던 동선이 리프레시된 느낌",
                     "재배치 덕분에 루트를 다시 짜야 해서 신선했음",
                     "익숙했던 루트가 안 통해서 오히려 즐거웠음"],
        "negative": ["보스 위치 바뀐거 그냥 헷갈리기만 함",
                     "위치 재배치가 불편함만 늘렸다고 봄",
                     "예전 위치가 더 나았는데 왜 바꿨는지 모르겠음",
                     "재배치 때문에 루트 다시 짜기 귀찮음"],
    },
    "테크트리순서": {
        "true_positive_rate": 0.42,
        "keyword": "테크트리",
        "positive": ["테크트리 순서 재구성이 고민하는 재미를 줌",
                     "테크트리 바뀐 뒤로 선택의 폭이 넓어진 기분"],
        "negative": ["테크트리 순서 때문에 진행이 꼬여서 스트레스",
                     "테크트리 재료 요구량이 이상해져서 헷갈림",
                     "테크트리 개편 후 뭘 먼저 해야할지 모르겠음",
                     "예전 테크트리가 더 직관적이었음"],
    },
    "밸런스난이도": {
        "true_positive_rate": 0.33,
        "keyword": "밸런스",
        "positive": ["밸런스 조정 덕분에 진행이 자연스러워짐"],
        "negative": ["밸런스가 계속 어려워지기만 해서 피곤함",
                     "난이도 밸런스 패치 이후로 그라인딩이 심해짐",
                     "밸런스 변경이 과했다고 생각함",
                     "밸런스 때문에 초반부터 너무 빡빡함"],
    },
}

UNRELATED_PHRASES = {
    "true_positive_rate": 0.55,
    "positive": ["그래픽도 좋고 사운드도 좋아요", "친구랑 같이 하니 정말 재밌어요",
                 "신규 지역 볼거리가 많아서 좋습니다", "협동 콘텐츠가 알차요"],
    "negative": ["버그가 많아요 최적화 필요합니다", "가격 대비 콘텐츠가 부족해요",
                 "서버 렉이 심해요", "로딩 시간이 너무 깁니다"],
}


def generate_realistic_reviews(n_total=3000, seed=42):
    rng = random.Random(seed)
    category_share = {"위치재배치": 0.15, "테크트리순서": 0.15, "밸런스난이도": 0.15, "무관": 0.55}
    rows = []
    for _ in range(n_total):
        roll = rng.random()
        cum = 0
        chosen = "무관"
        for cat, share in category_share.items():
            cum += share
            if roll < cum:
                chosen = cat
                break

        if chosen == "무관":
            true_pos_rate = UNRELATED_PHRASES["true_positive_rate"]
            phrases = UNRELATED_PHRASES
        else:
            true_pos_rate = CATEGORY_PHRASES[chosen]["true_positive_rate"]
            phrases = CATEGORY_PHRASES[chosen]

        voted_up = 1 if rng.random() < true_pos_rate else 0
        text = rng.choice(phrases["positive"] if voted_up else phrases["negative"])
        rows.append((text, voted_up, 1752000000 + rng.randint(0, 500000)))
    return rows


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS reviews")
cur.execute("CREATE TABLE reviews (review_text TEXT, voted_up INTEGER, timestamp_created INTEGER)")

rows = generate_realistic_reviews()
cur.executemany("INSERT INTO reviews VALUES (?,?,?)", rows)
conn.commit()

count = cur.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
overall_pos = cur.execute("SELECT AVG(voted_up) FROM reviews").fetchone()[0]
print(f"DB 생성 완료: {DB_PATH}")
print(f"적재된 리뷰 수: {count} (테스트용, 카테고리별 내재 신호 포함)")
print(f"전체 긍정 비율(검증용 실제값): {overall_pos:.1%}")
conn.close()
