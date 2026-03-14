"""디스코드 지원사업 알림 봇"""

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
from crawlers import (
    crawl_all_new, crawl_startupplus, SupportPost,
    filter_for_pre_startup, sort_by_deadline, calc_idea_relevance,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

if not TOKEN:
    raise ValueError("DISCORD_TOKEN이 .env 파일에 설정되지 않았습니다.")
if not CHANNEL_ID:
    raise ValueError("DISCORD_CHANNEL_ID가 .env 파일에 설정되지 않았습니다.")

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 소스별 색상
SOURCE_COLORS = {
    "기업마당": 0x2ECC71,       # 초록
    "K-Startup": 0x3498DB,     # 파랑
    "중기부 기술개발": 0xE74C3C,  # 빨강
    "서울산업진흥원": 0xF39C12,   # 주황
    "스타트업플러스": 0x9B59B6,   # 보라
}

# ── 우리 아이디어 매칭 키워드 ──
# 가중치: 핵심 키워드(3점), 관련 키워드(2점), 일반 키워드(1점)
IDEA_KEYWORDS = {
    # 핵심 (AI 광고 모델 마켓플레이스 직접 관련)
    "AI광고": 3, "AI모델": 3, "ai광고": 3, "ai모델": 3,
    "인공지능 광고": 3, "딥페이크": 3, "가상모델": 3, "버추얼모델": 3,
    "AI 마켓플레이스": 3, "광고 자동화": 3, "AI 콘텐츠 제작": 3,
    "생성형 AI": 3, "생성형AI": 3, "GenAI": 3,

    # 관련 (기술 분야)
    "인공지능": 2, "AI": 2, "딥러닝": 2, "머신러닝": 2,
    "음성합성": 2, "음성 합성": 2, "TTS": 2, "보이스": 2,
    "얼굴인식": 2, "얼굴 인식": 2, "페이스": 2, "영상합성": 2,
    "영상 생성": 2, "이미지 생성": 2, "디지털 휴먼": 2,
    "초상권": 2, "데이터 마켓": 2,

    # 관련 (사업 분야)
    "광고": 1, "콘텐츠": 1, "마케팅": 1, "플랫폼": 1,
    "마켓플레이스": 1, "크리에이터": 1, "MCN": 1,
    "영상제작": 1, "영상 제작": 1, "미디어": 1,
    "스타트업": 1, "창업": 1,
}

MATCH_THRESHOLD = 3  # 이 점수 이상이면 "우리 아이디어 관련" 판정


def match_idea(post: SupportPost) -> tuple[bool, int, list[str]]:
    """공고가 우리 아이디어(AI 광고 모델 마켓플레이스)와 관련 있는지 판별.
    Returns: (매칭 여부, 점수, 매칭된 키워드 리스트)
    """
    text = f"{post.title} {post.organization}".lower()
    score = 0
    matched = []
    for keyword, weight in IDEA_KEYWORDS.items():
        if keyword.lower() in text:
            score += weight
            matched.append(keyword)
    return score >= MATCH_THRESHOLD, score, matched


def make_embed(post: SupportPost) -> discord.Embed:
    """지원사업 게시글을 디스코드 Embed로 변환"""
    is_match, score, matched_keywords = match_idea(post)

    if is_match:
        return _make_idea_embed(post, score, matched_keywords)
    return _make_normal_embed(post)


def _make_normal_embed(post: SupportPost) -> discord.Embed:
    """일반 공고 템플릿"""
    color = SOURCE_COLORS.get(post.source, 0x95A5A6)
    embed = discord.Embed(
        title=post.title[:256],
        url=post.url if post.url else None,
        color=color,
    )
    embed.add_field(name="출처", value=post.source, inline=True)

    if post.organization:
        embed.add_field(name="주관기관", value=post.organization, inline=True)
    if post.deadline:
        embed.add_field(name="마감일", value=post.deadline, inline=True)
    if post.status:
        embed.add_field(name="상태", value=post.status, inline=True)

    embed.set_footer(text=f"수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return embed


def _make_idea_embed(post: SupportPost, score: int, keywords: list[str]) -> discord.Embed:
    """우리 아이디어 관련 공고 - 특별 템플릿"""
    # 골드 컬러 + 눈에 띄는 디자인
    embed = discord.Embed(
        title=f"\u2b50 [AI 광고 플랫폼 관련] {post.title}"[:256],
        url=post.url if post.url else None,
        color=0xFFD700,  # 골드
        description=(
            "**이 공고는 우리 아이디어와 연관성이 높습니다!**\n"
            "관련도: {} ({}점)".format("\u2b50" * min(score, 5), score)
        ),
    )

    embed.add_field(name="출처", value=post.source, inline=True)
    if post.organization:
        embed.add_field(name="주관기관", value=post.organization, inline=True)
    if post.deadline:
        embed.add_field(name="마감일", value=post.deadline, inline=True)
    if post.status:
        embed.add_field(name="상태", value=post.status, inline=True)

    # 매칭 키워드 표시
    tags = " ".join(f"`{kw}`" for kw in keywords[:8])
    embed.add_field(name="매칭 키워드", value=tags, inline=False)

    # 우리 아이디어와의 연결 포인트
    relevance_notes = []
    text_lower = f"{post.title} {post.organization}".lower()
    if any(k in text_lower for k in ["ai", "인공지능", "딥러닝", "생성형"]):
        relevance_notes.append("AI/딥러닝 기술 지원")
    if any(k in text_lower for k in ["광고", "마케팅", "콘텐츠"]):
        relevance_notes.append("광고/콘텐츠 산업")
    if any(k in text_lower for k in ["플랫폼", "마켓플레이스", "데이터"]):
        relevance_notes.append("플랫폼/데이터 사업")
    if any(k in text_lower for k in ["음성", "보이스", "tts", "얼굴", "페이스", "영상"]):
        relevance_notes.append("음성/영상/얼굴 기술")
    if any(k in text_lower for k in ["창업", "스타트업"]):
        relevance_notes.append("창업 지원")

    if relevance_notes:
        embed.add_field(
            name="관련 분야",
            value="\n".join(f"\u2022 {n}" for n in relevance_notes),
            inline=False,
        )

    embed.set_footer(
        text=f"\U0001f680 AI 광고 모델 마켓플레이스 | 수집: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return embed


@bot.event
async def on_ready():
    logger.info(f"봇 로그인 완료: {bot.user}")
    if not check_new_posts.is_running():
        check_new_posts.start()


@tasks.loop(hours=1)
async def check_new_posts():
    """1시간마다 새로운 지원사업 크롤링"""
    logger.info("크롤링 시작...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"채널을 찾을 수 없습니다: {CHANNEL_ID}")
        return

    new_posts = await crawl_all_new()

    if not new_posts:
        logger.info("새로운 지원사업 없음")
        return

    # 관련 공고 우선 정렬 (점수 높은 순)
    new_posts.sort(key=lambda p: match_idea(p)[1], reverse=True)

    idea_count = sum(1 for p in new_posts if match_idea(p)[0])
    if idea_count > 0:
        await channel.send(
            f"**\U0001f514 새로운 지원사업 {len(new_posts)}건 발견!** "
            f"(우리 아이디어 관련: **{idea_count}건**)"
        )

    for post in new_posts[:20]:
        try:
            embed = make_embed(post)
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")

    if len(new_posts) > 20:
        await channel.send(f"... 외 {len(new_posts) - 20}건의 새로운 지원사업이 있습니다.")

    logger.info(f"{len(new_posts)}건 알림 전송 완료 (관련 공고: {idea_count}건)")


@check_new_posts.before_loop
async def before_check():
    await bot.wait_until_ready()


@bot.command(name="크롤링")
async def manual_crawl(ctx):
    """수동으로 크롤링 실행: !크롤링"""
    await ctx.send("🔍 크롤링을 시작합니다...")
    new_posts = await crawl_all_new()

    if not new_posts:
        await ctx.send("새로운 지원사업이 없습니다.")
        return

    for post in new_posts[:20]:
        embed = make_embed(post)
        await ctx.send(embed=embed)

    if len(new_posts) > 20:
        await ctx.send(f"... 외 {len(new_posts) - 20}건")


@bot.command(name="맞춤")
async def custom_search(ctx):
    """예비창업자 맞춤 지원사업 검색: !맞춤"""
    await ctx.send("🔍 예비창업자 맞춤 지원사업을 검색합니다...")

    import aiohttp
    from crawlers import crawl_bizinfo, crawl_kstartup, crawl_smtech, crawl_sba
    all_posts = []
    async with aiohttp.ClientSession() as session:
        for crawler in [crawl_startupplus, crawl_bizinfo, crawl_kstartup, crawl_smtech, crawl_sba]:
            try:
                posts = await crawler(session)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(f"Crawler error ({crawler.__name__}): {e}")

    if not all_posts:
        await ctx.send("❌ 데이터를 불러오지 못했습니다.")
        return

    # 예비창업자 필터 → 마감순 정렬
    filtered = filter_for_pre_startup(all_posts)
    sorted_posts = sort_by_deadline(filtered)

    if not sorted_posts:
        await ctx.send("현재 예비창업자 대상 지원사업이 없습니다.")
        return

    # 헤더 임베드
    header = discord.Embed(
        title="🎯 예비창업자 맞춤 지원사업",
        description=(
            "**조건**: 사업자등록증·사무실 없는 예비창업자 대상\n"
            "**정렬**: 마감 임박순\n"
            f"**검색 결과**: 전체 {len(all_posts)}건 중 **{len(sorted_posts)}건** 해당"
        ),
        color=0xFFD700,
    )
    header.set_footer(text=f"검색 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await ctx.send(embed=header)

    # 최대 15건 표시
    for i, post in enumerate(sorted_posts[:15], 1):
        relevance = calc_idea_relevance(post)
        stars = "⭐" * min(relevance, 5) if relevance > 0 else "—"

        # 마감까지 남은 일수 계산
        d_day = ""
        if post.deadline:
            try:
                dl = datetime.strptime(post.deadline, "%Y-%m-%d %H:%M")
                days_left = (dl - datetime.now()).days
                if days_left == 0:
                    d_day = "🔴 오늘 마감!"
                elif days_left <= 3:
                    d_day = f"🔴 D-{days_left}"
                elif days_left <= 7:
                    d_day = f"🟡 D-{days_left}"
                else:
                    d_day = f"🟢 D-{days_left}"
            except ValueError:
                pass

        # 색상: 관련도에 따라
        if relevance >= 3:
            color = 0xFFD700  # 골드
        elif relevance >= 1:
            color = 0x3498DB  # 파랑
        else:
            color = 0x95A5A6  # 회색

        embed = discord.Embed(
            title=f"{i}. {post.title}"[:256],
            url=post.url if post.url else None,
            color=color,
        )

        # 핵심 정보 필드
        embed.add_field(name="📅 접수 마감", value=f"{post.deadline or '미정'}\n{d_day}", inline=True)
        embed.add_field(name="🏢 주관기관", value=post.organization or "—", inline=True)
        embed.add_field(name="📌 상태", value=post.status or "—", inline=True)

        if post.category:
            embed.add_field(name="📂 분류", value=post.category, inline=True)
        if post.target:
            embed.add_field(name="🎯 대상", value=post.target, inline=True)

        # 결과 발표일
        embed.add_field(
            name="📢 결과 발표",
            value=post.result_date if post.result_date else "공고문 확인 필요",
            inline=True,
        )

        # 관련도
        embed.add_field(name="💡 AI광고 플랫폼 관련도", value=stars, inline=False)

        if post.receipt_begin:
            embed.set_footer(text=f"접수 시작: {post.receipt_begin}")

        await ctx.send(embed=embed)

    if len(sorted_posts) > 15:
        await ctx.send(f"... 외 **{len(sorted_posts) - 15}건**이 더 있습니다.")


@bot.command(name="상태")
async def status(ctx):
    """봇 상태 확인: !상태"""
    from crawlers import load_seen_posts
    seen = load_seen_posts()
    embed = discord.Embed(title="봇 상태", color=0x3498DB)
    embed.add_field(name="크롤링 주기", value="1시간", inline=True)
    embed.add_field(name="누적 수집 건수", value=f"{len(seen)}건", inline=True)
    embed.add_field(
        name="크롤링 대상",
        value="기업마당, K-Startup, 중기부 기술개발, 서울산업진흥원, 스타트업플러스",
        inline=False,
    )
    await ctx.send(embed=embed)


bot.run(TOKEN)
