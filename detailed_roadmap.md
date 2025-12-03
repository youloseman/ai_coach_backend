# AI Triathlon Coach - Detailed Roadmap 2025

## 🎯 Development Timeline

```
Week 1-2  │ Фаза 1: Стабилизация 🔧
Week 3-6  │ Фаза 2: Core Features 🚀
Week 7-10 │ Фаза 3: Social & Growth 👥
Week 11-16│ Фаза 4: Monetization 💰
Week 17+  │ Фаза 5: Scale & Advanced 🔬
```

---

## 📅 Фаза 1: Стабилизация (Weeks 1-2)

**Цель**: Production-ready MVP with multi-user support

### Week 1: Critical Fixes

**День 1-2: Immediate Fixes**
- [x] Fix GPT model (gpt-5.1 → gpt-4o)
- [x] Create .gitignore
- [x] Add error handling frontend
- [ ] Test plan generation

**День 3-4: Multi-user Strava**
- [ ] Create strava_auth.py
- [ ] Update strava_client.py
- [ ] Update main.py callbacks
- [ ] Update api_coach.py endpoints
- [ ] Test with 2 users

**День 5: Testing**
- [ ] Manual testing all flows
- [ ] Fix discovered bugs
- [ ] Document API changes

### Week 2: Database & Deployment

**День 1-2: PostgreSQL Migration**
```bash
# Tasks:
- Install PostgreSQL locally
- Update database.py
- Create Alembic migrations
- Test migrations
- Update .env with DATABASE_URL
```

**День 3-4: CI/CD Setup**
```yaml
# GitHub Actions pipeline:
- Linting (flake8, mypy)
- Unit tests (pytest)
- Build frontend
- Deploy to staging (Railway)
```

**День 5: Production Deploy**
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel/Railway
- [ ] Configure PostgreSQL on Railway
- [ ] Test production deployment
- [ ] Setup monitoring (Sentry)

**Success Metrics:**
- ✅ All critical bugs fixed
- ✅ Multi-user Strava working
- ✅ PostgreSQL in production
- ✅ CI/CD pipeline active
- ✅ Zero downtime deployment

---

## 🚀 Фаза 2: Core Features (Weeks 3-6)

**Цель**: Killer features for user retention

### Week 3: Visualization & Analytics

**Feature 1: Performance Management Chart**
```typescript
// Components to create:
1. PerformanceChart.tsx (recharts)
2. WeeklyVolumeChart.tsx
3. SportDistributionPie.tsx
4. CalendarHeatmap.tsx
```

**Backend endpoints:**
```python
GET /analytics/fitness_timeline?days=90
GET /analytics/weekly_volume?weeks=12
GET /analytics/sport_distribution?weeks=12
```

**Estimated time:** 12-16 hours

**Feature 2: Training Load Analysis**
```python
# New endpoint:
GET /analytics/training_load_analysis

# Returns:
{
  "ramp_rate": 6.5,  # TSS/week increase
  "risk_level": "medium",  # low/medium/high
  "current_ctl": 85.2,
  "current_atl": 92.1,
  "current_tsb": -6.9,
  "form_status": "maintaining",
  "recommendations": [
    "Ramp rate is optimal (5-8 TSS/week)",
    "Consider reducing volume this week due to TSB < 0"
  ]
}
```

**Estimated time:** 8-10 hours

### Week 4: Real-time Strava Sync

**Feature: Strava Webhooks**

**Backend:**
```python
# main.py - new endpoints

@app.get("/strava/webhook")
async def verify_webhook(
    hub_mode: str, 
    hub_verify_token: str, 
    hub_challenge: str
):
    """Verify Strava webhook subscription"""
    VERIFY_TOKEN = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return {"hub.challenge": hub_challenge}
    raise HTTPException(status_code=403)

@app.post("/strava/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Strava activity updates"""
    data = await request.json()
    
    if data["object_type"] == "activity":
        if data["aspect_type"] == "create":
            # New activity - fetch and cache
            await sync_new_activity(data["owner_id"], data["object_id"], db)
        elif data["aspect_type"] == "update":
            # Activity updated - refresh cache
            await update_cached_activity(data["object_id"], db)
        elif data["aspect_type"] == "delete":
            # Activity deleted - remove from cache
            await delete_cached_activity(data["object_id"], db)
    
    return {"status": "ok"}
```

