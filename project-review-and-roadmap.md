# 🏃‍♂️ AI Triathlon Coach - Полный анализ и дорожная карта развития

## 📊 Текущее состояние проекта (Декабрь 2025)

### ✅ Что уже реализовано и работает хорошо

#### 1. **Архитектура и техническая база (9/10)**

**Backend (FastAPI + PostgreSQL):**
- ✅ Многопользовательская система с JWT-аутентификацией
- ✅ Полноценная база данных с 11 таблицами (Users, Activities, Goals, Plans, etc.)
- ✅ SQLAlchemy ORM + Alembic миграции
- ✅ Rate limiting и CORS настроены правильно
- ✅ Async/await для всех операций
- ✅ Структурное логирование (structlog)

**Frontend (Next.js 16 + TypeScript):**
- ✅ App Router архитектура
- ✅ Полная типизация TypeScript
- ✅ Адаптивный дизайн (Tailwind CSS)
- ✅ Axios клиент с перехватчиками для JWT

**Оценка:** Архитектура на уровне production-ready стартапа. Можно масштабировать на тысячи пользователей.

#### 2. **Интеграции (8/10)**

**Strava API:**
- ✅ OAuth 2.0 flow с refresh token
- ✅ Автоматическая синхронизация активностей
- ✅ Кеширование в базе данных
- ✅ Поддержка всех видов спорта (run, bike, swim, triathlon)

**OpenAI GPT:**
- ✅ Генерация недельных планов
- ✅ Многонедельные планы (до 12 недель)
- ✅ JSON mode для структурированных ответов
- ✅ Учет истории тренировок в промпте

**Email (Resend):**
- ✅ HTML отчеты
- ✅ Экспорт календарей (.ics)
- ✅ Автоматические недельные отчеты

**Что можно улучшить:**
- ⚠️ Нет интеграции с Garmin/Polar/Apple Watch
- ⚠️ Нет webhook от Strava для реалтайм обновлений

#### 3. **Функциональность (7/10)**

**Что работает отлично:**

✅ **Профиль атлета:**
- Возраст, пол, вес, рост, опыт
- Автоматический расчет метрик из истории Strava
- Тренировочные зоны (HR, pace, power) для всех дисциплин

✅ **Цели и планирование:**
- Создание целей (Sprint, Olympic, Half IM, Full IM, etc.)
- Генерация персонализированных планов через GPT
- Учет доступных часов в неделю
- План vs факт анализ

✅ **Аналитика тренировок:**
- CTL (Chronic Training Load) - fitness
- ATL (Acute Training Load) - fatigue  
- TSB (Training Stress Balance) - form
- Графики за 90 дней
- Определение риска перетренированности

✅ **Отчеты и экспорт:**
- Недельные HTML-отчеты на email
- 12-недельные планы с фазами
- .ics файлы для календаря

**Что реализовано в backend, но НЕ на frontend (40% функционала):**

❌ **Analytics (5 эндпоинтов готовы):**
- Анализ нагрузки с ramp rate
- Статус формы (Fresh/Fatigued/Optimal)
- Детекция усталости (HR drift, pace decline)
- Прогноз времени на гонку
- Прогнозы для всех дистанций

❌ **Nutrition (5 эндпоинтов готовы):**
- Расчет калорий и макронутриентов
- Планы питания на гонку
- Pre-race, during-race, recovery стратегии

❌ **Segments & PRs (10 эндпоинтов готовы):**
- Отслеживание любимых сегментов Strava
- Личные рекорды на всех дистанциях
- История улучшений
- Предупреждения о рисках травм

❌ **Recent Activities:**
- Список последних тренировок из Strava
- Детальная статистика по каждой

---

## 🎯 Дорожная карта развития

### **ФАЗА 1: Завершение текущего функционала (2-3 недели)**

#### Приоритет 1: Подключить готовые backend эндпоинты к фронтенду

**Неделя 1-2: Analytics Enhancement**

