-- ======================================================================
-- 롤 사망 위치 기반 트롤 탐지 (포지션+라인전 시간대 그룹, 순수 SQL 버전)
-- ======================================================================
-- [프로젝트 주도자 노트]
-- '적진 사망'을 전체 유저 기준 하나로 판단하지 않고, 포지션(및 탑/미드는
-- 라인전 여부)별로 서로 다른 정상 기준선과 비교함. 정글/서포터는
-- 원래 적진 사망이 잦고, 탑/미드는 라인전 이후에만 잦아지는 게 정상,
-- 원딜은 라인 제약이 커서 적진 사망 자체가 드묾 — 이 도메인 지식을
-- '그룹' 정의 하나로 압축해 SQL로 구현함.
--
-- SQLite에는 STDDEV 집계함수가 없어, 표준편차를 직접 계산하는 공식
-- (AVG(x^2) - AVG(x)^2의 제곱근)을 사용함.
--
-- 실행 방법: python3로 실행하거나, sqlite3 CLI가 있다면
--            sqlite3 lol_matches.db < lol_troll_detection.sql
-- ======================================================================

-- ----------------------------------------------------------------------
-- 1단계: 그룹 정의 — 포지션 + (탑/미드는 라인전 여부)를 하나의 라벨로
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS death_events_grouped;
CREATE VIEW death_events_grouped AS
SELECT
    player_id,
    position,
    game_time,
    died_in_enemy_territory,
    is_troll_actual,
    CASE
        WHEN position IN ('TOP', 'MID') AND game_time < 900 THEN position || '-라인전'
        WHEN position IN ('TOP', 'MID') AND game_time >= 900 THEN position || '-라인전이후'
        ELSE position
    END AS player_group
FROM death_events;

-- ----------------------------------------------------------------------
-- 2단계: 유저별(그룹별) 적진 사망 비율 집계
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS player_stats;
CREATE VIEW player_stats AS
SELECT
    player_id,
    player_group,
    AVG(died_in_enemy_territory * 1.0) AS enemy_death_rate,
    MAX(is_troll_actual)               AS is_troll_actual
FROM death_events_grouped
GROUP BY player_id, player_group;

-- ----------------------------------------------------------------------
-- 3단계: 그룹별 기준선(평균/표준편차) — 같은 그룹끼리만 비교
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS group_baseline;
CREATE VIEW group_baseline AS
SELECT
    player_group,
    AVG(enemy_death_rate) AS group_mean,
    -- 표준편차를 SQLite 기본함수만으로 직접 계산 (내장 STDDEV 없음)
    SQRT(
        AVG(enemy_death_rate * enemy_death_rate) - AVG(enemy_death_rate) * AVG(enemy_death_rate)
    ) AS group_std
FROM player_stats
GROUP BY player_group;

-- ----------------------------------------------------------------------
-- 4단계: Z-score 계산 및 의심유저 판정 (0으로 나누기 방지 포함)
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS flagged_players;
CREATE VIEW flagged_players AS
SELECT
    ps.player_id,
    ps.player_group,
    ps.enemy_death_rate,
    gb.group_mean,
    gb.group_std,
    (ps.enemy_death_rate - gb.group_mean) / (CASE WHEN gb.group_std = 0 THEN 0.01 ELSE gb.group_std END) AS z_score,
    ps.is_troll_actual,
    CASE
        WHEN (ps.enemy_death_rate - gb.group_mean)
             / (CASE WHEN gb.group_std = 0 THEN 0.01 ELSE gb.group_std END) > 2.0
        THEN 1 ELSE 0
    END AS flagged_suspect
FROM player_stats ps
JOIN group_baseline gb ON ps.player_group = gb.player_group;

-- ----------------------------------------------------------------------
-- 5단계: 그룹별 기준선 출력
-- ----------------------------------------------------------------------
SELECT '=== [1] 그룹별(포지션+라인전 여부) 적진 사망 기준선 ===' AS section;
SELECT player_group,
       ROUND(group_mean, 3) AS 평균_적진사망비율,
       ROUND(group_std, 3)  AS 표준편차
FROM group_baseline
ORDER BY group_mean;

-- ----------------------------------------------------------------------
-- 6단계: 탐지 성능 검증 (정밀도/재현율을 SQL 집계로 직접 계산)
-- ----------------------------------------------------------------------
SELECT '=== [2] 탐지 성능 (가상 정답 라벨 대비) ===' AS section;
SELECT
    SUM(is_troll_actual)                                                     AS 실제_트롤_수,
    SUM(flagged_suspect)                                                     AS 탐지된_의심유저_수,
    SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END) AS TP,
    SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=0 THEN 1 ELSE 0 END) AS FP,
    SUM(CASE WHEN flagged_suspect=0 AND is_troll_actual=1 THEN 1 ELSE 0 END) AS FN,
    ROUND(
        1.0 * SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(flagged_suspect), 0), 3
    ) AS 정밀도,
    ROUND(
        1.0 * SUM(CASE WHEN flagged_suspect=1 AND is_troll_actual=1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(is_troll_actual), 0), 3
    ) AS 재현율
FROM flagged_players;

-- ----------------------------------------------------------------------
-- 7단계: 그룹별 의심유저 탐지 비율
-- ----------------------------------------------------------------------
SELECT '=== [3] 그룹별 의심유저 탐지 비율 ===' AS section;
SELECT
    player_group,
    COUNT(*)                                          AS 전체_유저수,
    SUM(flagged_suspect)                               AS 의심유저수,
    ROUND(100.0 * SUM(flagged_suspect) / COUNT(*), 1)  AS 탐지비율_퍼센트
FROM flagged_players
GROUP BY player_group
ORDER BY 탐지비율_퍼센트 DESC;

-- ----------------------------------------------------------------------
-- 8단계: Z-score 상위 10명
-- ----------------------------------------------------------------------
SELECT '=== [4] Z-score 상위 10명 ===' AS section;
SELECT player_id, player_group,
       ROUND(enemy_death_rate, 3) AS 적진사망비율,
       ROUND(z_score, 2)          AS Z점수,
       flagged_suspect
FROM flagged_players
ORDER BY z_score DESC
LIMIT 10;
