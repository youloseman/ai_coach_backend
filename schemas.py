from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class SportType(str, Enum):
    """Sport types"""
    RUN = "run"
    RIDE = "ride"
    SWIM = "swim"
    WORKOUT = "workout"
    WALK = "walk"
    HIKE = "hike"
    OTHER = "other"


class GoalType(str, Enum):
    """Goal types for triathlon"""
    SPRINT = "SPRINT"
    OLYMPIC = "OLYMPIC"
    HALF_IRONMAN = "HALF_IRONMAN"
    IRONMAN = "IRONMAN"
    MARATHON = "MARATHON"
    HALF_MARATHON = "HALF_MARATHON"
    CUSTOM = "CUSTOM"


class RiskLevel(str, Enum):
    """Injury risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
    """Update athlete profile with validation"""
    age: Optional[int] = Field(None, ge=10, le=120, description="Age in years")
    weight_kg: Optional[float] = Field(None, gt=30, lt=300, description="Weight in kg")
    height_cm: Optional[float] = Field(None, gt=100, lt=250, description="Height in cm")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    years_of_experience: Optional[int] = None
    primary_discipline: Optional[str] = None
    available_hours_per_week: Optional[float] = Field(None, ge=0, le=168)
    preferred_training_days: Optional[List[str]] = None
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v and v not in {'male', 'female', 'other'}:
            raise ValueError('gender must be male, female, or other')
        return v


class TrainingZonesUpdate(BaseModel):
    """Update training zones with validation"""
    model_config = ConfigDict(populate_by_name=True)

    ftp: Optional[int] = Field(None, gt=0, lt=600, description="FTP in watts")

    # canonical backend names (accept legacy aliases too)
    threshold_pace: Optional[float] = Field(
        None,
        gt=2.0,
        lt=10.0,
        alias="threshold_pace_min_per_km",
        description="Threshold pace (min/km) for running"
    )
    css_pace_100m: Optional[float] = Field(
        None,
        gt=30,
        lt=300,
        alias="css_pace_100m_seconds",
        description="Critical Swim Speed (seconds/100m) for swimming"
    )

    max_hr: Optional[int] = Field(None, ge=100, le=220, description="Max HR in bpm")
    rest_hr: Optional[int] = Field(None, ge=30, le=100, description="Resting HR in bpm")
    
    @field_validator('rest_hr')
    @classmethod
    def rest_hr_less_than_max(cls, v, info):
        """Ensure rest HR < max HR"""
        max_hr = info.data.get('max_hr')
        if v and max_hr and v >= max_hr:
            raise ValueError('rest_hr must be less than max_hr')
        return v


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    age: Optional[int]
    gender: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    years_of_experience: Optional[int]
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
    """Create goal with validation"""
    goal_type: GoalType
    race_date: date
    target_time: Optional[str] = Field(None, pattern="^[0-9]{1,2}:[0-9]{2}:[0-9]{2}$")
    race_name: Optional[str] = None
    race_location: Optional[str] = None
    is_primary: bool = False
    priority: int = Field(default=3, ge=1, le=5)
    
    @field_validator('race_date')
    @classmethod
    def race_date_future(cls, v):
        """Ensure race date is in the future"""
        if v < date.today():
            raise ValueError('race_date must be in the future')
        return v


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


# ============= ACTIVITY SCHEMAS =============

class ActivityBase(BaseModel):
    """Base activity schema"""
    name: Optional[str] = None
    sport_type: SportType
    distance_meters: Optional[float] = Field(None, ge=0)
    moving_time_seconds: Optional[int] = Field(None, ge=0)
    elapsed_time_seconds: Optional[int] = Field(None, ge=0)
    total_elevation_gain: Optional[float] = Field(None, ge=0)


class ActivityCreate(ActivityBase):
    """Create activity"""
    strava_id: Optional[str] = None
    start_date: datetime


class ActivityResponse(ActivityBase):
    """Activity response"""
    id: int
    strava_id: Optional[str]
    start_date: datetime
    tss: Optional[float] = Field(None, ge=0)
    average_watts: Optional[float]
    average_heartrate: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    """List of activities with pagination"""
    activities: List[ActivityResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============= WEEKLY PLAN SCHEMAS =============

class DayPlan(BaseModel):
    """Single day in weekly plan"""
    date: date
    sport: str
    session_type: str  # e.g., "Interval", "Easy", "Long"
    duration_min: int = Field(gt=0, le=480)  # Max 8 hours
    intensity: str  # e.g., "Zone 2", "Threshold"
    description: str = Field(max_length=500)
    target_tss: Optional[float] = Field(None, ge=0, le=300)


class WeeklyPlanCreate(BaseModel):
    """Create weekly plan"""
    week_start_date: date
    goal_id: Optional[int] = None
    available_hours: float = Field(gt=0, le=168)  # Max 7 days * 24 hours
    days: List[DayPlan] = Field(min_items=1, max_items=7)


class WeeklyPlanResponse(BaseModel):
    """Weekly plan response"""
    id: int
    week_start_date: date
    goal_id: Optional[int]
    days: List[DayPlan]
    total_planned_tss: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= PMC / ANALYTICS SCHEMAS =============

class PMCDataPoint(BaseModel):
    """Single day PMC data"""
    date: date
    ctl: float = Field(ge=0, description="Chronic Training Load (Fitness)")
    atl: float = Field(ge=0, description="Acute Training Load (Fatigue)")
    tsb: float = Field(description="Training Stress Balance (Form)")
    daily_tss: float = Field(ge=0, description="Total TSS for the day")
    rr: float = Field(description="Ramp Rate")


class PMCResponse(BaseModel):
    """PMC chart data"""
    data: List[PMCDataPoint]
    current_ctl: float
    current_atl: float
    current_tsb: float
    current_rr: float
    form_status: str  # peaked/fresh/neutral/optimal_overload/high_risk


class FitnessSummary(BaseModel):
    """Fitness summary for dashboard"""
    ctl_7day_change: float
    atl_7day_change: float
    form_status: str
    days_until_peaked: Optional[int]
    recommended_tss_today: float


# ============= NUTRITION SCHEMAS =============

class NutritionTargetCreate(BaseModel):
    """Create nutrition target"""
    calories_per_day: int = Field(gt=0, le=10000)
    protein_g: int = Field(gt=0, le=500)
    carbs_g: int = Field(gt=0, le=1000)
    fat_g: int = Field(gt=0, le=500)


class NutritionPlanResponse(BaseModel):
    """Nutrition plan response"""
    id: int
    date: date
    calories_actual: Optional[int]
    protein_actual: Optional[float]
    carbs_actual: Optional[float]
    fat_actual: Optional[float]
    notes: Optional[str]
    
    class Config:
        from_attributes = True