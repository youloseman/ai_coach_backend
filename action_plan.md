# Action Plan: Улучшение AI Триатлон Тренера

## QUICK WINS (можно сделать сегодня, 2-4 часа)

### 1. Исправление модели GPT

**Проблема**: В коде используется несуществующая модель "gpt-5.1"

```python
# coach.py - ДО
completion = openai_client.chat.completions.create(
    model="gpt-5.1",  # ❌ НЕ СУЩЕСТВУЕТ
    messages=[...],
)

# coach.py - ПОСЛЕ
completion = openai_client.chat.completions.create(
    model="gpt-4o",  # ✅ Реальная модель, быстрая и качественная
    # или "gpt-4-turbo" для более длинного контекста
    messages=[...],
)
```

**Команды:**
```bash
# Замена во всех файлах
sed -i 's/gpt-5.1/gpt-4o/g' coach.py progress.py
# Или вручную в редакторе
```

---

### 2. Добавление .gitignore

```bash
# .gitignore
strava_token.json
*.pyc
__pycache__/
.env
.venv/
venv/
*.log
data/
.DS_Store
```

---

### 3. Вынос констант в config

```python
# config.py - ДОБАВИТЬ

# === TRAINING CONSTANTS ===
DEFAULT_MAX_VOLUME_INCREASE_PCT = 10  # max +10% per week
DEFAULT_ACTIVITY_FETCH_LIMIT = 80
DEFAULT_WEEKS_FOR_ANALYSIS = 260
DEFAULT_PROGRESS_WEEKS = 8

# === STRAVA PAGINATION ===
STRAVA_PER_PAGE = 50
STRAVA_MAX_RETRIES = 3

# === GPT SETTINGS ===
GPT_MODEL = "gpt-4o"
GPT_TEMPERATURE_PLANNING = 0.25
GPT_TEMPERATURE_ASSESSMENT = 0.3
GPT_TEMPERATURE_PROGRESS = 0.2
GPT_MAX_TOKENS = 4000

# === EMAIL SETTINGS ===
EMAIL_SUBJECT_PREFIX = "AI Coach – "
```

Затем использовать:
```python
# coach.py
from config import GPT_MODEL, GPT_TEMPERATURE_PLANNING

completion = openai_client.chat.completions.create(
    model=GPT_MODEL,
    temperature=GPT_TEMPERATURE_PLANNING,
    ...
)
```

---

### 4. Создание utils.py для общих функций

```python
# utils.py
from typing import Optional
import datetime as dt


def normalize_sport(sport_type: Optional[str]) -> str:
    """
    Нормализует название вида спорта из Strava.
    
    Examples:
        >>> normalize_sport("Run")
        'run'
        >>> normalize_sport("VirtualRide")
        'bike'
        >>> normalize_sport("Swim")
        'swim'
    """
    if not sport_type:
        return "other"
    
    s = sport_type.lower()
    
    # Running
    if any(word in s for word in ["run", "jog", "trail"]):
        return "run"
    
    # Cycling
    if any(word in s for word in ["ride", "bike", "cycl", "virtual"]):
        return "bike"
    
    # Swimming
    if "swim" in s:
        return "swim"
    
    # Strength
    if any(word in s for word in ["strength", "gym", "workout", "weight"]):
        return "strength"
    
    return "other"


def parse_activity_date(activity: dict) -> Optional[dt.date]:
    """
    Извлекает дату из Strava активности.
    
    Args:
        activity: dict с полем "start_date" в ISO формате
        
    Returns:
        date object или None если parsing не удался
    """
    raw_start = activity.get("start_date")
    if not raw_start:
        return None
    
    try:
        dt_start = dt.datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        return dt_start.date()
    except (ValueError, AttributeError):
        return None


def activity_duration_hours(activity: dict) -> float:
    """
    Возвращает длительность активности в часах.
    
    Args:
        activity: dict с полем "moving_time_s" или "moving_time"
        
    Returns:
        float: часы тренировки
    """
    seconds = activity.get("moving_time_s") or activity.get("moving_time") or 0
    return float(seconds) / 3600.0


def get_week_start(date: dt.date) -> dt.date:
    """
    Возвращает понедельник для данной даты.
    
    Args:
        date: любая дата
        
    Returns:
        date: понедельник той же недели
    """
    return date - dt.timedelta(days=date.weekday())


def format_duration(minutes: Optional[float]) -> str:
    """
    Форматирует длительность в читаемый вид.
    
    Examples:
        >>> format_duration(45)
        '45 min'
        >>> format_duration(90)
        '1 h 30 min'
        >>> format_duration(120)
        '2 h'
    """
    if not minutes:
        return "-"
    
    minutes = int(minutes)
    h = minutes // 60
    m = minutes % 60
    
    if h == 0:
        return f"{m} min"
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"
```

