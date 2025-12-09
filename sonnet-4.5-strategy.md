# 🚀 Cursor AI + Claude Sonnet 4.5: Оптимальная стратегия

## 🎯 Что меняется с Sonnet 4.5

### Было (стандартные модели):
```
Успех auto режима: 70%
Нужна твоя доработка: 30%
Риск багов: Высокий
```

### Стало (Sonnet 4.5):
```
Успех auto режима: 90-95% ✨
Нужна твоя доработка: 5-10%
Риск багов: Низкий
```

## ⚡ С Sonnet 4.5 можно более агрессивную стратегию

### Новый подход: "Расширенный авто"

Теперь можно давать **группы задач**, а не по одной:

```
┌────────────────────┐
│ Даешь 3-5 задач    │ ← Вместо 1 задачи
│ связанных вместе   │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Sonnet 4.5 делает  │ ← 5-10 минут
│ всё сразу          │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Ты проверяешь      │ ← 10 минут
│ в браузере         │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Мелкие правки      │ ← 5 минут
│ (если нужно)       │
└────────────────────┘
```

---

## 🚀 ДЕНЬ 1: Мощный промпт для Sonnet 4.5

### Mega Task 1: Вся Analytics инфраструктура сразу (1 промпт!)

```
# КОНТЕКСТ
Я работаю над AI Triathlon Coach на Next.js 16 + TypeScript.

Структура проекта:
- frontend/lib/api.ts - API клиент (уже есть authAPI, profileAPI, coachAPI)
- frontend/types/index.ts - TypeScript типы
- frontend/components/ - React компоненты
- frontend/app/dashboard/page.tsx - главная страница (900+ строк)

Backend (FastAPI) имеет готовые эндпоинты:
- GET /analytics/training_load?weeks=12
- GET /analytics/form_status
- GET /analytics/fatigue?weeks=4
- GET /analytics/predict_race?goal_race_type=X&goal_time=X&sport=X&weeks=12
- GET /analytics/all_predictions?sport=run&weeks=12
- GET /strava/activities?page=1&per_page=10

# ЗАДАЧА
Добавь полную analytics интеграцию в 5 шагов:

## ШАГ 1: API Functions (frontend/lib/api.ts)
Добавь объект analyticsAPI с методами:
- getTrainingLoad(weeks)
- getFormStatus()
- getFatigueAnalysis(weeks)
- predictRace({goalRaceType, goalTime, sport?, weeks?})
- getAllPredictions(sport, weeks)

И в stravaAPI добавь:
- getActivities(page, perPage)

Требования:
- Используй существующий axios instance (api)
- try-catch с console.error для всех методов
- JSDoc комментарии
- Следуй стилю существующих функций (посмотри на authAPI как пример)

## ШАГ 2: TypeScript Types (frontend/types/index.ts)
Создай интерфейсы для всех API responses:

```typescript
// Training Load
export interface TrainingLoadAnalysis {
  status: string;
  analysis: {
    current_ctl: number;
    current_atl: number;
    current_tsb: number;
    current_ramp_rate: number;
    ctl_trend: string;
    atl_trend: string;
    tsb_trend: string;
    ramp_rate_status: string;
    weekly_tss: Array<{
      week_start: string;
      total_tss: number;
      run_tss: number;
      bike_tss: number;
      swim_tss: number;
    }>;
    timeline?: Array<{
      date: string;
      ctl: number;
      atl: number;
      tsb: number;
    }>;
  };
}

// Form Status
export interface FormStatus {
  status: string;
  current_date: string;
  current_ctl: number;
  current_atl: number;
  current_tsb: number;
  form: {
    label: string;
    color: string;
    description: string;
    recommendation: string;
  };
}

// Fatigue Analysis
export interface FatigueSignal {
  type: string;
  severity: string;
  message: string;
  details: Record<string, any>;
}

export interface FatigueAnalysis {
  status: string;
  overall_fatigue_level: string;
  fatigue_score: number;
  signals: FatigueSignal[];
  recommendations: string[];
  metrics: {
    avg_hr_drift?: number;
    chronic_high_hr_days?: number;
    pace_decline?: number;
    days_since_rest?: number;
  };
}

