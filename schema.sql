-- ============================================================
-- 📦 Raw Layer 스키마 (job-market-analytics-pipeline)
-- DB: MySQL 8.0+
-- 테이블: company, job_posting, job_skill, crawl_log
-- ============================================================

CREATE DATABASE IF NOT EXISTS job_market
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE job_market;

-- ──────────────────────────────────────────────────────────
-- 1. crawl_log  — 크롤링 실행 이력
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crawl_log (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    crawled_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_url  VARCHAR(255)    NOT NULL COMMENT '크롤링 대상 URL',
    total_pages TINYINT         NOT NULL DEFAULT 13,
    total_rows  SMALLINT        NOT NULL DEFAULT 0,
    status      ENUM('success','partial','failed') NOT NULL DEFAULT 'success',
    note        TEXT,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────────────────────
-- 2. company  — 기업 마스터
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS company (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    company_name    VARCHAR(120)    NOT NULL,
    company_size    ENUM('대기업','중견기업','외국계','스타트업')
                                    NOT NULL DEFAULT '스타트업',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_company_name (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────────────────────
-- 3. job_posting  — 채용공고 (핵심 테이블)
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_posting (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    company_id          INT UNSIGNED    NOT NULL,
    crawl_log_id        INT UNSIGNED    NOT NULL,
    position            VARCHAR(200)    NOT NULL            COMMENT '직무/포지션명',
    position_category   ENUM(
                            '데이터분석가',
                            '데이터사이언티스트',
                            'DE/ML엔지니어',
                            '기획/전략',
                            '리서치/컨설팅',
                            '기타'
                        )               NOT NULL DEFAULT '기타',
    employment_type     ENUM('인턴','신입','정규직','계약직','경력')
                                        NULL     DEFAULT NULL,
    city                VARCHAR(30)     NULL                COMMENT '근무 도시',
    location            VARCHAR(255)    NULL                COMMENT '근무지역 상세',
    duration            VARCHAR(100)    NULL                COMMENT '근무기간',
    salary              VARCHAR(100)    NULL                COMMENT '급여 원문',
    skill_count         TINYINT         NOT NULL DEFAULT 0,
    url                 VARCHAR(512)    NOT NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_url (url(255)),
    KEY idx_company     (company_id),
    KEY idx_crawl_log   (crawl_log_id),
    KEY idx_category    (position_category),
    KEY idx_emp_type    (employment_type),
    KEY idx_city        (city),
    CONSTRAINT fk_posting_company
        FOREIGN KEY (company_id)     REFERENCES company(id)   ON DELETE CASCADE,
    CONSTRAINT fk_posting_crawl_log
        FOREIGN KEY (crawl_log_id)   REFERENCES crawl_log(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────────────────────
-- 4. job_skill  — 공고별 요구 스킬 (1:N)
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS job_skill (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    posting_id  INT UNSIGNED    NOT NULL,
    skill_name  VARCHAR(60)     NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_posting_skill (posting_id, skill_name),
    KEY idx_skill_name (skill_name),
    CONSTRAINT fk_skill_posting
        FOREIGN KEY (posting_id) REFERENCES job_posting(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