Затем заменить дублирование:
```python
# plan_vs_fact.py, progress.py, main.py
from utils import normalize_sport, parse_activity_date, activity_duration_hours

# Удалить локальные функции _normalize_sport и т.д.
```

---

### 5. Добавление базового error handling

```python
# strava_client.py - обновить fetch_activities_last_n_weeks

import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def fetch_activities_last_n_weeks(weeks: int = 8) -> list[dict]:
    """
    Тянем активности за последние N недель с retry logic.
    """
    try:
        access_token = await get_valid_access_token()
        # ... existing code ...
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava API error: {e.response.status_code}")
        if e.response.status_code == 429:
            logger.warning("Rate limit hit, waiting before retry")
        raise
    
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to Strava: {e}")
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error fetching activities: {e}")
        raise
```

---

## КРИТИЧЕСКИЕ УЛУЧШЕНИЯ (1-2 недели)

### 6. Миграция на PostgreSQL

#### Шаг 1: Установка зависимостей

```bash
pip install sqlalchemy psycopg2-binary alembic
```

#### Шаг 2: Модели БД

```python
# models.py

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, 
    JSON, ForeignKey, Boolean, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    
    # Strava integration
    strava_athlete_id = Column(BigInteger, unique=True, index=True)
    strava_access_token = Column(String)
    strava_refresh_token = Column(String)
    strava_expires_at = Column(Integer)
    
    # Profile
    level = Column(String, default="intermediate")
    max_hours_per_week = Column(Float, default=8.0)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    age = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = relationship("Activity", back_populates="user")
    plans = relationship("WeeklyPlan", back_populates="user")
    reports = relationship("WeeklyReport", back_populates="user")


class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Strava data
    strava_id = Column(BigInteger, unique=True, index=True, nullable=False)
    name = Column(String)
    sport_type = Column(String, index=True)
    start_date = Column(DateTime, index=True)
    
    # Metrics
    distance_m = Column(Float)
    moving_time_s = Column(Integer)
    elapsed_time_s = Column(Integer)
    total_elevation_gain_m = Column(Float)
    
    # Intensity data
    average_speed_m_s = Column(Float)
    average_heartrate = Column(Float)
    max_heartrate = Column(Float)
    has_heartrate = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="activities")


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    week_start_date = Column(Date, index=True, nullable=False)
    plan_json = Column(JSON, nullable=False)
    
    # Metadata
    total_planned_hours = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="plans")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    week_start_date = Column(Date, index=True, nullable=False)
    report_json = Column(JSON, nullable=False)
    
    # Summary metrics
    readiness_score = Column(Float)
    completion_pct = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="reports")
```

#### Шаг 3: Database connection

```python
# database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/triathlon_coach"
)

# Fix for Heroku postgres URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency для FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Шаг 4: Миграция данных

```python
# migrate_to_db.py

import json
from pathlib import Path
from database import SessionLocal, engine
from models import Base, User, Activity, WeeklyPlan
import datetime as dt


def migrate_json_to_db():
    """
    Мигрирует данные из JSON файлов в PostgreSQL.
    """
    # Создаём таблицы
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Создаём пользователя (MVP: один пользователь)
        user = User(
            email="artur@example.com",
            strava_athlete_id=20550676,  # из Strava_API.txt
        )
        
        # Загружаем токены Strava
        token_file = Path("strava_token.json")
        if token_file.exists():
            tokens = json.loads(token_file.read_text())
            user.strava_access_token = tokens.get("access_token")
            user.strava_refresh_token = tokens.get("refresh_token")
            user.strava_expires_at = tokens.get("expires_at")
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Created user: {user.id}")
        
        # 2. Миграция планов
        plans_dir = Path("data/plans")
        if plans_dir.exists():
            for plan_file in plans_dir.glob("*.json"):
                week_start_str = plan_file.stem  # "2025-03-10"
                week_start = dt.date.fromisoformat(week_start_str)
                plan_data = json.loads(plan_file.read_text())
                
                plan = WeeklyPlan(
                    user_id=user.id,
                    week_start_date=week_start,
                    plan_json=plan_data,
                    total_planned_hours=plan_data.get("total_planned_hours", 0)
                )
                db.add(plan)
            
            db.commit()
            print(f"✅ Migrated {len(list(plans_dir.glob('*.json')))} plans")
        
        # 3. Можно добавить миграцию активностей из Strava API
        # (но обычно они хранятся в кеше, не в файлах)
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_json_to_db()
```

#### Шаг 5: Обновление endpoints

```python
# main.py - обновить endpoints

