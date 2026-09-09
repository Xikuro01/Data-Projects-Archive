-- ======================================================================
-- 롤 사망 위치 기반 트롤 탐지 — 실제 Riot API 데이터 버전
-- ======================================================================
-- [가상 데이터 버전과의 차이]
-- 가상 데이터에서는 died_in_enemy_territory가 이미 0/1로 주어져 있었지만,
-- 실제 데이터는 death_x, death_y 좌표만 있음. 이 스크립트는 "좌표 → 적진
-- 사망 여부"를 실제로 계산하는, 원래 기획 의도(좌표 기반 판단)가 처음
-- 구현되는 지점임.
--
-- [팀 판별] 실제 데이터에는 팀 컬럼이 없어 participant_id(1~10) 기반으로
-- 판별. Riot Match-V5 API 관례상 1~5=블루팀(100), 6~10=레드팀(200)이며,
-- 이 데이터셋에서도 1~5의 평균 사망좌표합(x+y)이 6~10보다 유의하게
-- 낮아(자기 진영에 가깝게 죽는 경향) 이 관례와 일치함을 실측으로 확인함.
--
-- [적진 판정 기준] 넥서스 좌표는 데이터에 없어, 실제 Riot 매치 타임라인
-- 공개 맵 데이터(hextechdocs.dev)의 블루/레드 넥서스 타워 좌표를 사용해
-- 각 팀 베이스 위치를 근사함:
--   블루 베이스 ≈ (1962, 2038)  -- BLUE_TOP/BOT_NEXUS_TURRET 평균
--   레드 베이스 ≈ (12831, 12848) -- RED_TOP/BOT_NEXUS_TURRET 평균
-- 각 사망 지점이 "자기 베이스보다 적 베이스에 더 가까우면" 적진 사망으로 판정.
--
-- [분석 단위 수정] 가상 데이터 버전은 player_id 자체가 게임을 넘나드는
-- 고유 유저였지만, 실제 데이터의 player_id(1~10)는 매치마다 리셋되는
-- 자리번호(participant slot)일 뿐 동일 인물이 아님. 따라서 그룹핑 키를
-- (player_id, group)에서 (match_id, player_id, group)로 바꿔, "이 사람이
-- 여러 게임에서 반복적으로" 가 아니라 "이 사람이 이 한 게임에서" 이례적인가를
-- 보는 것으로 분석 프레임을 조정함 (README에 명시 필요).
--
-- [검증 방식 변경] 가상 데이터는 정답 라벨(is_troll_actual)로 정밀도/재현율을
-- 계산했지만, 실제 데이터엔 정답이 없음 — 이는 실전 트롤 탐지의 진짜 조건과
-- 동일함(비지도 이상탐지). 따라서 여기서는 상위 Z-score 유저 목록을 뽑아
-- 정성적으로 검토하는 방식으로 전환함.
-- ======================================================================

-- ----------------------------------------------------------------------
-- 0단계: 리메이크(조기 종료) 매치 제외 — 데스 이벤트 수가 비정상적으로
--        적은 매치는 정상 게임이 아닐 가능성이 높음 (예: 41초만에 게임 종료)
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS valid_matches;
CREATE VIEW valid_matches AS
SELECT match_id
FROM lol_death_events
GROUP BY match_id
HAVING COUNT(*) >= 10;   -- 임계값: 정상 게임 표본 대비 지나치게 적은 매치 컷

-- ----------------------------------------------------------------------
-- 1단계: 팀 판별 + 좌표 기반 적진 사망 계산 + 그룹(포지션+라인전여부) 정의
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS death_events_processed;
CREATE VIEW death_events_processed AS
SELECT
    e.match_id,
    e.player_id,
    e.position,
    e.game_time,
    e.death_x,
    e.death_y,
    CASE WHEN e.player_id <= 5 THEN 'BLUE' ELSE 'RED' END AS team_side,

    -- 자기 베이스까지의 거리
    CASE WHEN e.player_id <= 5
        THEN SQRT((e.death_x - 1962.0)*(e.death_x - 1962.0) + (e.death_y - 2038.0)*(e.death_y - 2038.0))
        ELSE SQRT((e.death_x - 12831.0)*(e.death_x - 12831.0) + (e.death_y - 12848.0)*(e.death_y - 12848.0))
    END AS dist_to_own_base,

    -- 적 베이스까지의 거리
    CASE WHEN e.player_id <= 5
        THEN SQRT((e.death_x - 12831.0)*(e.death_x - 12831.0) + (e.death_y - 12848.0)*(e.death_y - 12848.0))
        ELSE SQRT((e.death_x - 1962.0)*(e.death_x - 1962.0) + (e.death_y - 2038.0)*(e.death_y - 2038.0))
    END AS dist_to_enemy_base,

    -- 적 베이스가 자기 베이스보다 가까우면 적진 사망
    CASE WHEN (
        CASE WHEN e.player_id <= 5
            THEN SQRT((e.death_x - 12831.0)*(e.death_x - 12831.0) + (e.death_y - 12848.0)*(e.death_y - 12848.0))
            ELSE SQRT((e.death_x - 1962.0)*(e.death_x - 1962.0) + (e.death_y - 2038.0)*(e.death_y - 2038.0))
        END
        <
        CASE WHEN e.player_id <= 5
            THEN SQRT((e.death_x - 1962.0)*(e.death_x - 1962.0) + (e.death_y - 2038.0)*(e.death_y - 2038.0))
            ELSE SQRT((e.death_x - 12831.0)*(e.death_x - 12831.0) + (e.death_y - 12848.0)*(e.death_y - 12848.0))
        END
    ) THEN 1 ELSE 0 END AS died_in_enemy_territory,

    -- 그룹 정의: 가상 데이터 버전과 동일 로직, 실제 라벨(MIDDLE)에 맞게 조정
    CASE
        WHEN e.position IN ('TOP', 'MIDDLE') AND e.game_time < 900 THEN e.position || '-라인전'
        WHEN e.position IN ('TOP', 'MIDDLE') AND e.game_time >= 900 THEN e.position || '-라인전이후'
        ELSE e.position
    END AS player_group

