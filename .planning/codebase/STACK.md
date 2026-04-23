# Tech Stack Map

## Overview
TrackFit Ultra is a full-stack health and fitness tracking application comprising a FastAPI backend and an Expo/React Native frontend, designed for both mobile use and web access. It uses on-device step counting and AI-based image recognition.

## Backend Stack
- **Language**: Python 3.x
- **Framework**: FastAPI (0.115.6) with Uvicorn/Gunicorn servers.
- **Data Persistence**: SQLAlchemy (2.0.36) for ORM. Configured for SQLite locally (`trackfit.db`) and PostgreSQL for production (`psycopg2-binary`). Uses `aiosqlite`.
- **Authentication**: JWT tokens encoded with `python-jose` (HS256 algorithm) and hashed passwords using `passlib[bcrypt]`. Includes lightweight rate limiting with `slowapi` and `limits`.
- **AI / ML**: 
  - `transformers` and `torch` for food recognition and coaching. Models loaded from `.pt` and `.json` assets.
  - `mediapipe` (0.10.14) and `opencv-python-headless` for server-side pose detection, specifically counting reps for body-weight exercises.
- **Server Execution**: Docker & docker-compose support with an Alpine PostgreSQL container and custom backend build.

## Frontend Stack
- **Framework**: React Native (0.81.5) wrapped in Expo (SDK ~54) using Expo Router for file-based routing.
- **State Management**: React Query (`@tanstack/react-query`) combined with Context APIs (e.g., `AppContext`, `AuthContext`, `FitnessContext`, `FoodContext`).
- **Storage**: AsyncStorage for persistent, offline-capable local storage.
- **Native Integrations**: 
  - `react-native-health-connect` for pulling pedometer and sleep data on Android. 
  - Real-time step counter utilizing Expo Sensors (Accelerometer) and a custom native Android module (`@trackfit/step-counter` excluded from autolinking).
  - Health & Device sensors: Expo Camera, Location, Notifications, Haptics.
- **Styling**: Contextual ThemeProvider + Inter font (`@expo-google-fonts/inter`) prioritizing dark modes (`#0A0E1A`).

## Local Development
- Python `venv` + `requirements.txt`
- `npm` for Expo app manager, heavily leveraging `patch-package` for modifying misbehaving native modules.