from sqlalchemy.orm import Session
from database import get_db
from models import User, WeeklyPlan

@app.post("/coach/weekly_plan")
async def create_weekly_plan(
    req: WeeklyPlanRequest,
    db: Session = Depends(get_db)
):
    """Генерация недельного плана с сохранением в БД"""
    
    # TODO: получить user_id из JWT токена
    user_id = 1  # Временно
    
    activities = await fetch_recent_activities_for_coach(limit=80)
    plan = await run_weekly_plan(req, activities)
    
    # Сохраняем в БД
    db_plan = WeeklyPlan(
        user_id=user_id,
        week_start_date=dt.date.fromisoformat(req.week_start_date),
        plan_json=plan,
        total_planned_hours=plan.get("total_planned_hours", 0)
    )
    db.add(db_plan)
    db.commit()
    
    return plan


@app.get("/coach/plans")
async def get_user_plans(
    user_id: int = 1,  # TODO: из JWT
    db: Session = Depends(get_db)
):
    """Получить все планы пользователя"""
    plans = db.query(WeeklyPlan)\
        .filter(WeeklyPlan.user_id == user_id)\
        .order_by(WeeklyPlan.week_start_date.desc())\
        .all()
    
    return [
        {
            "week_start_date": plan.week_start_date.isoformat(),
            "total_hours": plan.total_planned_hours,
            "plan": plan.plan_json
        }
        for plan in plans
    ]
```

---

### 7. Добавление JWT Authentication

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

```python
# auth.py

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Извлекает текущего пользователя из JWT токена.
    Используется как dependency в protected endpoints.
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user
```

```python
# main.py - добавить endpoints для auth

from auth import create_access_token, get_password_hash, verify_password, get_current_user

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str


@app.post("/auth/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    
    # Проверяем, нет ли уже такого email
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Создаём пользователя
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Создаём токен
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email}
    }


@app.post("/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Вход существующего пользователя"""
    
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email}
    }


@app.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "level": current_user.level,
        "max_hours_per_week": current_user.max_hours_per_week
    }


# Теперь защищаем все endpoints:

@app.post("/coach/weekly_plan")
async def create_weekly_plan(
    req: WeeklyPlanRequest,
    current_user: User = Depends(get_current_user),  # ✅ Добавляем auth
    db: Session = Depends(get_db)
):
    activities = await fetch_recent_activities_for_coach(
        user_id=current_user.id,
        limit=80
    )
    plan = await run_weekly_plan(req, activities)
    # ... save to DB ...
```

---

### 8. Улучшение промпта

Замените содержимое `prompts/trainer_prompt.py` (если его нет — создайте):

```python
# prompts/trainer_prompt.py

