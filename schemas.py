from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date


# ===== AUTH SCHEMAS =====

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    strava_athlete_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ===== PROFILE SCHEMAS =====

class ProfileUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    years_of_experience: Optional[int] = None
    primary_discipline: Optional[str] = None
    available_hours_per_week: Optional[float] = None
    preferred_training_days: Optional[List[str]] = None


class TrainingZonesUpdate(BaseModel):
    """Update training zones for TSS calculation"""
    ftp: Optional[int] = Field(None, description="Functional Threshold Power (watts) for cycling")
    threshold_pace_min_per_km: Optional[float] = Field(None, description="Threshold pace (min/km) for running")
    css_pace_100m_seconds: Optional[float] = Field(None, description="Critical Swim Speed (seconds/100m) for swimming")
    max_hr: Optional[int] = Field(None, description="Maximum heart rate (bpm)")
    rest_hr: Optional[int] = Field(None, description="Resting heart rate (bpm)")


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    age: Optional[int]
    gender: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    years_of_experience: int
    primary_discipline: Optional[str]
    training_zones_run: Optional[dict]
    training_zones_bike: Optional[dict]
    training_zones_swim: Optional[dict]
    available_hours_per_week: float
    auto_avg_hours_last_12_weeks: float
    auto_current_weekly_streak_weeks: int
    
    class Config:
        from_attributes = True


# ===== GOAL SCHEMAS =====

class GoalCreate(BaseModel):
    goal_type: str = Field(description="SPRINT, OLYMPIC, HALF_IRONMAN, IRONMAN, etc.")
    target_time: Optional[str] = Field(None, description="Target time like '4:30' or 'sub 5:00'")
    race_date: date
    race_name: Optional[str] = None
    race_location: Optional[str] = None
    is_primary: bool = False


class GoalResponse(BaseModel):
    id: int
    user_id: int
    goal_type: str
    target_time: Optional[str]
    race_date: date
    race_name: Optional[str]
    race_location: Optional[str]
    is_primary: bool
    is_completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True