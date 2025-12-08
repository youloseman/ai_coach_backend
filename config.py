import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import logging

# Загружаем переменные окружения
load_dotenv()

# ===== STRAVA CONFIG =====
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")

if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET or not STRAVA_REDIRECT_URI:
    # Не падаем, чтобы backend мог стартовать на Railway даже без Strava-конфига
    print(
        "WARNING: STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET / STRAVA_REDIRECT_URI "
        "not set. Strava OAuth will not work until these are configured."
    )

# ===== OPENAI CONFIG =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    # Не падаем, чтобы /health и базовые эндпоинты работали без ключа
    print(
        "WARNING: OPENAI_API_KEY not set. AI features (plans, reports, analysis) "
        "will be disabled until OPENAI_API_KEY is configured."
    )
    openai_client = None
else:
    # Клиент OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# DEPRECATED: TOKENS_FILE removed - tokens are now stored per-user in database
# Use strava_auth.get_user_tokens(user_id, db) instead


# ===== EMAIL CONFIG =====
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)
EMAIL_TO = os.getenv("EMAIL_TO")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
STRAVA_WEBHOOK_VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

if not RESEND_API_KEY and (not EMAIL_USER or not EMAIL_PASSWORD):
    # Можно не падать, а просто потом проверять это перед отправкой email
    print(
        "WARNING: Neither RESEND_API_KEY nor SMTP credentials configured. "
        "Email sending will not work."
    )

# ===== TRAINING CONSTANTS =====
DEFAULT_MAX_VOLUME_INCREASE_PCT = 10  # максимум +10% в неделю
DEFAULT_ACTIVITY_FETCH_LIMIT = 80
DEFAULT_WEEKS_FOR_ANALYSIS = 260
DEFAULT_PROGRESS_WEEKS = 8

# ===== STRAVA PAGINATION =====
STRAVA_PER_PAGE = 50
STRAVA_MAX_RETRIES = 3

# ===== GPT SETTINGS =====
GPT_MODEL = "gpt-4o"  # OpenAI GPT-4o model
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