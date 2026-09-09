"""
lol_troll_detection.sql을 실행하고 결과를 출력하는 러너.
[역할 구분] 이 스크립트는 '실행 및 출력'만 담당하며, 분석 로직은
전혀 포함하지 않음 — 전부 .sql 파일 안에 작성되어 있음.
"""
import sqlite3

conn = sqlite3.connect("/home/claude/lol_matches.db")
cur = conn.cursor()

with open("/home/claude/lol_troll_detection.sql", "r") as f:
    sql_script = f.read()

# executescript로 VIEW 생성 + 전체 SELECT까지 한 번에 안전하게 실행
# (이전 버전의 '문자열을 세미콜론으로 직접 나눠 실행'하던 방식이
#  오류(view already exists)의 원인이었음 — executescript는 SQLite가
#  스크립트 전체를 표준 방식으로 파싱해 실행하므로 이 문제가 없음)
cur.executescript(sql_script)
conn.commit()

# executescript는 마지막 SELECT 결과만 커서에 남기므로, 각 SELECT를
# 결과 확인을 위해 다시 한 번씩 개별 실행
queries = [
    ("[1] 그룹별 적진 사망 기준선", """
        SELECT player_group, ROUND(group_mean,3) AS 평균_적진사망비율, ROUND(group_std,3) AS 표준편차
        FROM group_baseline ORDER BY group_mean
    """),
    ("[2] 탐지 성능", """
        SELECT
            SUM(is_troll_actual) AS 실제_트롤_수,
            SUM(flagged_suspect) AS 탐지된_의심유저_수,
            SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END) AS TP,
            SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=0 THEN 1 ELSE 0 END) AS FP,
            SUM(CASE WHEN flagged_suspect=0 AND is_troll_actual=1 THEN 1 ELSE 0 END) AS FN,
            ROUND(1.0*SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END)/NULLIF(SUM(flagged_suspect),0),3) AS 정밀도,
            ROUND(1.0*SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END)/NULLIF(SUM(is_troll_actual),0),3) AS 재현율
        FROM flagged_players
    """),
    ("[3] 그룹별 의심유저 탐지 비율", """
        SELECT player_group, COUNT(*) AS 전체_유저수, SUM(flagged_suspect) AS 의심유저수,
               ROUND(100.0*SUM(flagged_suspect)/COUNT(*),1) AS 탐지비율_퍼센트
        FROM flagged_players GROUP BY player_group ORDER BY 탐지비율_퍼센트 DESC
    """),
    ("[4] Z-score 상위 10명", """
        SELECT player_id, player_group, ROUND(enemy_death_rate,3) AS 적진사망비율,
               ROUND(z_score,2) AS Z점수, flagged_suspect
        FROM flagged_players ORDER BY z_score DESC LIMIT 10
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
