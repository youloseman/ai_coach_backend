# User Data Isolation Test Guide

This guide helps you test that user data isolation is working correctly after all security fixes.

## Prerequisites

1. Backend server running on `http://localhost:8000` (or update `BASE_URL` in script)
2. Python 3.8+ with `requests` library installed
3. Database should be accessible

## Option 1: Automated Testing (Recommended)

Run the automated test script:

```bash
# Install requests if needed
pip install requests

# Run the test script
python test_user_isolation.py

# Or with custom base URL
python test_user_isolation.py http://your-backend-url.com
```

The script will:
1. ✅ Register User A
2. ✅ Create goal "Ironman 2025" for User A
3. ✅ Verify User A sees their goal
4. ✅ Logout User A
5. ✅ Register User B
6. ✅ Verify User B dashboard is EMPTY (no User A data)
7. ✅ Create goal "Marathon sub 4" for User B
8. ✅ Verify User B sees only their goal
9. ✅ Logout User B
10. ✅ Login User A
11. ✅ Verify User A sees only "Ironman 2025" (not "Marathon sub 4")

## Option 2: Manual Testing via Frontend

### Step 1: Clear Database (Optional)

If you want to start fresh:

```bash
# Connect to database
railway run psql $DATABASE_URL

# Clear all data
DELETE FROM users CASCADE;

# Exit
\q
```

### Step 2: Test User A

1. **Register User A**
   - Go to `/register`
   - Email: `user_a@test.com`
   - Password: `testpass123`
   - Register

2. **Add Goal**
   - Go to `/goals` or `/onboarding`
   - Add goal: "Ironman 2025"
   - Race type: "Full Ironman 140.6"
   - Date: 2025-07-15
   - Target time: 12:00:00

3. **Connect Strava** (Optional)
   - Go to `/coach`
   - Click "Connect Strava"
   - Authorize

4. **Check Dashboard**
   - Go to `/dashboard`
   - ✅ Should see "Ironman 2025" goal
   - ✅ Should see User A's activities (if Strava connected)

5. **Logout**
   - Click logout button
   - ✅ Should redirect to `/login`

### Step 3: Test User B

1. **Register User B**
   - Go to `/register`
   - Email: `user_b@test.com`
   - Password: `testpass456`
   - Register

2. **Check Dashboard**
   - Go to `/dashboard`
   - ✅ Should be EMPTY
   - ✅ Should NOT see "Ironman 2025" goal
   - ✅ Should NOT see User A's activities

3. **Add Goal**
   - Go to `/goals` or `/onboarding`
   - Add goal: "Marathon sub 4"
   - Race type: "Marathon"
   - Date: 2025-04-20
   - Target time: 3:59:59

4. **Connect Strava** (Optional)
   - Go to `/coach`
   - Click "Connect Strava"
   - Authorize

5. **Check Dashboard**
   - Go to `/dashboard`
   - ✅ Should see only "Marathon sub 4" goal
   - ✅ Should NOT see "Ironman 2025"
   - ✅ Should see only User B's activities

6. **Logout**
   - Click logout button

### Step 4: Verify User A Isolation

1. **Login User A**
   - Go to `/login`
   - Email: `user_a@test.com`
   - Password: `testpass123`
   - Login

2. **Check Dashboard**
   - Go to `/dashboard`
   - ✅ Should see only "Ironman 2025" goal
   - ✅ Should NOT see "Marathon sub 4"
   - ✅ Should see only User A's activities

## Expected Results

### ✅ All Tests Pass If:

- User B sees empty dashboard after User A creates data
- User B does NOT see User A's goals
- User B does NOT see User A's activities
- User A does NOT see User B's goals after logout/login
- Each user only sees their own data

### ❌ Tests Fail If:

- User B sees User A's goals
- User B sees User A's activities
- User A sees User B's goals
- Data leaks between users

## Troubleshooting

### Test Script Fails

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check database connection:**
   - Verify `DATABASE_URL` is set correctly
   - Check database is accessible

3. **Check API endpoints:**
   - `/auth/register` - should return 200
   - `/auth/login` - should return 200
   - `/goals` - should require authentication

### Frontend Tests Fail

1. **Clear browser cache and localStorage:**
   - Open DevTools (F12)
   - Application tab → Clear Storage
   - Clear all

2. **Check network requests:**
   - Open DevTools → Network tab
   - Verify requests include `Authorization: Bearer <token>`
   - Check responses are filtered by user_id

3. **Check console for errors:**
   - Open DevTools → Console
   - Look for authentication or API errors

## Security Checklist

After testing, verify:

- [ ] Users cannot see each other's goals
- [ ] Users cannot see each other's activities
- [ ] Users cannot see each other's profiles
- [ ] Users cannot see each other's plans
- [ ] Logout clears all user data from frontend
- [ ] Login loads fresh data from API
- [ ] All API endpoints require authentication
- [ ] All database queries filter by user_id

## Notes

- The test script creates test users that can be deleted after testing
- Strava connection is optional but recommended for full testing
- If you see data leakage, check:
  1. `crud.py` - all queries filter by `user_id`
  2. `api_coach.py` - all endpoints use `current_user.id`
  3. `main.py` - all endpoints use `current_user.id`
  4. Frontend - clears data on logout and validates token on mount

