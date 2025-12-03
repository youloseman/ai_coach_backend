# Roadmap: AI Триатлон Тренер (18 месяцев)

## PHILOSOPHY

**Принцип разработки**: Ship early, iterate fast, listen to users

**Метрики успеха**:
- Week 1-4: 5-10 beta users (друзья, знакомые)
- Month 3: 50 paying users
- Month 6: 200 paying users
- Month 12: 1000 paying users
- Month 18: 3000+ paying users, $30K+ MRR

---

## ФАЗА 0: MVP FIX (1 неделя) 🔥

**Цель**: Сделать текущий код production-ready

### Tasks

| Task | Effort | Priority | Owner |
|------|--------|----------|-------|
| Fix GPT model (gpt-5.1 → gpt-4o) | 30 min | P0 | Dev |
| Add .gitignore | 5 min | P0 | Dev |
| Move constants to config | 1 hour | P0 | Dev |
| Create utils.py (normalize functions) | 2 hours | P0 | Dev |
| Add basic error handling | 4 hours | P0 | Dev |
| Improve system prompt | 4 hours | P0 | Dev |
| Test with real Strava data | 2 hours | P0 | Dev |

**Total effort**: ~2 days
**Outcome**: Проект работает стабильно, можно тестировать на себе

---

## ФАЗА 1: MULTI-USER MVP (2-3 недели) ✅

**Цель**: 5-10 beta пользователей могут пользоваться продуктом

### Infrastructure

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| PostgreSQL setup | 1 day | P0 | Models, migrations, connection |
| JWT authentication | 1 day | P0 | Register, login, /me endpoint |
| Multi-user Strava OAuth | 1 day | P0 | Привязка токенов к users |
| Basic error handling | 1 day | P1 | Retry logic, structured logging |
| Deployment setup | 1 day | P1 | Railway/Render + PostgreSQL |

### Features

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| User dashboard API | 1 day | P0 | GET /dashboard — summary |
| Email reports fix | 0.5 day | P0 | Персональные для каждого user |
| Activity sync scheduler | 1 day | P1 | Cron job для синка Strava |
| Onboarding flow | 1 day | P1 | Первый вход, заполнение профиля |

**Total effort**: 2-3 недели (1 разработчик)
**Outcome**: 5-10 друзей могут зарегистрироваться и получать планы

### Launch checklist
- [ ] Strava OAuth работает для нескольких пользователей
- [ ] Планы генерируются персонально
- [ ] Email отправляются каждому пользователю
- [ ] БД не падает под нагрузкой 10 users

---

## ФАЗА 2: BASIC PRODUCT (4-6 недель) 🚀

**Цель**: Запуск на Product Hunt, 50 paying users

### Frontend (Next.js)

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| Landing page | 2 days | P0 | Hero, features, pricing, testimonials |
| Registration/Login UI | 2 days | P0 | Forms, validation, error handling |
| Dashboard | 3 days | P0 | Current plan, upcoming workouts, stats |
| Weekly plan view | 2 days | P0 | Calendar view, workout details |
| Plan vs Fact view | 2 days | P1 | Table с статусами (done/missed) |
| Settings page | 1 day | P1 | Profile, goals, preferences |

### Backend enhancements

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| Improved system prompt | 2 days | P0 | Add zones, examples, specificity |
| Training zones calculation | 2 days | P0 | Auto-detect from race efforts |
| Workout library | 2 days | P1 | 20-30 готовых тренировок |
| Progress tracker v2 | 2 days | P1 | Better metrics, visualization data |
| Stripe integration | 2 days | P0 | Payment processing |

### Marketing & Growth

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| Product Hunt launch | 1 day | P0 | Write post, gather upvotes |
| SEO optimization | 1 day | P1 | Meta tags, sitemap, schema.org |
| Blog setup | 1 day | P2 | 3-5 SEO articles |
| Social media | ongoing | P2 | Twitter, Instagram presence |

**Total effort**: 4-6 недель (1 frontend + 1 backend)
**Outcome**: Готовый продукт, можно продавать ($9.99/month)

### Success metrics
- [ ] 100 registrations in first week
- [ ] 10-20 paying users (10-20% conversion)
- [ ] <5% churn in first month
- [ ] NPS > 40

---

## ФАЗА 3: ADVANCED FEATURES (2-3 месяца) 🔥

**Цель**: 200 paying users, начало word-of-mouth роста

