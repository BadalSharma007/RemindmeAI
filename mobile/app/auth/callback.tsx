import { useEffect } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors } from '../../constants/theme';

export default function AuthCallbackScreen() {
  const { token, email } = useLocalSearchParams<{ token?: string; email?: string }>();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      if (token) {
        await AsyncStorage.setItem('access_token', token);
        if (email) await AsyncStorage.setItem('user_email', email);
        router.replace('/(tabs)');
      } else {
        router.replace('/login');
      }
    })();
  }, [token]);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={Colors.primary} />
      <Text style={styles.text}>Signing you in...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  text: {
    color: Colors.onSurfaceVariant,
    fontSize: 14,
  },
});
