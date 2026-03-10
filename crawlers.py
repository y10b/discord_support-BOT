"""지원사업 크롤러 모듈 - 4개 사이트 크롤링"""

import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set
import json
import os
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

        posts.append(SupportPost(
            title=title,
            url=href,
            source="기업마당",
            organization=org,
            deadline=deadline,
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

        posts.append(SupportPost(
            title=title,
            url=href,
            source="K-Startup",
            organization=org,
            deadline=deadline,
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

        posts.append(SupportPost(
            title=title,
            url=href,
            source="중기부 기술개발",
            deadline=deadline,
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

        posts.append(SupportPost(
            title=title,
            url=href,
            source="서울산업진흥원",
            deadline=deadline,
            status=status,
        ))

    logger.info(f"[서울산업진흥원] {len(posts)}건 크롤링 완료")
    return posts


ALL_CRAWLERS = [crawl_bizinfo, crawl_kstartup, crawl_smtech, crawl_sba]


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
