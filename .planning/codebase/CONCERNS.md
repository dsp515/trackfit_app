# Codebase Concerns & Debt

## 1. Massive Frontend Context Files
- `AppContext.tsx` is over 700 lines long and handles everything from streak logic, syncing, local storage caching, to fetching diverse domains (hydration, workouts, food, steps). This is a God Object anti-pattern and makes debugging race conditions difficult.

## 2. Hardcoded Credentials & Secrets
- `config.py` in the backend seems to expect sensitive hardcoded fallback strings directly in code (e.g., JWT_SECRET defaulting to `"trackfit-ultra-secret-key-change-in-production-2024"`).
- Frontend `api.ts` hardcodes a remote backend URL (`https://trackfit-backend...`) if EXPO_PUBLIC_API_URL isn't injected.

## 3. Database Sync / Race Conditions
- The frontend blindly overwrites backend state in some `POST` updates after waking from offline modes, and the backend schema relies on implicit default values (e.g., `_run_schema_compat_migrations` dynamically injecting SQLite columns on startup). 
- Health Connect and Accelerometer fallback in `stepCounter.ts` may double count if the hardware module and the passive health API resolve incorrectly after app suspension.

## 4. Complex ML Model Loading
- `pose_service.py` dynamically loads a MediaPipe model. `coach_service.py` also loads large local PyTorch models (`.pt`). These are highly memory-intensive and block execution threads if not handled as background Celery/Redis tasks (currently it appears they are synchronous endpoints).

## 5. Lack of Backend Test Coverage
- There are no automated tests preventing regression on complex calculations or AI chat prompts.