### Priority 1 features

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **Fatigue detection** | 1 week | High | Auto-adjust plan when fatigued |
| **Race strategy generator** | 1 week | High | Detailed race-day plan |
| **Plan adaptation** | 1 week | High | "I'm sick" / "Skip workout" → replan |
| **Weekly report v2** | 1 week | Medium | Better visualizations, insights |
| **Mobile app (React Native)** | 3 weeks | High | iOS + Android |

### Priority 2 features

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **Workout library v2** | 1 week | Medium | User-created workouts |
| **Social features** | 2 weeks | Medium | Follow friends, compare progress |
| **Garmin integration** | 1 week | Medium | Import workouts, auto-sync |
| **Advanced analytics** | 1.5 weeks | High | PMC chart, fitness curve |

### Infrastructure

| Task | Effort | Priority | Details |
|------|--------|----------|---------|
| Redis caching | 2 days | P0 | Cache Strava data, plans |
| Background jobs | 2 days | P0 | Celery/RQ for async tasks |
| Monitoring | 2 days | P0 | Sentry, Datadog, alerts |
| Performance optimization | 3 days | P1 | Query optimization, indexes |

**Total effort**: 2-3 месяца (2 backend + 1 frontend + 1 mobile)
**Outcome**: Конкурентоспособный продукт с уникальными фичами

### Success metrics
- [ ] 200 paying users
- [ ] $2K+ MRR
- [ ] <10% monthly churn
- [ ] 15-20% referral rate
- [ ] 4.5+ App Store rating

---

## ФАЗА 4: SCALE & DIFFERENTIATION (3-6 месяцев) 🚀

**Цель**: 1000 paying users, $10K+ MRR

### Unique features (конкурентное преимущество)

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **AI Video form analysis** | 3 weeks | Very High | GPT-4 Vision + pose detection |
| **Voice coach** | 2 weeks | High | Real-time audio coaching |
| **Nutrition planner** | 2 weeks | High | Race-day nutrition strategy |
| **Equipment optimizer** | 1 week | Medium | Bike fit, gear recommendations |
| **Weather-aware training** | 1 week | Medium | Adjust plan based on forecast |

### Community & Social

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **Group training** | 2 weeks | Medium | Coaches can manage athletes |
| **Challenges** | 2 weeks | Medium | Monthly challenges, leaderboards |
| **Forums** | 1 week | Low | Community discussion |
| **Live events** | ongoing | Medium | Virtual group workouts |

### Business features

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **Coach marketplace** | 3 weeks | High | Certified coaches sell plans |
| **Corporate wellness** | 2 weeks | High | B2B sales |
| **API for 3rd parties** | 1 week | Medium | Partners can integrate |

**Total effort**: 3-6 месяцев (3-4 разработчика)
**Outcome**: Уникальный продукт, который сложно скопировать

### Success metrics
- [ ] 1000 paying users
- [ ] $10K+ MRR
- [ ] Featured in TechCrunch / Triathlete Magazine
- [ ] Partnership with Ironman or similar
- [ ] <8% monthly churn
- [ ] 20-30% referral rate

---

## ФАЗА 5: ENTERPRISE & GLOBAL (6-12 месяцев) 🌍

**Цель**: 3000+ paying users, $30K+ MRR, venture-ready

### Enterprise features

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **White-label solution** | 4 weeks | High | Coaches rebrand as their own |
| **Team management** | 3 weeks | High | Clubs, corporate teams |
| **Custom branding** | 2 weeks | Medium | Logo, colors, domain |
| **Advanced analytics** | 3 weeks | Medium | Coach dashboard, athlete comparison |
| **API v2** | 2 weeks | Medium | RESTful + GraphQL |

### Global expansion

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **Internationalization** | 2 weeks | High | Spanish, German, French |
| **Local currencies** | 1 week | High | EUR, GBP, CAD pricing |
| **Regional coaches** | ongoing | Medium | Partner with local coaches |

### Research & Development

| Feature | Effort | Impact | Details |
|---------|--------|--------|---------|
| **AI model fine-tuning** | 4 weeks | High | Train on real athlete data |
| **Predictive analytics** | 3 weeks | High | Injury risk prediction |
| **Biomechanics analysis** | 4 weeks | Very High | Advanced form analysis |

**Total effort**: 6-12 месяцев (5-7 разработчиков)
**Outcome**: Ведущая платформа для триатлона

