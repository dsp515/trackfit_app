# TrackFit Ultra

## Overview
TrackFit Ultra is a comprehensive, production-ready fitness tracking application combining a React Native mobile frontend with a robust FastAPI backend. It helps users log their daily food intake, track steps, monitor hydration, and leverage AI for personalized coaching and food recognition.

## Features
- **AI Coach**: Interactive coaching assistant for personalized fitness tips and guidance.
- **Food Recognition**: Take photos of food to instantly identify calories and macros using Vision AI.
- **Barcode Scanning**: Quickly log packaged foods via standard barcode lookup.
- **Step Tracking**: Automatic step counting and activity monitoring.

## Tech Stack
- **Frontend**: Expo React Native (TypeScript, Expo Router)
- **Backend**: FastAPI (Python, SQLAlchemy, PostgreSQL/SQLite)
- **Deployment**: Google Cloud Run / Docker

## Run Locally

### Backend
1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the development server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
1. Navigate to the `Fitness-Implement` directory.
2. Install dependencies:
```bash
npm install
```
3. Start the Expo server:
```bash
npx expo start
```

## API Config

Set your environment variables in `.env` based on the provided `.env.example`.

**Local Development (WiFi LAN):**
```env
EXPO_PUBLIC_API_URL=http://192.168.X.X:8000/api/v1
```

**Production (Cloud Run):**
```env
EXPO_PUBLIC_API_URL=https://trackfit-backend-bypyw43ziq-uc.a.run.app/api/v1
```

## Build APK

To generate a standalone APK for Android, ensure you have an Expo dev account and EAS CLI installed, then run:

```bash
eas build -p android --profile preview
```
*Note: Due to file size and security, the built APK is not stored in this repository. You can download the latest APK from the GitHub Releases page or the shared Google Drive link.*

## Notes
- The application implements a safe fallback architecture; if an API fails, it will continue to function gracefully without crashing.
- Works perfectly fine without the optional third-party API keys (API_NINJAS_KEY, USDA_API_KEY) by using safe local fallbacks and prediction mechanisms.
