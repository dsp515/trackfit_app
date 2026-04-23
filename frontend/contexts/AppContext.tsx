import React, { createContext, useContext, useEffect, useMemo, useState, useCallback, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from './AuthContext';
import {
  foodApi,
  workoutApi,
  hydrationApi,
  usersApi,
  statsApi,
  coachApi,
} from '../lib/api-client';

// Types
export interface UserProfile {
  goal: string;
  age: number;
  gender: string;
  height_cm: number;
  weight_kg: number;
  activity_level: string;
  preferred_cuisine: string;
  daily_calorie_goal: number;
  daily_protein_goal: number;
  daily_carbs_goal: number;
  daily_fat_goal: number;
  daily_water_ml_goal: number;
  daily_step_goal: number;
}

export interface FoodEntry {
  id: string;
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  amount_g: number;
  meal_type: string;
  logged_at: string;
}

export interface WorkoutLog {
  id: string;
  exercise_name: string;
  exercise_type: string;
  duration_minutes: number;
  calories_burned: number;
  sets: number;
  reps: number;
  logged_at: string;
}

export interface DailyStats {
  calories_consumed: number;
  calories_burned: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  water_ml: number;
  steps: number;
  workouts_count: number;
  daily_score: number;
}

interface AppContextValue {
  profile: UserProfile | null;
  todayStats: DailyStats;
  foodLogs: FoodEntry[];
  workoutLogs: WorkoutLog[];
  streak: number;
  isLoading: boolean;
  // Actions
  loadProfile: () => Promise<void>;
  saveProfile: (data: Partial<UserProfile>) => Promise<boolean>;
  loadTodayStats: () => Promise<void>;
  addWater: (ml: number) => Promise<void>;
  logFood: (data: any) => Promise<boolean>;
  logWorkout: (data: any) => Promise<boolean>;
  getDailyScore: () => number;
  chatWithCoach: (message: string) => Promise<string>;
}

const AppContext = createContext<AppContextValue | null>(null);

const DEFAULT_STATS: DailyStats = {
  calories_consumed: 0,
  calories_burned: 0,
  protein_g: 0,
  carbs_g: 0,
  fat_g: 0,
  water_ml: 0,
  steps: 0,
  workouts_count: 0,
  daily_score: 0,
};

export function AppProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [todayStats, setTodayStats] = useState<DailyStats>(DEFAULT_STATS);
  const [foodLogs, setFoodLogs] = useState<FoodEntry[]>([]);
  const [workoutLogs, setWorkoutLogs] = useState<WorkoutLog[]>([]);
  const [streak, setStreak] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadAll();
    }
  }, [isAuthenticated]);

  const loadAll = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadProfile(), loadTodayStats(), loadFoodLogs(), loadWorkoutLogs()]);
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProfile = async () => {
    try {
      const res = await usersApi.getProfile();
      setProfile(res.data);
    } catch {
      setProfile(null);
    }
  };

  const saveProfile = async (data: Partial<UserProfile>): Promise<boolean> => {
    try {
      if (profile) {
        const res = await usersApi.updateProfile(data);
        setProfile(res.data);
      } else {
        const res = await usersApi.createProfile(data);
        setProfile(res.data);
      }
      return true;
    } catch {
      return false;
    }
  };

  const loadTodayStats = async () => {
    try {
      const [foodRes, hydrationRes, workoutRes, scoreRes] = await Promise.all([
        foodApi.getToday(),
        hydrationApi.getToday(),
        workoutApi.getToday(),
        statsApi.getDailyScore(),
      ]);

      const foodData = foodRes.data;
      const hydrationData = hydrationRes.data;
      const workouts = workoutRes.data;
      const scoreData = scoreRes.data;

      setTodayStats({
        calories_consumed: foodData.total_calories || 0,
        calories_burned: workouts.reduce((sum: number, w: any) => sum + (w.calories_burned || 0), 0),
        protein_g: foodData.total_protein || 0,
        carbs_g: foodData.total_carbs || 0,
        fat_g: foodData.total_fat || 0,
        water_ml: hydrationData.total_ml || 0,
        steps: 0,
        workouts_count: workouts.length,
        daily_score: scoreData.total_score || 0,
      });

      setStreak(scoreData.streak_bonus ? Math.round(scoreData.streak_bonus / 2) : 0);
    } catch (e) {
      console.error('Error loading today stats:', e);
    }
  };

  const loadFoodLogs = async () => {
    try {
      const res = await foodApi.getToday();
      setFoodLogs(res.data.logs || []);
    } catch {
      setFoodLogs([]);
    }
  };

  const loadWorkoutLogs = async () => {
    try {
      const res = await workoutApi.getToday();
      setWorkoutLogs(res.data || []);
    } catch {
      setWorkoutLogs([]);
    }
  };

  const addWater = useCallback(async (ml: number) => {
    try {
      await hydrationApi.logWater(ml);
      await loadTodayStats();
    } catch (e) {
      console.error('Error logging water:', e);
    }
  }, []);

  const logFood = useCallback(async (data: any): Promise<boolean> => {
    try {
      await foodApi.logFood(data);
      await Promise.all([loadFoodLogs(), loadTodayStats()]);
      return true;
    } catch {
      return false;
    }
  }, []);

  const logWorkout = useCallback(async (data: any): Promise<boolean> => {
    try {
      await workoutApi.logWorkout(data);
      await Promise.all([loadWorkoutLogs(), loadTodayStats()]);
      return true;
    } catch {
      return false;
    }
  }, []);

  const getDailyScore = useCallback(() => {
    return todayStats.daily_score;
  }, [todayStats]);

  const chatWithCoach = useCallback(async (message: string): Promise<string> => {
    try {
      const res = await coachApi.chat(message);
      return res.data.reply;
    } catch {
      return "I'm having trouble connecting right now. Try checking your internet connection!";
    }
  }, []);

  const value = useMemo(
    () => ({
      profile,
      todayStats,
      foodLogs,
      workoutLogs,
      streak,
      isLoading,
      loadProfile,
      saveProfile,
      loadTodayStats,
      addWater,
      logFood,
      logWorkout,
      getDailyScore,
      chatWithCoach,
    }),
    [profile, todayStats, foodLogs, workoutLogs, streak, isLoading]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
