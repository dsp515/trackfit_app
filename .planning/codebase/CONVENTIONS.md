# Conventions & Practices

## Frontend (React Native / Expo)
- **State Management Contexts**: Giant context files (`AppContext.tsx`) parse everything from `AsyncStorage`. There is an established pattern of defining types, mapping default states, then pulling from AsyncStorage and overlaying server data via `Promise.allSettled()`.
- **Typing**: Strict TypeScript. Common types (Profile, Log) exported at context bottoms.
- **Async API**: Uses utility `apiFetch` in `api.ts` that reads the JWT token from AsyncStorage. Promises try to swallow network failures so the app can remain offline-first.
- **Permissions**: Hardcoded inside `HealthConnect` flows instead of abstracted hooks.

## Backend (FastAPI Python)
- **Dependency Injection**: Uses `Depends(get_db)` and `Depends(get_current_user)` extensively across routes.
- **Exception Handling**: Standard `HTTPException` raises handled mostly at the router level.
- **ORM Patterns**: Heavily relies on Pydantic models in `schemas/` mapped to SQLAlchemy models in `models/` by the `.from_orm` parameter (or `model_validate`).

# Testing

## Frontend
- Configured using `vitest`.
- Mocks out native functionality (ex: `@react-native-async-storage/async-storage`, `expo-sensors`) via `__tests__/setup-rn-mocks.ts`.
- Checks logic heavily decoupled from UI (like rep counting thresholds in `rep-counter.test.ts`).
- Standard run via `npm run test` and `npm run test:watch`.

## Backend
- Lacks a visible tests folder. It is heavily reliant on FastAPI auto-docs + likely manual local testing for AI services since models are large binary files. 