```typescript
// Что добавить на Dashboard:

1. 📊 Current Form Card
   - Fresh/Optimal/Fatigued status
   - Цветовая индикация (зеленый/желтый/красный)
   - Рекомендации на основе формы

2. ⚠️ Fatigue Warning Banner
   - Появляется при high fatigue score
   - Показывает детекцию усталости:
     * HR drift > 5%
     * Pace decline > 10%
     * Days without rest
   - Конкретные рекомендации (rest day, easy workouts)

3. 🎯 Race Predictions Card
   - Прогноз времени на primary goal
   - Вероятность достижения цели (%)
   - Рекомендуемые пейсы для гонки
   - Predictions для всех дистанций (5K, 10K, HM, Marathon)

4. 📈 Recent Activities Section
   - Последние 10 тренировок
   - Компактные карточки с:
     * Sport type icon
     * Distance, time, pace
     * Elevation gain
     * TSS (если есть)
   - Клик → детальная информация
```

**Реализация:**
```bash
# День 1-2: API Functions
frontend/lib/api.ts
  + analyticsAPI.getFormStatus()
  + analyticsAPI.getFatigueAnalysis()
  + analyticsAPI.predictRace()
  + analyticsAPI.getAllPredictions()
  + stravaAPI.getActivities()

# День 3-4: Components
frontend/components/FormStatusCard.tsx
frontend/components/FatigueWarningBanner.tsx
frontend/components/RacePredictionCard.tsx
frontend/components/ActivityCard.tsx

# День 5-6: Integration в Dashboard
app/dashboard/page.tsx
  - Добавить новые компоненты
  - Параллельные API calls
  - Loading states
  - Error handling
```

**Неделя 3: Nutrition & Segments Pages**

```bash
# Nutrition Page
frontend/app/nutrition/page.tsx
  [Section 1] Daily Targets Calculator
    - Weight, height, activity level
    - Goals (maintain/lose/gain weight)
    - Результат: калории + carbs/protein/fat
  
  [Section 2] Race Fueling Planner
    - Race type selector
    - Expected race time
    - Результат: pre-race meal plan, during-race gels/drinks, recovery

# Segments/Performance Page  
frontend/app/segments/page.tsx
  [Section 1] Favorite Segments
    - Список сегментов с картой
    - PR time на каждом
    - История улучшений (график)
  
  [Section 2] Personal Records
    - PRs по дистанциям (5K, 10K, HM, Marathon, 40K TT)
    - График прогресса за год
    - Predictions vs Actual
  
  [Section 3] Injury Risk Warnings
    - Active warnings (high priority)
    - История resolved warnings
```

**Результат Фазы 1:**
- ✅ 100% готового backend функционала подключено к frontend
- ✅ Dashboard становится полноценным аналитическим центром
- ✅ 2 новые страницы: Nutrition + Segments/Performance
- ✅ Проект готов к публичному запуску (MVP+)

---

### **ФАЗА 2: Улучшение AI и UX (3-4 недели)**

#### 2.1. Умный AI тренер (1 неделя)

**Проблема:** Текущий промпт для GPT слишком общий, планы могут быть неоптимальными.

**Решение: Переписать промпт с:**

1. **Конкретными формулами тренировочных зон:**
```
Running Zones (% of Threshold HR or Pace):
  Zone 1 (Recovery): <70% HR, very easy conversation
  Zone 2 (Endurance): 70-80% HR, easy conversation  
  Zone 3 (Tempo): 80-88% HR, short sentences
  Zone 4 (Threshold): 88-92% HR, few words
  Zone 5 (VO2max): 92-97% HR, no talking

Polarized Training: 80% Zone 1-2, 20% Zone 4-5
```

2. **Примерами идеальных планов:**
```
Example: Olympic Distance (12 weeks out, 8 hrs/week):
Monday: Rest or easy 30min recovery run
Tuesday: Swim 45min (technique drills + 5x100m @Zone4)
Wednesday: Bike 90min (2hr endurance Zone 2)
Thursday: Run 60min (10min warmup, 5x5min @threshold, 10min cool)
Friday: Swim 45min (open water practice if available)
Saturday: Brick: Bike 2hr Zone 2 → Run 30min off the bike
Sunday: Long run 90min Zone 2 (conversational pace)
```

3. **Race-specific периодизацией:**
```
Full Ironman 20-week plan phases:
Weeks 1-4: Base building (volume focus, low intensity)
Weeks 5-8: Build 1 (introduce tempo work)
Weeks 9-12: Build 2 (threshold + VO2max intervals)
Weeks 13-16: Peak (race-specific work, brick sessions)
Weeks 17-19: Taper (reduce volume 30%→50%→70%)
Week 20: Race week (minimal training, stay loose)
```

