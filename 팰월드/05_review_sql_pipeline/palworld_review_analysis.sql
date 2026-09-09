-- ======================================================================
-- 팰월드 1.0 리뷰 분석 — 카테고리별 구조변경 긍부정 + 통계적 유의성 검정
-- ======================================================================
-- 위치재배치/테크트리순서/밸런스난이도 3개 카테고리로 나눠, 각 카테고리를
-- 언급한 리뷰의 긍정비율이 전체 평균과 다른지 이표본 비율 z-검정으로 확인.
-- z = (p1-p2) / sqrt(p_pool*(1-p_pool)*(1/n1+1/n2)), |z|>1.96 → 유의미(95%)
-- (SQLite에 통계함수가 없어 공식을 직접 구현)
-- ======================================================================

DROP VIEW IF EXISTS overall_baseline;
CREATE VIEW overall_baseline AS
SELECT COUNT(*) AS n, SUM(voted_up) AS pos, AVG(voted_up)*1.0 AS pos_rate FROM reviews;

DROP VIEW IF EXISTS cat_location;
CREATE VIEW cat_location AS SELECT * FROM reviews WHERE review_text LIKE '%위치%';

DROP VIEW IF EXISTS cat_techtree;
CREATE VIEW cat_techtree AS SELECT * FROM reviews WHERE review_text LIKE '%테크트리%';

DROP VIEW IF EXISTS cat_balance;
CREATE VIEW cat_balance AS SELECT * FROM reviews WHERE review_text LIKE '%밸런스%';

DROP VIEW IF EXISTS cat_location_broad;
CREATE VIEW cat_location_broad AS
SELECT * FROM reviews WHERE review_text LIKE '%위치%' OR review_text LIKE '%재배치%' OR review_text LIKE '%루트%';

-- 카테고리별 요약 + z-검정 (한 번에 계산)
DROP VIEW IF EXISTS category_summary;
CREATE VIEW category_summary AS
WITH base AS (SELECT n, pos, pos_rate FROM overall_baseline),
cats AS (
    SELECT '위치재배치' AS category, COUNT(*) AS n, SUM(voted_up) AS pos, AVG(voted_up)*1.0 AS pos_rate FROM cat_location
    UNION ALL SELECT '테크트리순서', COUNT(*), SUM(voted_up), AVG(voted_up)*1.0 FROM cat_techtree
    UNION ALL SELECT '밸런스난이도', COUNT(*), SUM(voted_up), AVG(voted_up)*1.0 FROM cat_balance
)
SELECT
    cats.category                                                          AS 카테고리,
    cats.n                                                                 AS 표본수,
    ROUND(cats.pos_rate * 100, 1)                                          AS 긍정비율,
    ROUND((cats.pos_rate - base.pos_rate) * 100, 1)                        AS 차이_퍼센트포인트,
    ROUND((cats.pos_rate - base.pos_rate) / SQRT(
        ((cats.pos + base.pos)*1.0/(cats.n + base.n)) * (1 - (cats.pos + base.pos)*1.0/(cats.n + base.n))
        * (1.0/cats.n + 1.0/base.n)), 2)                                   AS z_score,
    CASE WHEN ABS((cats.pos_rate - base.pos_rate) / SQRT(
        ((cats.pos + base.pos)*1.0/(cats.n + base.n)) * (1 - (cats.pos + base.pos)*1.0/(cats.n + base.n))
        * (1.0/cats.n + 1.0/base.n))) > 1.96 THEN '유의미' ELSE '유의미X' END AS 판정
FROM cats, base
ORDER BY z_score;

-- 민감도 검증: 키워드를 넓히면 결과가 바뀌는지
DROP VIEW IF EXISTS sensitivity_check;
CREATE VIEW sensitivity_check AS
SELECT '좁은 키워드(위치만)' AS 버전, COUNT(*) AS 표본수, ROUND(AVG(voted_up)*100,1) AS 긍정비율 FROM cat_location
UNION ALL
SELECT '넓은 키워드(+재배치,루트)', COUNT(*), ROUND(AVG(voted_up)*100,1) FROM cat_location_broad;
