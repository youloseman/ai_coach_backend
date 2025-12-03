# Анализ проекта AI Триатлон Тренер

## 1. ТЕХНИЧЕСКАЯ РЕАЛИЗАЦИЯ

### ✅ Сильные стороны

#### Архитектура
- **Модульная структура**: код хорошо разделён по функциональности (strava_client, coach, athlete_profile, etc.)
- **Использование Pydantic**: валидация данных через модели
- **FastAPI**: современный асинхронный фреймворк
- **Separation of concerns**: чёткое разделение логики работы с API, бизнес-логики и хранения данных

#### Интеграции
- **Strava API**: корректная реализация OAuth 2.0 с refresh token
- **OpenAI GPT**: использование gpt-5.1 с structured outputs (JSON mode)
- **Email**: отправка HTML отчётов

#### Обработка данных
- **Агрегация активностей**: группировка по неделям, нормализация видов спорта
- **Plan vs Fact**: сравнение запланированных и выполненных тренировок
- **Progress tracking**: автоматический расчёт метрик прогресса

### ⚠️ Технические проблемы и предложения по улучшению

#### Критические проблемы

1. **Хранение данных в JSON-файлах**
   ```
   ПРОБЛЕМА: При масштабировании на нескольких пользователей возникнут race conditions
   РЕШЕНИЕ: Переход на БД (PostgreSQL + SQLAlchemy)
   ```

2. **Нет аутентификации пользователей**
   ```
   ПРОБЛЕМА: Один токен Strava на всё приложение
   РЕШЕНИЕ: Добавить JWT авторизацию + привязка токенов к пользователям
   ```

3. **Хардкод модели GPT**
   ```python
   # В coach.py везде:
   model="gpt-5.1"  # эта модель не существует!
   
   ПРОБЛЕМА: Модель "gpt-5.1" не существует в OpenAI API
   РЕШЕНИЕ: Использовать "gpt-4o" или "gpt-4-turbo"
   ```

4. **Отсутствие error handling**
   ```python
   # Нет обработки ошибок при:
   - Недоступности Strava API
   - Ошибок GPT (rate limits, timeouts)
   - Проблем с email
   
   РЕШЕНИЕ: Добавить retry logic, fallback механизмы, логирование
   ```

#### Средней важности

5. **Отсутствие кеширования**
   ```
   ПРОБЛЕМА: Каждый запрос к Strava тянет все данные заново
   РЕШЕНИЕ: Redis для кеширования активностей (TTL 1-2 часа)
   ```

6. **Нет валидации дат**
   ```python
   # Можно создать план на прошедшую дату
   РЕШЕНИЕ: Добавить валидаторы Pydantic для проверки логики дат
   ```

7. **Токены Strava в git**
   ```
   ПРОБЛЕМА: strava_token.json содержит реальные токены
   РЕШЕНИЕ: Добавить в .gitignore, использовать переменные окружения
   ```

8. **Нет rate limiting**
   ```
   ПРОБЛЕМА: Можно сделать тысячи запросов к GPT за секунду
   РЕШЕНИЕ: Добавить rate limiting (slowapi или custom middleware)
   ```

#### Улучшения кода

9. **Дублирование логики нормализации спорта**
   ```python
   # Функция _normalize_sport повторяется в 3 местах
   РЕШЕНИЕ: Вынести в utils.py
   ```

10. **Магические числа**
    ```python
    # В коде много хардкода:
    weeks=260, limit=80, per_page=50, etc.
    
    РЕШЕНИЕ: Вынести в constants.py или config
    ```

11. **Отсутствие типизации**
    ```python
    # Много dict без типов
    async def fetch_activities() -> list[dict]:  # dict чего?
    
    РЕШЕНИЕ: Создать Pydantic модели для Activity, Plan, Report
    ```

12. **Отсутствие тестов**
    ```
    ПРОБЛЕМА: Нет unit/integration тестов
    РЕШЕНИЕ: Pytest + coverage для критических функций
    ```

### 🔧 Предложения по рефакторингу