4. **Персонализацией по профилю:**
```python
# В промпте учитывать:
- Age: если > 40 → больше recovery, меньше интенсивности
- Gender: женщины → другая периодизация во время менструального цикла
- Experience: beginners → больше техники, меньше volume
- Injury history: если были травмы → больше strength training
```

**Реализация:**
```python
# prompts/trainer_prompt.py - полностью переписать
TRAINING_ZONES_GUIDE = """
[Detailed zones with formulas, %HR, RPE, descriptions]
"""

RACE_SPECIFIC_STRATEGIES = {
    "SPRINT": "[Sprint-specific pacing, transitions, etc]",
    "OLYMPIC": "[...]",
    "HALF_IRONMAN": "[...]", 
    "IRONMAN": "[...]"
}

EXAMPLE_PLANS = [
    # 5 примеров планов с комментариями коуча
]

def generate_enhanced_prompt(profile, goal, history):
    """Строит промпт с учетом всего контекста"""
    # ...
```

#### 2.2. Улучшенная визуализация (1 неделя)

**Текущая проблема:** Графики базовые, мало инсайтов.

**Что добавить:**

1. **Interactive Performance Chart**
```typescript
// Вместо простого line chart:
- Zoom & Pan
- Hover tooltips с деталями тренировки
- Маркеры ключевых событий (race day, illness, тяжелые недели)
- Переключение метрик (CTL/ATL/TSB, Hours, TSS, Distance)
- Export to PNG
```

2. **Training Distribution Donut Chart**
```
Pie chart показывающий:
- % времени в каждой зоне (Zone 1, 2, 3, 4, 5)
- Текущее vs оптимальное (80/20 rule)
- Warning если слишком много высокой интенсивности
```

3. **Volume & Intensity Heatmap**
```
Calendar heatmap (как на GitHub):
- Каждый день = квадрат
- Цвет = training load (зеленый→желтый→красный)
- Клик → детали дня
```

4. **Goal Progress Arc**
```
Circular progress indicator:
- Weeks until race (countdown)
- Readiness score 0-100%
- Predicted finish time vs goal
```

#### 2.3. Mobile-First UX (2 недели)

**Проблема:** Сейчас дизайн работает на мобильных, но не оптимизирован.

**Решение:**

1. **Bottom Navigation** (как в Instagram/Strava):
```
[Dashboard] [Coach] [Activities] [Goals] [Profile]
```

2. **Swipeable Cards** для планов:
```typescript
// Свайп влево/вправо между днями недели
<SwipeableViews>
  <DayCard day="Monday" />
  <DayCard day="Tuesday" />
  ...
</SwipeableViews>
```

3. **Quick Actions Floating Button**:
```
FAB (floating action button):
  - Sync Strava
  - Generate plan
  - Log manual workout
```

4. **Progressive Web App (PWA)**:
```json
// next.config.ts + manifest.json
{
  "name": "AI Triathlon Coach",
  "short_name": "AI Coach",
  "display": "standalone",
  "start_url": "/dashboard",
  "icons": [...]
}
```

---

### **ФАЗА 3: Продвинутые фичи (4-6 недель)**

#### 3.1. Multi-Sport Events Support (1 неделя)

**Сейчас:** Только триатлон + отдельные виды спорта.

**Добавить:**

1. **Duathlon**
```python
# models.py
goal_type = "DUATHLON_SPRINT"  # 5K run + 20K bike + 2.5K run
goal_type = "DUATHLON_STANDARD" # 10K run + 40K bike + 5K run
```

2. **Aquathlon**
```python
goal_type = "AQUATHLON"  # Swim + Run
```

3. **Ultra Distance**
```python
goal_type = "ULTRA_MARATHON_50K"
goal_type = "ULTRA_MARATHON_100K"
goal_type = "ULTRA_TRAIL"  # с набором высоты
```

4. **Custom Events**
```typescript
interface CustomGoal {
  name: string;
  disciplines: Array<{
    sport: 'swim' | 'bike' | 'run';
    distance: number;
    order: number;
  }>;
  totalTime: string;
}

// Example: 
// Swim 3.8km → Bike 180km → Run 42.2km (Full Ironman custom)
```

