-- ============================================================
-- 📦 마트 테이블 (Mart Layer)
-- raw 테이블: company, job_posting, job_skill, crawl_log
-- 마트 목적: 구성원(분석가, PM, 엔지니어)이 바로 쿼리 가능한
--            집계/가공 테이블 제공
-- 작성 기준: job-market-analytics-pipeline / MySQL
-- ============================================================


-- ──────────────────────────────────────────────────────────
-- 1. mart_skill_demand
--    스킬별 수요 현황 (요구 공고 수, 비율, 순위)
--    BI 툴에서 "어떤 스킬이 가장 많이 요구되는가" 바로 조회 가능
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW mart_skill_demand AS
SELECT
    js.skill_name,
    COUNT(DISTINCT js.job_id)                                     AS posting_count,
    ROUND(
        COUNT(DISTINCT js.job_id) * 100.0
        / (SELECT COUNT(*) FROM job_posting),
    1)                                                            AS demand_rate_pct,
    RANK() OVER (ORDER BY COUNT(DISTINCT js.job_id) DESC)        AS skill_rank
FROM job_skill js
GROUP BY js.skill_name
ORDER BY posting_count DESC;


-- ──────────────────────────────────────────────────────────
-- 2. mart_job_summary
--    직무/고용형태/지역/기업규모별 공고 현황 요약
--    "어떤 포지션이 얼마나 뽑는가" 한 눈에 파악
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW mart_job_summary AS
SELECT
    jp.position_category                                          AS 직무카테고리,
    jp.employment_type                                            AS 고용형태,
    jp.city                                                       AS 지역,
    c.company_size                                                AS 기업규모,
    COUNT(*)                                                      AS posting_count,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
    1)                                                            AS share_pct,
    ROUND(AVG(jp.skill_count), 1)                                AS avg_skill_count
FROM job_posting jp
JOIN company c ON jp.company_id = c.id
GROUP BY
    jp.position_category,
    jp.employment_type,
    jp.city,
    c.company_size
ORDER BY posting_count DESC;


-- ──────────────────────────────────────────────────────────
-- 3. mart_skill_by_position
--    직무 카테고리별 Top 스킬 조합
--    "DE/ML엔지니어는 어떤 스킬을 요구하는가" 분석
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW mart_skill_by_position AS
SELECT
    jp.position_category,
    js.skill_name,
    COUNT(*)                                                      AS posting_count,
    RANK() OVER (
        PARTITION BY jp.position_category
        ORDER BY COUNT(*) DESC
    )                                                             AS rank_within_category
FROM job_posting jp
JOIN job_skill js ON jp.id = js.job_id
GROUP BY jp.position_category, js.skill_name
ORDER BY jp.position_category, posting_count DESC;


-- ──────────────────────────────────────────────────────────
-- 4. mart_entry_level_postings
--    신입/인턴 공고만 필터링한 마트
--    취업 준비생 대상 진입 기회 파악용
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW mart_entry_level_postings AS
SELECT
    jp.id,
    c.company_name,
    c.company_size,
    jp.position,
    jp.position_category,
    jp.employment_type,
    jp.city,
    jp.salary,
    jp.skill_count,
    jp.url,
    cl.crawled_at
FROM job_posting jp
JOIN company c      ON jp.company_id = c.id
JOIN crawl_log cl   ON jp.crawl_log_id = cl.id
WHERE jp.employment_type IN ('인턴', '신입')
ORDER BY cl.crawled_at DESC;


-- ──────────────────────────────────────────────────────────
-- 5. mart_company_hiring_volume
--    기업별 채용 공고 수 및 스킬 다양성 집계
--    "어떤 회사가 가장 활발히 채용하는가" 파악
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW mart_company_hiring_volume AS
SELECT
    c.company_name,
    c.company_size,
    COUNT(DISTINCT jp.id)                                         AS total_postings,
    COUNT(DISTINCT jp.position_category)                         AS position_variety,
    ROUND(AVG(jp.skill_count), 1)                                AS avg_skill_count,
    GROUP_CONCAT(DISTINCT jp.position_category ORDER BY jp.position_category) AS position_categories
FROM company c
JOIN job_posting jp ON c.id = jp.company_id
GROUP BY c.company_name, c.company_size
ORDER BY total_postings DESC;