**Setup steps:**
1. Register webhook subscription with Strava
2. Add webhook URL to environment
3. Handle webhook events
4. Update cache automatically

**Estimated time:** 10-12 hours

### Week 5: Improved AI Prompts

**Feature: Enhanced Coach Prompts**

```python
# prompts/trainer_prompt.py - COMPREHENSIVE VERSION

TRAINER_SYSTEM_PROMPT = """You are a world-class triathlon coach with expertise in:

PERIODIZATION MODELS:
- Linear periodization (Base → Build → Peak → Taper)
- Block periodization (Accumulation → Intensification → Realization)
- Reverse periodization (for time-crunched athletes)

TRAINING PRINCIPLES:
1. Progressive Overload: Volume increases 5-10% per week
2. Specificity: Training becomes race-specific as event approaches
3. Individualization: Consider athlete's history, goals, constraints
4. Recovery: Hard days HARD, easy days EASY (polarized training)
5. Periodization: Structured phases with clear objectives

WEEKLY STRUCTURE (TRIATHLON):
Monday: Recovery swim (technique focus) OR rest
Tuesday: Bike intervals (Z3-Z4) + Run brick (15-20min Z2)
Wednesday: Run tempo (Z3) OR intervals (Z4-Z5)
Thursday: Long swim (endurance + technique)
Friday: Easy recovery (Z1-Z2) OR rest
Saturday: Long bike (2-3x typical run duration, Z2 mostly)
Sunday: Long run (progressive: Z2 → Z3)

KEY WORKOUTS:
- Bike intervals: 4x8min @ Z4 with 3min recovery
- Run tempo: 30-40min @ Z3 (threshold pace)
- Swim intervals: 10x100m @ Z4 with 15s rest
- Brick workout: 45min bike Z3 → 15min run Z3

RACE-SPECIFIC FOCUS:
- Sprint distance: High intensity, less volume
- Olympic: Balanced intensity and volume
- Half Ironman: Aerobic endurance + threshold work
- Full Ironman: Massive aerobic base + race-pace practice

INTENSITY DISTRIBUTION:
- 80% of time in Z1-Z2 (easy aerobic)
- 20% of time in Z3-Z5 (tempo to VO2max)
- No Z3 "gray zone" junk miles

WORKOUT STRUCTURE:
Every workout includes:
- Warm-up (10-15min Z1)
- Main set (intervals, tempo, or steady)
- Cool-down (10min Z1)
- Total duration as specified

RESPONSE FORMAT:
Always return valid JSON with EXACTLY this structure:
{
  "week_start_date": "YYYY-MM-DD",
  "total_planned_hours": float,
  "days": [
    {
      "date": "YYYY-MM-DD",
      "sport": "Run|Bike|Swim|Strength|Brick|Rest",
      "session_type": "Long run|Bike intervals|Swim technique|etc",
      "duration_min": int,
      "intensity": "Z1/Z2/Z3/Z4/Z5 with detailed zones",
      "description": "SPECIFIC workout with exact intervals/paces",
      "primary_goal": "aerobic endurance|threshold power|VO2max|technique|recovery",
      "priority": "low|medium|high",
      "warmup_min": int,
      "main_set_min": int,
      "cooldown_min": int
    }
  ],
  "notes": {
    "overall_focus": "weekly training emphasis",
    "key_workouts": ["list of 2-3 most important sessions"],
    "recovery_guidelines": "how to approach recovery this week",
    "nutrition_tips": "race-specific fueling advice",
    "gear_recommendations": "equipment needed for key workouts"
  }
}

BE SPECIFIC with intervals:
❌ BAD: "Do some bike intervals"
✅ GOOD: "Warm-up 15min Z1, then 4x8min @ Z4 (95-105% FTP) with 3min Z1 recovery, cool-down 10min Z1. Total: 67min"

❌ BAD: "Long run"
✅ GOOD: "Warm-up 10min Z1, then 60min progressive: first 30min Z2, next 20min Z2-Z3, final 10min Z3, cool-down 10min Z1. Total: 80min"
"""

# Prompt для Race Day Strategy
RACE_STRATEGY_PROMPT = """Generate a comprehensive race day strategy including:

PRE-RACE (T-2 weeks):
- Taper guidelines (reduce volume by 40-60%)
- Last hard workout timing
- Sleep and stress management
- Travel considerations

RACE WEEK:
- Monday-Thursday: Short, easy workouts with race-pace efforts
- Friday: Swim 20min easy, practice transition
- Saturday: Rest or 20min bike + 10min run shakeout

RACE MORNING:
- Wake time (3-4 hours before start)
- Breakfast (400-600 cal, low fiber, familiar foods)
- Hydration (500-750ml water)
- Warm-up routine

TRANSITION SETUP:
- Bike: shoes, helmet, glasses, nutrition
- Run: shoes, race belt, hat/visor
- Checklist for both transitions

SWIM STRATEGY:
- Starting position (based on pace)
- First 400m: controlled effort (don't blow up)
- Middle: find draft, settle into rhythm
- Last 200m: increase effort slightly

BIKE STRATEGY:
- First 20km: hold back (Z2, maybe 90-92% target pace)
- Middle: settle into goal pace/power
- Nutrition: 60-90g carbs per hour
- Hydration: 500-750ml per hour
- Power/HR targets with ranges

RUN STRATEGY:
- First 5km: CONTROL PACE (even if feeling good)
- Middle: maintain rhythm, focus on form
- Last 5-10km: push if feeling strong
- Nutrition: 30-60g carbs per hour
- Walk aid stations if needed

MENTAL CUES:
- Swim: "smooth and steady"
- Bike: "save the legs"
- Run: "one mile at a time"
- Overall: "trust your training"

CONTINGENCY PLANS:
- If feeling too good on bike → still hold back
- If struggling early → slow down, regroup
- If stomach issues → slow down, take water only
- If cramping → stretch, salt tabs, slow down
"""
```