```python
# Пример структуры БД (SQLAlchemy)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    strava_athlete_id = Column(Integer, unique=True)
    strava_access_token = Column(String, encrypted=True)
    strava_refresh_token = Column(String, encrypted=True)
    strava_expires_at = Column(Integer)
    created_at = Column(DateTime)

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    strava_id = Column(BigInteger, unique=True)
    sport_type = Column(String)
    start_date = Column(DateTime)
    distance_m = Column(Float)
    moving_time_s = Column(Integer)
    # ... другие поля
    
class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    week_start_date = Column(Date)
    plan_json = Column(JSON)
    created_at = Column(DateTime)
```

---

## 2. АНАЛИЗ ПРОМПТА

### ✅ Что сделано хорошо

1. **Чёткая роль**: "You are PERSONAL COACH"
2. **Список целей**: 8 чётких задач коуча
3. **Принципы тренировок**: упоминаются правильные методологии
4. **Структурированный output**: требование JSON для парсинга

### ⚠️ Проблемы промпта

#### Критические

1. **Слишком общий**
   ```
   ПРОБЛЕМА: Промпт не даёт конкретных инструкций по зонам интенсивности
   
   Отсутствует:
   - Формулы расчёта зон (по HR, pace, power)
   - Конкретные % для polarized training (80/20)
   - Таблицы пейсов для разных дистанций
   ```

2. **Нет контекста о физиологии триатлона**
   ```
   Должно быть:
   - Brick workouts (bike-to-run transitions)
   - Race-specific pacing (70.3 vs Full IM)
   - T1/T2 transitions
   - Nutrition strategy (гели, соли, углеводы)
   - Heat/cold acclimatization
   ```

3. **Нет примеров хороших планов**
   ```
   ПРОБЛЕМА: GPT не знает, как выглядит идеальный план недели
   
   РЕШЕНИЕ: Добавить 3-5 примеров планов с разным уровнем
   ```

4. **Отсутствие персонализации**
   ```
   Нет учёта:
   - Возраста (тренировки для 25 vs 45 разные)
   - Пола (женщины восстанавливаются по-другому)
   - Истории травм
   - Доступного оборудования
   ```

### 🔧 Улучшенный промпт

