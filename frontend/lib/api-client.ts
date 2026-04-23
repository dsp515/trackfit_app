import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'https://trackfit-backend-bypyw43ziq-uc.a.run.app/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await AsyncStorage.removeItem('access_token');
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const authApi = {
  signup: (data: { email: string; password: string; name: string }) =>
    api.post('/auth/signup', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
};

// Users
export const usersApi = {
  getMe: () => api.get('/users/me'),
  getProfile: () => api.get('/users/profile'),
  createProfile: (data: any) => api.post('/users/profile', data),
  updateProfile: (data: any) => api.put('/users/profile', data),
};

// Food — search, log, recognition, barcode
export const foodApi = {
  search: (query: string, cuisine?: string, limit = 20) =>
    api.get('/food/search', { params: { q: query, cuisine, limit } }),
  getFoodDetails: (foodKey: string) => api.get(`/food/db/${foodKey}`),
  recognize: (imageBase64: string) =>
    api.post('/food/recognize', { image_base64: imageBase64 }),
  barcode: (barcode: string) =>
    api.post('/food/barcode', { barcode }),
  logFood: (data: any) => api.post('/food/log', data),
  getToday: () => api.get('/food/today'),
  deleteLog: (logId: string) => api.delete(`/food/log/${logId}`),
};

// Workout — search, log, rep counting
export const workoutApi = {
  searchExercises: (query: string, limit = 20) =>
    api.get('/workout/exercises/search', { params: { q: query, limit } }),
  logWorkout: (data: any) => api.post('/workout/log', data),
  logRepCounting: (data: {
    exercise_name: string;
    exercise_type?: string;
    total_reps: number;
    sets_data?: string;
    duration_seconds?: number;
    form_score?: number;
    calories_burned?: number;
  }) => api.post('/workout/rep-log', data),
  getToday: () => api.get('/workout/today'),
  getHistory: (limit = 30) =>
    api.get('/workout/history', { params: { limit } }),
};

// Hydration
export const hydrationApi = {
  logWater: (amountMl: number) =>
    api.post('/hydration/log', { amount_ml: amountMl }),
  getToday: () => api.get('/hydration/today'),
};

// Steps / Google Fit sync
export const stepsApi = {
  syncSteps: (data: {
    date: string;
    steps: number;
    distance_m?: number;
    calories_burned?: number;
    active_minutes?: number;
    source?: string;
  }) => api.post('/steps/sync', data),
  getToday: () => api.get('/steps/today'),
};

// Coach — chat with AI
export const coachApi = {
  chat: (message: string) => api.post('/coach/chat', { message }),
  getHistory: (limit = 50) =>
    api.get('/coach/history', { params: { limit } }),
};

// Stats
export const statsApi = {
  getDailyScore: (date?: string) =>
    api.get('/stats/daily-score', { params: date ? { target_date: date } : {} }),
  getWeekly: () => api.get('/stats/weekly'),
  getHistory: () => api.get('/stats/history'),
};
