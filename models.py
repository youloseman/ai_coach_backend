from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Date, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    """User accounts"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Strava integration
    strava_athlete_id = Column(String, unique=True, nullable=True)
    strava_access_token = Column(String, nullable=True)
    strava_refresh_token = Column(String, nullable=True)
    strava_token_expires_at = Column(DateTime, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("AthleteProfileDB", back_populates="user", uselist=False)
    weekly_plans = relationship("WeeklyPlanDB", back_populates="user")
    activities = relationship("ActivityDB", back_populates="user")
    goals = relationship("GoalDB", back_populates="user")
    segment_efforts = relationship("SegmentEffortDB", backref="user_efforts")
    personal_records = relationship("PersonalRecordDB", backref="user_records")
    injury_risks = relationship("InjuryRiskDB", backref="user_risks")
    nutrition_targets = relationship("NutritionTargetDB", backref="user")
    nutrition_plans = relationship("NutritionPlanDB", backref="user")


class AthleteProfileDB(Base):
    """Athlete profile - training zones, preferences, stats"""
    __tablename__ = "athlete_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Basic info
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    
    # Experience
    years_of_experience = Column(Integer, default=0)
    primary_discipline = Column(String, nullable=True)  # run, bike, swim
    
    # Training zones (JSON)
    training_zones_run = Column(JSON, nullable=True)
    training_zones_bike = Column(JSON, nullable=True)
    training_zones_swim = Column(JSON, nullable=True)
    zones_last_updated = Column(Date, nullable=True)
    
    # Auto-calculated stats
    auto_weeks_analyzed = Column(Integer, default=0)
    auto_current_weekly_streak_weeks = Column(Integer, default=0)
    auto_longest_weekly_streak_weeks = Column(Integer, default=0)
    auto_avg_hours_last_12_weeks = Column(Float, default=0.0)
    auto_avg_hours_last_52_weeks = Column(Float, default=0.0)
    auto_discipline_hours_per_week = Column(JSON, nullable=True)
    
    # Preferences
    preferred_training_days = Column(JSON, nullable=True)  # ["monday", "wednesday", ...]
    available_hours_per_week = Column(Float, default=8.0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")


class GoalDB(Base):
    """Training goals"""
    __tablename__ = "goals"
    
    __table_args__ = (
        Index('idx_goals_user_date', 'user_id', 'race_date'),
        Index('idx_goals_user_type', 'user_id', 'goal_type'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    goal_type = Column(String, nullable=False)  # SPRINT, OLYMPIC, HALF_IRONMAN, etc.
    target_time = Column(String, nullable=True)  # "4:30" or "sub 5:00"
    race_date = Column(Date, nullable=False)
    race_name = Column(String, nullable=True)
    race_location = Column(String, nullable=True)
    
    is_primary = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="goals")


class WeeklyPlanDB(Base):
    """Weekly training plans"""
    __tablename__ = "weekly_plans"
    
    __table_args__ = (
        Index('idx_weekly_plans_user_date', 'user_id', 'week_start_date'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    week_start_date = Column(Date, nullable=False)
    week_number = Column(Integer, nullable=True)  # week in training cycle
    
    # Plan content (JSON from GPT)
    plan_json = Column(JSON, nullable=False)
    
    # Metadata
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    available_hours = Column(Float, nullable=True)
    coach_notes = Column(Text, nullable=True)
    
    # Actual vs planned
    completed = Column(Boolean, default=False)
    completion_rate = Column(Float, nullable=True)  # 0-100%
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="weekly_plans")


class ActivityDB(Base):
    """Cached Strava activities"""
    __tablename__ = "activities"
    
    __table_args__ = (
        Index('idx_activities_user_date', 'user_id', 'start_date'),
        Index('idx_activities_user_sport', 'user_id', 'sport_type'),
        Index('idx_activities_strava', 'strava_id'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    strava_id = Column(String, unique=True, nullable=False, index=True)
    
    # Basic info
    name = Column(String, nullable=False)
    sport_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    
    # Metrics
    distance_meters = Column(Float, nullable=True)
    moving_time_seconds = Column(Integer, nullable=True)
    elapsed_time_seconds = Column(Integer, nullable=True)
    total_elevation_gain = Column(Float, nullable=True)
    
    # Heart rate
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Float, nullable=True)
    
    # Power (cycling)
    average_watts = Column(Float, nullable=True)
    weighted_average_watts = Column(Float, nullable=True)
    
    # Calculated metrics
    tss = Column(Float, nullable=True)
    intensity_factor = Column(Float, nullable=True)
    
    # Raw data from Strava
    raw_data = Column(JSON, nullable=True)
    
    # Sync info
    synced_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activities")
    segment_efforts = relationship("SegmentEffortDB", back_populates="activity")
    personal_records = relationship("PersonalRecordDB", back_populates="activity")


class TrainingLoadDB(Base):
    """Daily training load calculations (CTL, ATL, TSB)"""
    __tablename__ = "training_load"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uix_training_load_user_date'),
        Index('idx_training_load_user_date', 'user_id', 'date'),
        {'sqlite_autoincrement': True},
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    date = Column(Date, nullable=False)
    
    # Training metrics
    daily_tss = Column(Float, default=0.0)
    ctl = Column(Float, default=0.0)  # Chronic Training Load (fitness)
    atl = Column(Float, default=0.0)  # Acute Training Load (fatigue)
    tsb = Column(Float, default=0.0)  # Training Stress Balance (form)
    
    # Volume
    total_hours = Column(Float, default=0.0)
    run_hours = Column(Float, default=0.0)
    bike_hours = Column(Float, default=0.0)
    swim_hours = Column(Float, default=0.0)
    
    calculated_at = Column(DateTime, default=func.now())


class AppState(Base):
    """Simple key-value storage for JSON blobs (e.g., persisted settings)"""
    __tablename__ = "app_state"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SegmentDB(Base):
    """Strava segments"""
    __tablename__ = "segments"
    
    id = Column(Integer, primary_key=True)
    strava_segment_id = Column(String, unique=True, nullable=False, index=True)
    
    # Basic info
    name = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)  # Run, Ride
    distance_meters = Column(Float, nullable=False)
    
    # Location
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Elevation
    average_grade = Column(Float, nullable=True)
    maximum_grade = Column(Float, nullable=True)
    elevation_high = Column(Float, nullable=True)
    elevation_low = Column(Float, nullable=True)
    total_elevation_gain = Column(Float, nullable=True)
    
    # Stats
    athlete_count = Column(Integer, default=0)  # Total athletes who have ridden this segment
    effort_count = Column(Integer, default=0)   # Total efforts on this segment
    star_count = Column(Integer, default=0)     # Number of stars
    
    # Raw data from Strava
    raw_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    efforts = relationship("SegmentEffortDB", back_populates="segment")


class SegmentEffortDB(Base):
    """User's efforts on Strava segments"""
    __tablename__ = "segment_efforts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True, index=True)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=False, index=True)
    
    strava_effort_id = Column(String, unique=True, nullable=False, index=True)
    
    # Timing
    start_date = Column(DateTime, nullable=False, index=True)
    elapsed_time_seconds = Column(Integer, nullable=False)
    moving_time_seconds = Column(Integer, nullable=True)
    
    # Performance
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Float, nullable=True)
    average_watts = Column(Float, nullable=True)
    average_cadence = Column(Float, nullable=True)
    
    # Rankings (at time of effort)
    pr_rank = Column(Integer, nullable=True)  # Personal rank (1 = PR)
    kom_rank = Column(Integer, nullable=True)  # Overall rank on segment
    
    # Metadata
    is_pr = Column(Boolean, default=False, index=True)  # Is this a Personal Record?
    device_watts = Column(Boolean, default=False)  # True if power from device, not estimated
    
    # Raw data from Strava
    raw_data = Column(JSON, nullable=True)
    
    # Timestamps
    synced_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="segment_efforts", overlaps="user_efforts")
    activity = relationship("ActivityDB", back_populates="segment_efforts")
    segment = relationship("SegmentDB", back_populates="efforts")


