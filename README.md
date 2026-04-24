# 🚀 TrackFit – AI Fitness App

TrackFit is a full-stack fitness tracking mobile app built using **Expo React Native** and **FastAPI**, featuring AI-powered food recognition, barcode scanning, and a smart fitness coach.

---

# 📱 Features

* 🤖 **AI Coach** – Smart fitness suggestions with fallback mode
* 🍔 **Food Recognition** – Detect food using camera (AI + fallback)
* 📷 **Barcode Scanner** – Scan packaged food items
* 👣 **Step Counter** – Sensor-based tracking (no native modules)
* 💧 **Hydration Tracking**
* 🏋️ **Workout Logging & Progress Tracking**
* 📊 **Daily Activity Dashboard**

---

# 🛠 Tech Stack

### Frontend

* React Native (Expo SDK 54)
* TypeScript
* Expo Camera & Sensors

### Backend

* FastAPI (Python)
* SQLite / PostgreSQL
* Async APIs (httpx)

### Deployment

* Google Cloud Run (Backend)
* EAS Build (APK)

---

# 📦 Project Structure

```
trackfit_app/
│
├── backend/              # FastAPI backend
├── Fitness-Implement/   # Expo React Native app
├── .gitignore
├── README.md
```

---

# 🚀 Run Locally

## 🔧 Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API Docs:

```
http://localhost:8000/docs
```

---

## 📱 Frontend

```bash
cd Fitness-Implement
npm install
npx expo start
```

---

# 🌐 API Configuration

### 🔹 Local Development (Expo Go)

```env
EXPO_PUBLIC_API_URL=http://192.168.X.X:8000/api/v1
```

👉 Replace with your system IP

---

### 🔹 Production (APK)

```env
EXPO_PUBLIC_API_URL=https://trackfit-backend-bypyw43ziq-uc.a.run.app/api/v1
```

---

# 📱 Build APK

```bash
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

👉 Download APK from build link

---

# 📥 Download APK

👉 https://expo.dev/accounts/dsp515/projects/trackfit/builds/6129f073-3c07-4cd6-b07b-41faefc7e9cb

---

# ⚠️ Notes

* App uses **fallback responses** if API fails
* Works even on **slow or unstable networks**
* Food/barcode APIs are optional (keys not required)
* No native modules → fully Expo compatible

---

# 🔐 Security

* `.env` files are not included
* No API keys exposed
* Use `.env.example` for configuration

---

# 🧪 Tested

* ✅ Expo Go
* ✅ Android APK
* ✅ Cloud backend
* ✅ Offline fallback

---

# 📸 Screenshots

<img width="720" height="1600" alt="screenshot_foodlog" src="https://github.com/user-attachments/assets/749cd90d-4d41-4cf7-99eb-3cfa65fd0e73" />
<img width="720" height="1600" alt="screenshot_food" src="https://github.com/user-attachments/assets/d0f067a5-0485-40b2-844f-7ad0e946fa52" />
<img width="720" height="1600" alt="screenshot_steps" src="https://github.com/user-attachments/assets/ceb54c48-2d01-496a-95b3-b0aa1970deca" />
<img width="720" height="1600" alt="screenshot_home" src="https://github.com/user-attachments/assets/2f6b8afb-9a49-4854-b03c-9cd8c0d6e378" />


---

# 👨‍💻 Author

**Srinivas Prakash**

---

# ⭐ Future Improvements

* Add real nutrition APIs
* Improve AI accuracy
* Push notifications (FCM)
* Play Store deployment

---

# 📌 License

This project is for educational and development purposes.
