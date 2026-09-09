"""palworld_review_analysis.sql 실행 및 결과 출력 (간결화 버전)."""
import sqlite3

conn = sqlite3.connect("/home/claude/palworld_reviews.db")
cur = conn.cursor()
cur.executescript(open("/home/claude/palworld_review_analysis.sql").read())
conn.commit()

# SQL에 정의된 뷰만 그대로 조회 — 쿼리문 중복 없음
views = ["overall_baseline", "category_summary", "sensitivity_check"]
titles = ["전체 베이스라인", "카테고리별 긍정비율 · z검정", "민감도 검증(키워드 범위)"]

for title, view in zip(titles, views):
    print(f"\n[{title}]")
    cur.execute(f"SELECT * FROM {view}")
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    for row in cur.fetchall():
        print(row)

conn.close()
