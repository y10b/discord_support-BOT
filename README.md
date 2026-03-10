# discord_support-BOT

정부 지원사업을 자동 크롤링하여 디스코드 채널에 알림을 보내는 봇입니다.
**AI 광고 모델 마켓플레이스** 아이디어와 관련된 공고는 특별 템플릿(골드)으로 강조 표시됩니다.

## 크롤링 대상 사이트

| 사이트 | URL | Embed 색상 |
|--------|-----|-----------|
| 기업마당 | bizinfo.go.kr | 초록 |
| K-Startup | k-startup.go.kr | 파랑 |
| 중기부 기술개발 | smtech.go.kr | 빨강 |
| 서울산업진흥원 | sba.seoul.kr | 주황 |

## 주요 기능

- **자동 크롤링**: 1시간마다 4개 사이트 자동 크롤링
- **새 글 감지**: 이전에 보낸 적 없는 새 글만 디스코드에 알림
- **아이디어 매칭**: AI/광고/콘텐츠 관련 키워드를 3단계 가중치로 분석하여 관련 공고를 골드 템플릿으로 강조
- **디스코드 명령어**: `!크롤링` (수동 실행), `!상태` (봇 상태 확인)

## 아이디어 매칭 시스템

공고 제목/기관명에서 키워드를 매칭하여 점수를 산출합니다. 3점 이상이면 관련 공고로 판정됩니다.

| 가중치 | 분류 | 키워드 예시 |
|--------|------|-----------|
| 3점 | 핵심 | AI광고, AI모델, 생성형AI, 광고 자동화, 딥페이크, 가상모델 |
| 2점 | 기술 | 인공지능, 딥러닝, 음성합성, 얼굴인식, 디지털 휴먼, TTS |
| 1점 | 사업 | 광고, 콘텐츠, 플랫폼, 마켓플레이스, 창업, 스타트업 |

### 템플릿 비교

| | 일반 공고 | 관련 공고 (골드) |
|---|---|---|
| 색상 | 소스별 (초록/파랑/빨강/주황) | 골드 (#FFD700) |
| 제목 | 원본 제목 | `[AI 광고 플랫폼 관련]` 접두어 |
| 관련도 | 없음 | 별점 + 점수 |
| 매칭 키워드 | 없음 | 태그로 표시 |
| 관련 분야 | 없음 | AI기술/광고산업/플랫폼/창업 자동 분류 |

## 설치 및 실행

### 1. 사전 준비

- Python 3.9+
- Discord Bot Token ([Developer Portal](https://discord.com/developers/applications)에서 발급)
- 알림 받을 Discord 채널 ID

### 2. 설치

```bash
cd discord-support-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 토큰과 채널 ID 입력:

```
DISCORD_TOKEN=발급받은_봇_토큰
DISCORD_CHANNEL_ID=알림_채널_ID
```

### 4. Discord 봇 설정

1. [Developer Portal](https://discord.com/developers/applications) → Bot 메뉴
2. **MESSAGE CONTENT INTENT** 활성화
3. OAuth2 → URL Generator → `bot` 스코프 선택
4. Bot Permissions: `Send Messages`, `Embed Links` 선택
5. 생성된 URL로 봇을 서버에 초대

### 5. 실행

```bash
python bot.py
```

## 디스코드 명령어

| 명령어 | 설명 |
|--------|------|
| `!크롤링` | 즉시 크롤링 실행 |
| `!상태` | 봇 상태 및 누적 수집 건수 확인 |

## 프로젝트 구조

```
discord-support-bot/
├── bot.py              # 디스코드 봇 메인 (명령어, 스케줄러, Embed 템플릿)
├── crawlers.py         # 4개 사이트 크롤러 모듈
├── requirements.txt    # Python 패키지 의존성
├── .env.example        # 환경 변수 템플릿
├── .gitignore          # Git 제외 파일 설정
└── data/               # 크롤링 데이터 저장 (자동 생성)
    └── seen_posts.json # 이미 알림한 공고 목록
```

## 기술 스택

- **Python 3.9+**
- **discord.py** - 디스코드 봇 프레임워크
- **aiohttp** - 비동기 HTTP 클라이언트
- **BeautifulSoup4 + lxml** - HTML 파싱
- **python-dotenv** - 환경 변수 관리
- **APScheduler** - 작업 스케줄링
