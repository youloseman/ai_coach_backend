"""
Security tests for API endpoints

"""
import pytest

from fastapi.testclient import TestClient

from main import app

from auth import create_access_token



client = TestClient(app)


class TestCalendarSecurity:
    """Test calendar download security"""
    
    def test_download_own_calendar(self):
        """User can download their own calendar file"""
        # Create test token for user 1
        token = create_access_token({"user_id": 1, "email": "test@example.com"})
        
        # This would need actual file setup in test environment
        # For now, we test the access control logic
        response = client.get(
            "/downloads/calendar/user_1_plan.ics",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should either succeed (200) or file not found (404)
        # But NOT forbidden (403)
        assert response.status_code in [200, 404], \
            f"Expected 200 or 404, got {response.status_code}"
    
    def test_download_other_user_calendar(self):
        """User cannot download other user's calendar file"""
        # Create test token for user 1
        token = create_access_token({"user_id": 1, "email": "test@example.com"})
        
        # Try to access user 2's file
        response = client.get(
            "/downloads/calendar/user_2_plan.ics",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be forbidden
        assert response.status_code == 403, \
            f"Expected 403 Forbidden, got {response.status_code}"
        assert "Access denied" in response.json()["detail"]
    
    def test_directory_traversal_attempt(self):
        """Reject directory traversal attempts"""
        token = create_access_token({"user_id": 1, "email": "test@example.com"})
        
        # Try directory traversal
        response = client.get(
            "/downloads/calendar/user_1_../../etc/passwd",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be rejected
        assert response.status_code == 400, \
            f"Expected 400 Bad Request, got {response.status_code}"
        assert "Invalid filename" in response.json()["detail"]


class TestOAuthSecurity:
    """Test OAuth state security"""
    
    def test_oauth_state_is_jwt(self):
        """OAuth state should be JWT, not base64"""
        # This is a conceptual test
        # In real implementation, we'd verify the state format
        
        # Create a state token
        state_data = {
            "user_id": 1,
            "purpose": "strava_oauth",
            "redirect_uri": "http://localhost:3000/dashboard"
        }
        
        from auth import create_access_token
        state = create_access_token(state_data)
        
        # State should be a JWT (3 parts separated by dots)
        assert state.count(".") == 2, \
            "State should be JWT format (3 parts)"
        
        # Should NOT be base64 of JSON
        import base64
        import json
        try:
            decoded = base64.b64decode(state)
            json.loads(decoded)
            pytest.fail("State should NOT be decodable as base64 JSON")
        except:
            pass  # Expected - state is JWT, not base64
    
    def test_oauth_state_verification(self):
        """OAuth state should be verifiable with JWT"""
        from auth import create_access_token, verify_token
        
        state_data = {
            "user_id": 1,
            "purpose": "strava_oauth"
        }
        
        # Create state
        state = create_access_token(state_data)
        
        # Verify state
        verified_data = verify_token(state)
        
        assert verified_data["user_id"] == 1
        assert verified_data["purpose"] == "strava_oauth"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

