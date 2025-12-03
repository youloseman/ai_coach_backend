import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import logging

# Загружаем переменные окружения
load_dotenv()

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")

if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET or not STRAVA_REDIRECT_URI:
    raise RuntimeError("Please set STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REDIRECT_URI in .env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set OPENAI_API_KEY in .env")

# Файл для хранения Strava токенов (MVP: один пользователь)
TOKENS_FILE = Path("strava_token.json")

# Клиент OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)


EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)
EMAIL_TO = os.getenv("EMAIL_TO")

if not EMAIL_USER or not EMAIL_PASSWORD:
    # Можно не падать, а просто потом проверять это перед отправкой email
    print("WARNING: EMAIL_USER or EMAIL_PASSWORD not set. Email sending will not work.")

# ===== TRAINING CONSTANTS =====
DEFAULT_MAX_VOLUME_INCREASE_PCT = 10  # максимум +10% в неделю
DEFAULT_ACTIVITY_FETCH_LIMIT = 80
DEFAULT_WEEKS_FOR_ANALYSIS = 260
DEFAULT_PROGRESS_WEEKS = 8

# ===== STRAVA PAGINATION =====
STRAVA_PER_PAGE = 50
STRAVA_MAX_RETRIES = 3

# ===== GPT SETTINGS =====
GPT_MODEL = "gpt-5.1"  # ваша рабочая модель
GPT_TEMPERATURE_PLANNING = 0.25
GPT_TEMPERATURE_ASSESSMENT = 0.3
GPT_TEMPERATURE_PROGRESS = 0.2
GPT_MAX_TOKENS = 4000

# ===== LOGGING =====
import structlog

# Настраиваем structlog для удобного логирования
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

logger = structlog.get_logger()