**Estimated time:** 6-8 hours

### Week 6: Activity Caching & Performance

**Feature: Intelligent Activity Cache**

```python
# strava_cache.py - new module

from models import ActivityDB
from sqlalchemy.orm import Session
import datetime as dt

async def sync_user_activities(
    user_id: int,
    db: Session,
    weeks: int = 12,
    force_refresh: bool = False
) -> list[dict]:
    """
    Smart sync:
    1. Check last sync time
    2. Only fetch new activities if > 1 hour since last sync
    3. Use DB cache for recent queries
    """
    
    # Check last sync
    last_activity = db.query(ActivityDB).filter(
        ActivityDB.user_id == user_id
    ).order_by(ActivityDB.synced_at.desc()).first()
    
    # If synced within last hour and not force refresh, use cache
    if not force_refresh and last_activity:
        time_since_sync = dt.datetime.now() - last_activity.synced_at
        if time_since_sync < dt.timedelta(hours=1):
            # Use cache
            cutoff = dt.datetime.now() - dt.timedelta(weeks=weeks)
            cached_activities = db.query(ActivityDB).filter(
                ActivityDB.user_id == user_id,
                ActivityDB.start_date >= cutoff
            ).order_by(ActivityDB.start_date.desc()).all()
            
            return [a.raw_data for a in cached_activities]
    
    # Fetch from Strava
    after_timestamp = None
    if last_activity:
        after_timestamp = int(last_activity.start_date.timestamp())
    
    new_activities = await fetch_activities_from_strava(
        user_id, db, after=after_timestamp
    )
    
    # Save to cache
    for activity_data in new_activities:
        # Check if already exists
        existing = db.query(ActivityDB).filter(
            ActivityDB.strava_id == str(activity_data["id"])
        ).first()
        
        if existing:
            # Update
            existing.raw_data = activity_data
            existing.synced_at = dt.datetime.now()
        else:
            # Insert new
            activity = ActivityDB(
                user_id=user_id,
                strava_id=str(activity_data["id"]),
                name=activity_data["name"],
                sport_type=activity_data["sport_type"],
                start_date=parse_activity_date(activity_data),
                distance_meters=activity_data.get("distance"),
                moving_time_seconds=activity_data.get("moving_time"),
                average_heartrate=activity_data.get("average_heartrate"),
                average_watts=activity_data.get("average_watts"),
                raw_data=activity_data,
                synced_at=dt.datetime.now()
            )
            db.add(activity)
    
    db.commit()
    
    # Return all activities from cache
    cutoff = dt.datetime.now() - dt.timedelta(weeks=weeks)
    all_activities = db.query(ActivityDB).filter(
        ActivityDB.user_id == user_id,
        ActivityDB.start_date >= cutoff
    ).order_by(ActivityDB.start_date.desc()).all()
    
    return [a.raw_data for a in all_activities]
```