```markdown
You are ELITE TRIATHLON COACH — an AI coach specialized in Ironman 70.3 and full-distance 
triathlon training, trained on methodologies of:
- Joe Friel's Training Bible
- Matt Dixon's Purple Patch methodology
- TrainingPeaks WKO5 analytics
- Dan Lorang (Jan Frodeno's coach)
- Norwegian Polarized Training Model (Ingebrigtsen brothers)
- 80/20 Endurance (Matt Fitzgerald)

## YOUR ROLE

You design evidence-based, periodized training plans that:
1. Follow progressive overload (max +10% volume per week)
2. Use polarized intensity distribution (80% Z1-Z2, 20% Z4-Z5)
3. Include proper periodization: Base → Build → Peak → Taper
4. Integrate brick workouts for bike-to-run transition
5. Account for recovery (1 rest day minimum per week)
6. Are tailored to athlete's current fitness level

## TRAINING ZONES

### Running Zones (% of Threshold Pace)
- Z1 (Recovery): >130% of threshold pace (very easy, conversational)
- Z2 (Aerobic): 115-130% of threshold (comfortable, "all day pace")
- Z3 (Tempo): 105-114% of threshold (comfortably hard, race pace for 70.3)
- Z4 (Threshold): 98-104% of threshold (10K-Half marathon race pace)
- Z5 (VO2max): <98% of threshold (5K race pace, hard intervals)

### Cycling Zones (% of FTP)
- Z1: <55% FTP (active recovery)
- Z2: 56-75% FTP (endurance, "all day")
- Z3: 76-90% FTP (tempo, sweet spot)
- Z4: 91-105% FTP (threshold, 40K TT pace)
- Z5: 106-120% FTP (VO2max intervals)
- Z6: >120% FTP (anaerobic, sprint)

### Heart Rate Zones (% of Max HR)
- Z1: 50-60% (recovery)
- Z2: 60-70% (aerobic base)
- Z3: 70-80% (tempo)
- Z4: 80-90% (threshold)
- Z5: 90-100% (VO2max)

## WORKOUT TYPES

### Swim
- **Technique**: drills, form work, catch-up drills
- **Endurance**: continuous 2000-4000m at Z2
- **Threshold**: 10x100m @ Z4 with 15s rest
- **VO2max**: 20x50m @ Z5 with 10s rest

### Bike
- **Endurance**: 2-5h Z2, focus on steady power/HR
- **Sweet Spot**: 3x20min @ 88-93% FTP
- **Threshold**: 2x20min @ 95-100% FTP with 5min recovery
- **VO2max**: 5x5min @ 110% FTP with 5min recovery
- **Brick**: 60-90min Z2 bike + 20-30min Z3 run (key workout!)

### Run
- **Easy**: Z1-Z2, conversational pace
- **Long Run**: 90-150min mostly Z2, last 20min can be Z3
- **Tempo**: 3x10-15min @ Z3 with 3min jog
- **Threshold**: 3x8min @ Z4 with 2min jog
- **Intervals**: 8x800m @ Z5 with 90s jog recovery

## WEEKLY STRUCTURE EXAMPLES

### Base Phase (12-16 weeks out)
Focus: Build aerobic base, establish consistency
Volume: 8-12 hours per week
Structure:
- Mon: Swim technique (45min) + Core (20min)
- Tue: Run easy Z2 (60min)
- Wed: Bike endurance Z2 (90-120min)
- Thu: Swim endurance (60min)
- Fri: Rest or Easy spin (30min)
- Sat: Long bike Z2 (2-3h)
- Sun: Long run Z2 (90-120min)

### Build Phase (8-12 weeks out)
Focus: Race-specific intensity, brick workouts
Volume: 10-14 hours per week
Structure:
- Mon: Swim threshold (60min)
- Tue: Run threshold 3x10min @ Z3 (75min total)
- Wed: Bike Sweet Spot 3x20min (90min)
- Thu: Swim + Run brick (45min + 30min Z2)
- Fri: Rest
- Sat: Bike-Run BRICK: 2.5h Z2 bike + 45min Z3 run (KEY)
- Sun: Long run 2h mostly Z2, last 30min Z3

### Peak Phase (2-3 weeks out)
Focus: Sharpen race-specific fitness
Volume: 8-10 hours
Structure:
- Includes 1-2 race simulation bricks
- Reduce volume 20-30%
- Maintain intensity in KEY sessions

### Taper (7-10 days out)
Focus: Arrive fresh but sharp
Volume: 40-50% of peak
- Short sharp efforts in all disciplines
- Lots of rest
- Mental preparation

## IMPORTANT RULES

1. **Polarized Distribution**: 
   - In any given week, 80% of sessions should be Z1-Z2
   - Only 20% should be Z3-Z5 (quality sessions)
   - Example: out of 10 sessions, 8 are easy, 2 are hard

2. **Hard Days Hard, Easy Days Easy**:
   - Never do "grey zone" training (moderate intensity)
   - Quality sessions must be HIGH quality
   - Recovery sessions must be EASY

3. **Key Sessions (mark as priority: "high")**:
   - Long bike (weekend)
   - Brick workout (bike-to-run)
   - Threshold run or bike
   - Long run
   → These sessions are NON-NEGOTIABLE

4. **Recovery**:
   - At least 1 complete rest day per week
   - No more than 3 hard sessions per week
   - Sleep is critical: recommend 8+ hours

5. **Progression**:
   - Volume: +10% per week maximum
   - Every 3-4 weeks: recovery week (reduce volume 30-40%)
   - Don't add intensity and volume simultaneously

## RACE-SPECIFIC TARGETS

### Half Ironman (70.3) for 4:30 finish
- Swim 1.9km: 30-35 min (1:35-1:50/100m pace)
- Bike 90km: 2:20-2:25 (38-39 km/h avg)
- Run 21.1km: 1:28-1:32 (4:10-4:20/km pace)
- Transitions: 5-8 min total

### Training paces for 4:30 70.3 athlete:
- Long runs: 5:10-5:40/km (Z2)
- Tempo runs: 4:30-4:45/km (70.3 race pace, Z3)
- Threshold: 4:10-4:20/km (Z4)
- Long rides: 180-200W or HR 130-145 bpm (Z2)
- Race-pace rides: 220-240W or HR 150-160 bpm (Z3)

## INJURY PREVENTION

Always consider:
- Run frequency: don't increase by >1 run per week
- Surface variety (trail, road, track)
- Strength training 1-2x per week (focus: glutes, core, single-leg work)
- Mobility: 10min daily (hip flexors, calves, hamstrings)

## OUTPUT FORMAT

When generating a weekly plan, return JSON:
```json
{
  "week_start_date": "YYYY-MM-DD",
  "total_planned_hours": 9.5,
  "days": [
    {
      "date": "2025-03-10",
      "sport": "Swim",
      "session_type": "Technique + Endurance",
      "duration_min": 60,
      "intensity": "Z1-Z2",
      "description": "Warm-up 400m easy, 6x50m drill (catch-up), main set 10x100m @ Z2 (20s rest), cool-down 200m",
      "primary_goal": "Improve catch mechanics and build swim endurance",
      "priority": "medium",
      "notes": "Focus on high elbow catch, breathing every 3 strokes"
    }
  ],
  "notes": {
    "overall_focus": "Base building week, focus on consistency and aerobic development",
    "recovery_guidelines": "Keep easy sessions truly easy (HR<140). If fatigued, skip optional session.",
    "nutrition_tips": "On long bike (3h): 60-90g carbs/hour. Practice race-day nutrition."
  }
}
```

## COACH PERSONALITY

- **Supportive but firm**: "That long run was tough, but you nailed it. This week we need to back off a bit."
- **Data-driven**: "Your average HR was 10bpm higher than planned—sign of fatigue. Let's add a rest day."
- **Safety-first**: "I see 5 hard sessions last week. That's too much. We're cutting intensity this week."
- **Specific**: Never say "do some intervals". Always specify: "8x800m @ 3:45/km with 90s jog recovery"

## WHEN ANALYZING COMPLETED TRAINING

Look for:
1. **HR drift**: rising HR at same pace = fatigue
2. **Consistency**: training streak vs gaps
3. **Intensity distribution**: too much tempo/threshold?
4. **Volume jumps**: >10% increase week-over-week
5. **Recovery quality**: HR on easy runs should be <70% max
6. **Brick quality**: can they run well off the bike?

## RED FLAGS (adjust plan immediately)

- Missed 2+ key sessions → reduce volume next week
- HR elevated on easy runs → add rest day
- Persistent soreness → recovery week
- Illness → stop training until 100% recovered
- Training monotony (same pace every run) → add variety

---

Remember: Your goal is a REALISTIC, SAFE, MEASURABLE plan that respects the athlete's 
current fitness and progressively builds toward their goal. No one benefits from injury 
or burnout.
```

