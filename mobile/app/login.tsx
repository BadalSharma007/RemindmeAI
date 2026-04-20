import { View, Text, Pressable, StyleSheet, Dimensions, Alert, ActivityIndicator } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors, FontSize, Radius, Spacing } from '../constants/theme';
import { API_BASE_URL } from '../constants/theme';
import { Ionicons } from '@expo/vector-icons';
import { setGlobalAuth } from './_layout';

const { width } = Dimensions.get('window');

export default function LoginScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      // Build deep link callback URL for Expo Go
      const redirectUrl = Linking.createURL('auth/callback');
      const loginUrl = `${API_BASE_URL}/auth/start/gmail?redirect_url=${encodeURIComponent(redirectUrl)}`;

      // Open system browser for OAuth
      const result = await WebBrowser.openAuthSessionAsync(loginUrl, redirectUrl);

      if (result.type === 'success' && result.url) {
        // Use Linking.parse() — works with exp:// and custom schemes
        const parsed = Linking.parse(result.url);
        const token = parsed.queryParams?.token as string | undefined;
        const email = parsed.queryParams?.email as string | undefined;

        if (token) {
          await AsyncStorage.setItem('access_token', token);
          if (email) await AsyncStorage.setItem('user_email', email);
          // Update global auth state → triggers route guard → navigates to tabs
          setGlobalAuth(true);
        } else {
          Alert.alert('Login Failed', 'No token received. Please try again.');
        }
      }
    } catch (e) {
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Ambient glow */}
      <View style={styles.glowTop} />
      <View style={styles.glowBottom} />

      <View style={styles.content}>
        {/* Brand */}
        <View style={styles.brand}>
          <LinearGradient
            colors={[Colors.primary, Colors.primaryContainer]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.brandIcon}
          >
            <Ionicons name="sparkles" size={28} color={Colors.onPrimary} />
          </LinearGradient>
          <Text style={styles.brandText}>
            Remindme<Text style={{ color: Colors.primary }}>AI</Text>
          </Text>
        </View>

        {/* Card */}
        <View style={styles.card}>
          <Text style={styles.label}>WELCOME BACK</Text>
          <Text style={styles.title}>Sign in to your workspace</Text>
          <Text style={styles.subtitle}>Your intelligent email-based reminder system awaits.</Text>

          {/* Feature pills */}
          <View style={styles.pills}>
            {[
              { icon: 'bulb' as const, label: 'AI-Powered' },
              { icon: 'shield-checkmark' as const, label: 'Secure' },
              { icon: 'flash' as const, label: 'Real-time' },
            ].map((f) => (
              <View key={f.label} style={styles.pill}>
                <Ionicons name={f.icon} size={12} color={Colors.primary} />
                <Text style={styles.pillText}>{f.label}</Text>
              </View>
            ))}
          </View>

          {/* CTA */}
          <Pressable onPress={handleLogin} disabled={loading} style={({ pressed }) => [styles.ctaWrapper, pressed && { opacity: 0.9 }]}>
            <LinearGradient
              colors={[Colors.primary, Colors.primaryContainer]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.cta}
            >
              {loading ? (
                <ActivityIndicator color={Colors.onPrimary} size="small" />
              ) : (
                <>
                  <Ionicons name="logo-google" size={18} color={Colors.onPrimary} />
                  <Text style={styles.ctaText}>Sign in with Gmail</Text>
                  <Ionicons name="arrow-forward" size={18} color={Colors.onPrimary} />
                </>
              )}
            </LinearGradient>
          </Pressable>
        </View>

        <Text style={styles.footer}>
          By signing in, you agree to our Terms of Service and Privacy Policy.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  glowTop: {
    position: 'absolute',
    top: '15%',
    left: '50%',
    width: 400,
    height: 400,
    marginLeft: -200,
    borderRadius: 200,
    backgroundColor: 'rgba(192,193,255,0.04)',
  },
  glowBottom: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: 'rgba(239,184,66,0.03)',
  },
  content: {
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 40,
  },
  brandIcon: {
    width: 48,
    height: 48,
    borderRadius: Radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  brandText: {
    fontSize: FontSize.xxl,
    color: Colors.onSurface,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  card: {
    width: '100%',
    backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.xl,
    padding: Spacing.xxl,
    alignItems: 'center',
  },
  label: {
    fontSize: FontSize.xs,
    color: Colors.onSurfaceVariant,
    letterSpacing: 1.5,
    fontWeight: '600',
    marginBottom: Spacing.md,
  },
  title: {
    fontSize: FontSize.lg,
    color: Colors.onSurface,
    fontWeight: '600',
    marginBottom: Spacing.sm,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: FontSize.md,
    color: Colors.onSurfaceVariant,
    textAlign: 'center',
    marginBottom: Spacing.xl,
    lineHeight: 20,
  },
  pills: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginBottom: Spacing.xxl,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.surfaceContainerHigh,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.full,
  },
  pillText: {
    fontSize: FontSize.xs,
    color: Colors.onSurfaceVariant,
    fontWeight: '500',
  },
  ctaWrapper: {
    width: '100%',
  },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 16,
    borderRadius: Radius.lg,
  },
  ctaText: {
    fontSize: FontSize.md,
    color: Colors.onPrimary,
    fontWeight: '700',
  },
  footer: {
    fontSize: FontSize.xs,
    color: 'rgba(142,142,147,0.5)',
    textAlign: 'center',
    marginTop: Spacing.xxxl,
    lineHeight: 16,
  },
});