**Performance improvements:**
- Cache hit rate: 80%+ (most requests use cache)
- API call reduction: 5x fewer Strava calls
- Page load time: 2-3x faster

**Estimated time:** 8-10 hours

**Phase 2 Success Metrics:**
- ✅ PMC visualization live
- ✅ Real-time Strava sync
- ✅ Improved AI prompts
- ✅ 80%+ cache hit rate
- ✅ User retention +30%

---

## 👥 Фаза 3: Social & Engagement (Weeks 7-10)

**Цель**: Build community and increase engagement

### Week 7-8: Training Log

**Feature: Public Training Log**

**Database models:**
```python
# models.py - add

class TrainingLogEntry(Base):
    __tablename__ = "training_log"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    
    date = Column(Date, nullable=False, index=True)
    sport = Column(String, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Metrics
    duration_min = Column(Integer, nullable=True)
    distance_km = Column(Float, nullable=True)
    rpe = Column(Integer, nullable=True)  # 1-10
    
    # Social
    is_public = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", backref="training_log")
    activity = relationship("ActivityDB")
    
class TrainingLogComment(Base):
    __tablename__ = "training_log_comments"
    
    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, ForeignKey("training_log.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
class TrainingLogLike(Base):
    __tablename__ = "training_log_likes"
    
    id = Column(Integer, primary_key=True)
    log_entry_id = Column(Integer, ForeignKey("training_log.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('log_entry_id', 'user_id', name='unique_like'),
    )
```

**API endpoints:**
```python
# api_social.py - new router

@router.post("/log")
async def create_log_entry(
    entry: TrainingLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a training log entry"""
    pass

@router.get("/log/feed")
async def get_training_feed(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public training log feed (from followed users)"""
    pass

@router.post("/log/{entry_id}/like")
async def like_log_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like a training log entry"""
    pass

@router.post("/log/{entry_id}/comment")
async def comment_on_entry(
    entry_id: int,
    content: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Comment on training log entry"""
    pass
```

**Frontend:**
```typescript
// app/feed/page.tsx

export default function FeedPage() {
  const [entries, setEntries] = useState<TrainingLogEntry[]>([]);
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1>Training Feed</h1>
      
      {entries.map(entry => (
        <TrainingLogCard
          key={entry.id}
          entry={entry}
          onLike={handleLike}
          onComment={handleComment}
        />
      ))}
    </div>
  );
}
```

**Estimated time:** 20-24 hours

### Week 9: Achievements System

**Feature: Badges & Achievements**

```python
# achievements.py - new module

from enum import Enum

class AchievementType(str, Enum):
    # Distance milestones
    FIRST_5K = "first_5k"
    FIRST_10K = "first_10k"
    FIRST_HM = "first_half_marathon"
    FIRST_MARATHON = "first_marathon"
    CENTURY_RIDE = "century_ride"  # 100km bike
    
    # Volume milestones
    WEEK_10H = "week_10_hours"
    WEEK_15H = "week_15_hours"
    MONTH_50H = "month_50_hours"
    YEAR_500H = "year_500_hours"
    
    # Consistency
    STREAK_7 = "streak_7_days"
    STREAK_30 = "streak_30_days"
    STREAK_100 = "streak_100_days"
    STREAK_365 = "streak_365_days"
    
    # Racing
    FIRST_RACE = "first_race"
    FIRST_PODIUM = "first_podium"
    FIRST_WIN = "first_win"
    
    # Multi-sport
    FIRST_TRIATHLON = "first_triathlon"
    FIRST_IRON_DISTANCE = "first_iron_distance"
    
async def check_and_award_achievements(
    user_id: int,
    db: Session
) -> list[Achievement]:
    """Check if user earned any new achievements"""
    
    user = db.query(User).filter(User.id == user_id).first()
    earned = []
    
    # Check distance achievements
    activities = db.query(ActivityDB).filter(
        ActivityDB.user_id == user_id
    ).all()
    
    # First 5K run
    first_5k_run = next((a for a in activities 
                        if a.sport_type == "Run" 
                        and a.distance_meters >= 5000), None)
    if first_5k_run:
        achievement = await award_achievement(
            user_id, AchievementType.FIRST_5K, db
        )
        if achievement:
            earned.append(achievement)
    
    # Weekly volume
    weekly_hours = calculate_weekly_hours(activities)
    if any(h >= 10 for h in weekly_hours):
        achievement = await award_achievement(
            user_id, AchievementType.WEEK_10H, db
        )
        if achievement:
            earned.append(achievement)
    
    # ... check other achievements
    
    return earned

async def award_achievement(
    user_id: int,
    achievement_type: AchievementType,
    db: Session
) -> Optional[Achievement]:
    """Award achievement if not already earned"""
    
    # Check if already earned
    existing = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.achievement_type == achievement_type
    ).first()
    
    if existing:
        return None
    
    # Create achievement
    achievement_data = ACHIEVEMENT_DEFINITIONS[achievement_type]
    achievement = Achievement(
        user_id=user_id,
        achievement_type=achievement_type,
        title=achievement_data["title"],
        description=achievement_data["description"],
        icon_url=achievement_data["icon_url"]
    )
    db.add(achievement)
    db.commit()
    
    # Send notification
    await send_achievement_notification(user_id, achievement)
    
    return achievement

ACHIEVEMENT_DEFINITIONS = {
    AchievementType.FIRST_5K: {
        "title": "First 5K",
        "description": "Completed your first 5K run",
        "icon_url": "/achievements/first_5k.svg",
        "points": 10
    },
    AchievementType.STREAK_30: {
        "title": "Consistency King",
        "description": "Trained for 30 days straight",
        "icon_url": "/achievements/streak_30.svg",
        "points": 50
    },
    # ... more definitions
}
```