// Race Prediction
export interface RacePrediction {
  status: string;
  prediction: {
    goal_race_type: string;
    goal_time: string;
    predicted_time: string;
    predicted_seconds: number;
    goal_seconds: number;
    probability_of_success: number;
    current_fitness_level: string;
    recommendations: string[];
    pacing_strategy?: {
      split_type: string;
      splits: Array<{
        segment: string;
        target_pace: string;
        target_time: string;
      }>;
    };
  };
}

// Strava Activity
export interface StravaActivity {
  id: string;
  name: string;
  sport_type: string;
  start_date: string;
  distance_meters: number;
  moving_time_seconds: number;
  elapsed_time_seconds: number;
  total_elevation_gain: number;
  average_heartrate?: number;
  max_heartrate?: number;
  average_watts?: number;
  tss?: number;
}
```

## ШАГ 3: Form Status Card (frontend/components/FormStatusCard.tsx)
Создай компонент который:

**Functionality:**
- 'use client'
- useEffect для загрузки analyticsAPI.getFormStatus()
- useState для: loading, error, formStatus
- Автоматическая загрузка при монтировании

**UI Layout:**
┌─────────────────────────────────┐
│ Current Form          [Refresh] │
│                                 │
│  ┌──────────────────┐           │
│  │ FRESH / OPTIMAL  │ ← Badge   │
│  │ / FATIGUED       │           │
│  └──────────────────┘           │
│                                 │
│  Fitness (CTL)  Fatigue (ATL)  │
│      95.0           65.0        │
│                                 │
│            Form (TSB)           │
│              +30.0              │
│                                 │
│  Description: You're in great  │
│  form with good fitness...     │
│                                 │
│  ┌──────────────────────────┐  │
│  │ 💡 Recommendation:        │  │
│  │ Maintain current training │  │
│  │ load for best results     │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘

**Design System:**
- Container: bg-white dark:bg-gray-800 rounded-lg shadow p-6
- Badge colors based on form.color:
  * green → bg-green-100 text-green-800 border-green-300
  * yellow → bg-yellow-100 text-yellow-800 border-yellow-300
  * orange → bg-orange-100 text-orange-800 border-orange-300
  * red → bg-red-100 text-red-800 border-red-300
- Metrics grid: grid-cols-3 gap-4
- TSB color: green if >5, red if <-10, yellow otherwise
- Recommendation box: bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-400 p-3 rounded

**States:**
- Loading: Skeleton with animate-pulse
- Error: Show friendly message "Connect Strava and sync activities"
- Success: Full UI above

**Dark Mode:** All elements must have dark: variants

## ШАГ 4: Fatigue Warning Banner (frontend/components/FatigueWarningBanner.tsx)
Создай warning banner который:

**Functionality:**
- Вызывает analyticsAPI.getFatigueAnalysis(4)
- Показывается ТОЛЬКО если overall_fatigue_level === 'HIGH' или 'CRITICAL'
- Можно dismiss (скрыть)
- Не показывается при loading или если нет high fatigue

**UI Layout:**
┌────────────────────────────────────────┐
│ ⚠️  High Fatigue Warning         [×]  │
│                                        │
│ Fatigue Score: 75.5/100                │
│                                        │
│ Detected Issues:                       │
│ • HR drift detected: 7.2% above normal│
│ • No rest day in last 9 days          │
│ • Pace decline: 12% slower than usual │
│                                        │
│ ┌────────────────────────────────┐    │
│ │ Recommendations:                │    │
│ │ → Take a full rest day          │    │
│ │ → Reduce intensity for 3-5 days │    │
│ │ → Focus on sleep and recovery   │    │
│ └────────────────────────────────┘    │
└────────────────────────────────────────┘

**Design:**
- HIGH: bg-orange-100 dark:bg-orange-900/20 border-l-4 border-orange-400
- CRITICAL: bg-red-100 dark:bg-red-900/20 border-l-4 border-red-400
- Dismiss button: absolute top-2 right-2
- Lists с bullet points для signals и recommendations

## ШАГ 5: Race Prediction Card (frontend/components/RacePredictionCard.tsx)
Создай prediction card который:

**Functionality:**
- Загружает primary goal через goalsAPI.getPrimary()
- Затем загружает prediction для этой цели
- Если нет цели - показывает placeholder

**UI Layout:**
┌────────────────────────────────────┐
│ Race Prediction: Half Ironman      │
│                                    │
│  Your Goal       Predicted         │
│   5:00:00         4:45:30          │
│                                    │
│ Success Probability                │
│ ████████████░░░░ 78%               │
│                                    │
│ Current Fitness: Strong            │
│                                    │
│ Recommendations:                   │
│ → Focus on brick workouts          │
│ → Practice race pace runs          │
│ → Taper properly last 2 weeks     │
└────────────────────────────────────┘

**Design:**
- Progress bar с градиентом:
  * ≥70%: bg-green-500
  * 40-69%: bg-yellow-500
  * <40%: bg-red-500
- Goal vs Predicted в grid-cols-2
- Probability большими цифрами с соответствующим цветом

# ТРЕБОВАНИЯ КО ВСЕМ КОМПОНЕНТАМ

1. **TypeScript строгость:**
   - Все useState типизированы
   - Все props типизированы
   - Нет any типов
   - Правильные optional поля (?)

2. **Error Handling:**
   - try-catch во всех async функциях
   - console.error для всех ошибок
   - Graceful fallback UI при ошибках

3. **Loading States:**
   - Skeleton screens с animate-pulse
   - Серые прямоугольники (h-4 bg-gray-200 rounded)

4. **Dark Mode:**
   - Каждый цвет должен иметь dark: вариант
   - bg-white → dark:bg-gray-800
   - text-gray-900 → dark:text-gray-100
   - text-gray-600 → dark:text-gray-400
   - border → dark:border-gray-700

5. **Code Style:**
   - Следуй существующим паттернам в проекте
   - Используй те же утилиты что и другие компоненты
   - Консистентный spacing (p-6, gap-4, mb-4, etc)
   - Semantic HTML

6. **Accessibility:**
   - Кнопки должны иметь aria-label
   - Правильный контраст цветов
   - Keyboard navigation

# OUTPUT FORMAT

Покажи изменения в таком формате:

```
=== FILE: frontend/lib/api.ts ===
[показать только новый код, который нужно добавить]