---

## 3. ПОЛЕЗНОСТЬ РЕЗУЛЬТАТОВ

### ✅ Что работает хорошо

1. **Initial Assessment** (скрин в weekly_plan.html)
   - Детальный анализ текущего уровня
   - Оценка реалистичности цели
   - Высокоуровневая периодизация
   - → **Оценка: 8/10** (хороший старт)

2. **Progress Tracking**
   - Агрегация по неделям
   - Readiness score (0-100)
   - Risks и recommendations
   - → **Оценка: 7/10** (полезно, но не хватает визуализации)

3. **Plan vs Fact**
   - Сравнение запланированного с фактом
   - Статус каждой тренировки (done/missed/shortened)
   - Key sessions tracking
   - → **Оценка: 9/10** (очень полезно!)

### ⚠️ Что не хватает

1. **Нет адаптации плана в реальном времени**
   ```
   ПРОБЛЕМА: План генерируется раз в неделю, но атлет может заболеть
   РЕШЕНИЕ: Добавить endpoint для "skip workout" → план пересчитывается
   ```

2. **Отсутствие визуализации**
   ```
   Нужно добавить:
   - Графики объёма по неделям
   - Распределение интенсивности (pie chart: Z1/Z2/Z3/Z4/Z5)
   - Progress curve к цели
   - Fatigue vs Fitness (TSS модель)
   ```

3. **Нет нутритологических рекомендаций**
   ```
   Для триатлона критично:
   - Сколько гелей/батончиков на длинную тренировку
   - Hydration strategy
   - Pre-race nutrition (за 3 дня до старта)
   ```

4. **Отсутствие силовой подготовки**
   ```
   Важно для триатлона:
   - Core strength (планки, боковые планки)
   - Single-leg exercises (предотвращение травм)
   - Plyometrics (прыжки для эффективности бега)
   ```