#### 3.2. Команда и тренер (2 недели)

**Концепция:** Режим для тренеров, работающих с группой атлетов.

```python
# models.py
class Coach(Base):
    __tablename__ = "coaches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    coach_name = Column(String)
    certification = Column(String)  # "USAT Level 1", etc
    bio = Column(Text)
    
    # Relationships
    athletes = relationship("AthleteCoachLink", back_populates="coach")

class AthleteCoachLink(Base):
    __tablename__ = "athlete_coach_links"
    id = Column(Integer, primary_key=True)
    athlete_user_id = Column(Integer, ForeignKey("users.id"))
    coach_id = Column(Integer, ForeignKey("coaches.id"))
    status = Column(String)  # "pending", "active", "inactive"
    created_at = Column(DateTime)
```

**Фичи для тренера:**
- Dashboard со всеми атлетами
- Bulk план generation (один клик → планы для всех)
- Messaging система (чат с атлетами)
- Progress tracking (как атлеты выполняют планы)
- Templates (сохранить план и переиспользовать)

**Фичи для атлета:**
- Invite coach by email
- Share training data
- Receive customized feedback
- Ask questions

#### 3.3. Социальные функции (1 неделя)

**Зачем:** Мотивация через community.

```python
# models.py
class TrainingGroup(Base):
    __tablename__ = "training_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    location = Column(String)  # "San Francisco, CA"
    created_by = Column(Integer, ForeignKey("users.id"))

class GroupMembership(Base):
    __tablename__ = "group_memberships"
    group_id = Column(Integer, ForeignKey("training_groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)  # "admin", "member"

class Activity_Comment(Base):
    __tablename__ = "activity_comments"
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    comment_text = Column(Text)
    created_at = Column(DateTime)
```

**Фронтенд:**
```typescript
// app/community/page.tsx
- Training groups в твоем городе
- Group challenges (кто больше км за месяц)
- Activity feed (как в Strava)
- Kudos/comments на тренировки
```

#### 3.4. Advanced Analytics (2 недели)

**1. Performance Testing**
```python
# Новый эндпоинт
@app.post("/analytics/performance-test")
async def run_performance_test(
    test_type: str,  # "FTP", "VO2max", "Critical_Power"
    activity_id: int,
    current_user = Depends(get_current_user)
):
    """
    Анализ тестовых тренировок для определения:
    - FTP (Functional Threshold Power)
    - VO2max estimate
    - Critical Power (CP)
    - Lactate Threshold Heart Rate
    """
```

**2. Training Peaks Integration**
```python
# Формулы из TrainingPeaks:
- Intensity Factor (IF) = NP / FTP
- Variability Index (VI) = NP / AP
- Efficiency Factor (EF) = NP / Average HR
```

**3. Weather-Adjusted Predictions**
```python
# Учитывать погоду на гонке:
@app.get("/analytics/race-weather")
async def get_race_weather_impact(
    goal_id: int,
    current_user = Depends(get_current_user)
):
    """
    - Температура (heat acclimatization needed?)
    - Влажность (dehydration risk)
    - Ветер (pacing strategy adjustment)
    - Высота (altitude acclimatization)
    """
```

---

### **ФАЗА 4: Масштабирование и монетизация (8-12 недель)**

#### 4.1. Pricing Tiers

**Free Tier:**
- 1 active goal
- Basic weekly plans (GPT-3.5)
- Basic analytics (CTL/ATL/TSB)
- Strava sync
- 10 GPT requests/month

**Pro ($9.99/month):**
- Unlimited goals
- Advanced plans (GPT-4)
- Full analytics + predictions
- Nutrition plans
- Segments tracking
- Email reports
- 100 GPT requests/month

**Coach ($29.99/month):**
- Все из Pro
- До 20 атлетов
- Team dashboard
- Bulk planning
- Templates library
- Priority support
- Unlimited GPT requests

**Team ($99/month):**
- Для команд/клубов
- До 100 атлетов
- Group challenges
- Custom branding
- API access
- Dedicated account manager

#### 4.2. Реализация платежей

