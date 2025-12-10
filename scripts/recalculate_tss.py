# scripts/recalculate_tss.py

"""
Management script to recalculate TSS for all existing activities.

Usage:
    python scripts/recalculate_tss.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import ActivityDB, User
from services.activity_service import calculate_and_save_tss
from config import logger


def recalculate_all_tss_sync():
    """
    Synchronous version - recalculate TSS for all activities that don't have it
    """
    db = SessionLocal()
    
    try:
        # Get all activities without TSS
        activities = db.query(ActivityDB).filter(
            ActivityDB.tss.is_(None)
        ).all()
        
        print(f"Found {len(activities)} activities without TSS")
        
        if len(activities) == 0:
            print("No activities to update. All activities already have TSS.")
            return
        
        updated_count = 0
        skipped_count = 0
        
        for activity in activities:
            # Get user
            user = db.query(User).filter(User.id == activity.user_id).first()
            if not user:
                print(f"Skipping activity {activity.id}: user not found")
                skipped_count += 1
                continue
            
            # Calculate TSS
            try:
                activity = calculate_and_save_tss(activity, user, db)
                if activity.tss:
                    print(f"Activity {activity.id} ({activity.sport_type}): TSS = {activity.tss:.1f}")
                    updated_count += 1
                else:
                    print(f"Activity {activity.id}: TSS calculation returned 0 (skipped)")
                    skipped_count += 1
            except Exception as e:
                print(f"Error calculating TSS for activity {activity.id}: {e}")
                logger.error("tss_recalculation_error", activity_id=activity.id, error=str(e))
                skipped_count += 1
        
        print(f"\nDone!")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error("tss_recalculation_fatal", error=str(e))
        raise
    finally:
        db.close()


def recalculate_all_tss_force():
    """
    Force recalculate TSS for ALL activities (even if they already have TSS)
    """
    db = SessionLocal()
    
    try:
        # Get all activities
        activities = db.query(ActivityDB).all()
        
        print(f"Found {len(activities)} total activities")
        print("Recalculating TSS for all activities (force mode)...")
        
        updated_count = 0
        skipped_count = 0
        
        for activity in activities:
            # Get user
            user = db.query(User).filter(User.id == activity.user_id).first()
            if not user:
                print(f"Skipping activity {activity.id}: user not found")
                skipped_count += 1
                continue
            
            # Calculate TSS (will overwrite existing)
            try:
                old_tss = activity.tss
                activity = calculate_and_save_tss(activity, user, db)
                if activity.tss:
                    change = f"({old_tss:.1f} -> {activity.tss:.1f})" if old_tss else "(new)"
                    print(f"Activity {activity.id} ({activity.sport_type}): TSS = {activity.tss:.1f} {change}")
                    updated_count += 1
                else:
                    print(f"Activity {activity.id}: TSS calculation returned 0 (skipped)")
                    skipped_count += 1
            except Exception as e:
                print(f"Error calculating TSS for activity {activity.id}: {e}")
                logger.error("tss_recalculation_error", activity_id=activity.id, error=str(e))
                skipped_count += 1
        
        print(f"\nDone!")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error("tss_recalculation_fatal", error=str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Recalculate TSS for activities")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalculate TSS for all activities, even if they already have TSS"
    )
    
    args = parser.parse_args()
    
    if args.force:
        print("Running in FORCE mode (will recalculate all activities)...")
        recalculate_all_tss_force()
    else:
        print("Running in normal mode (only activities without TSS)...")
        recalculate_all_tss_sync()

