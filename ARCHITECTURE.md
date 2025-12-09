# Архитектура проекта AI Triathlon Coach

## 📋 Содержание

1. [Обзор системы](#обзор-системы)
2. [Технологический стек](#технологический-стек)
3. [Архитектура базы данных](#архитектура-базы-данных)
4. [Backend архитектура](#backend-архитектура)
5. [Frontend архитектура](#frontend-архитектура)
6. [Аутентификация и авторизация](#аутентификация-и-авторизация)
7. [Интеграции](#интеграции)
8. [Потоки данных](#потоки-данных)
9. [Деплой и инфраструктура](#деплой-и-инфраструктура)
10. [Безопасность](#безопасность)

---

## Обзор системы

**AI Triathlon Coach** — это веб-приложение для персонального AI-тренера триатлетов, которое:

- Управляет профилем атлета и тренировочными целями
- Интегрируется со Strava для автоматической синхронизации тренировок
- Рассчитывает тренировочные зоны и метрики производительности
- Генерирует персонализированные тренировочные планы с помощью GPT
- Анализирует прогресс и риск травм
- Предоставляет аналитику и прогнозы результатов

### Архитектурный паттерн

Проект использует **клиент-серверную архитектуру** с разделением на:
- **Backend**: FastAPI REST API (Python)
- **Frontend**: Next.js SPA (TypeScript/React)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **External APIs**: Strava OAuth2, OpenAI GPT

---

## Технологический стек

### Backend

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.11+ | Основной язык |
| FastAPI | Latest | Web framework |
| SQLAlchemy | Latest | ORM для работы с БД |
| Alembic | Latest | Миграции БД |
| Pydantic | Latest | Валидация данных |
| JWT (python-jose) | Latest | Аутентификация |
| HTTPX | Latest | Асинхронные HTTP-запросы |
| OpenAI | Latest | GPT интеграция |

### Frontend

| Технология | Версия | Назначение |
|------------|--------|------------|
| Next.js | 16.0.5 | React framework |
| React | Latest | UI библиотека |
| TypeScript | Latest | Типизация |
| Tailwind CSS | Latest | Стилизация |
| React Query | Latest | Управление состоянием и кэширование |
| Axios | Latest | HTTP клиент |

### Database

- **Development**: SQLite (`triathlon_coach.db`)
- **Production**: PostgreSQL (Railway)

### Deployment

- **Platform**: Railway
- **Build System**: Nixpacks
- **CI/CD**: GitHub Actions

---

## Архитектура базы данных

### Схема данных

Проект использует **SQLAlchemy ORM** с декларативными моделями. Основные таблицы:

#### 1. `users` — Пользователи

```python
class User(Base):
    id: int (PK)
    email: str (unique)
    username: str (unique)
    hashed_password: str
    full_name: str (optional)
    
    # Strava интеграция
    strava_athlete_id: str (optional)
    strava_access_token: str (optional)
    strava_refresh_token: str (optional)
    strava_token_expires_at: datetime (optional)
    
    # Статус аккаунта
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
```

**Связи:**
- `One-to-One` с `AthleteProfileDB`
- `One-to-Many` с `GoalDB`, `WeeklyPlanDB`, `ActivityDB`

#### 2. `athlete_profiles` — Профиль атлета

```python
class AthleteProfileDB(Base):
    id: int (PK)
    user_id: int (FK → users.id, unique)
    
    # Базовая информация
    age: int (optional)
    gender: str (optional)
    weight_kg: float (optional)
    height_cm: float (optional)
    years_of_experience: int
    
    # Тренировочные зоны (JSON)
    training_zones_run: JSON
    training_zones_bike: JSON
    training_zones_swim: JSON
    zones_last_updated: date
    
    # Автоматически рассчитанные метрики
    auto_weeks_analyzed: int
    auto_current_weekly_streak_weeks: int
    auto_longest_weekly_streak_weeks: int
    auto_avg_hours_last_12_weeks: float
    auto_avg_hours_last_52_weeks: float
    auto_discipline_hours_per_week: JSON
    
    # Предпочтения
    primary_discipline: str (run/bike/swim)
    preferred_training_days: JSON (array)
    available_hours_per_week: float
```

#### 3. `goals` — Тренировочные цели

```python
class GoalDB(Base):
    id: int (PK)
    user_id: int (FK → users.id)
    
    goal_type: str (SPRINT, OLYMPIC, HALF_IRONMAN, IRONMAN, etc.)
    target_time: str (optional, "4:30" или "sub 5:00")
    race_date: date
    race_name: str (optional)
    race_location: str (optional)
    
    is_primary: bool (только одна primary цель)
    is_completed: bool
```

#### 4. `weekly_plans` — Недельные планы

```python
class WeeklyPlanDB(Base):
    id: int (PK)
    user_id: int (FK → users.id)
    goal_id: int (FK → goals.id, optional)
    
    week_start_date: date
    week_number: int (неделя в цикле)
    plan_json: JSON (структура от GPT)
    
    available_hours: float
    coach_notes: text
    
    completed: bool
    completion_rate: float (0-100%)
```

#### 5. `activities` — Кэш активностей Strava

```python
class ActivityDB(Base):
    id: int (PK)
    user_id: int (FK → users.id)
    strava_activity_id: int (unique)
    
    activity_type: str
    name: str
    distance_meters: float
    moving_time_seconds: int
    elapsed_time_seconds: int
    total_elevation_gain: float
    start_date: datetime
    
    # Детали (JSON)
    details_json: JSON
    
    cached_at: datetime
```

#### 6. Дополнительные таблицы

- `segments` — Отслеживаемые сегменты Strava
- `segment_efforts` — Усилия на сегментах
- `personal_records` — Личные рекорды
- `injury_risks` — Анализ риска травм
- `nutrition_targets` — Цели по питанию
- `nutrition_plans` — Планы питания

### Миграции

Проект использует **Alembic** для управления миграциями:

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head
```

Файлы миграций находятся в `alembic/versions/`.

---

## Backend архитектура

### Структура модулей

```
ai_coach_backend/
├── main.py                 # Точка входа, FastAPI app, CORS, rate limiting
├── database.py            # Подключение к БД, SessionLocal, init_db
├── models.py               # SQLAlchemy модели
├── schemas.py              # Pydantic схемы для валидации
├── crud.py                 # CRUD операции с БД
├── auth.py                 # JWT аутентификация
│
├── api_auth.py             # Эндпоинты: /auth/register, /auth/login, /auth/me
├── api_user.py             # Эндпоинты: /profile, /goals
├── api_coach.py            # Эндпоинты: /coach/* (планы, зоны, профиль)
├── api_segments.py         # Эндпоинты: /segments/* (сегменты, PR)
├── api_nutrition.py        # Эндпоинты: /nutrition/* (цели, планы)
│
├── strava_client.py        # Клиент Strava API (OAuth, активности)
├── strava_auth.py         # Сохранение Strava токенов
├── segment_sync.py         # Синхронизация сегментов и PR
│
├── coach.py                # Логика генерации планов (GPT)
├── athlete_profile.py      # JSON профиль атлета (legacy)
├── training_zones.py       # Расчет тренировочных зон
├── performance_predictions.py  # Прогнозы результатов
├── fatigue_detection.py    # Анализ усталости
├── analytics.py            # Аналитика нагрузки, формы
├── progress.py             # Отслеживание прогресса
│
├── config.py               # Конфигурация, переменные окружения
├── dependencies.py         # FastAPI dependencies
├── utils.py                # Утилиты
└── requirements.txt        # Python зависимости
```

### Основные компоненты

#### 1. `main.py` — FastAPI Application

```python
app = FastAPI(title="AI Triathlon Coach API")

# CORS middleware (должен быть первым)
app.add_middleware(CORSMiddleware, ...)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Подключение роутеров
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="", tags=["user"])
app.include_router(coach_router, prefix="/coach", tags=["coach"])
app.include_router(segments_router, prefix="/segments", tags=["segments"])
app.include_router(nutrition_router, prefix="/nutrition", tags=["nutrition"])

# Инициализация БД при старте
@app.on_event("startup")
async def startup():
    init_db()
```

**Ключевые middleware:**
- **CORS**: Разрешает запросы с фронтенда
- **Rate Limiting**: Ограничивает количество запросов
- **Authentication**: JWT токены через `get_current_user` dependency

#### 2. `auth.py` — JWT Аутентификация

```python
# Создание токена
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# Получение текущего пользователя
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
```

#### 3. `strava_client.py` — Strava API Client

**Основные функции:**

```python
# Получение токенов пользователя
async def get_user_tokens(user_id: int, db: Session) -> dict:
    """Получает актуальные токены из БД, обновляет если истекли"""
    
# Загрузка активностей
async def fetch_activities_last_n_weeks_for_user(
    user_id: int,
    db: Session,
    weeks: int = 12
) -> list[dict]:
    """Загружает активности за последние N недель"""
    
# Обмен кода на токены
async def exchange_code_for_token(code: str) -> dict:
    """OAuth2: обмен authorization code на access/refresh токены"""
```

**Особенности:**
- Автоматическое обновление истекших токенов
- Кэширование активностей в БД
- Graceful handling когда пользователь не подключен к Strava

#### 4. `coach.py` — Генерация планов

```python
async def run_weekly_plan(
    goal: GoalInput,
    start_date: date,
    available_hours: float,
    activities_history: list[dict]
) -> dict:
    """Генерирует недельный план через GPT"""
    
    # 1. Подготовка контекста (профиль, цели, история)
    # 2. Вызов OpenAI API с промптом
    # 3. Парсинг JSON ответа
    # 4. Валидация структуры плана
    # 5. Возврат структурированного плана
```

**Промпт находится в:** `prompts/trainer_prompt.py`

#### 5. `api_coach.py` — Coach Endpoints

**Основные эндпоинты:**

- `POST /coach/plan` — Генерация недельного плана
- `GET /coach/weekly_plan` — Получение текущего плана
- `POST /coach/profile/auto_from_history` — Авто-заполнение профиля из Strava
- `POST /zones/calculate` — Расчет тренировочных зон (run/bike/swim)
- `GET /coach/profile` — Профиль коуча (JSON)

### Обработка ошибок

Backend использует **graceful degradation**:

```python
try:
    activities = await fetch_activities_last_n_weeks_for_user(user_id, db, weeks=12)
    if not activities:
        return {
            "status": "no_data",
            "message": "Connect to Strava to see activities"
        }
except Exception as e:
    logger.error("error_fetching_activities", error=str(e))
    return {
        "status": "error",
        "message": "Unable to fetch activities"
    }
```

---

## Frontend архитектура

### Структура проекта

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Главная (роутинг)
│   ├── providers.tsx      # React Query provider
│   │
│   ├── login/             # Страница входа
│   ├── register/          # Страница регистрации
│   ├── onboarding/       # Онбординг (профиль + цель)
│   ├── dashboard/         # Главная страница дашборда
│   ├── coach/             # Настройки (профиль, Strava)
│   ├── goals/             # Управление целями
│   ├── plans/             # Детальный просмотр планов
│   ├── segments/          # Сегменты Strava
│   └── nutrition/         # Питание (цели, планы)
│
├── components/            # React компоненты
│   ├── Header.tsx         # Навигация
│   ├── FormStatusCard.tsx # Карточка формы (CTL/ATL/TSB)
│   ├── InjuryRisk.tsx     # Риск травм
│   ├── WeeklyPlanCompact.tsx  # Компактный план
│   ├── SegmentsSummary.tsx     # Сводка сегментов
│   ├── NutritionQuickStats.tsx # Быстрая статистика питания
│   └── ...
│
├── lib/
│   ├── api.ts            # Axios клиент, API методы
│   └── auth.ts            # Работа с localStorage
│
└── types/
    └── index.ts           # TypeScript типы
```

### Next.js App Router

Проект использует **App Router** (Next.js 13+):

- **Server Components** по умолчанию
- **Client Components** с `"use client"` директивой
- **Route Handlers** для API routes (если нужны)

### Управление состоянием

#### React Query

```typescript
// lib/api.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 минут
      gcTime: 1000 * 60 * 30,    // 30 минут
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

**Использование:**

```typescript
// В компоненте
const { data, isLoading, isError } = useQuery({
  queryKey: ['weeklyPlan'],
  queryFn: () => coachAPI.getWeeklyPlan(),
});
```

#### Local Storage

JWT токен хранится в `localStorage`:

```typescript
// lib/auth.ts
export function setAuthToken(token: string, user: User) {
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(user));
}
```

### API Client (`lib/api.ts`)

**Axios instance с interceptors:**

```typescript
const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: добавляет JWT токен
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Перенаправление на /login
    }
    return Promise.reject(error);
  }
);
```

**API методы организованы по доменам:**

```typescript
export const authAPI = { register, login, getMe };
export const userAPI = { getProfile, updateProfile, getGoals, createGoal };
export const coachAPI = { getProfile, generateWeeklyPlan, ... };
export const zonesAPI = { calculate };
export const weeklyPlanAPI = { getCurrent };
export const performanceAPI = { getInjuryRisks, getRecentSegmentPRs, ... };
export const nutritionAPI = { getTargets, updateTargets, ... };
```

### Компоненты

#### Пример: `WeeklyPlanCompact.tsx`

```typescript
export function WeeklyPlanCompact() {
  const { data, isLoading, isError } = useQuery<WeeklyPlanResponse>({
    queryKey: ['weeklyPlanPreview'],
    queryFn: async () => {
      const res = await coachAPI.getWeeklyPlan();
      return res;
    },
  });

  // Рендер компактной версии плана
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
      {/* ... */}
    </div>
  );
}
```

**Особенности компонентов:**
- Все используют единый стиль (Tailwind: `bg-slate-900`, `border-slate-800`)
- Обработка loading/error состояний
- Responsive дизайн (mobile-first)

---

## Аутентификация и авторизация

### Поток регистрации

```
1. Пользователь заполняет форму (/register)
   ↓
2. POST /auth/register
   {
     email, username, password, full_name
   }
   ↓
3. Backend:
   - Хеширует пароль (bcrypt)
   - Создает User в БД
   - Создает дефолтный AthleteProfileDB
   - Генерирует JWT токен
   ↓
4. Возвращает:
   {
     access_token: "eyJ...",
     token_type: "bearer",
     user: { id, email, username, ... }
   }
   ↓
5. Frontend сохраняет токен в localStorage
   ↓
6. Редирект на /onboarding или /dashboard
```

### Поток входа

```
1. POST /auth/login
   {
     email, password
   }
   ↓
2. Backend проверяет пароль (bcrypt.verify)
   ↓
3. Генерирует JWT токен
   ↓
4. Возвращает токен + user
   ↓
5. Frontend сохраняет в localStorage
```

### JWT Token Structure

```json
{
  "sub": 123,  // user_id
  "exp": 1234567890,  // expiration timestamp
  "iat": 1234567890   // issued at
}
```

**Секретный ключ:** `SECRET_KEY` из переменных окружения

### Защита эндпоинтов

```python
@app.get("/profile")
async def get_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # current_user автоматически извлекается из JWT токена
    profile = db.query(models.AthleteProfileDB).filter(
        models.AthleteProfileDB.user_id == current_user.id
    ).first()
    return profile
```

### Strava OAuth Flow

```
1. Пользователь нажимает "Connect Strava" (/coach)
   ↓
2. Frontend формирует URL:
   GET /auth/strava/login?state={base64_encoded_jwt}
   (state содержит JWT токен пользователя)
   ↓
3. Backend редиректит на Strava:
   https://www.strava.com/oauth/authorize?
     client_id=...
     &redirect_uri=...
     &state={jwt_token}
   ↓
4. Пользователь авторизуется в Strava
   ↓
5. Strava редиректит на:
   GET /auth/strava/callback?code=...&state={jwt_token}
   ↓
6. Backend:
   - Декодирует state → получает user_id
   - Обменивает code на access/refresh токены
   - Сохраняет токены в User.strava_* поля
   ↓
7. Возвращает HTML с редиректом на /coach
```

**Важно:** `state` параметр используется для идентификации пользователя, т.к. в OAuth callback нет `Authorization` заголовка.

---

## Интеграции

### 1. Strava API

**OAuth 2.0 Flow:**
- Authorization Code Grant
- Scopes: `read`, `activity:read_all`
- Refresh token для обновления access token

**Основные эндпоинты Strava:**
- `GET /athlete/activities` — список активностей
- `GET /activities/{id}` — детали активности
- `GET /segments/{id}` — информация о сегменте
- `GET /segments/explore` — поиск сегментов

**Реализация:** `strava_client.py`

### 2. OpenAI GPT

**Использование:**
- Модель: `gpt-4o` (или `gpt-4-turbo`)
- JSON mode для структурированных ответов
- System prompt в `prompts/trainer_prompt.py`

**Основные функции:**
- Генерация недельных планов
- Initial assessment
- Прогнозы результатов
- Анализ прогресса

**Реализация:** `coach.py`, `performance_predictions.py`

### 3. Email (Resend)

**Использование:**
- Отправка недельных планов
- Отправка отчетов
- Экспорт календарей (.ics)

**Реализация:** `email_resend.py`

---

## Потоки данных

### 1. Генерация недельного плана

```
Frontend: POST /coach/plan
  ↓
Backend:
  1. Получает primary goal из БД
  2. Загружает профиль атлета
  3. Загружает последние 12 недель из Strava
  4. Формирует промпт для GPT
  5. Вызывает OpenAI API
  6. Парсит JSON ответ
  7. Сохраняет план в WeeklyPlanDB
  8. Возвращает план
  ↓
Frontend: Отображает план на /dashboard
```

### 2. Автоматический расчет зон

```
Frontend: POST /zones/calculate?activity_type=run
  ↓
Backend:
  1. Загружает активности из Strava
  2. Ищет лучшие усилия (5K, 10K, HM, Marathon)
  3. Рассчитывает зоны по формулам (VDOT, etc.)
  4. Сохраняет в AthleteProfileDB.training_zones_run
  5. Обновляет JSON профиль (legacy)
  6. Возвращает зоны
  ↓
Frontend: Отображает зоны на /dashboard
```

### 3. Синхронизация активностей Strava

```
Пользователь подключает Strava
  ↓
Backend сохраняет токены в User
  ↓
При запросе активностей:
  1. Проверяет срок действия токена
  2. Если истек → обновляет через refresh_token
  3. Загружает активности из Strava API
  4. Кэширует в ActivityDB
  5. Возвращает активности
```

### 4. Анализ риска травм

```
Frontend: GET /analytics/injury_risk
  ↓
Backend:
  1. Загружает последние 4-8 недель активностей
  2. Анализирует:
     - Резкое увеличение объема
     - Частота тренировок
     - Восстановление между тренировками
     - Интенсивность
  3. Рассчитывает risk_score (0-100)
  4. Определяет risk_level (low/moderate/high)
  5. Формирует рекомендации
  6. Возвращает результат
  ↓
Frontend: Отображает в InjuryRiskCard
```

---

## Деплой и инфраструктура

### Railway Deployment

**Backend Service:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `DATABASE_URL` (PostgreSQL)
  - `SECRET_KEY`
  - `OPENAI_API_KEY`
  - `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`
  - `FRONTEND_BASE_URL`

**Frontend Service:**
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Root Directory**: `frontend/`
- **Nixpacks Config**: `frontend/nixpacks.toml` (Node.js 20)

### GitHub Actions CI/CD

```yaml
# .github/workflows/ci.yml
- name: Deploy backend
  run: |
    railway link --service backend
    railway up --service backend

- name: Deploy frontend
  run: |
    railway link --service frontend
    railway up --service frontend
```

**Триггеры:**
- Push в `main` ветку
- Pull request (только тесты)

### Database Migrations

**Production:**
```bash
# На Railway через CLI или вручную
alembic upgrade head
```

**Development:**
```bash
# Автоматически при старте (init_db)
# Или вручную:
alembic upgrade head
```

---

## Безопасность

### 1. Аутентификация

- **JWT токены** с expiration (24 часа)
- **Bcrypt** для хеширования паролей
- **HTTPS only** в production

### 2. CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[...],  # Только разрешенные домены
    allow_origin_regex=r"https://.*\.up\.railway\.app",
    allow_credentials=True,
)
```

### 3. Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/coach/plan")
@limiter.limit("10/minute")
async def generate_plan(...):
    ...
```

### 4. Валидация данных

- **Pydantic** схемы для всех входных данных
- **SQLAlchemy** для защиты от SQL injection
- **Type checking** на фронтенде (TypeScript)

### 5. Secrets Management

- Все секреты в переменных окружения
- Не коммитятся в Git
- Управляются через Railway dashboard

---

## Заключение

Проект использует современный стек технологий с четким разделением ответственности:

- **Backend**: FastAPI + SQLAlchemy + JWT
- **Frontend**: Next.js + React Query + TypeScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Deployment**: Railway + GitHub Actions

Архитектура масштабируема и готова к добавлению новых функций.

---

**Последнее обновление:** 2025-12-09
**Версия документации:** 1.0