FROM lol_death_events e
JOIN valid_matches v ON e.match_id = v.match_id;

-- ----------------------------------------------------------------------
-- 2단계: (매치, 플레이어) 단위로 적진 사망 비율 집계
--        ※ player_id는 매치마다 리셋되므로 match_id를 반드시 키에 포함
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS player_stats_real;
CREATE VIEW player_stats_real AS
SELECT
    match_id,
    player_id,
    player_group,
    AVG(died_in_enemy_territory * 1.0) AS enemy_death_rate,
    COUNT(*) AS n_deaths
FROM death_events_processed
GROUP BY match_id, player_id, player_group;

-- ----------------------------------------------------------------------
-- 3단계: 그룹별 기준선(평균/표준편차/표본수)
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS group_baseline_real;
CREATE VIEW group_baseline_real AS
SELECT
    player_group,
    COUNT(*) AS n_samples,
    AVG(enemy_death_rate) AS group_mean,
    SQRT(
        AVG(enemy_death_rate * enemy_death_rate) - AVG(enemy_death_rate) * AVG(enemy_death_rate)
    ) AS group_std
FROM player_stats_real
GROUP BY player_group;

-- ----------------------------------------------------------------------
-- 4단계: Z-score 계산 + 의심 케이스 판정
-- ----------------------------------------------------------------------
DROP VIEW IF EXISTS flagged_players_real;
CREATE VIEW flagged_players_real AS
SELECT
    ps.match_id,
    ps.player_id,
    ps.player_group,
    ps.n_deaths,
    ps.enemy_death_rate,
    gb.group_mean,
    gb.group_std,
    gb.n_samples AS group_n_samples,
    (ps.enemy_death_rate - gb.group_mean) / (CASE WHEN gb.group_std = 0 THEN 0.01 ELSE gb.group_std END) AS z_score,
    CASE
        WHEN (ps.enemy_death_rate - gb.group_mean)
             / (CASE WHEN gb.group_std = 0 THEN 0.01 ELSE gb.group_std END) > 2.0
        THEN 1 ELSE 0
    END AS flagged_suspect,

    -- [소표본 노이즈 방지] 데스 1~2건으로 100% 적진사망 찍는 경우가 흔해
    -- Z-score만으로는 오탐이 잦음 → 데스 4건 이상인 경우만 "신뢰 가능"으로 표시
    CASE WHEN ps.n_deaths >= 4 THEN 1 ELSE 0 END AS reliable_sample
FROM player_stats_real ps
JOIN group_baseline_real gb ON ps.player_group = gb.player_group;

-- ----------------------------------------------------------------------
-- 5단계: 결과 출력
-- ----------------------------------------------------------------------
SELECT '=== [1] 그룹별(포지션+라인전 여부) 적진 사망 기준선 (실데이터) ===' AS section;
SELECT player_group,
       n_samples AS 표본수,
       ROUND(group_mean, 3) AS 평균_적진사망비율,
       ROUND(group_std, 3)  AS 표준편차
FROM group_baseline_real
ORDER BY group_mean;

SELECT '=== [2] Z-score 상위 10건 (정성 검토 대상) ===' AS section;
SELECT match_id, player_id, player_group,
       n_deaths AS 데스수,
       ROUND(enemy_death_rate, 3) AS 적진사망비율,
       ROUND(z_score, 2) AS Z점수,
       flagged_suspect AS 의심여부
FROM flagged_players_real
ORDER BY z_score DESC
LIMIT 10;

SELECT '=== [3] 그룹별 의심 케이스 탐지 비율 ===' AS section;
SELECT
    player_group,
    COUNT(*) AS 전체_표본수,
    SUM(flagged_suspect) AS 의심케이스수,
    ROUND(100.0 * SUM(flagged_suspect) / COUNT(*), 1) AS 탐지비율_퍼센트
FROM flagged_players_real
GROUP BY player_group
ORDER BY 탐지비율_퍼센트 DESC;

SELECT '=== [4] 고신뢰 의심 케이스 (데스 4건 이상 & Z-score > 2) ===' AS section;
SELECT match_id, player_id, player_group, n_deaths,
       ROUND(enemy_death_rate, 3) AS 적진사망비율,
       ROUND(z_score, 2) AS Z점수
FROM flagged_players_real
WHERE flagged_suspect = 1 AND reliable_sample = 1
ORDER BY z_score DESC;
