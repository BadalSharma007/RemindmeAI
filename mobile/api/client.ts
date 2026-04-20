import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL } from '../constants/theme';

/**
 * Lightweight API client for React Native — no axios needed.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await AsyncStorage.getItem('access_token');

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('user_email');
    throw new Error('UNAUTHORIZED');
  }

  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem('access_token');
}

export async function setToken(token: string, email?: string): Promise<void> {
  await AsyncStorage.setItem('access_token', token);
  if (email) await AsyncStorage.setItem('user_email', email);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem('access_token');
  await AsyncStorage.removeItem('user_email');
}
