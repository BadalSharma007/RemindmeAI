import { useEffect, useState } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SplashScreen from 'expo-splash-screen';
import * as Linking from 'expo-linking';
import { Colors } from '../constants/theme';

SplashScreen.preventAutoHideAsync();

// Global auth state — updated by login screen
export let setGlobalAuth: (loggedIn: boolean) => void = () => {};

export default function RootLayout() {
  const [isReady, setIsReady] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const router = useRouter();
  const segments = useSegments();

  // Expose setter so login screen can trigger re-render
  setGlobalAuth = setIsLoggedIn;

  // Check token on mount
  useEffect(() => {
    (async () => {
      const token = await AsyncStorage.getItem('access_token');
      setIsLoggedIn(!!token);
      setIsReady(true);
      await SplashScreen.hideAsync();
    })();
  }, []);

  // Handle deep links (OAuth callback while app is open)
  useEffect(() => {
    const handleUrl = async ({ url }: { url: string }) => {
      if (url.includes('auth/callback')) {
        const parsed = Linking.parse(url);
        const token = parsed.queryParams?.token as string | undefined;
        const email = parsed.queryParams?.email as string | undefined;
        if (token) {
          await AsyncStorage.setItem('access_token', token);
          if (email) await AsyncStorage.setItem('user_email', email);
          setIsLoggedIn(true);
        }
      }
    };

    const sub = Linking.addEventListener('url', handleUrl);
    return () => sub.remove();
  }, []);

  // Route guard
  useEffect(() => {
    if (!isReady) return;
    const inAuthGroup = segments[0] === 'login' || segments[0] === 'auth';
    if (!isLoggedIn && !inAuthGroup) {
      router.replace('/login');
    } else if (isLoggedIn && inAuthGroup) {
      router.replace('/(tabs)');
    }
  }, [isReady, isLoggedIn, segments]);

  if (!isReady) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="light" backgroundColor={Colors.background} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: Colors.background },
          animation: 'fade',
        }}
      >
        <Stack.Screen name="login" />
        <Stack.Screen name="auth/callback" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}
