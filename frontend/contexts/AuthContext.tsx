import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api, { authApi, usersApi } from '../lib/api-client';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
}

interface AuthContextValue {
  authUser: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearAuthError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadAuth();
  }, []);

  const loadAuth = async () => {
    try {
      const sessionStr = await AsyncStorage.getItem('current_session');
      if (sessionStr) {
        setAuthUser(JSON.parse(sessionStr));
      }
    } catch (e) {
      console.error('Error loading auth:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (name: string, email: string, password: string): Promise<boolean> => {
    try {
      setAuthError('');
      const normalizedEmail = email.trim().toLowerCase();
      if (!name.trim() || !normalizedEmail || !password) {
        setAuthError('All fields are required.');
        return false;
      }
      if (password.length < 6) {
        setAuthError('Password must be at least 6 characters.');
        return false;
      }

      const res = await authApi.signup({ name: name.trim(), email: normalizedEmail, password });
      const { access_token } = res.data;
      await AsyncStorage.setItem('access_token', access_token);

      const userRes = await usersApi.getMe();
      const user = userRes.data;
      const session: AuthUser = { id: user.id, name: user.name, email: user.email };
      await AsyncStorage.setItem('current_session', JSON.stringify(session));
      setAuthUser(session);
      return true;
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || 'Signup failed. Please try again.');
      return false;
    }
  };

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      setAuthError('');
      const normalizedEmail = email.trim().toLowerCase();
      if (!normalizedEmail || !password) {
        setAuthError('Please enter your email and password.');
        return false;
      }

      const res = await authApi.login({ email: normalizedEmail, password });
      const { access_token } = res.data;
      await AsyncStorage.setItem('access_token', access_token);

      const userRes = await usersApi.getMe();
      const user = userRes.data;
      const session: AuthUser = { id: user.id, name: user.name, email: user.email };
      await AsyncStorage.setItem('current_session', JSON.stringify(session));
      setAuthUser(session);
      return true;
    } catch (e: any) {
      setAuthError(e.response?.data?.detail || 'Login failed. Please try again.');
      return false;
    }
  };

  const logout = async () => {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('current_session');
    setAuthUser(null);
  };

  const clearAuthError = () => setAuthError('');

  const value = useMemo(
    () => ({
      authUser,
      isAuthenticated: !!authUser,
      isLoading,
      authError,
      login,
      signup,
      logout,
      clearAuthError,
    }),
    [authUser, isLoading, authError]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
