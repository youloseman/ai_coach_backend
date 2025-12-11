Project Structure (key files)
=============================

Root
 - README.md — project overview and usage
 - ARCHITECTURE.md — detailed architecture
 - TSS_CALCULATION.md — TSS logic and backfill script
 - TRAINING_ZONES_SETUP.md — how to set training zones
 - action-plan.md — implementation plan
 - requirements.txt — backend deps
 - package.json (frontend/) — frontend deps/scripts

Backend (root)
 - main.py — FastAPI app bootstrap, routers, middleware
 - api_coach.py — weekly plans, weekly report email, plan preview formatter
 - api_nutrition.py — nutrition targets and daily plan endpoints
 - api_analytics.py — PMC and fitness summary endpoints
 - api_user.py — profile/training zones update
 - crud.py — DB helpers (activity upsert with TSS calc, profiles, etc.)
 - models.py — SQLAlchemy models (users, profiles, activities, etc.)
 - schemas.py — Pydantic schemas (including TrainingZonesUpdate)
 - database.py — DB session/engine setup
 - performance_predictions.py — race prediction logic
 - coach.py — AI coach prompt usage (initial/weekly plans)
 - analytics/
   - __init__.py — compatibility exports
   - pmc.py — PMCCalculator (CTL/ATL/TSB/RR)
   - tss.py — TSS calculators (bike/run/swim, auto selector)
 - prompts/
   - builder.py — builds coach prompt from modules + context
   - sport_modules/
     - triathlon.py — triathlon prompt module
     - swimming.py — swimming prompt module
   - __init__.py — exports builder
 - services/
   - activity_service.py — calculate_and_save_tss for activities
 - scripts/
   - recalculate_tss.py — backfill TSS for existing activities
 - tests/
   - test_pmc.py — PMC unit tests
   - test_tss.py — TSS unit tests

Frontend (frontend/)
 - next.config.js, tsconfig.json — Next.js/TS config
 - app/dashboard/page.tsx — main dashboard composition
 - lib/api.ts — API client (coach, analytics, nutrition, profile/zones)
 - types/index.ts — shared TS types (FormStatus, RacePrediction, zones, etc.)
 - components/
   - charts/PMCChart.tsx — PMC visualization
   - analytics/FitnessSummary.tsx — fitness summary card
   - FormStatusCard.tsx — form/status card (dark)
   - RacePredictionCard.tsx — race prediction card (dark)
   - RecentActivitiesList.tsx — recent activities list (dark)
   - ActivityCard.tsx — activity card (dark)
   - settings/TrainingZones.tsx — training zones form

Other
 - scripts/ (root) — package marker
 - services/ (root) — package marker

