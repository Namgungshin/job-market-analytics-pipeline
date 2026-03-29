## ⚙️ ETL 파이프라인 구조

본 프로젝트는 **Extract → Transform → Load** 3단계 ETL 파이프라인으로 설계되었습니다.

### Extract — 원천 데이터 추출
- `crawler.py`를 통해 인디스워크(inthiswork.com) 데이터분석 카테고리 전체 13페이지 크롤링
- 재시도 로직(최대 3회) 및 요청 딜레이(3초)로 안정적인 수집
- 수집 항목: 회사명, 직무명, 고용형태, 근무지역, 급여, 요구스킬, 공고 URL
- 수집 결과: 317건 원본 데이터 → `inthiswork_data_jobs.csv`

### Transform — 정제 및 가공
- 고용형태 정규화: 비정형 텍스트 → 인턴/신입/정규직/계약직/경력 분류
- 지역 정규화: 상세 주소 → 도시 단위 분류 (서울/경기/부산 등)
- 스킬 태깅: 37개 키워드 사전 기반 매칭 및 중복 제거
- 기업규모 분류: 대기업/중견기업/외국계/스타트업
- 직무 카테고리 분류: 데이터분석가/데이터사이언티스트/DE·ML엔지니어 등
- 탐색적 분석(EDA): `analysis.ipynb`에서 집계·시각화 수행

### Load — 적재 및 서빙
- MySQL 기반 4개 Raw 테이블에 정제 데이터 적재 (`schema.sql`)
- 분석가·PM이 바로 활용할 수 있는 **5개 마트 테이블** 생성 (`mart_tables.sql`)

---

## 🗃️ 데이터 계층 구조

```
Raw Layer       →    Mart Layer
──────────────       ──────────────────────────────────
company              mart_skill_demand        (스킬 수요 순위)
job_posting    →     mart_job_summary         (직무·지역·기업규모 집계)
job_skill            mart_skill_by_position   (포지션별 Top 스킬)
crawl_log            mart_entry_level_postings(신입·인턴 공고 필터)
                     mart_company_hiring_volume(기업별 채용 활성도)
```

마트 테이블은 `CREATE OR REPLACE VIEW`로 정의되어, Raw 테이블 업데이트 시 자동으로 최신 상태를 반영합니다.
