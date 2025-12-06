"""
Integration tests for AI Coach Backend.

Tests critical components and integrations.
"""

import pytest
import sys
from pathlib import Path

# Ensure project root is on path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal, init_db
from models import (
    User, AthleteProfileDB, GoalDB, WeeklyPlanDB, ActivityDB,
    SegmentDB, SegmentEffortDB, PersonalRecordDB, InjuryRiskDB, AppState
)
import crud
from schemas import UserCreate, GoalCreate
from datetime import datetime, date
import json


@pytest.fixture(scope="module")
def db_session():
    """Create test database session."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up: drop all tables after tests
        Base.metadata.drop_all(bind=engine)


class TestDatabase:
    """Test database models and CRUD operations."""
    
    def test_all_tables_exist(self, db_session):
        """Verify all expected tables exist."""
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "users", "athlete_profiles", "goals", "weekly_plans",
            "activities", "training_load", "app_state",
            "segments", "segment_efforts", "personal_records", "injury_risks"
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"
    
    def test_create_user(self, db_session: Session):
        """Test user creation."""
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            full_name="Test User"
        )
        
        user = crud.create_user(db_session, user_data)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password != "testpass123"  # Should be hashed
        assert user.profile is not None  # Profile should be created automatically
    
    def test_user_relationships(self, db_session: Session):
        """Test that user relationships work correctly."""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert user is not None
        
        # Check profile relationship
        assert user.profile is not None
        assert user.profile.user_id == user.id
        
        # Check that relationships exist (may be empty lists)
        assert hasattr(user, 'weekly_plans')
        assert hasattr(user, 'activities')
        assert hasattr(user, 'goals')
        assert hasattr(user, 'segment_efforts')
        assert hasattr(user, 'personal_records')
        assert hasattr(user, 'injury_risks')


class TestCRUDOperations:
    """Test CRUD operations for all models."""
    
    def test_activity_crud(self, db_session: Session):
        """Test activity CRUD operations."""
        # Create a test user first
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        
        if not user:
            user_data = UserCreate(
                email="test@example.com",
                username="testuser",
                password="testpass123"
            )
            user = crud.create_user(db_session, user_data)
        
        # Test upsert_activity
        strava_activity = {
            "id": 12345,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date": "2025-12-06T08:00:00Z",
            "distance": 10000,  # 10km in meters
            "moving_time": 2400,  # 40 minutes
            "elapsed_time": 2400,
            "total_elevation_gain": 100.5,
            "average_heartrate": 145.0,
            "max_heartrate": 165.0,
            "average_watts": None
        }
        
        activity = crud.upsert_activity(db_session, user.id, strava_activity)
        
        assert activity.id is not None
        assert activity.strava_id == "12345"
        assert activity.name == "Morning Run"
        assert activity.distance_meters == 10000
        assert activity.user_id == user.id
        
        # Test that update works (upsert with same ID)
        strava_activity["name"] = "Updated Run"
        updated_activity = crud.upsert_activity(db_session, user.id, strava_activity)
        
        assert updated_activity.id == activity.id
        assert updated_activity.name == "Updated Run"
    
    def test_segment_crud(self, db_session: Session):
        """Test segment and segment effort CRUD."""
        segment_data = {
            "id": 999,
            "name": "Test Hill Climb",
            "activity_type": "Ride",
            "distance": 5000,  # 5km
            "average_grade": 5.2,
            "city": "Test City",
            "country": "Test Country",
            "athlete_count": 1000,
            "effort_count": 5000
        }
        
        segment = crud.upsert_segment(db_session, segment_data)
        
        assert segment.id is not None
        assert segment.strava_segment_id == "999"
        assert segment.name == "Test Hill Climb"
        assert segment.distance_meters == 5000
    
    def test_personal_record_crud(self, db_session: Session):
        """Test personal record creation."""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        
        pr = crud.create_personal_record(
            db=db_session,
            user_id=user.id,
            activity_db_id=None,
            sport_type="run",
            distance_category="5K",
            distance_meters=5000,
            time_seconds=1200,  # 20 minutes
            achieved_date=datetime(2025, 12, 6, 10, 0, 0)
        )
        
        assert pr.id is not None
        assert pr.sport_type == "run"
        assert pr.distance_category == "5K"
        assert pr.time_seconds == 1200
        assert pr.is_current_pr is True
        assert pr.pace_per_km is not None
        
        # Test that getting PRs works
        prs = crud.get_current_personal_records(db_session, user.id)
        assert len(prs) >= 1
        assert any(p.distance_category == "5K" for p in prs)


class TestTrainingZones:
    """Test training zones calculations."""
    
    def test_import_training_zones(self):
        """Verify training_zones module can be imported and basic functions exist."""
        import training_zones
        
        # Check that key functions exist (using actual function names)
        assert hasattr(training_zones, 'calculate_running_zones_from_race')
        assert hasattr(training_zones, 'calculate_cycling_zones_from_ftp')
        assert hasattr(training_zones, 'find_best_race_efforts')
    
    def test_run_zones_calculation(self):
        """Test run zones calculation."""
        from training_zones import calculate_running_zones_from_race
        
        # Test with a 10K time of 40:00 (distance 10km, time 2400 seconds)
        zones = calculate_running_zones_from_race(
            distance_km=10.0,
            time_seconds=2400  # 40:00
        )
        
        # Function should return zones object with pace information
        assert zones is not None
        # Check that it has zone attributes (it's a RunningZones object)
        assert hasattr(zones, 'z1_min') or hasattr(zones, 'threshold_pace_per_km')


class TestAnalytics:
    """Test analytics functions."""
    
    def test_import_analytics(self):
        """Verify analytics module can be imported."""
        import analytics
        
        assert hasattr(analytics, 'analyze_training_load')
        assert hasattr(analytics, 'calculate_training_metrics')
        assert hasattr(analytics, 'get_form_interpretation')
    
    def test_fatigue_detection_import(self):
        """Verify fatigue detection can be imported."""
        import fatigue_detection
        
        assert hasattr(fatigue_detection, 'detect_fatigue')


class TestSegmentSync:
    """Test segment synchronization functions."""
    
    def test_import_segment_sync(self):
        """Verify segment_sync module can be imported."""
        import segment_sync
        
        assert hasattr(segment_sync, 'sync_segment_efforts_for_activity')
        assert hasattr(segment_sync, 'detect_personal_records')
        assert hasattr(segment_sync, 'analyze_injury_risk')


class TestMultiWeekPlanner:
    """Test multi-week planning."""
    
    def test_import_multi_week_planner(self):
        """Verify multi_week_planner can be imported."""
        import multi_week_planner
        
        assert hasattr(multi_week_planner, 'generate_multi_week_plan')
        assert hasattr(multi_week_planner, 'get_phase_template')
        assert hasattr(multi_week_planner, 'determine_recovery_weeks')
    
    def test_recovery_weeks_calculation(self):
        """Test recovery weeks determination."""
        from multi_week_planner import determine_recovery_weeks
        
        # 12 weeks should have recovery weeks at 4, 8
        recovery = determine_recovery_weeks(12)
        assert 4 in recovery
        assert 8 in recovery
        assert 12 not in recovery  # Last week should not be recovery (it's taper)


class TestAPIImports:
    """Test that API modules can be imported."""
    
    def test_api_modules_import(self):
        """Verify all API modules can be imported."""
        import api_auth
        import api_user
        import api_coach
        import api_segments
        
        # Check that routers exist
        assert hasattr(api_auth, 'router')
        assert hasattr(api_user, 'router')
        assert hasattr(api_coach, 'router')
        assert hasattr(api_segments, 'router')


class TestConfig:
    """Test configuration."""
    
    def test_config_import(self):
        """Verify config module can be imported."""
        import config
        
        # Check that key config exists (may be None in test env)
        assert hasattr(config, 'STRAVA_CLIENT_ID')
        # DATABASE_URL is in database.py, not config.py


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

