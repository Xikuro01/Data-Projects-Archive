"""lol_troll_detection_real.sql 실행 및 결과 출력 (실데이터 버전)"""
import sqlite3

conn = sqlite3.connect("/home/claude/lol_analytics.db")
cur = conn.cursor()

with open("/home/claude/lol_troll_detection_real.sql", "r") as f:
    sql_script = f.read()

cur.executescript(sql_script)
conn.commit()

queries = [
    ("[0] 유효 매치 수 / 제외된 매치", """
        SELECT
            (SELECT COUNT(DISTINCT match_id) FROM lol_death_events) AS 원본_매치수,
            (SELECT COUNT(*) FROM valid_matches) AS 유효_매치수
    """),
    ("[1] 그룹별 적진 사망 기준선 (실데이터)", """
        SELECT player_group, n_samples AS 표본수,
               ROUND(group_mean,3) AS 평균_적진사망비율, ROUND(group_std,3) AS 표준편차
        FROM group_baseline_real ORDER BY group_mean
    """),
    ("[2] Z-score 상위 10건", """
        SELECT match_id, player_id, player_group, n_deaths AS 데스수,
               ROUND(enemy_death_rate,3) AS 적진사망비율, ROUND(z_score,2) AS Z점수, flagged_suspect AS 의심여부
        FROM flagged_players_real ORDER BY z_score DESC LIMIT 10
    """),
    ("[3] 그룹별 의심 케이스 탐지 비율", """
        SELECT player_group, COUNT(*) AS 전체_표본수, SUM(flagged_suspect) AS 의심케이스수,
               ROUND(100.0*SUM(flagged_suspect)/COUNT(*),1) AS 탐지비율_퍼센트
        FROM flagged_players_real GROUP BY player_group ORDER BY 탐지비율_퍼센트 DESC
    """),
    ("[4] 고신뢰 의심 케이스 (데스 4건 이상 & Z-score > 2)", """
        SELECT match_id, player_id, player_group, n_deaths,
               ROUND(enemy_death_rate,3) AS 적진사망비율, ROUND(z_score,2) AS Z점수
        FROM flagged_players_real
        WHERE flagged_suspect=1 AND reliable_sample=1
        ORDER BY z_score DESC
    """),
]

for title, q in queries:
    print("=" * 70)
    print(title)
    print("=" * 70)
    cur.execute(q)
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall():
        print(row)
    print()

conn.close()
