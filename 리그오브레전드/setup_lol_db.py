"""
[역할 구분 명시]
이 스크립트는 '데이터를 만들어서 DB에 적재'하는 역할만 함(Python).
실제 분석 로직(포지션+라인전 시간대별 그룹 기준선, Z-score, 트롤
탐지 판정)은 전부 별도의 lol_troll_detection.sql 파일 안에 순수
SQL로 작성됨. 포트폴리오에서 보여주고자 하는 건 이 SQL 파일 쪽임.

[데이터 고지] 실제 Riot Timeline API 접근이 불가한 환경이라 가상
데이터 사용. 실제 사용 시 이 스크립트의 데이터 생성 부분만 실제
API 호출로 교체.
"""

import sqlite3
import numpy as np

np.random.seed(42)
DB_PATH = "/home/claude/lol_matches.db"
LANE_PHASE_CUTOFF = 900  # 15분(초) — 라인전이 사실상 끝나는 시점(가정)


def generate_mock_death_events(n_players=500, deaths_per_player=8):
    positions = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
    # 포지션별 '적진에서 죽는 게 정상인' 기준 확률(도메인 지식 기반 가정)
    base_enemy_death_rate = {"TOP": 0.20, "JUNGLE": 0.35, "MID": 0.20, "ADC": 0.08, "SUPPORT": 0.30}

    rows = []
    for pid in range(n_players):
        position = np.random.choice(positions)
        is_troll = pid < n_players * 0.03
        for _ in range(deaths_per_player):
            game_time = np.random.uniform(60, 1800)
            rate = base_enemy_death_rate[position]
            if position in ["TOP", "MID"] and game_time < LANE_PHASE_CUTOFF:
                rate *= 0.3
            if is_troll:
                rate = min(rate + 0.35, 0.95)
            died_in_enemy_territory = int(np.random.random() < rate)
            rows.append((pid, position, float(game_time), died_in_enemy_territory, int(is_troll)))
    return rows


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS death_events")
cur.execute("""
    CREATE TABLE death_events (
        player_id INTEGER,
        position TEXT,
        game_time REAL,
        died_in_enemy_territory INTEGER,
        is_troll_actual INTEGER  -- 검증용 정답 라벨(실제 서비스에는 없는 컬럼)
    )
""")
rows = generate_mock_death_events()
cur.executemany("INSERT INTO death_events VALUES (?,?,?,?,?)", rows)
conn.commit()

count = cur.execute("SELECT COUNT(*) FROM death_events").fetchone()[0]
print(f"DB 생성 완료: {DB_PATH}")
print(f"적재된 행 수: {count}")
conn.close()
