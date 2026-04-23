# External Integrations

## Backend Services
- **API Ninjas**: Used primarily for nutrition lookup. Configured via `API_NINJAS_KEY` in environment. 
- **OpenRouter (LLM)**: Hooked in via `OPENROUTER_API_KEY` to potentially drive AI Coach chatbot responses.
- **HuggingFace**: Uses `HF_TOKEN` to pull deep learning models securely without hitting rate limits (for the ViT models used in food classification and local coaching inference).

## Frontend Integrations
- **Google Health Connect**: Natively integrated on Android to pull passive step count and health metrics when the app starts or comes to the foreground.
- **Expo Application Services (EAS)**: Deeply integrated via `eas.json` for managing dev, preview, and production builds (`eas build` mapped to scripts). Includes over-the-air `expo-updates`.

## Databases
- Locally uses SQLite (`trackfit.db`).
- Docker deployment uses a `postgres:15-alpine` container (`POSTGRES_USER=trackfit`).