**Frontend:**
```typescript
// app/profile/achievements/page.tsx

export default function AchievementsPage() {
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  
  return (
    <div className="grid grid-cols-3 gap-4">
      {achievements.map(achievement => (
        <div key={achievement.id} className="p-4 border rounded">
          <img src={achievement.icon_url} className="w-16 h-16 mx-auto" />
          <h3 className="text-center font-bold">{achievement.title}</h3>
          <p className="text-sm text-gray-600">{achievement.description}</p>
          <p className="text-xs text-gray-400">
            Earned {new Date(achievement.earned_at).toLocaleDateString()}
          </p>
        </div>
      ))}
    </div>
  );
}
```

**Estimated time:** 16-20 hours

### Week 10: Social Features

**Feature: Follow System & Leaderboards**

```python
# models.py - add

class UserFollow(Base):
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey("users.id"))
    following_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
    )

# api_social.py - add endpoints

@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow a user"""
    pass

@router.get("/leaderboard/weekly")
async def get_weekly_leaderboard(
    sport: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get weekly leaderboard by:
    - Total distance
    - Total hours
    - Consistency streak
    """
    pass
```

**Estimated time:** 12-16 hours

**Phase 3 Success Metrics:**
- ✅ Training log feature live
- ✅ 30%+ users post to log weekly
- ✅ Achievement system with 20+ badges
- ✅ Follow/leaderboard engagement 50%+
- ✅ DAU/MAU ratio > 30%

---

## 💰 Фаза 4: Monetization (Weeks 11-16)

**Цель**: Generate revenue

### Week 11-12: Stripe Integration

**Feature: Subscription Management**

```python
# requirements.txt - add
stripe==7.0.0

# stripe_service.py - new module

import stripe
from config import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY

# Products & Prices (create in Stripe Dashboard)
PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "features": [
            "1 weekly plan per month",
            "Basic analytics",
            "Strava sync",
            "Community features"
        ]
    },
    "pro": {
        "name": "Pro",
        "price_id": "price_xxx",  # from Stripe
        "price": 9.99,
        "features": [
            "Unlimited weekly plans",
            "12-week planning",
            "Advanced analytics",
            "Race predictions",
            "Priority support"
        ]
    },
    "coach": {
        "name": "Coach",
        "price_id": "price_yyy",
        "price": 29.99,
        "features": [
            "All Pro features",
            "Race day strategy",
            "Nutrition planning",
            "Form analysis",
            "1:1 chat support"
        ]
    }
}

async def create_checkout_session(
    user_id: int,
    plan: str,
    db: Session
) -> dict:
    """Create Stripe checkout session"""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=['card'],
        line_items=[{
            'price': PLANS[plan]["price_id"],
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f"https://aicoach.com/dashboard?success=true",
        cancel_url=f"https://aicoach.com/pricing?canceled=true",
        metadata={
            'user_id': user_id,
            'plan': plan
        }
    )
    
    return {"checkout_url": session.url, "session_id": session.id}

async def handle_webhook(request: Request, db: Session):
    """Handle Stripe webhooks"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400)
    
    # Handle subscription events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await activate_subscription(session, db)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await cancel_subscription(subscription, db)
    
    return {"status": "ok"}
```

