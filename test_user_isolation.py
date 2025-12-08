"""
Test script for user data isolation.
Tests that users can only see their own data after logout/login.
"""

import requests
import json
import time
from typing import Optional, Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Change if needed

# Check if backend is running before tests
def check_backend_health(base_url: str) -> bool:
    """Check if backend is running"""
    try:
        import requests
        response = requests.get(f"{base_url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False
USER_A_EMAIL = "user_a@test.com"
USER_A_PASSWORD = "testpass123"
USER_B_EMAIL = "user_b@test.com"
USER_B_PASSWORD = "testpass456"

class TestClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.session = requests.Session()
    
    def register(self, email: str, password: str, username: str = None) -> Dict[str, Any]:
        """Register a new user"""
        if username is None:
            username = email.split("@")[0]
        
        response = self.session.post(
            f"{self.base_url}/auth/register",
            json={
                "email": email,
                "password": password,
                "username": username,
                "full_name": username.title()
            }
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return data
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            data={
                "username": email,  # OAuth2 uses 'username' field
                "password": password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token")
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get user info
        me_response = self.session.get(f"{self.base_url}/auth/me")
        if me_response.status_code == 200:
            self.user_id = me_response.json().get("id")
        
        return data
    
    def logout(self):
        """Clear session"""
        self.token = None
        self.user_id = None
        self.session.headers.pop("Authorization", None)
    
    def create_goal(self, race_name: str, goal_type: str, race_date: str, target_time: str) -> Dict[str, Any]:
        """Create a training goal"""
        response = self.session.post(
            f"{self.base_url}/goals",
            json={
                "race_name": race_name,
                "goal_type": goal_type,
                "race_date": race_date,
                "target_time": target_time,
                "is_primary": True
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_goals(self) -> list:
        """Get user goals"""
        response = self.session.get(f"{self.base_url}/goals")
        response.raise_for_status()
        return response.json()
    
    def get_primary_goal(self) -> Optional[Dict[str, Any]]:
        """Get primary goal"""
        try:
            response = self.session.get(f"{self.base_url}/goals/primary")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def get_activities(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Get Strava activities"""
        response = self.session.get(
            f"{self.base_url}/strava/activities",
            params={"page": page, "per_page": per_page}
        )
        response.raise_for_status()
        return response.json()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data"""
        data = {}
        
        # Get profile
        try:
            response = self.session.get(f"{self.base_url}/profile")
            if response.status_code == 200:
                data["profile"] = response.json()
        except:
            pass
        
        # Get primary goal
        data["primary_goal"] = self.get_primary_goal()
        
        # Get goals
        data["goals"] = self.get_goals()
        
        # Get activities
        try:
            data["activities"] = self.get_activities()
        except:
            data["activities"] = None
        
        return data


def test_user_isolation():
    """Run user isolation tests"""
    print("=" * 60)
    print("USER DATA ISOLATION TEST")
    print("=" * 60)
    
    # Check backend is running
    print("\n[PRE-CHECK] Checking if backend is running...")
    if not check_backend_health(BASE_URL):
        print(f"❌ Backend is not running at {BASE_URL}")
        print("\nPlease start the backend first:")
        print("  python -m uvicorn main:app --reload --port 8000")
        print("\nOr if using Railway/production:")
        print(f"  python test_user_isolation.py <your-backend-url>")
        return False
    print(f"✅ Backend is running at {BASE_URL}")
    
    client = TestClient(BASE_URL)
    all_tests_passed = True
    
    # ===== TEST 1: Register User A =====
    print("\n[TEST 1] Registering User A...")
    try:
        client.register(USER_A_EMAIL, USER_A_PASSWORD)
        print(f"✅ User A registered (ID: {client.user_id})")
    except Exception as e:
        print(f"❌ Failed to register User A: {e}")
        return False
    
    # ===== TEST 2: User A creates goal =====
    print("\n[TEST 2] User A creates goal 'Ironman 2025'...")
    try:
        goal_a = client.create_goal(
            race_name="Ironman 2025",
            goal_type="Full Ironman 140.6",
            race_date="2025-07-15",
            target_time="12:00:00"
        )
        print(f"✅ Goal created: {goal_a.get('race_name')} (ID: {goal_a.get('id')})")
    except Exception as e:
        print(f"❌ Failed to create goal: {e}")
        all_tests_passed = False
    
    # ===== TEST 3: User A checks dashboard =====
    print("\n[TEST 3] User A checks dashboard...")
    try:
        dashboard_a = client.get_dashboard_data()
        goals_a = dashboard_a.get("goals", [])
        primary_goal_a = dashboard_a.get("primary_goal")
        
        print(f"  Goals count: {len(goals_a)}")
        if primary_goal_a:
            print(f"  Primary goal: {primary_goal_a.get('race_name')}")
        
        if primary_goal_a and "Ironman" in primary_goal_a.get("race_name", ""):
            print("✅ User A sees their own goal")
        else:
            print("❌ User A does NOT see their goal")
            all_tests_passed = False
    except Exception as e:
        print(f"❌ Failed to get dashboard: {e}")
        all_tests_passed = False
    
    # ===== TEST 4: User A logout =====
    print("\n[TEST 4] User A logs out...")
    client.logout()
    print("✅ User A logged out")
    
    # ===== TEST 5: Register User B =====
    print("\n[TEST 5] Registering User B...")
    try:
        client.register(USER_B_EMAIL, USER_B_PASSWORD)
        print(f"✅ User B registered (ID: {client.user_id})")
    except Exception as e:
        print(f"❌ Failed to register User B: {e}")
        return False
    
    # ===== TEST 6: User B checks dashboard (should be EMPTY) =====
    print("\n[TEST 6] User B checks dashboard (should be EMPTY)...")
    try:
        dashboard_b = client.get_dashboard_data()
        goals_b = dashboard_b.get("goals", [])
        primary_goal_b = dashboard_b.get("primary_goal")
        activities_b = dashboard_b.get("activities")
        
        print(f"  Goals count: {len(goals_b)}")
        print(f"  Primary goal: {primary_goal_b}")
        print(f"  Activities: {activities_b}")
        
        if len(goals_b) == 0 and primary_goal_b is None:
            print("✅ User B dashboard is EMPTY (correct!)")
        else:
            print("❌ User B sees data from User A (ISOLATION BROKEN!)")
            if goals_b:
                print(f"  Found goals: {[g.get('race_name') for g in goals_b]}")
            all_tests_passed = False
    except Exception as e:
        print(f"❌ Failed to get dashboard: {e}")
        all_tests_passed = False
    
    # ===== TEST 7: User B creates goal =====
    print("\n[TEST 7] User B creates goal 'Marathon sub 4'...")
    try:
        goal_b = client.create_goal(
            race_name="Marathon sub 4",
            goal_type="Marathon",
            race_date="2025-04-20",
            target_time="3:59:59"
        )
        print(f"✅ Goal created: {goal_b.get('race_name')} (ID: {goal_b.get('id')})")
    except Exception as e:
        print(f"❌ Failed to create goal: {e}")
        all_tests_passed = False
    
    # ===== TEST 8: User B checks dashboard =====
    print("\n[TEST 8] User B checks dashboard (should see only their goal)...")
    try:
        dashboard_b = client.get_dashboard_data()
        goals_b = dashboard_b.get("goals", [])
        primary_goal_b = dashboard_b.get("primary_goal")
        
        print(f"  Goals count: {len(goals_b)}")
        if primary_goal_b:
            print(f"  Primary goal: {primary_goal_b.get('race_name')}")
        
        goal_names = [g.get("race_name") for g in goals_b]
        if "Marathon sub 4" in goal_names and "Ironman 2025" not in goal_names:
            print("✅ User B sees only their own goal")
        else:
            print(f"❌ User B sees wrong goals: {goal_names}")
            all_tests_passed = False
    except Exception as e:
        print(f"❌ Failed to get dashboard: {e}")
        all_tests_passed = False
    
    # ===== TEST 9: User B logout =====
    print("\n[TEST 9] User B logs out...")
    client.logout()
    print("✅ User B logged out")
    
    # ===== TEST 10: User A login =====
    print("\n[TEST 10] User A logs in...")
    try:
        client.login(USER_A_EMAIL, USER_A_PASSWORD)
        print(f"✅ User A logged in (ID: {client.user_id})")
    except Exception as e:
        print(f"❌ Failed to login User A: {e}")
        return False
    
    # ===== TEST 11: User A checks dashboard (should see only their goal) =====
    print("\n[TEST 11] User A checks dashboard (should see only 'Ironman 2025')...")
    try:
        dashboard_a = client.get_dashboard_data()
        goals_a = dashboard_a.get("goals", [])
        primary_goal_a = dashboard_a.get("primary_goal")
        
        print(f"  Goals count: {len(goals_a)}")
        if primary_goal_a:
            print(f"  Primary goal: {primary_goal_a.get('race_name')}")
        
        goal_names = [g.get("race_name") for g in goals_a]
        if "Ironman 2025" in goal_names and "Marathon sub 4" not in goal_names:
            print("✅ User A sees only their own goal")
        else:
            print(f"❌ User A sees wrong goals: {goal_names}")
            all_tests_passed = False
    except Exception as e:
        print(f"❌ Failed to get dashboard: {e}")
        all_tests_passed = False
    
    # ===== FINAL RESULT =====
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED - User isolation works correctly!")
    else:
        print("❌ SOME TESTS FAILED - User isolation is broken!")
    print("=" * 60)
    
    return all_tests_passed


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
        print(f"Using base URL: {BASE_URL}")
    
    success = test_user_isolation()
    sys.exit(0 if success else 1)