```python
# Добавить Stripe
pip install stripe

# models.py
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String)  # "free", "pro", "coach", "team"
    stripe_subscription_id = Column(String)
    status = Column(String)  # "active", "canceled", "past_due"
    current_period_end = Column(DateTime)

# api_billing.py
@router.post("/subscribe")
async def create_subscription(
    plan: str,
    payment_method_id: str,
    current_user = Depends(get_current_user)
):
    # Create Stripe subscription
    # Update user's plan
    # Enable/disable features
```

**Frontend:**
```typescript
// app/pricing/page.tsx
- Pricing table с 4 тирами
- Feature comparison
- "Start 14-day free trial" CTA

// app/settings/billing/page.tsx
- Current plan
- Usage stats (GPT requests used)
- Payment method
- Billing history
- Cancel/upgrade
```

#### 4.3. Mobile Apps (10-12 недель)

**Подход: React Native (code sharing с web)**

```bash
# Структура monorepo
ai-coach/
├── packages/
│   ├── shared/           # Shared code
│   │   ├── types/
│   │   ├── api/
│   │   └── utils/
│   ├── web/              # Next.js app (current frontend)
│   ├── mobile/           # React Native
│   └── backend/          # FastAPI (current)
```

**Фичи mobile app:**
1. Offline-first (sync when online)
2. Push notifications:
   - "Time for your workout!"
   - "Great job on today's run! 🎉"
   - "New weekly plan is ready"
3. Widget для iOS/Android:
   - Today's workout
   - CTL/ATL/TSB
   - Days to race
4. Watch app (Apple Watch/Wear OS):
   - Display workout
   - Live HR zones
   - Pace alerts

#### 4.4. Интеграции

**Priority integrations:**

1. **Garmin Connect**
```python
# Больше данных:
- Advanced Running Dynamics
- Training Effect
- Recovery Time
- HRV (Heart Rate Variability)
```

2. **Polar Flow**
3. **Wahoo**
4. **TrainingPeaks** (import/export)
5. **Zwift** (virtual training)

**Webhooks для реалтайм обновлений:**
```python
@app.post("/webhooks/strava")
async def strava_webhook(request: Request):
    """
    Strava webhook: новая тренировка → автоматом обновить CTL/ATL/TSB
    """
```

---

## 🚀 Quick Wins (можно сделать за выходные)

### 1. Dark Mode (4 часа)
```typescript
// app/layout.tsx + Tailwind config
- Добавить theme toggle
- dark: классы для всех компонентов
```

### 2. Activity Map (6 часов)
```typescript
// Показать маршрут тренировки на карте
// Используя polyline из Strava
import { MapContainer, Polyline } from 'react-leaflet';
```

### 3. Workout Library (8 часов)
```python
# Библиотека готовых тренировок
class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"
    name = Column(String)  # "Fartlek 10x1min"
    sport = Column(String)
    description = Column(Text)
    structure = Column(JSON)  # intervals, durations, zones

# Frontend: выбрать из библиотеки вместо AI generation
```

### 4. Export to PDF (6 часов)
```python
# Создавать красивый PDF с планом/отчетом
pip install reportlab

@app.post("/coach/export_plan_pdf")
async def export_plan_to_pdf(...):
    # Generate PDF
    return FileResponse("plan.pdf")
```

### 5. Sharable Training Plans (4 часа)
```python
# Поделиться планом по ссылке (как Google Docs)
class SharedPlan(Base):
    plan_id = Column(Integer, ForeignKey("weekly_plans.id"))
    share_token = Column(String, unique=True)  # UUID
    expires_at = Column(DateTime)

# GET /shared/plans/{share_token} - публичный доступ
```

---

## 💡 Innovative Ideas (для выделения на рынке)

### 1. AI Video Analysis
```python
# Загрузить видео техники бега/плавания
# GPT-4 Vision API → анализ формы, рекомендации

@app.post("/analyze-form")
async def analyze_running_form(video_file: UploadFile):
    """
    1. Extract frames
    2. Send to GPT-4 Vision
    3. Get feedback on:
       - Foot strike
       - Cadence
       - Arm swing
       - Posture
    """
```

### 2. Voice Coach
```python
# Голосовой AI тренер (как с наушниками во время тренировки)
# "Speed up to Zone 3", "Great pace!", "2 minutes left"

# Интеграция с OpenAI TTS + Whisper:
- Text-to-Speech для инструкций
- Speech-to-Text для voice commands
```

