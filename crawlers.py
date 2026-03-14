"""지원사업 크롤러 모듈 - 4개 사이트 + startup-plus.kr API 크롤링"""

import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set
import json
import os
import re
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SEEN_FILE = os.path.join(DATA_DIR, "seen_posts.json")


@dataclass
class SupportPost:
    title: str
    url: str
    source: str
    deadline: str = ""
    organization: str = ""
    status: str = ""
    category: str = ""
    target: str = ""
    result_date: str = ""
    receipt_begin: str = ""


def load_seen_posts() -> set:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_posts(seen: set):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30), ssl=False) as resp:
            if resp.status == 200:
                return await resp.text()
            logger.warning(f"HTTP {resp.status} for {url}")
    except Exception as e:
        logger.error(f"Fetch error for {url}: {e}")
    return None


async def crawl_bizinfo(session: aiohttp.ClientSession) -> List[SupportPost]:
    """기업마당 (bizinfo.go.kr) 크롤링"""
    posts = []
    url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
    html = await fetch_page(session, url)
    if not html:
        return posts

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table tbody tr")

    for row in rows:
        cols = row.select("td")
        if len(cols) < 4:
            continue
        title_tag = row.select_one("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.bizinfo.go.kr" + href

        org = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        deadline = cols[3].get_text(strip=True) if len(cols) > 3 else ""
        status_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        category_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""

        posts.append(SupportPost(
            title=title,
            url=href,
            source="기업마당",
            organization=org,
            deadline=deadline,
            status=status_text,
            category=category_text,
            target="전체",
        ))

    logger.info(f"[기업마당] {len(posts)}건 크롤링 완료")
    return posts


async def crawl_kstartup(session: aiohttp.ClientSession) -> List[SupportPost]:
    """K-Startup (k-startup.go.kr) 크롤링"""
    posts = []
    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    html = await fetch_page(session, url)
    if not html:
        return posts

    soup = BeautifulSoup(html, "lxml")
    items = soup.select(".list_wrap .list_item, .tbl_list tbody tr, .announcement_list li")

    for item in items:
        title_tag = item.select_one("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.k-startup.go.kr" + href

        deadline_tag = item.select_one(".date, .period, td:last-child")
        deadline = deadline_tag.get_text(strip=True) if deadline_tag else ""

        org_tag = item.select_one(".org, .agency, td:nth-child(2)")
        org = org_tag.get_text(strip=True) if org_tag else ""

        status_tag = item.select_one(".status, .state, .badge")
        status_text = status_tag.get_text(strip=True) if status_tag else ""
        category_tag = item.select_one(".category, .cate, td:nth-child(3)")
        category_text = category_tag.get_text(strip=True) if category_tag else ""

        posts.append(SupportPost(
            title=title,
            url=href,
            source="K-Startup",
            organization=org,
            deadline=deadline,
            status=status_text,
            category=category_text,
            target="전체",
        ))

    logger.info(f"[K-Startup] {len(posts)}건 크롤링 완료")
    return posts


async def crawl_smtech(session: aiohttp.ClientSession) -> List[SupportPost]:
    """중소기업 기술개발사업 (smtech.go.kr) 크롤링"""
    posts = []
    url = "https://www.smtech.go.kr/front/ifg/no/notice02_list.do"
    html = await fetch_page(session, url)
    if not html:
        return posts

    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table tbody tr")

    for row in rows:
        cols = row.select("td")
        if len(cols) < 3:
            continue

        title_tag = row.select_one("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.smtech.go.kr" + href

        deadline = cols[-1].get_text(strip=True) if cols else ""

        status_tag = row.select_one(".status, .state, td:nth-child(2)")
        status_text = status_tag.get_text(strip=True) if status_tag else ""

        posts.append(SupportPost(
            title=title,
            url=href,
            source="중기부 기술개발",
            deadline=deadline,
            status=status_text,
            target="전체",
        ))

    logger.info(f"[중기부 기술개발] {len(posts)}건 크롤링 완료")
    return posts


async def crawl_sba(session: aiohttp.ClientSession) -> List[SupportPost]:
    """서울산업진흥원 (sba.seoul.kr) 크롤링"""
    posts = []
    url = "https://www.sba.seoul.kr/kr/sbcu400"
    html = await fetch_page(session, url)
    if not html:
        return posts

    soup = BeautifulSoup(html, "lxml")
    items = soup.select("table tbody tr, .board_list li, .list_wrap .item")

    for item in items:
        title_tag = item.select_one("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.sba.seoul.kr" + href

        deadline_tag = item.select_one(".date, td:last-child")
        deadline = deadline_tag.get_text(strip=True) if deadline_tag else ""

        status_tag = item.select_one(".status, .state, .badge")
        status = status_tag.get_text(strip=True) if status_tag else ""

        category_tag = item.select_one(".category, .cate")
        category_text = category_tag.get_text(strip=True) if category_tag else ""

        posts.append(SupportPost(
            title=title,
            url=href,
            source="서울산업진흥원",
            deadline=deadline,
            status=status,
            category=category_text,
            target="전체",
        ))

    logger.info(f"[서울산업진흥원] {len(posts)}건 크롤링 완료")
    return posts


def _extract_result_date(guide_html: str) -> str:
    """공고 HTML 본문에서 결과 발표일 추출"""
    if not guide_html:
        return ""
    text = BeautifulSoup(guide_html, "lxml").get_text()
    patterns = [
        r"(?:최종\s*)?결과\s*발표[:\s]*(\d{4}[\.\-/년]\s*\d{1,2}[\.\-/월]\s*\d{1,2}일?)",
        r"선정\s*결과[:\s]*(\d{4}[\.\-/년]\s*\d{1,2}[\.\-/월]\s*\d{1,2}일?)",
        r"합격\s*(?:자\s*)?발표[:\s]*(\d{4}[\.\-/년]\s*\d{1,2}[\.\-/월]\s*\d{1,2}일?)",
        r"발표\s*(?:예정)?[:\s]*(\d{4}[\.\-/년]\s*\d{1,2}[\.\-/월]\s*\d{1,2}일?)",
        r"결과\s*통보[:\s]*(\d{4}[\.\-/년]\s*\d{1,2}[\.\-/월]\s*\d{1,2}일?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


# 예비창업자 제외 카테고리 (입주기업 전용 등)
_EXCLUDE_CATEGORIES = {"RES", "MOV"}

# 예비창업자 관련 키워드
_PRE_STARTUP_KEYWORDS = [
    "예비창업", "예비 창업", "창업지원", "창업 지원",
    "액셀러레이팅", "교육", "멘토링",
]

# 사업계획서 기반 관심 키워드
_IDEA_KEYWORDS_STARTUP_PLUS = [
    "AI", "인공지능", "광고", "콘텐츠", "플랫폼",
    "마케팅", "스타트업", "창업", "디지털", "영상",
    "데이터", "딥러닝", "ICT", "SW", "소프트웨어",
    "미디어", "예비창업", "예비 창업",
]


async def crawl_startupplus(session: aiohttp.ClientSession) -> List[SupportPost]:
    """startup-plus.kr API를 통한 지원사업 크롤링"""
    posts = []
    api_url = "https://startup-plus.kr/api/project/list"

    for page in range(0, 5):  # 최대 5페이지
        try:
            params = {"size": 20, "page": page}
            async with session.get(
                api_url,
                params=params,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"startup-plus API HTTP {resp.status}")
                    break
                data = await resp.json()
        except Exception as e:
            logger.error(f"startup-plus API error: {e}")
            break

        if not data.get("result"):
            break

        contents = data.get("data", {}).get("contents", [])
        if not contents:
            break

        for item in contents:
            project_target = item.get("projectTarget", {})
            biz_category = item.get("businessCategory", {})
            target_code = project_target.get("code", "")
            category_code = biz_category.get("code", "")

            # 입주기업 전용 제외
            if category_code in _EXCLUDE_CATEGORIES:
                continue
            if target_code == "MOV":
                continue

            project_name = item.get("projectName", "")
            org_name = item.get("organizationName", "")
            portal_name = item.get("portalName", "")
            status_info = item.get("status", {})
            status_name = status_info.get("name", "")
            project_code = item.get("projectCode", "")
            guide_html = item.get("guide", "")

            receipt_end = item.get("receiptEndDate", "")
            receipt_begin = item.get("receiptBeginDate", "")

            # 날짜 포맷 정리
            deadline_str = ""
            if receipt_end:
                try:
                    dt = datetime.strptime(receipt_end.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    deadline_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    deadline_str = receipt_end[:16]

            begin_str = ""
            if receipt_begin:
                try:
                    dt = datetime.strptime(receipt_begin.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    begin_str = dt.strftime("%Y-%m-%d")
                except ValueError:
                    begin_str = receipt_begin[:10]

            result_date = _extract_result_date(guide_html)

            detail_url = f"https://startup-plus.kr/project/view/{project_code}" if project_code else ""

            posts.append(SupportPost(
                title=project_name,
                url=detail_url,
                source="스타트업플러스",
                deadline=deadline_str,
                organization=org_name or portal_name,
                status=status_name,
                category=biz_category.get("name", ""),
                target=project_target.get("name", ""),
                result_date=result_date,
                receipt_begin=begin_str,
            ))

    logger.info(f"[스타트업플러스] {len(posts)}건 크롤링 완료")
    return posts


def filter_for_pre_startup(posts: List[SupportPost]) -> List[SupportPost]:
    """예비창업자에게 적합한 공고만 필터링"""
    filtered = []
    for post in posts:
        text = f"{post.title} {post.organization} {post.category} {post.target}".lower()
        # 입주기업 전용이면 제외
        if "입주" in text and "전용" in text:
            continue
        # 예비창업 관련이거나 전체 대상이면 포함
        is_relevant = any(kw.lower() in text for kw in _PRE_STARTUP_KEYWORDS)
        is_all_target = "전체" in post.target
        if is_relevant or is_all_target:
            filtered.append(post)
    return filtered


def calc_idea_relevance(post: SupportPost) -> int:
    """사업계획서 기반 관련도 점수 계산"""
    text = f"{post.title} {post.organization} {post.category}".lower()
    score = 0
    for kw in _IDEA_KEYWORDS_STARTUP_PLUS:
        if kw.lower() in text:
            score += 1
    return score


def sort_by_relevance(posts: List[SupportPost]) -> List[SupportPost]:
    """중요도순 정렬: 관련도 높은 순 → 같은 점수면 마감 임박순 (마감 지난 건 제외)"""
    now = datetime.now()
    scored = []
    for post in posts:
        relevance = calc_idea_relevance(post)
        # 마감일 파싱
        try:
            dl = datetime.strptime(post.deadline, "%Y-%m-%d %H:%M")
            if dl < now:
                continue  # 마감 지난 건 제외
            deadline_dt = dl
        except (ValueError, TypeError):
            if post.deadline:
                continue  # 파싱 불가한 마감일은 제외
            deadline_dt = datetime.max

        scored.append((-relevance, deadline_dt, post))

    scored.sort(key=lambda x: (x[0], x[1]))
    return [p for _, _, p in scored]


def sort_by_deadline(posts: List[SupportPost]) -> List[SupportPost]:
    """마감일 임박순 정렬 (마감 지난 건 제외)"""
    now = datetime.now()
    valid = []
    for post in posts:
        if not post.deadline:
            valid.append((datetime.max, post))
            continue
        try:
            dt = datetime.strptime(post.deadline, "%Y-%m-%d %H:%M")
            if dt >= now:
                valid.append((dt, post))
        except ValueError:
            valid.append((datetime.max, post))

    valid.sort(key=lambda x: x[0])
    return [p for _, p in valid]


ALL_CRAWLERS = [crawl_bizinfo, crawl_kstartup, crawl_smtech, crawl_sba, crawl_startupplus]


async def crawl_all_new() -> List[SupportPost]:
    """전체 사이트 크롤링 후 새로운 게시글만 반환"""
    seen = load_seen_posts()
    new_posts = []

    async with aiohttp.ClientSession() as session:
        for crawler in ALL_CRAWLERS:
            try:
                posts = await crawler(session)
                for post in posts:
                    key = f"{post.source}:{post.title}"
                    if key not in seen:
                        seen.add(key)
                        new_posts.append(post)
            except Exception as e:
                logger.error(f"Crawler error ({crawler.__name__}): {e}")

    save_seen_posts(seen)
    logger.info(f"새로운 지원사업 {len(new_posts)}건 발견")
    return new_posts