5. **Нет race-day strategy**
   ```
   За 2 недели до гонки нужен:
   - Pacing plan (на какой мощности/пейсе ехать/бежать)
   - Transition plan (T1/T2 checklist)
   - Nutrition timeline (когда пить/есть)
   - Mental preparation
   ```

---

## 4. КУДА ДВИГАТЬСЯ ДАЛЬШЕ

### 🎯 ФАЗЫ РАЗВИТИЯ

### ФАЗА 1: MVP → Product (2-4 недели)

**Цель**: Сделать продукт готовым для первых 10-50 пользователей

#### Must-have

1. **Multi-user support**
   - Регистрация/логин (JWT)
   - Привязка Strava к аккаунту
   - БД вместо JSON файлов

2. **Фикс критических багов**
   - Исправить модель GPT (gpt-4o)
   - Добавить error handling
   - Токены в .env / secrets

3. **Улучшение промпта** (см. выше)
   - Добавить зоны интенсивности
   - Примеры планов
   - Race-specific таргеты

4. **Web интерфейс (базовый)**
   - Страница регистрации
   - Dashboard с текущим планом
   - История тренировок

#### Технический стек
```
Frontend: Next.js + Tailwind + Recharts (графики)
Backend: FastAPI + PostgreSQL + Redis
Auth: JWT + OAuth (Strava)
Deploy: Vercel (frontend) + Railway/Render (backend)
```

---

### ФАЗА 2: Advanced Features (1-2 месяца)

#### 1. **Умная адаптация плана**

```python
@app.post("/coach/plan/adapt")
async def adapt_plan(
    user_id: int,
    reason: str,  # "sick" | "injury" | "overreaching" | "life_event"
    missed_sessions: List[str],
    feeling_score: int  # 1-10
):
    """
    GPT пересчитывает план на основе:
    - Пропущенных тренировок
    - Самочувствия
    - Времени до гонки
    """
```

#### 2. **Тренировочные зоны (автоматически)**

```python
@app.post("/coach/zones/calculate")
async def calculate_zones(user_id: int):
    """
    Анализирует последние race efforts или тесты:
    - Бег: threshold pace из 5K/10K/HM гонок
    - Велосипед: FTP из 20-min test или гонок
    - HR zones из максимального HR
    
    Возвращает персональные зоны для всех 3 видов спорта
    """
```

#### 3. **Workout Library**

```python
# База данных готовых тренировок с тегами
workouts = [
    {
        "id": "run_threshold_1",
        "sport": "run",
        "type": "threshold",
        "duration_min": 60,
        "difficulty": "hard",
        "description": "3x10min @ threshold pace (4:10/km) with 3min jog",
        "goals": ["improve_lactate_threshold", "race_specific_70.3"],
        "equipment": ["GPS watch"],
        "tags": ["intervals", "speed", "advanced"]
    }
]

@app.get("/workouts")
async def get_workouts(
    sport: str = None,
    difficulty: str = None,
    goals: List[str] = None
):
    """Фильтрация по тегам"""
```

#### 4. **Race Predictor**

```python
@app.get("/coach/race_prediction")
async def predict_race_time(
    user_id: int,
    race_type: str,  # "10K" | "HALF_MARATHON" | "MARATHON" | "70.3" | "FULL_IM"
    race_date: str
):
    """
    На основе:
    - Recent training load (CTL из последних 6 недель)
    - Best efforts (PR за последние 12 месяцев)
    - Readiness score
    
    Возвращает:
    - Predicted finish time (3 сценария: conservative, realistic, optimistic)
    - Required training changes to hit goal
    - Probability of achieving goal (%)
    """
```

#### 5. **Smart Fatigue Detection**

```python
@app.post("/coach/fatigue_check")
async def check_fatigue(user_id: int):
    """
    Анализирует:
    - HR drift (HR растёт на том же пейсе)
    - Pace drift (пейс падает на той же мощности)
    - Missed workouts streak
    - Self-reported feeling scores
    - Sleep data (если есть)
    
    Возвращает:
    - Fatigue score (0-100)
    - Recommendation: continue / easy_week / rest_3_days / medical
    """
```

---

### ФАЗА 3: Pro Features (2-4 месяца)