class PersonalRecordDB(Base):
    """Personal records for different distances and activities"""
    __tablename__ = "personal_records"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Record type
    sport_type = Column(String, nullable=False, index=True)  # run, bike, swim
    distance_category = Column(String, nullable=False, index=True)  # 5K, 10K, HM, Marathon, 40K, etc.
    
    # Performance
    distance_meters = Column(Float, nullable=False)
    time_seconds = Column(Integer, nullable=False)
    pace_per_km = Column(Float, nullable=True)  # seconds per km
    speed_kmh = Column(Float, nullable=True)    # km/h
    
    # Additional metrics
    average_heartrate = Column(Float, nullable=True)
    average_watts = Column(Float, nullable=True)
    elevation_gain = Column(Float, nullable=True)
    
    # Context
    achieved_date = Column(DateTime, nullable=False, index=True)
    activity_name = Column(String, nullable=True)
    
    # Status
    is_current_pr = Column(Boolean, default=True, index=True)  # False if beaten
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    superseded_at = Column(DateTime, nullable=True)  # When this PR was beaten
    
    # Relationships
    user = relationship("User", back_populates="personal_records", overlaps="user_records")
    activity = relationship("ActivityDB", back_populates="personal_records")


class InjuryRiskDB(Base):
    """AI-detected injury risk warnings"""
    __tablename__ = "injury_risks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Risk assessment
    risk_level = Column(String, nullable=False)  # low, medium, high, critical
    risk_type = Column(String, nullable=False)   # overtraining, sudden_spike, chronic_fatigue, etc.
    
    # Details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    
    # Metrics that triggered the warning
    trigger_metrics = Column(JSON, nullable=True)  # {ctl: 120, atl: 80, tsb: -40, ...}
    
    # Status
    detected_date = Column(Date, nullable=False, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="injury_risks", overlaps="user_risks")


class NutritionTargetDB(Base):
    """Daily nutrition targets for users"""
    __tablename__ = "nutrition_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Target calories and macros
    daily_calories = Column(Float, nullable=True)  # kcal
    daily_carbs_grams = Column(Float, nullable=True)  # grams
    daily_protein_grams = Column(Float, nullable=True)  # grams
    daily_fat_grams = Column(Float, nullable=True)  # grams
    
    # Activity level multipliers
    activity_level = Column(String, nullable=True)
    training_days_per_week = Column(Integer, nullable=True, default=3)
    
    # Goals
    goal_type = Column(String, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    # user relationship is created via backref in User model


class NutritionPlanDB(Base):
    """Race day and recovery nutrition plans"""
    __tablename__ = "nutrition_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Plan type
    plan_type = Column(String, nullable=False, index=True)
    race_type = Column(String, nullable=True)
    race_duration_hours = Column(Float, nullable=True)
    
    # Pre-race nutrition
    pre_race_meals = Column(JSON, nullable=True)
    
    # During race nutrition
    during_race_fueling = Column(JSON, nullable=True)
    
    # Post-race recovery
    recovery_nutrition = Column(JSON, nullable=True)
    
    # Daily nutrition breakdown
    daily_meals = Column(JSON, nullable=True)
    
    # Notes and recommendations
    notes = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    # user relationship is created via backref in User model