**Database:**
```python
# models.py - add

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    
    plan = Column(String, nullable=False)  # free, pro, coach
    status = Column(String, nullable=False)  # active, canceled, past_due
    
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", backref="subscription")
```

**API:**
```python
# api_billing.py - new router

@router.post("/billing/checkout")
async def create_checkout(
    plan: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session"""
    
    if plan not in ["pro", "coach"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    checkout = await create_checkout_session(current_user.id, plan, db)
    return checkout

@router.get("/billing/portal")
async def customer_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe customer portal session"""
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404)
    
    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url="https://aicoach.com/dashboard"
    )
    
    return {"portal_url": session.url}
```

**Frontend:**
```typescript
// app/pricing/page.tsx

export default function PricingPage() {
  const plans = [
    {
      name: "Free",
      price: "$0",
      features: [
        "1 weekly plan per month",
        "Basic analytics",
        "Strava sync",
        "Community features"
      ]
    },
    {
      name: "Pro",
      price: "$9.99",
      recommended: true,
      features: [
        "Unlimited weekly plans",
        "12-week planning",
        "Advanced analytics",
        "Race predictions"
      ]
    },
    {
      name: "Coach",
      price: "$29.99",
      features: [
        "All Pro features",
        "Race day strategy",
        "Nutrition planning",
        "1:1 support"
      ]
    }
  ];

  const handleSubscribe = async (plan: string) => {
    const response = await api.post('/billing/checkout', { plan });
    window.location.href = response.data.checkout_url;
  };

  return (
    <div className="grid grid-cols-3 gap-8">
      {plans.map(plan => (
        <PricingCard
          key={plan.name}
          plan={plan}
          onSubscribe={handleSubscribe}
        />
      ))}
    </div>
  );
}
```

**Estimated time:** 24-32 hours

### Week 13-14: Usage Limits & Feature Gates

**Feature: Plan-based Feature Access**

```python
# permissions.py - new module

from functools import wraps
from fastapi import HTTPException

def require_plan(min_plan: str):
    """Decorator to enforce plan requirements"""
    
    PLAN_HIERARCHY = {"free": 0, "pro": 1, "coach": 2}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db),
            **kwargs
        ):
            subscription = db.query(Subscription).filter(
                Subscription.user_id == current_user.id
            ).first()
            
            user_plan = subscription.plan if subscription else "free"
            
            if PLAN_HIERARCHY[user_plan] < PLAN_HIERARCHY[min_plan]:
                raise HTTPException(
                    status_code=403,
                    detail=f"This feature requires {min_plan} plan or higher"
                )
            
            return await func(*args, current_user=current_user, db=db, **kwargs)
        
        return wrapper
    return decorator

# Usage in endpoints
@router.post("/coach/multi_week_plan")
@require_plan("pro")
async def generate_multi_week_plan(...):
    """Pro feature: Multi-week planning"""
    pass

@router.post("/coach/race_strategy")
@require_plan("coach")
async def generate_race_strategy(...):
    """Coach feature: Race day strategy"""
    pass
```

**Usage tracking:**
```python
# models.py - add

class UsageQuota(Base):
    __tablename__ = "usage_quotas"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Free plan quotas (monthly)
    plans_generated_this_month = Column(Integer, default=0)
    max_plans_per_month = Column(Integer, default=1)
    
    # Reset date
    quota_reset_date = Column(Date)
    
    user = relationship("User")

async def check_and_increment_usage(
    user_id: int,
    feature: str,
    db: Session
) -> bool:
    """Check if user has quota and increment usage"""
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    # Pro/Coach have unlimited
    if subscription and subscription.plan in ["pro", "coach"]:
        return True
    
    # Free users have limits
    quota = db.query(UsageQuota).filter(
        UsageQuota.user_id == user_id
    ).first()
    
    if not quota:
        # Create initial quota
        quota = UsageQuota(
            user_id=user_id,
            quota_reset_date=get_next_month_start()
        )
        db.add(quota)
        db.commit()
    
    # Check if reset needed
    if dt.date.today() >= quota.quota_reset_date:
        quota.plans_generated_this_month = 0
        quota.quota_reset_date = get_next_month_start()
        db.commit()
    
    # Check limit
    if feature == "weekly_plan":
        if quota.plans_generated_this_month >= quota.max_plans_per_month:
            return False
        
        quota.plans_generated_this_month += 1
        db.commit()
    
    return True
```