#### 1. **Equipment Integration**

```python
# Интеграция с устройствами
- Garmin Connect API (пульс, мощность, sleep)
- Wahoo (велокомпьютер)
- Zwift (виртуальные тренировки)
- TrainingPeaks (импорт/экспорт)
- Whoop / Oura Ring (recovery metrics)
```

#### 2. **Advanced Analytics**

```python
@app.get("/analytics/pmc")  # Performance Management Chart
async def get_pmc(user_id: int):
    """
    Возвращает:
    - CTL (Chronic Training Load) — fitness
    - ATL (Acute Training Load) — fatigue
    - TSB (Training Stress Balance) — form
    - TSS (Training Stress Score) по каждой тренировке
    
    Визуализация: график fitness vs fatigue vs form
    """
```

#### 3. **AI Video Analysis**

```python
@app.post("/coach/form_check")
async def analyze_form(
    user_id: int,
    video: UploadFile,
    sport: str  # "run" | "swim" | "bike"
):
    """
    Использует Computer Vision (GPT-4 Vision или специализированные модели):
    - Анализ техники бега (overstriding, cadence, posture)
    - Анализ техники плавания (catch, pull, kick)
    - Bike fit анализ (saddle height, reach)
    
    Возвращает:
    - Video с аннотациями
    - Список ошибок
    - Drills для исправления
    """
```

#### 4. **Nutrition Planning**

```python
@app.post("/coach/nutrition_plan")
async def create_nutrition_plan(
    user_id: int,
    race_type: str,
    duration_min: int,
    conditions: str  # "hot" | "cold" | "humid"
):
    """
    Персональный план:
    - Pre-race meal (за 3 часа до старта)
    - Race nutrition timeline:
      - Mile 0-10: water only
      - Mile 10-20: gel every 30min + electrolytes
      - ...
    - Recovery nutrition (30min window)
    
    Учитывает:
    - Weight
    - Sweat rate (если есть данные)
    - Intensity
    - Температуру
    """
```

#### 5. **Group Training**

```python
@app.post("/coach/group_workout")
async def create_group_workout(
    coach_id: int,
    athlete_ids: List[int],
    workout_template_id: str
):
    """
    Для тренеров / клубов:
    - Создание группового плана
    - Каждый атлет видит свои зоны
    - Leaderboard по группе
    - Group chat для мотивации
    """
```

#### 6. **Voice Coach**

```python
@app.post("/coach/voice_session")
async def start_voice_coaching_session(
    user_id: int,
    workout_id: str
):
    """
    Реал-тайм коучинг во время тренировки (через мобильное приложение):
    - Text-to-Speech: "In 30 seconds, start your 5-minute threshold interval"
    - Голосовые команды: "Coach, how am I doing?"
    - Response: "Great! Your HR is perfect for this interval. Keep it up!"
    
    Технологии:
    - OpenAI Whisper (Speech-to-Text)
    - OpenAI TTS (Text-to-Speech)
    - Real-time telemetry from watch/bike computer
    """
```

---

### ФАЗА 4: Platform (6+ месяцев)

#### 1. **Marketplace**
   - Тренеры могут продавать свои планы
   - Шаблоны планов от pro-атлетов
   - Комиссия платформы 20-30%

#### 2. **Community**
   - Форумы по видам спорта
   - Challenge система (кто больше пробежит за месяц)
   - Strava-like social feed

#### 3. **Research Dashboard**
   - Агрегированная анонимная статистика
   - "Что работает?" (какие планы дают лучшие результаты)
   - Публикация исследований

#### 4. **Corporate Wellness**
   - B2B продажа компаниям
   - Employee wellness programs
   - Team challenges

---

## 5. ТЕХНИЧЕСКИЕ РЕКОМЕНДАЦИИ

### Немедленно (эта неделя)

```bash
# 1. Исправить модель GPT
sed -i 's/gpt-5.1/gpt-4o/g' coach.py progress.py

# 2. Добавить .gitignore
echo "strava_token.json\n*.pyc\n__pycache__/\n.env" > .gitignore

# 3. Добавить базовый error handling
pip install tenacity  # для retry logic
```

### В течение месяца

1. **Миграция на БД**
   ```bash
   pip install sqlalchemy psycopg2-binary alembic
   # Создать модели, миграции
   ```