### Success metrics
- [ ] 3000+ paying users
- [ ] $30K+ MRR
- [ ] 50+ enterprise clients
- [ ] International presence (3+ countries)
- [ ] Series A ready ($1M+ ARR)

---

## ОЦЕНКА РЕСУРСОВ

### MVP (Фаза 0-1): 1 месяц

**Team**: 1 full-stack developer
**Budget**: $0-5K
- Domain & hosting: $100/month
- OpenAI API: $200-500/month
- PostgreSQL: Free tier (Railway/Render)
- Email: SendGrid free tier

**Funding**: Bootstrap / personal savings

### Product Launch (Фаза 2): 2 месяца

**Team**: 
- 1 backend developer (full-time)
- 1 frontend developer (full-time or contract)
- 1 designer (contract, part-time)

**Budget**: $10K-15K
- Developers: $5K-10K/month
- Designer: $2K-3K (one-time)
- Infrastructure: $300-500/month
- OpenAI API: $500-1000/month

**Funding**: Bootstrap / angel investment ($50K-100K)

### Growth (Фаза 3-4): 6 месяцев

**Team**:
- 2 backend developers
- 1 frontend developer
- 1 mobile developer
- 1 designer
- 1 marketer / growth hacker

**Budget**: $30K-50K/month
- Salaries: $25K-40K/month
- Infrastructure: $2K-5K/month
- Marketing: $3K-5K/month

**Funding**: Seed round ($500K-1M)

### Scale (Фаза 5): 12 месяцев

**Team**:
- 3 backend developers
- 2 frontend developers
- 2 mobile developers
- 1 DevOps engineer
- 1 data scientist
- 1 designer
- 2 marketers
- 1 sales person

**Budget**: $80K-120K/month
- Salaries: $60K-90K/month
- Infrastructure: $10K-15K/month
- Marketing: $10K-15K/month

**Funding**: Series A ($3M-5M)

---

## РИСКИ И МИТИГАЦИЯ

### Технические риски

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GPT API costs too high | Medium | High | Cache aggressively, use cheaper models for some tasks |
| Strava API rate limits | Medium | Medium | Cache activities, batch requests |
| Database performance | Low | High | Proper indexing, Redis caching |
| Security breach | Low | Critical | Regular audits, encryption, compliance |

### Business risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low user adoption | High | Critical | Focus on beta testing, iterate based on feedback |
| Competition (TrainingPeaks, etc) | High | High | Differentiate with AI features they don't have |
| High churn rate | Medium | High | Improve onboarding, add social features |
| Legal issues (liability) | Low | High | Disclaimers, terms of service, insurance |

### Execution risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | High | Medium | Strict prioritization, MVP mindset |
| Burnout | Medium | High | Sustainable pace, hire help early |
| Running out of money | Medium | Critical | Lean spending, revenue focus, fundraise early |

---

## МЕТРИКИ ДЛЯ TRACKING

### Product metrics

```python
# Key metrics to track weekly

NORTH_STAR_METRIC = "Active Weekly Users"  # Users who view/complete workouts

SECONDARY_METRICS = {
    "acquisition": [
        "New signups",
        "Conversion rate (visitor → signup)",
        "Strava connection rate"
    ],
    "activation": [
        "Completed onboarding %",
        "First plan generated within 24h",
        "First workout completed"
    ],
    "retention": [
        "Weekly active users (WAU)",
        "Monthly active users (MAU)",
        "D7 / D30 retention rate"
    ],
    "revenue": [
        "MRR (Monthly Recurring Revenue)",
        "ARPU (Average Revenue Per User)",
        "LTV (Lifetime Value)",
        "CAC (Customer Acquisition Cost)"
    ],
    "referral": [
        "K-factor (viral coefficient)",
        "NPS (Net Promoter Score)",
        "Social shares"
    ]
}
```

### Quality metrics

```python
QUALITY_METRICS = {
    "plan_quality": [
        "Plans generated successfully",
        "GPT errors/failures",
        "Plans edited by user (% changed)"
    ],
    "accuracy": [
        "Race predictions accuracy",
        "Zone calculations accuracy",
        "Fatigue detection precision"
    ],
    "satisfaction": [
        "NPS score",
        "App Store rating",
        "Support tickets"
    ]
}
```

---

## КОНКУРЕНТНЫЙ АНАЛИЗ

### Прямые конкуренты

