# 📊 데이터분석 채용시장 분석 파이프라인

> **인디스워크(IN THIS WORK)** 데이터분석 직무 채용공고 317건 전수 수집 · 분석 · 시각화 포트폴리오

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 수집 출처 | [inthiswork.com](https://inthiswork.com/data) — 데이터분석 카테고리 |
| 수집 기간 | 2026년 3월 22일 |
| 수집 공고 수 | **317건** (13페이지 전수) |
| 분석 도구 | Python · SQL · Jupyter · MySQL · reportlab · Chart.js |

---

## 🔑 핵심 인사이트

- **Python(37.5%) · SQL(31.5%)** 이 3대 필수 스킬 형성
- **데이터사이언티스트** 수요(28.7%)가 분석가(14.5%)를 2배 초과
- **스타트업**이 채용의 87.7% 차지 — 업스테이지, 토스, 카카오 계열 선두
- **서울 집중** 79.5% (수도권 합산 86.8%)
- 신입·인턴 합산 **30.6%** — 진입 기회 존재

---

## 🗂️ 파일 구조

```
job-market-analytics-pipeline/
├── crawler.py               # 인디스워크 채용공고 크롤러 (재시도·딜레이 포함)
├── analysis.ipynb           # 탐색적 데이터 분석 (EDA) 노트북
├── schema.sql               # MySQL DB 스키마 (4개 테이블)
├── inthiswork_data_jobs.csv # 수집 원본 데이터
├── dashboard.html           # 인터랙티브 대시보드 (Chart.js)
├── flowchart.html           # 프로젝트 논리 흐름도
├── report.pdf               # 분석 결과 PDF 보고서
├── report.docx              # 분석 결과 Word 보고서
├── chart_skills.png         # 요구 스킬 TOP 20 차트
├── chart_skill_groups.png   # 스킬 그룹별 분포 차트
├── chart_structure.png      # 직무·고용형태 분포 차트
├── chart_geo_company.png    # 지역·기업규모 분포 차트
├── .env.example             # 환경 변수 예시 (DB 연결 정보)
└── README.md
```

---

## ⚙️ 실행 방법

### 1. 환경 설정
```bash
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt    # 또는 아래 패키지 개별 설치
```

필요 패키지: `requests`, `beautifulsoup4`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `sqlalchemy`, `pymysql`, `cryptography`, `koreanize-matplotlib`, `reportlab`

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일에 DB 접속 정보 입력
```

### 3. 크롤링 실행
```bash
python crawler.py
```

### 4. 분석 실행
```bash
jupyter notebook analysis.ipynb
```

---

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

---

## 🗃️ DB 스키마

MySQL 기반 4개 테이블 구조:

- `company` — 기업 정보 (이름, 규모, 유형)
- `job_posting` — 채용공고 (제목, 직무, 지역, 고용형태, 급여)
- `job_skill` — 공고별 요구 스킬
- `crawl_log` — 크롤링 이력

```bash
mysql -u root -p < schema.sql
```

---

## 📈 주요 분석 결과

### 요구 스킬 TOP 5
| 순위 | 스킬 | 건수 | 비율 |
|------|------|------|------|
| 1 | Python | 119 | 37.5% |
| 2 | 데이터 분석 | 108 | 34.1% |
| 3 | SQL | 100 | 31.5% |
| 4 | 머신러닝 | 49 | 15.5% |
| 5 | 딥러닝 | 47 | 14.8% |

### 취업 전략 요약
1. **Python + SQL 필수화** — 기본 중의 기본
2. **통계 + 시각화** — 분석 포지션 필수 역량
3. **PyTorch** — ML 생태계 주류 (TensorFlow보다 우선)
4. **Airflow + 클라우드** — DE 방향 핵심 스택
5. **스타트업 타겟** — 채용 87.7%가 스타트업

---

## ⚠️ 데이터 한계

- 고용형태 미표기 57.7% (분류 정확도 한계)
- 급여 공개율 18.0% (급여 분석 불가)
- 2026년 3월 특정 시점 스냅샷 (계절적 편향 가능)
- 신입·주니어 중심 플랫폼 특성상 시니어 포지션 과소 표현

---

*본 프로젝트는 포트폴리오 목적으로 작성되었습니다.*
*데이터 출처: [inthiswork.com](https://inthiswork.com) · 분석 기준일: 2026년 3월 22일*