TRAINER_SYSTEM_PROMPT = """You are ELITE TRIATHLON COACH — an AI coach specialized in Ironman 70.3 and full-distance 
triathlon training, trained on methodologies of Joe Friel, Matt Dixon (Purple Patch), 
Dan Lorang (Jan Frodeno's coach), Norwegian Polarized Training Model, and 80/20 Endurance.

## YOUR CORE PRINCIPLES

1. **Polarized Training (80/20)**
   - 80% of training volume at Z1-Z2 (easy, conversational)
   - 20% at Z3-Z5 (hard intervals, threshold, VO2max)
   - NEVER program "grey zone" training (moderate intensity)

2. **Progressive Overload**
   - Maximum +10% volume increase per week
   - Every 3-4 weeks: recovery week (-30-40% volume)
   - Never increase volume AND intensity simultaneously

3. **Specificity**
   - Race-specific workouts 8-12 weeks before race
   - Brick workouts (bike-to-run) essential for triathlon
   - Practice race nutrition and pacing

4. **Recovery**
   - Minimum 1 full rest day per week
   - Maximum 3 hard sessions per week (across all sports)
   - Hard days HARD, easy days EASY

## TRAINING ZONES

### Running (% of Threshold Pace)
- Z1 (Recovery): >130% threshold (e.g., 5:40/km if threshold is 4:20/km)
- Z2 (Aerobic): 115-130% threshold (e.g., 5:00-5:40/km)
- Z3 (Tempo): 105-114% threshold (e.g., 4:33-4:57/km) — 70.3 race pace
- Z4 (Threshold): 98-104% threshold (e.g., 4:15-4:30/km) — 10K-HM pace
- Z5 (VO2max): <98% threshold (e.g., <4:15/km) — 5K race pace

### Cycling (% of FTP)
- Z1: <55% FTP (active recovery)
- Z2: 56-75% FTP (endurance base)
- Z3: 76-90% FTP (tempo, sweet spot) — 70.3 race power
- Z4: 91-105% FTP (threshold, 40K TT effort)
- Z5: 106-120% FTP (VO2max intervals)

### Swimming
- Z1-Z2: Easy, focus on technique
- Z3: CSS pace (Critical Swim Speed) — 70.3 race pace
- Z4-Z5: Hard intervals, short rests

## RACE-SPECIFIC TARGETS

### Half Ironman 70.3 — 4:30 Finish
- Swim 1.9km: 30-35min (1:35-1:50/100m)
- Bike 90km: 2:20-2:25 (220-240W @ 70-75kg)
- Run 21.1km: 1:28-1:32 (4:10-4:20/km)
- Transitions: 5-8min

### Training Paces for 4:30 70.3:
- **Easy runs**: 5:10-5:40/km (Z2)
- **Long runs**: 5:00-5:20/km, last 5km @ 4:30/km
- **Tempo runs**: 4:30-4:45/km (Z3, race pace)
- **Threshold**: 4:10-4:25/km (Z4)
- **Long rides**: 180-210W or HR 130-145 bpm
- **Race-pace rides**: 220-240W or HR 150-160 bpm
- **Swim CSS**: 1:40-1:50/100m

## WORKOUT STRUCTURE EXAMPLES

### Base Phase Week (12-16 weeks out)
Mon: Swim technique 45min + Core 20min
Tue: Run easy Z2 60min
Wed: Bike Z2 endurance 90-120min
Thu: Swim endurance 60min
Fri: Rest
Sat: Long bike Z2 2-3h
Sun: Long run Z2 90-120min

Total: 8-10 hours, mostly Z1-Z2

### Build Phase Week (8-12 weeks out)
Mon: Swim threshold (10x100m @ Z4)
Tue: Run threshold 3x10min @ Z3
Wed: Bike Sweet Spot 3x20min @ 88% FTP
Thu: Swim + Easy run brick
Fri: Rest
Sat: **BRICK**: 2.5h bike Z2 + 45min run Z3 (KEY SESSION)
Sun: Long run 2h, last 30min Z3

Total: 10-12 hours, 80% easy / 20% hard

## WHEN GENERATING PLANS

Always include:
1. **Specificity**: Exact duration, intensity zones, workout structure
2. **Rationale**: Why this session? What's the goal?
3. **Brick workouts**: At least 1 per week in Build/Peak phases
4. **Progression**: Show how this week fits into overall plan
5. **Recovery**: Highlight easy days and rest days

Example good workout:
```json
{
  "date": "2025-03-15",
  "sport": "Run",
  "session_type": "Threshold intervals",
  "duration_min": 75,
  "intensity": "Z4 (4:15-4:20/km) for intervals, Z1 (5:30/km) for recovery",
  "description": "Warm-up 15min easy, then 3x10min @ threshold pace (4:15-4:20/km) with 3min jog recovery, cool-down 10min",
  "primary_goal": "Build lactate threshold for Half Ironman run pace",
  "priority": "high",
  "notes": "Target HR 165-172 bpm during intervals. If HR >175, slow down."
}
```

## RED FLAGS — ADJUST PLAN IMMEDIATELY

- Missed 2+ key sessions in a row → reduce volume
- HR elevated on easy runs (+10 bpm) → add rest day
- Persistent muscle soreness → recovery week
- Getting sick → stop training until 100% recovered

## YOUR PERSONALITY

- **Supportive but firm**: "Great work this week, but I'm concerned about your recovery."
- **Specific**: Never vague. Always give exact paces/power/HR.
- **Safety-first**: Injury prevention > hitting workouts
- **Realistic**: Adjust expectations based on actual data

Remember: A consistent 8h/week beats an erratic 12h/week. Quality > Quantity.
"""
```

---

## ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ

### 9. Добавление Pydantic моделей для Activities

```python
# schemas.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ActivityBase(BaseModel):
    strava_id: int
    name: str
    sport_type: str
    start_date: datetime
    distance_m: Optional[float] = None
    moving_time_s: Optional[int] = None
    average_heartrate: Optional[float] = None


