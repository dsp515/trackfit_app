# Codebase Structure

## Root Folders
- `/backend`: The Python FastAPI application and its Dockerfile.
- `/Fitness-Implement`: The Expo / React Native frontend project.
- `.planning`: Agentic tracking state and codebase snapshots.

## Backend Layout (`/backend/app`)
- `api/`: Route definitions and controllers (split into versions, e.g., `v1/endpoints`).
- `core/`: System configuration, database session handling, and security logic.
- `db/`: JSON data seeds (`food_db.json`, `exercise_db.json`).
- `models/`: SQLAlchemy declarative classes mapping to Postgres/SQLite.
- `schemas/`: Pydantic models for request validation and response typing.
- `services/`: Heavy business logic separating routes from data handling. (e.g., OpenCV pose detection).
- `/data`, `/models`, `/training`: Storage for ML weights `.pt`, `.json` classes, and training scripts.

## Frontend Layout (`/Fitness-Implement`)
- `app/`: Expo Router file-based screens (`_layout.tsx`, `index.tsx`, `(tabs)`, `workout`).
- `assets/`: Images and static resources.
- `components/`: Pure visual or semi-smart UI pieces (e.g., `ErrorBoundary.tsx`).
- `context/`: Giant providers bridging SQLite/AsyncStorage to app state.
- `lib/`: Utilities (`stepCounter.ts`, `api.ts`, `google-fit.ts`).
- `modules/`: Contains explicit native module implementations (e.g., `StepCounter`).
- `server/`: Experimental or mocked Node-based server code (esbuild target).
- `shared/`: Shared schemas or constants (e.g., validation rules).
- `__tests__`: Vitest unit tests for TS files.