### 3. Virtual Training Partner
```python
# AI creates "virtual athlete" to train with
# Based on your level + goal

class VirtualPartner(Base):
    user_id = Column(Integer)
    name = Column(String)  # "Sarah (Olympic distance)"
    fitness_level = Column(JSON)  # CTL, FTP, etc
    personality = Column(String)  # "encouraging", "competitive"

# На тренировке видишь:
# "You're 30 seconds ahead of Sarah"
# "Sarah suggests slowing down to Zone 2"
```

### 4. Recovery Score (Whoop-style)
```python
# Ежедневный recovery score на основе:
- HRV (from Garmin/Apple Watch)
- Sleep quality
- Previous day's training load
- Self-reported soreness/mood

@app.get("/recovery/daily-score")
async def get_recovery_score():
    """
    Returns: 0-100% recovery
    Recommendations: rest / light / normal / hard workout
    """
```

### 5. Race Day Assistant
```python
# Special mode для дня гонки
@app.post("/race-day/start")
async def start_race_day_mode(goal_id: int):
    """
    Активирует:
    - Hour-by-hour nutrition reminders
    - Pacing alerts (send push at mile markers)
    - Weather updates
    - Gear checklist
    - Real-time adjustments based on conditions
    """
```

---

## 📈 Success Metrics

### Technical KPIs
- [ ] Backend test coverage > 80%
- [ ] Frontend test coverage > 60%
- [ ] API response time < 200ms (p95)
- [ ] Uptime > 99.9%
- [ ] Mobile app rating > 4.5/5

### Product KPIs
- [ ] User retention (Day 7) > 40%
- [ ] User retention (Day 30) > 20%
- [ ] Plans generated per user per month > 4
- [ ] Strava sync success rate > 95%
- [ ] Free-to-paid conversion > 5%

### Business KPIs
- [ ] 1000 active users (first 6 months)
- [ ] 100 paying users (first 6 months)
- [ ] MRR $1000 (first 6 months)
- [ ] 10,000 users (year 1)
- [ ] 1000 paying users (year 1)
- [ ] MRR $10,000 (year 1)

---

## 🛠️ Технические улучшения (детально)

### 1. Тестирование (критично перед запуском)

```python
# tests/test_coach.py
def test_weekly_plan_generation():
    """Test GPT plan generation with mocked response"""
    
def test_zones_calculation():
    """Test training zones formulas"""
    
def test_strava_oauth_flow():
    """Test full OAuth flow"""

# tests/test_integration.py  
def test_user_journey_end_to_end():
    """
    1. Register
    2. Connect Strava
    3. Set goal
    4. Generate plan
    5. Sync activities
    6. View analytics
    """
```

**Coverage targets:**
- Core business logic: 90%+
- API endpoints: 80%+
- Utils/helpers: 70%+

### 2. Мониторинг и наблюдаемость

```python
# Добавить
pip install sentry-sdk

# main.py
import sentry_sdk
sentry_sdk.init(dsn=SENTRY_DSN)

# Structured logging
import structlog
logger = structlog.get_logger()

# На каждый эндпоинт:
@app.post("/coach/plan")
async def generate_plan(...):
    logger.info("plan_generation_started", user_id=user.id)
    try:
        plan = ...
        logger.info("plan_generation_success", plan_id=plan.id)
    except Exception as e:
        logger.error("plan_generation_failed", error=str(e))
        sentry_sdk.capture_exception(e)
```

**Metrics to track:**
- GPT API latency
- Strava API errors
- Database query times
- User actions (plan generation, sync, etc)

### 3. Caching Strategy

```python
# Текущая проблема: каждый запрос тянет данные из Strava
# Решение: Redis cache

import redis
from functools import wraps

cache = redis.Redis(host='localhost', decode_responses=True)

def cached(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            cached_result = cache.get(key)
            if cached_result:
                return json.loads(cached_result)
            
            result = await func(*args, **kwargs)
            cache.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cached(ttl=7200)  # 2 hours
async def fetch_activities_for_user(user_id: int, weeks: int):
    # ...
```

**Cache invalidation:**
```python
# При новой синхронизации со Strava:
@app.post("/strava/sync")
async def sync_strava(current_user = Depends(get_current_user)):
    # Delete cache
    cache.delete(f"activities:{current_user.id}:*")
    # Fetch new data
    ...
```