**Estimated time:** 16-20 hours

### Week 15-16: Analytics & Optimization

**Admin Dashboard**

```python
# api_admin.py - new router (admin only)

@router.get("/admin/metrics")
async def get_platform_metrics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Platform-wide metrics"""
    
    total_users = db.query(User).count()
    
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active"
    ).count()
    
    mrr = db.query(Subscription).filter(
        Subscription.status == "active"
    ).all()
    
    total_mrr = sum(
        PLANS[sub.plan]["price"] for sub in mrr
    )
    
    # User activity
    active_users_7d = db.query(User).filter(
        User.last_login_at >= dt.datetime.now() - dt.timedelta(days=7)
    ).count()
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "mrr": total_mrr,
        "active_users_7d": active_users_7d,
        "conversion_rate": active_subscriptions / total_users if total_users > 0 else 0
    }

@router.get("/admin/users")
async def list_users(
    page: int = 1,
    per_page: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users with subscription info"""
    pass
```

**Estimated time:** 12-16 hours

**Phase 4 Success Metrics:**
- ✅ Stripe integration complete
- ✅ 3 pricing tiers live
- ✅ 10%+ free → paid conversion
- ✅ $1K+ MRR by end of phase
- ✅ Churn rate < 5%

---

## 🔬 Фаза 5: Advanced Features (Weeks 17+)

**Цель**: Differentiate from competitors

### Advanced Features List

**1. Race Day Strategy Generator** (Week 17-18)
- Comprehensive race plan with splits
- Nutrition timing
- Pacing strategy
- Transition optimization
- Mental cues

**2. Nutrition Planning** (Week 19-20)
- Race-specific fueling
- Daily nutrition recommendations
- Supplement guidance
- Hydration calculator

**3. Form Analysis** (Week 21-22)
- Video upload
- AI form check (using computer vision)
- Technique recommendations
- Injury prevention

**4. Voice Coach** (Week 23-24)
- Audio workout guidance
- Real-time coaching during runs
- Motivational prompts
- Form cues

**5. Wearables Integration** (Week 25+)
- Garmin Connect API
- Apple Watch integration
- Wahoo/Zwift integration
- Real-time data sync

---

## 📊 Key Metrics to Track

### Product Metrics
- **DAU** (Daily Active Users): target 100+ by Week 16
- **WAU** (Weekly Active Users): target 500+ by Week 16
- **Plans generated per user**: target 2+ per month
- **Feature adoption rate**: target 60%+ for new features

### Business Metrics
- **MRR** (Monthly Recurring Revenue): $1K by Week 16, $5K by Week 24
- **CAC** (Customer Acquisition Cost): target < $20
- **LTV** (Lifetime Value): target > $100
- **Churn rate**: target < 5% per month
- **Conversion rate (Free → Pro)**: target 10-15%

### Technical Metrics
- **API response time (p95)**: < 500ms
- **Error rate**: < 1%
- **Strava sync success rate**: > 95%
- **GPT API latency**: < 10s for plan generation
- **Uptime**: > 99.5%

---

## 🎯 Success Criteria

### By End of Phase 2 (Week 6)
- [ ] 100+ registered users
- [ ] 50+ active weekly users
- [ ] 200+ plans generated
- [ ] 0 critical bugs
- [ ] Production deploy stable

### By End of Phase 3 (Week 10)
- [ ] 500+ registered users
- [ ] 200+ active weekly users
- [ ] 30%+ engagement with social features
- [ ] 1000+ training log posts
- [ ] 50+ achievements earned

### By End of Phase 4 (Week 16)
- [ ] 1000+ registered users
- [ ] 100+ paying subscribers
- [ ] $1K+ MRR
- [ ] 15%+ free → paid conversion
- [ ] < 5% monthly churn

---

**Ready to build something amazing!** 🚀💪