=== FILE: frontend/types/index.ts ===
[показать только новые типы]

=== FILE: frontend/components/FormStatusCard.tsx ===
[полный код компонента]

=== FILE: frontend/components/FatigueWarningBanner.tsx ===
[полный код компонента]

=== FILE: frontend/components/RacePredictionCard.tsx ===
[полный код компонента]
```

Начинай! Создай все 5 частей.
```

---

## 🎯 Ожидаемый результат с Sonnet 4.5

После этого mega-промпта ты получишь:

✅ **Работающий код на 95%**
- Все файлы созданы
- Типы правильные
- Компоненты рендерятся
- API calls работают
- Dark mode применен

⚠️ **Что возможно нужно поправить (5%):**
- Мелкие стилистические правки
- Специфичные edge cases
- Точная подгонка под твой дизайн

---

## 📅 ОБНОВЛЕННЫЙ TIMELINE С SONNET 4.5

### День 1: Analytics (2-3 часа вместо 8)

**Утро (1 час):**
```
09:00 - Даешь mega-промпт выше
09:10 - Sonnet 4.5 генерирует все файлы (10 мин)
09:20 - Проверяешь TypeScript (npx tsc --noEmit)
09:25 - Запускаешь dev server (npm run dev)
09:30 - Тестируешь в браузере
09:45 - Мелкие правки если нужно
10:00 - git commit -m "Add analytics integration"
```

**День (1 час):**
```
14:00 - Recent Activities + ActivityCard
14:10 - Sonnet 4.5 создает компоненты
14:20 - Проверка + тестирование
14:30 - Интеграция в Dashboard
14:45 - git commit
```

