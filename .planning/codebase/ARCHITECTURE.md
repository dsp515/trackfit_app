# Architecture Map

## Overall Pattern
TrackFit follows a decoupled client-server architecture. The frontend is an offline-first Expo application that synchronizes state with a monolithic FastAPI Python backend. Data is fetched using REST endpoints. 

## Backend (`/backend`)
Follows standard MVC/Service layered pattern using FastAPI router mapping:
1. **Entry Point** (`app/main.py`): Initializes FastAPI, CORS, ORM schema migrations, and registers the `v1` routers.
2. **API Layer** (`app/api/v1/endpoints/`): Rest controllers. Functions are mapped to services.
3. **Services** (`app/services/`): Business logic and core features. E.g., `pose_service.py` runs MediaPipe against base64 image strings. `coach_service.py` houses model inference.
4. **Data Models** (`app/models/`): SQLAlchemy ORM models (Users, Profile, Logs, ChatHistory).
5. **Core** (`app/core/`): Centralized DB connection handling, Pydantic settings loading (`config.py`), and authentication utilities (`security.py`).

## Frontend (`/Fitness-Implement`)
Follows a modular React+Expo pattern with offline caching:
1. **Routing** (`app/`): Expo Router layout mapping to bottom tabs (`(tabs)`) and standalone screens like `workout/active`.
2. **Contexts** (`context/`): Heavy reliance on Context providers (`AppContext.tsx`) which act as a local Redux-like store pulling from `AsyncStorage`.
3. **Data Fetching/Syncing** (`lib/api.ts` & `lib/stepCounter.ts`): API clients handle appending JWT tokens. The step counter is a complex singleton that balances raw Accelerometer events vs OS Health Connect polling, gracefully syncing chunks to the backend. 
4. **Offline First Flow**: When the app boots, `AppContext` reads all user state from `AsyncStorage`. It then uses `Promise.allSettled` against `/users/profile`, `/food/today`, etc., to hydrate the latest data while allowing the app to render instantly.