class ActivityCreate(ActivityBase):
    pass


class Activity(ActivityBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Для SQLAlchemy models


class PlanDay(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    sport: str = Field(..., description="Run | Bike | Swim | Strength | Rest")
    session_type: str
    duration_min: int
    intensity: str
    description: str
    primary_goal: str
    priority: str = Field(..., description="low | medium | high")
    notes: Optional[str] = None


class WeeklyPlanResponse(BaseModel):
    week_start_date: str
    total_planned_hours: float
    days: list[PlanDay]
    notes: dict


class ProgressEvaluation(BaseModel):
    readiness_score: float = Field(..., ge=0, le=100)
    score_label: str = Field(..., regex="^(low|medium|high)$")
    comment: str
    main_risks: list[str]
    recommendations: list[str]
```

Затем использовать:
```python
# coach.py

from schemas import WeeklyPlanResponse

async def run_weekly_plan(...) -> WeeklyPlanResponse:
    # ...
    plan = json.loads(plan_json)
    return WeeklyPlanResponse(**plan)  # Валидация через Pydantic
```

---

### 10. Добавление тестов

```bash
pip install pytest pytest-asyncio httpx
```

```python
# tests/test_utils.py

import pytest
from utils import normalize_sport, parse_activity_date, activity_duration_hours
import datetime as dt


def test_normalize_sport():
    assert normalize_sport("Run") == "run"
    assert normalize_sport("VirtualRide") == "bike"
    assert normalize_sport("Swim") == "swim"
    assert normalize_sport("WeightTraining") == "strength"
    assert normalize_sport("Yoga") == "other"
    assert normalize_sport(None) == "other"


def test_parse_activity_date():
    activity = {"start_date": "2025-03-10T18:12:34Z"}
    result = parse_activity_date(activity)
    assert result == dt.date(2025, 3, 10)
    
    # Invalid date
    activity = {"start_date": "invalid"}
    result = parse_activity_date(activity)
    assert result is None


def test_activity_duration_hours():
    activity = {"moving_time_s": 3600}
    assert activity_duration_hours(activity) == 1.0
    
    activity = {"moving_time": 7200}
    assert activity_duration_hours(activity) == 2.0
    
    activity = {}
    assert activity_duration_hours(activity) == 0.0
```

```python
# tests/test_api.py

import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_plan_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/coach/weekly_plan",
            json={
                "goal": {
                    "main_goal_type": "HALF_IRONMAN",
                    "main_goal_target_time": "4:30",
                    "main_goal_race_date": "2026-05-24"
                },
                "week_start_date": "2025-03-10",
                "available_hours_per_week": 8.5
            }
        )
        # Should return 401 without auth token
        assert response.status_code == 401
```

Запуск тестов:
```bash
pytest tests/ -v
```

---

## ИТОГОВЫЙ CHECKLIST

### ✅ Quick Wins (сегодня)
- [ ] Исправить модель GPT (gpt-5.1 → gpt-4o)
- [ ] Добавить .gitignore
- [ ] Вынести константы в config
- [ ] Создать utils.py
- [ ] Добавить базовый error handling

### ✅ Критические (1-2 недели)
- [ ] Миграция на PostgreSQL
- [ ] JWT Authentication
- [ ] Multi-user support
- [ ] Улучшенный промпт
- [ ] Pydantic модели для валидации

### ✅ Тесты и мониторинг
- [ ] Unit тесты (pytest)
- [ ] Integration тесты для API
- [ ] Логирование (structlog)
- [ ] Sentry для error tracking

### ✅ Deployment
- [ ] Docker Compose для локальной разработки
- [ ] CI/CD (GitHub Actions)
- [ ] Production deployment (Railway / Render / Fly.io)

---

Теперь у вас есть конкретный план действий с примерами кода! 🚀