| Competitor | Strengths | Weaknesses | Our advantage |
|------------|-----------|------------|---------------|
| **TrainingPeaks** | Industry standard, lots of features | Complex, expensive ($199/year), no AI | AI simplicity, modern UX |
| **Humango** | AI coaching | Running only, no triathlon | Full triathlon, better AI |
| **Coach by Strava** | Free, integrated | Very basic, generic | Personalized AI, race strategy |
| **Final Surge** | Coach-focused | Not for self-coached athletes | Direct-to-athlete |

### Indirect конкуренты

- Human coaches ($150-500/month) — **Our price**: $9.99/month
- Running-only apps (Nike Run Club, etc) — **Our advantage**: triathlon
- Generic fitness apps (Fitbit, etc) — **Our advantage**: sport-specific

### Competitive moats (защита от копирования)

1. **Data network effect**: Чем больше атлетов, тем лучше AI
2. **Community**: Social features, challenges
3. **Integrations**: Strava, Garmin, TrainingPeaks, etc
4. **Brand**: "The AI Triathlon Coach"
5. **Speed of iteration**: Ship features faster than big companies

---

## GO-TO-MARKET STRATEGY

### Phase 1: Beta (Month 1-2)

**Target**: 10-20 beta users
**Channels**:
- Personal network
- Local triathlon club
- Reddit r/triathlon (post in weekly thread)
- Strava clubs

**Goal**: Validate product-market fit, collect feedback

### Phase 2: Launch (Month 3)

**Target**: 100 signups, 10-20 paying
**Channels**:
- Product Hunt launch
- Reddit r/triathlon announcement
- Facebook triathlon groups
- Triathlete.com forum
- Running/cycling podcasts (guests)

**Goal**: Build initial user base, generate buzz

### Phase 3: Growth (Month 4-6)

**Target**: 500 signups, 50-100 paying
**Channels**:
- Content marketing (blog, SEO)
- Partnerships (coaches, clubs)
- Referral program (give 1 month free)
- Paid ads (Facebook, Google, Strava)
- Influencers (triathlon YouTubers)

**Goal**: Sustainable growth channel

### Phase 4: Scale (Month 7-12)

**Target**: 3000 signups, 500-1000 paying
**Channels**:
- PR (TechCrunch, Triathlete Magazine)
- Events (Ironman expo booth)
- Affiliate program
- B2B sales (clubs, corporate)

**Goal**: Market leadership in niche

---

## ПРИМЕРНЫЙ TIMELINE

```
Month 1-2:  MVP Fix + Multi-user
            ↓
Month 3:    Launch on Product Hunt
            ↓
Month 4-6:  Advanced features + Growth
            ↓
Month 7-9:  Unique features + Fundraise (Seed)
            ↓
Month 10-12: Scale team, international expansion
            ↓
Month 13-18: Enterprise features, Series A prep
```

---

## ФИНАНСОВАЯ МОДЕЛЬ (18 месяцев)

### Revenue projections

| Month | Users | Paying | MRR | Cumulative |
|-------|-------|--------|-----|------------|
| 3 | 100 | 10 | $100 | $100 |
| 6 | 500 | 50 | $500 | $1,600 |
| 9 | 1500 | 200 | $2,000 | $9,100 |
| 12 | 3000 | 500 | $5,000 | $27,600 |
| 18 | 7000 | 1500 | $15,000 | $90,000 |

**Assumptions**:
- Price: $9.99/month
- Conversion rate: 10-20%
- Monthly churn: 5-10%
- Viral coefficient: 1.2-1.5 (каждый user приводит 1-2 друзей)

### Break-even analysis

**Fixed costs** (monthly):
- Developers (3): $20K
- Infrastructure: $2K
- Marketing: $3K
- **Total**: $25K/month

**Break-even**: 2500 paying users ($25K MRR)
**Timeline to break-even**: Month 12-14

---

## ЗАКЛЮЧЕНИЕ

**Проект имеет огромный потенциал!**

✅ **Market opportunity**: 1-3M триатлетов в мире, растущий рынок
✅ **Technical feasibility**: MVP уже работает
✅ **Unique value**: AI персонализация + триатлон-специфика
✅ **Scalability**: SaaS модель, high margins

**Next steps**:
1. Исправить критические баги (1 неделя)
2. Тестировать на себе 4-6 недель
3. Добавить 5-10 друзей в beta (1 месяц)
4. Доработать на основе feedback
5. Launch 🚀

**Готов начинать?** 💪
