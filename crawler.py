#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
  인디스워크(IN THIS WORK) 데이터분석 채용공고 크롤러
  https://inthiswork.com/data
============================================================
  수집 항목: 회사명, 직무명, 고용형태, 근무지역, 급여,
             근무기간, 요구스킬, 공고 URL
  실행 방법: python crawler.py
  결과 파일: inthiswork_data_jobs.csv
============================================================
"""

import re
import time
import csv
import logging
from dataclasses import dataclass, fields, asdict
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────
BASE_URL   = "https://inthiswork.com"
LIST_URL   = "https://inthiswork.com/data"          # 데이터분석 카테고리
TOTAL_PAGES = 13                                    # 전체 페이지 수 (변경 시 수정)
OUTPUT_CSV = "inthiswork_data_jobs.csv"
DELAY_SEC  = 3.0    # 요청 간 딜레이 (429 방지용으로 늘림)
TIMEOUT    = 15     # 요청 타임아웃(초)
RETRY_MAX  = 3      # 429 발생 시 재시도 횟수
RETRY_WAIT = 10     # 재시도 전 대기(초)

# 요구 스킬 키워드 사전 (매칭 순서 중요 — 긴 것 먼저)
SKILL_KEYWORDS = [
    "데이터 파이프라인", "데이터 분석", "머신러닝", "딥러닝",
    "시각화", "A/B 테스트", "A/B테스트",
    "Python", "SQL", "R언어", "Tableau", "Power BI", "Excel",
    "통계", "Spark", "Hadoop", "Airflow", "dbt", "ETL",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "Looker",
    "BigQuery", "Redshift", "MySQL", "PostgreSQL", "MongoDB",
    "ElasticSearch", "AWS", "GCP", "Azure", "EDA",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────────────────
@dataclass
class JobPosting:
    company:          str = ""
    position:         str = ""
    employment_type:  str = ""   # 인턴 / 신입 / 경력 / 계약직 / 정규직
    location:         str = ""
    city:             str = ""   # 서울 / 경기 / 부산 …
    duration:         str = ""   # 근무기간 (인턴의 경우)
    salary:           str = ""
    skills:           str = ""   # 쉼표 구분
    skill_count:      int = 0
    company_size:     str = ""   # 대기업 / 스타트업 / 중견기업 / 외국계
    position_category: str = ""  # 데이터분석가 / 데이터사이언티스트 / …
    url:              str = ""


# ──────────────────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────────────────
def get_soup(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    """URL을 가져와 BeautifulSoup 객체로 반환. 429 시 재시도, 실패 시 None."""
    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 429:
                wait = RETRY_WAIT * attempt
                log.warning("429 Too Many Requests — %d초 대기 후 재시도 (%d/%d)", wait, attempt, RETRY_MAX)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            log.warning("요청 실패: %s → %s", url, e)
            if attempt < RETRY_MAX:
                time.sleep(RETRY_WAIT)
    return None


def extract_field(text: str, *patterns: str) -> str:
    """본문 텍스트에서 정규식 패턴으로 필드 값 추출."""
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            # 첫 번째 캡처 그룹 반환, 없으면 전체 매칭
            val = (m.group(1) if m.lastindex else m.group()).strip()
            # 불필요한 후행 텍스트 제거 (다음 줄까지 잘라냄)
            val = val.split("\n")[0].strip()
            if len(val) > 3:
                return val[:120]
    return ""


def classify_employment(text: str) -> str:
    if re.search(r"인턴|Intern", text, re.I): return "인턴"
    if re.search(r"신입|전환형|공채", text):    return "신입"
    if re.search(r"정규직|Regular",  text):    return "정규직"
    if re.search(r"계약직|Contract", text, re.I): return "계약직"
    if re.search(r"경력|Career",     text, re.I): return "경력"
    return ""


def classify_city(text: str) -> str:
    mapping = {
        "서울": r"서울",
        "경기": r"경기|판교|수원|성남|분당|광교|용인|안양|평촌",
        "인천": r"인천",
        "부산": r"부산",
        "대전": r"대전",
        "대구": r"대구",
        "광주": r"광주",
        "제주": r"제주",
        "원격": r"원격|재택|Remote",
    }
    for city, pattern in mapping.items():
        if re.search(pattern, text):
            return city
    return "기타"


_BIG_COMPANIES = [
    "삼성", "현대", "LG", "SK텔레콤", "카카오", "네이버", "롯데",
    "포스코", "KT", "신한", "하나은행", "우리은행", "KB", "IBK",
    "한국전력", "POSCO", "CJ", "LX인터내셔널", "42dot",
]
_MID_COMPANIES  = ["KMAC", "한국전파", "코스맥스", "이마트", "GS리테일"]
_FOREIGN_COMPANIES = ["Ackerton", "PTKOREA", "McKinsey", "BCG", "Deloitte"]

def classify_company_size(company: str) -> str:
    if any(b in company for b in _BIG_COMPANIES):     return "대기업"
    if any(m in company for m in _MID_COMPANIES):     return "중견기업"
    if any(f in company for f in _FOREIGN_COMPANIES): return "외국계"
    return "스타트업"


def classify_position_category(position: str) -> str:
    p = position.lower()
    if re.search(r"데이터 ?분석|data anal|analyst",      p): return "데이터분석가"
    if re.search(r"사이언티스트|scientist|ml engineer",   p): return "데이터사이언티스트"
    if re.search(r"엔지니어|engineer|pipeline|etl|dba",  p): return "DE/ML엔지니어"
    if re.search(r"기획|pm |po |product|전략|planning",   p): return "기획/전략"
    if re.search(r"리서치|research|컨설",                  p): return "리서치/컨설팅"
    return "기타"


def extract_skills(text: str) -> list[str]:
    found = []
    for kw in SKILL_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw)
    # "R언어" 정규화
    normalized = ["R" if s == "R언어" else s for s in found]
    return list(dict.fromkeys(normalized))  # 중복 제거 (순서 유지)


# ──────────────────────────────────────────────────────────
# 목록 페이지 크롤링: 공고 URL + 기본 정보 수집
# ──────────────────────────────────────────────────────────
def collect_job_urls(session: requests.Session) -> list[dict]:
    """
    인디스워크 데이터분석 카테고리 전체 페이지를 순회해
    공고 URL과 회사명·직무명을 수집합니다.
    """
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, TOTAL_PAGES + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}/?paged1={page}"
        log.info("목록 수집 중: 페이지 %d/%d — %s", page, TOTAL_PAGES, url)

        soup = get_soup(url, session)
        if not soup:
            continue

        # 공고 링크: /archives/숫자 패턴
        for a_tag in soup.find_all("a", href=re.compile(r"/archives/\d+")):
            href = a_tag.get("href", "")
            full_url = href if href.startswith("http") else urljoin(BASE_URL, href)

            if full_url in seen_urls:
                continue

            title = a_tag.get_text(strip=True)
            if "｜" not in title or len(title) < 5:
                continue  # 회사명｜직무명 형식이 아닌 링크 제외

            parts = title.split("｜", 1)
            all_jobs.append({
                "url":      full_url,
                "company":  parts[0].strip(),
                "position": parts[1].strip() if len(parts) > 1 else title,
            })
            seen_urls.add(full_url)

        time.sleep(DELAY_SEC)

    log.info("총 %d개 공고 URL 수집 완료", len(all_jobs))
    return all_jobs


# ──────────────────────────────────────────────────────────
# 상세 페이지 크롤링: 세부 정보 추출
# ──────────────────────────────────────────────────────────
def parse_detail(soup: BeautifulSoup, base: dict) -> JobPosting:
    """상세 페이지 soup에서 JobPosting을 파싱합니다."""
    content = soup.find(class_=re.compile(r"entry-content|post-content|fusion-post-content"))
    text = content.get_text(separator="\n") if content else soup.get_text(separator="\n")

    # ── 기본 정보 ─────────────────────────────────────────
    position = base["position"]
    company  = base["company"]

    # ── 고용형태 ─────────────────────────────────────────
    emp_raw = extract_field(text,
        r"근무형태\s*[：:]\s*([^\n]+)",
        r"고용형태\s*[：:]\s*([^\n]+)",
    )
    employment_type = classify_employment(emp_raw or position)

    # ── 근무지역 ─────────────────────────────────────────
    location = extract_field(text,
        r"근무지역\s*[：:]\s*([^\n]+)",
        r"근무\s*위치\s*[：:]\s*([^\n]+)",
        r"주소\s*[：:]\s*([^\n]+)",
    )
    city = classify_city(location or text[:500])

    # ── 근무기간 ─────────────────────────────────────────
    duration = extract_field(text,
        r"근무기간\s*[：:]\s*([^\n]+)",
        r"계약기간\s*[：:]\s*([^\n]+)",
    )

    # ── 급여 ─────────────────────────────────────────────
    salary = extract_field(text,
        r"급여\s*[：:]\s*([^\n]+)",
        r"연봉\s*[：:]\s*([^\n]+)",
        r"월급\s*[：:]\s*([^\n]+)",
    )

    # ── 요구 스킬 ─────────────────────────────────────────
    skills = extract_skills(text)

    # ── 분류 ─────────────────────────────────────────────
    company_size      = classify_company_size(company)
    position_category = classify_position_category(position)

    return JobPosting(
        company=company,
        position=position,
        employment_type=employment_type,
        location=location,
        city=city,
        duration=duration,
        salary=salary,
        skills=", ".join(skills),
        skill_count=len(skills),
        company_size=company_size,
        position_category=position_category,
        url=base["url"],
    )


def crawl_details(job_list: list[dict], session: requests.Session) -> list[JobPosting]:
    """상세 페이지를 순회해 JobPosting 리스트를 반환합니다."""
    results: list[JobPosting] = []
    total = len(job_list)

    for i, job in enumerate(job_list, 1):
        if i % 20 == 0 or i == 1:
            log.info("상세 수집 중: %d/%d", i, total)

        soup = get_soup(job["url"], session)
        if soup:
            results.append(parse_detail(soup, job))
        else:
            # 실패 시 기본 정보만 저장
            results.append(JobPosting(
                company=job["company"],
                position=job["position"],
                url=job["url"],
            ))
        time.sleep(DELAY_SEC)

    log.info("상세 수집 완료: %d건", len(results))
    return results


# ──────────────────────────────────────────────────────────
# CSV 저장
# ──────────────────────────────────────────────────────────
_COLUMN_KO = {
    "company":           "회사명",
    "position":          "직무/포지션",
    "employment_type":   "고용형태",
    "location":          "근무지역(상세)",
    "city":              "근무지역(도시)",
    "duration":          "근무기간",
    "salary":            "급여",
    "skills":            "요구스킬",
    "skill_count":       "스킬수",
    "company_size":      "기업규모",
    "position_category": "직무카테고리",
    "url":               "공고URL",
}

def save_csv(postings: list[JobPosting], path: str) -> None:
    field_names = [f.name for f in fields(JobPosting)]
    ko_headers  = [_COLUMN_KO.get(f, f) for f in field_names]

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:  # BOM: Excel 호환
        writer = csv.DictWriter(fp, fieldnames=field_names)
        fp.write(",".join(ko_headers) + "\n")  # 한글 헤더 먼저 작성
        for p in postings:
            writer.writerow(asdict(p))

    log.info("CSV 저장 완료: %s (%d행)", path, len(postings))


# ──────────────────────────────────────────────────────────
# 통계 출력
# ──────────────────────────────────────────────────────────
def print_summary(postings: list[JobPosting]) -> None:
    from collections import Counter

    print("\n" + "=" * 55)
    print("  📊 수집 결과 요약")
    print("=" * 55)
    print(f"  총 공고 수:        {len(postings):,}건")

    def top(key: str, n=5) -> str:
        c = Counter(getattr(p, key) for p in postings if getattr(p, key))
        return "  /  ".join(f"{k}({v})" for k, v in c.most_common(n))

    print(f"  고용형태 TOP 5:    {top('employment_type')}")
    print(f"  도시 TOP 5:        {top('city')}")
    print(f"  기업규모:          {top('company_size', 4)}")
    print(f"  직무카테고리:      {top('position_category', 5)}")

    skill_counter: Counter = Counter()
    for p in postings:
        for s in p.skills.split(", "):
            if s.strip():
                skill_counter[s.strip()] += 1
    print("  요구스킬 TOP 10:   " +
          "  ".join(f"{k}({v})" for k, v in skill_counter.most_common(10)))

    with_salary = sum(1 for p in postings if p.salary)
    avg_skills  = sum(p.skill_count for p in postings) / max(len(postings), 1)
    print(f"  급여 공개 공고:    {with_salary}건 ({with_salary/len(postings)*100:.1f}%)")
    print(f"  평균 요구 스킬:    {avg_skills:.1f}개")
    print("=" * 55 + "\n")


# ──────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────
def main() -> None:
    log.info("크롤링 시작: %s", LIST_URL)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1단계: 목록 페이지에서 공고 URL 수집
    job_list = collect_job_urls(session)
    if not job_list:
        log.error("공고를 수집하지 못했습니다. 사이트 구조가 변경되었을 수 있습니다.")
        return

    # 2단계: 상세 페이지 크롤링
    postings = crawl_details(job_list, session)

    # 3단계: CSV 저장
    save_csv(postings, OUTPUT_CSV)

    # 4단계: 요약 출력
    print_summary(postings)

    log.info("완료! 결과 파일: %s", OUTPUT_CSV)


if __name__ == "__main__":
    main()