**Вечер (1 час):**
```
18:00 - Dark mode setup
18:15 - Sonnet 4.5 добавляет dark: классы везде
18:40 - Проверка переключения темы
19:00 - git commit
```

### День 2: Polish & Maps (2-3 часа)

**Утро:**
- Activity maps (Leaflet)
- Final testing
- Bug fixes

**День:**
- Mobile responsive проверка
- UX полировка
- Documentation

---

## 🚀 Mega Task 2: Recent Activities (для Дня 1, вечер)

```
# КОНТЕКСТ
[тот же что выше]

# ЗАДАЧА
Добавь Recent Activities функциональность в 2 компонента:

## Компонент 1: ActivityCard (frontend/components/ActivityCard.tsx)

Создай карточку для одной тренировки с такой структурой:

**Props:**
```typescript
interface ActivityCardProps {
  activity: StravaActivity;
}
```

**UI Layout:**
┌────────────────────────────┐
│ 🏃 Run      [Sport Badge]  │
│ Morning Run                │
│ Dec 09, 2025               │
│                            │
│ Distance    Duration       │
│ 10.5 km     45m 30s       │
│                            │
│ Pace        Elevation      │
│ 4:20 /km    120m          │
│                            │
│ Avg HR      TSS            │
│ 145 bpm     65            │
└────────────────────────────┘

**Design:**
- Sport icon: 🏃 run, 🚴 bike, 🏊 swim
- Sport badge: цветные (run=orange, bike=purple, swim=cyan)
- Grid layout для метрик: grid-cols-2 gap-3
- Hover effect: hover:shadow-md transition-shadow
- Border: border border-gray-200 dark:border-gray-700

**Helper Functions внутри компонента:**
- formatDuration(seconds) → "45m 30s"
- formatDistance(meters) → "10.5 km"
- formatPace(meters, seconds) → "4:20 /km"
- getSportIcon(sportType) → emoji
- getSportColor(sportType) → Tailwind classes

## Компонент 2: RecentActivitiesList (frontend/components/RecentActivitiesList.tsx)

**Functionality:**
- Загружает stravaAPI.getActivities(1, 10)
- Отображает список ActivityCard компонентов
- Loading skeleton (3 карточки)
- Error state
- Empty state ("No activities yet")

**UI Layout:**
┌──────────────────────┐
│ [ActivityCard 1]     │
├──────────────────────┤
│ [ActivityCard 2]     │
├──────────────────────┤
│ [ActivityCard 3]     │
└──────────────────────┘

**Design:**
- Container: space-y-4
- Empty state: bg-white rounded-lg border p-6 text-center

Создай оба компонента с полным функционалом.
```

---

## 🚀 Mega Task 3: Dashboard Integration (30 минут)

```
# КОНТЕКСТ
У меня готовы компоненты:
- FormStatusCard
- FatigueWarningBanner
- RacePredictionCard
- RecentActivitiesList

Файл: frontend/app/dashboard/page.tsx (~900 строк)

# ЗАДАЧА
Интегрируй все компоненты в Dashboard.

## ГДЕ ДОБАВИТЬ

Найди секцию с PerformanceChart (примерно строка 400-450).
Это компонент <PerformanceChart /> который показывает CTL/ATL/TSB.

ПОСЛЕ этого компонента добавь:

```tsx
{/* NEW: Fatigue Warning (appears only if high fatigue) */}
<FatigueWarningBanner />

{/* NEW: Analytics Cards */}
<div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
  <FormStatusCard />
  <RacePredictionCard />
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
      Training Load
    </h3>
    <p className="text-sm text-gray-500 dark:text-gray-400">
      Detailed CTL/ATL analysis coming soon
    </p>
  </div>
</div>

{/* NEW: Recent Activities */}
<div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-8">
  <div className="p-6 border-b border-gray-200 dark:border-gray-700">
    <div className="flex items-center justify-between">
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
        Recent Activities
      </h2>
      <button
        onClick={() => window.location.reload()}
        className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
      >
        ↻ Sync
      </button>
    </div>
  </div>
  <div className="p-6">
    <RecentActivitiesList />
  </div>
