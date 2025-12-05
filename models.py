from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Date, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

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


class AthleteProfileDB(Base):
    """Athlete profile - training zones, preferences, stats"""
    __tablename__ = "athlete_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
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
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
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
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    week_start_date = Column(Date, nullable=False)
    week_number = Column(Integer, nullable=True)  # week in training cycle
    
    # Plan content (JSON from GPT)
    plan_json = Column(JSON, nullable=False)
    
    # Metadata
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
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
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
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


class TrainingLoadDB(Base):
    """Daily training load calculations (CTL, ATL, TSB)"""
    __tablename__ = "training_load"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
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
    
    # Composite unique constraint
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class AppState(Base):
    """Simple key-value storage for JSON blobs (e.g., persisted settings)"""
    __tablename__ = "app_state"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())