### 4. Rate Limiting (per user)

```python
# Текущая проблема: rate limit по IP (shared IP issue)
# Решение: rate limit по user_id

from slowapi import Limiter
from slowapi.util import get_remote_address

def get_user_id(request: Request):
    # Extract user_id from JWT
    token = request.headers.get("Authorization")
    if token:
        payload = decode_token(token)
        return payload.get("sub")  # user_id
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_id)

@app.post("/coach/plan")
@limiter.limit("10/hour")  # 10 plans per hour per user
async def generate_plan(...):
    ...
```

### 5. Database Optimizations

```python
# Добавить индексы для частых запросов
from alembic import op

def upgrade():
    # Index на user_id + start_date для быстрого поиска активностей
    op.create_index(
        'ix_activities_user_start_date',
        'activities',
        ['user_id', 'start_date']
    )
    
    # Index на user_id + is_primary для поиска primary goal
    op.create_index(
        'ix_goals_user_primary',
        'goals',
        ['user_id', 'is_primary']
    )
    
    # Partial index только для активных целей
    op.execute("""
        CREATE INDEX ix_goals_active 
        ON goals (user_id) 
        WHERE is_completed = false
    """)
```

**Query optimization:**
```python
# До (N+1 queries):
users = db.query(User).all()
for user in users:
    profile = user.profile  # Отдельный запрос!

# После (1 query):
users = db.query(User).options(
    joinedload(User.profile)
).all()
```

---

## 🎨 UX/UI Improvements

### 1. Onboarding Flow (критично для retention)

**Текущий onboarding:**
1. Register
2. Set basic info
3. Set goal
4. → Dashboard

**Улучшенный onboarding (7 шагов):**

```typescript
// app/onboarding/page.tsx - переделать на wizard

Step 1: Welcome
  - "Hi! I'm your AI triathlon coach"
  - Explain what app does
  - [Let's get started]

Step 2: Your Experience
  - Slider: Beginner → Intermediate → Advanced → Elite
  - "How many years have you been training?"
  - Auto-suggestions based on level

Step 3: Connect Strava
  - "This helps me understand your current fitness"
  - [Connect Strava] button
  - Skip option (with warning)

Step 4: Your Goal
  - Big cards: Sprint / Olympic / 70.3 / Ironman
  - Race date picker
  - Target time (optional)

Step 5: Training Schedule
  - Calendar: mark available days
  - Slider: hours per week
  - Time of day preferences

Step 6: Your Profile
  - Age, gender, weight, height
  - Injury history (optional)
  - Equipment available

Step 7: First Plan
  - Generate initial assessment
  - Show preview of first week
  - [Go to Dashboard]

Total time: 3-5 minutes
```

### 2. Empty States

**Текущая проблема:** Когда нет данных, показываются пустые блоки.

**Решение:**
```typescript
// Everywhere в app:
{activities.length === 0 ? (
  <EmptyState
    icon={<RunningIcon />}
    title="No activities yet"
    description="Connect Strava or manually log your first workout"
    action={{
      label: "Connect Strava",
      onClick: () => router.push('/coach')
    }}
  />
) : (
  <ActivitiesList activities={activities} />
)}
```

### 3. Loading States (скелетоны)

```typescript
// components/SkeletonCard.tsx
export function SkeletonCard() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
    </div>
  );
}

// Использовать везде:
{isLoading ? (
  <SkeletonCard />
) : (
  <DataCard data={data} />
)}
```

### 4. Notifications System

```typescript
// context/NotificationContext.tsx
interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;  // auto-dismiss after X ms
}

// Использование:
const { showNotification } = useNotification();

onClick={() => {
  showNotification({
    type: 'success',
    title: 'Plan generated!',
    message: 'Your weekly plan is ready to view.'
  });
}}
```

### 5. Keyboard Shortcuts

```typescript
// Для power users
useKeyboardShortcuts({
  'g d': () => router.push('/dashboard'),  // Go to Dashboard
  'g c': () => router.push('/coach'),      // Go to Coach
  'g g': () => router.push('/goals'),      // Go to Goals
  'n p': () => generatePlan(),             // New Plan
  's s': () => syncStrava(),               // Sync Strava
  '?': () => toggleShortcutsHelp(),        // Show shortcuts
});
```