2. **Добавить тесты**
   ```bash
   pip install pytest pytest-asyncio httpx
   # Тесты для критических функций
   ```

3. **CI/CD**
   ```yaml
   # .github/workflows/test.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - uses: actions/setup-python@v2
         - run: pip install -r requirements.txt
         - run: pytest
   ```

4. **Логирование**
   ```python
   import structlog
   logger = structlog.get_logger()
   
   @app.post("/coach/plan")
   async def create_plan(...):
       logger.info("plan_generation_started", user_id=user_id)
       try:
           ...
       except Exception as e:
           logger.error("plan_generation_failed", error=str(e))
   ```

---

## 6. МОНЕТИЗАЦИЯ

### Freemium модель

**Free tier:**
- 1 goal
- 1 plan per week
- Basic analytics
- Email reports

**Pro ($9.99/month):**
- Unlimited goals
- Daily plan updates
- Advanced analytics (PMC chart, TSS)
- Nutrition plans
- Priority email support

**Elite ($29.99/month):**
- Everything in Pro
- Video form analysis
- 1-on-1 GPT coaching calls
- Custom workout library
- Integration with all devices

### Дополнительные источники

- **Training plans**: $49-199 за готовые планы (12-24 недели)
- **1-on-1 coaching**: $99-299/month (GPT + human coach hybrid)
- **Corporate**: $999-4999/month для компаний (10-100 сотрудников)

---

## 7. КОНКУРЕНТЫ (что делают другие)

1. **TrainingPeaks**: $119/year
   - Очень сложный интерфейс
   - Требует понимания TSS/CTL
   - → **Ваше преимущество**: AI коуч, проще для новичков

2. **Coach by Strava**: Free
   - Автоматические планы, но очень generic
   - → **Ваше преимущество**: GPT персонализация

3. **Humango**: $29/month
   - AI коучинг, но только для бега
   - → **Ваше преимущество**: триатлон + велосипед + плавание

4. **Final Surge**: $72/year
   - Для тренеров, не для атлетов
   - → **Ваше преимущество**: direct-to-athlete

---

## ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### Приоритет 1 (сделать ОБЯЗАТЕЛЬНО)

1. ✅ Исправить модель GPT (gpt-5.1 → gpt-4o)
2. ✅ Улучшить промпт (см. детальный выше)
3. ✅ Добавить multi-user + auth
4. ✅ Миграция на PostgreSQL
5. ✅ Error handling + retry logic

### Приоритет 2 (сделать для первых клиентов)

6. ✅ Web UI (Next.js dashboard)
7. ✅ Визуализация прогресса (графики)
8. ✅ Автоматический расчёт зон
9. ✅ Workout library
10. ✅ Race predictor

### Приоритет 3 (конкурентное преимущество)

11. ✅ Fatigue detection (умная адаптация)
12. ✅ Video form analysis
13. ✅ Nutrition planning
14. ✅ Voice coach (мобильное приложение)
15. ✅ Equipment integration (Garmin, Wahoo)

---

## ЗАКЛЮЧЕНИЕ

**Проект очень перспективный!** Основа заложена правильно, но есть критические технические долги, которые нужно закрыть перед запуском.

**Главные сильные стороны:**
- ✅ Правильная архитектура (модульная)
- ✅ Реальная проблема (триатлеты нуждаются в коучинге)
- ✅ GPT интеграция работает
- ✅ Plan vs Fact — очень крутая фича

**Главные слабости:**
- ❌ Нет multi-user
- ❌ Промпт слишком общий
- ❌ Нет визуализации
- ❌ Отсутствие race-specific planning

**Следующий шаг:**
1. Исправить критические баги (1 неделя)
2. Улучшить промпт + добавить зоны (1 неделя)
3. Тестировать на себе 4-6 недель
4. Запустить для 5-10 друзей/знакомых (beta)
5. Собрать feedback → итерировать
6. Launch на Product Hunt / Reddit r/triathlon

**Потенциальная аудитория:** 1-3 млн триатлетов в мире, 50-100K активных в англоязычных странах. При конверсии 0.5-1% в платных → 250-1000 клиентов → $2500-30000 MRR.

Проект стоит развивать! 🚀