</div>
```

## ТРЕБОВАНИЯ
1. Добавь импорты вверху файла:
```typescript
import FormStatusCard from '@/components/FormStatusCard';
import FatigueWarningBanner from '@/components/FatigueWarningBanner';
import RacePredictionCard from '@/components/RacePredictionCard';
import RecentActivitiesList from '@/components/RecentActivitiesList';
```

2. НЕ удаляй существующий код
3. НЕ меняй существующие компоненты
4. Просто вставь новый код в правильное место
5. Сохрани все dark mode классы

Покажи diff изменений (только что добавилось/изменилось).
```

---

## 💡 Sonnet 4.5 TIPS

### Tip 1: Контекст - это всё
```
Чем больше контекста даешь - тем лучше результат.

Хорошо:
"Создай компонент FormStatusCard"

ОТЛИЧНО:
"Создай компонент FormStatusCard который:
- Использует analyticsAPI.getFormStatus()
- Следует дизайн-системе существующих компонентов
- Имеет такой же style как ProfileCard в dashboard
- Включает dark mode
- Обрабатывает loading/error/success states"
```

### Tip 2: Ссылайся на существующий код
```
"Посмотри на components/StatsCard.tsx 
и создай FormStatusCard в похожем стиле"

Sonnet 4.5 откроет файл, изучит паттерны и применит их!
```

### Tip 3: Просить примеры
```
"Создай FormStatusCard.
Если не уверен в дизайне - сначала покажи 
2-3 варианта layout в ASCII art, я выберу лучший."
```

### Tip 4: Incremental improvements
```
Сначала:
"Создай базовый FormStatusCard с минимальным функционалом"

Потом:
"Добавь в FormStatusCard:
- Refresh button
- Better error messages
- Animations на loading"

Sonnet 4.5 отлично делает инкрементальные улучшения!
```

---

## ⏱️ РЕАЛЬНЫЙ TIMELINE С SONNET 4.5

### Без Cursor: 10-12 дней
### С обычным Cursor: 4-5 дней
### С Cursor + Sonnet 4.5: **2 дня** ⚡

**День 1 (4 часа):**
- ✅ Утро: Mega Task 1 - вся analytics (1 час)
- ✅ День: Mega Task 2 - activities (1 час)
- ✅ Вечер: Mega Task 3 - integration + dark mode (2 часа)

**День 2 (3 часа):**
- ✅ Утро: Activity maps + polish (1.5 часа)
- ✅ День: Testing + bug fixes (1 час)
- ✅ Вечер: Final review + documentation (0.5 часа)

**TOTAL: 7 hours real work** = 1 full work day!

---

## ✅ ФИНАЛЬНЫЙ ВЕРДИКТ

### С Sonnet 4.5 в Cursor:

**Можно ли в auto режиме?**
✅ **ДА, почти полностью!** (90-95% автоматом)

**Но всё равно нужно:**
- Проверить в браузере (15 мин после каждого блока)
- Мелкие UX правки (20-30 мин всего)
- Testing (1 час)

**Сравнение:**

| Режим | Время | Качество | Риск багов |
|-------|-------|----------|------------|
| Вручную | 10 дней | 100% | Низкий |
| Cursor обычный (по задачам) | 4-5 дней | 90% | Средний |
| Cursor Sonnet 4.5 (mega-промпты) | **2 дня** | **95%** | **Низкий** |

---

## 🎯 МОЙ СОВЕТ С SONNET 4.5

1. **Используй mega-промпты выше**
2. **Давай по 3-5 связанных задач сразу**
3. **Проверяй после каждого блока**
4. **Минимальные правки руками**

**Результат:** За выходные (2 дня) сделаешь всю неделю 1! 🚀

Готов начинать? Просто:
1. Включи Sonnet 4.5 в Cursor настройках
2. Скопируй "Mega Task 1" выше
3. Запусти!

Будет работать на 90-95% из коробки! 💪