---

## 💰 Monetization Ideas (кроме subscriptions)

### 1. Marketplace для тренеров
```
- Тренеры создают и продают шаблоны планов
- 70/30 revenue split (70% тренеру, 30% платформе)
- "Buy 12-week Ironman plan from Coach Sarah - $49"
```

### 2. Premium AI Models
```
- Free tier: GPT-3.5-turbo
- Pro tier: GPT-4
- Elite tier: Claude 3 Opus ($19.99/month)
  → "Get the smartest AI coach with Claude Opus"
```

### 3. White Label для команд/клубов
```
- Триатлон-клубы покупают branded версию
- Их logo, цвета, домен
- $500/month + $5/athlete
```

### 4. Affiliate Program
```
- Recommended gear (bikes, shoes, nutrition)
- Amazon Associates / Specialized / Garmin affiliate links
- "Based on your profile, we recommend..."
- 5-10% commission on sales
```

### 5. Sponsored Content
```
- Ironman race registrations
- Training camps
- Nutrition products (gels, drinks)
- "Featured opportunity: Ironman Boulder - Register now"
```

---

## 🏁 Финальные рекомендации

### Что делать ПРЯМО СЕЙЧАС (эта неделя):

1. **День 1-2: Analytics на Dashboard**
   - Подключить готовые эндпоинты
   - Form status, fatigue warning, race predictions
   - Реальная польза для пользователей

2. **День 3-4: Recent Activities**
   - Показать последние тренировки
   - Сделать UX более живым

3. **День 5: Dark Mode**
   - Quick win для современного вида

4. **День 6-7: Testing & Bug Fixing**
   - Пройти весь user journey
   - Исправить все баги

### Следующие 2 недели:

1. **Улучшить AI промпт** (самое важное!)
   - Качество планов = ключевая ценность
   - 80% успеха продукта

2. **Создать Nutrition page**
   - Уникальная фича, которой нет у многих
   - Высокая ценность для триатлетов

3. **Segments & PRs page**
   - Gamification + мотивация
   - Интеграция со Strava

### Через месяц:

1. **Soft launch**
   - Пригласить 10-20 триатлетов протестировать
   - Собрать feedback
   - Итерировать

2. **Mobile PWA**
   - Progressive Web App работает на телефоне
   - Push notifications

3. **Pricing page**
   - Запустить Free + Pro tier
   - $9.99/month кажется fair

### Через 3 месяца:

1. **Public launch**
   - Product Hunt
   - Reddit r/triathlon
   - Strava athletes groups
   - Triathlon forums

2. **Mobile apps** (iOS + Android)
   - React Native
   - Widgets

3. **Coach tier**
   - Найти 3-5 тренеров для beta
   - Отточить функционал

---

## 🎯 TL;DR - Главное

### Сильные стороны твоего проекта:
✅ Отличная архитектура (production-ready)
✅ Много функционала уже готово в backend
✅ Уникальное сочетание: AI + Triathlon + Analytics
✅ Интеграции со Strava и OpenAI работают

### Главные проблемы:
⚠️ 40% backend функционала не подключено к frontend
⚠️ AI промпт слишком общий (планы могут быть лучше)
⚠️ Нет четкой монетизации
⚠️ Мало визуализаций и UX полировки

### 3 самых важных действия:
1. **Подключить Analytics к Dashboard** (2 дня)
   → Сразу видна польза приложения
   
2. **Переписать AI промпт** (1 неделя)
   → Качество планов = главная ценность
   
3. **Создать Pricing page** (1 день)
   → Ясная модель монетизации

### Твое конкурентное преимущество:
```
TrainingPeaks: $20/month, сложный, старый дизайн
Strava: нет AI, нет планов
Final Surge: $10/month, только для тренеров

Твой продукт:
- AI-powered планы (уникально!)
- Красивый современный UI
- Все-в-одном (планы + аналитика + прогнозы)
- $9.99/month (доступно)

Target: 10,000 пользователей × 10% conversion × $9.99 = $10k MRR
```

---

**Следующий шаг:** Дай знать, на какой части хочешь сфокусироваться, и я помогу с детальной реализацией! 🚀
