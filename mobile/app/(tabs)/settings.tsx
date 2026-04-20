import { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable, TextInput, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Colors, FontSize, Radius, Spacing } from '../../constants/theme';
import { apiFetch, clearToken } from '../../api/client';
import type { UserProfile } from '../../api/types';

export default function SettingsScreen() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [leadMinutes, setLeadMinutes] = useState('60');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<UserProfile>('/auth/me');
        setUser(data);
      } catch {
        const email = await AsyncStorage.getItem('user_email');
        if (email) setUser({ id: '', email, display_name: null, timezone: 'UTC' });
      }
    })();
  }, []);

  const handleSave = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      await apiFetch('/preferences', {
        method: 'PUT',
        body: JSON.stringify({ reminder_lead_minutes: Number(leadMinutes) }),
      });
    } catch {}
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleDisconnect = () => {
    Alert.alert(
      'Disconnect Gmail',
      'This will revoke access and stop processing your emails. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
            try { await apiFetch('/auth/disconnect/gmail', { method: 'DELETE' }); } catch {}
          },
        },
      ]
    );
  };

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
          await clearToken();
          router.replace('/login');
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.titleRow}>
            <Ionicons name="settings-sharp" size={20} color={Colors.primary} />
            <Text style={styles.pageTitle}>Settings</Text>
          </View>
          <Text style={styles.pageSubtitle}>Manage your account and preferences.</Text>
        </View>

        {/* Account Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.cardIconBg}>
              <Ionicons name="person" size={16} color={Colors.primary} />
            </View>
            <Text style={styles.cardTitle}>Account</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Email</Text>
            <Text style={styles.infoValue}>{user?.email ?? '—'}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Timezone</Text>
            <Text style={styles.infoValue}>{user?.timezone ?? 'UTC'}</Text>
          </View>
          <Pressable onPress={handleLogout}
            style={({ pressed }) => [styles.logoutBtn, pressed && { opacity: 0.8 }]}>
            <Ionicons name="log-out" size={16} color={Colors.onSurfaceVariant} />
            <Text style={styles.logoutText}>Log out</Text>
          </Pressable>
        </View>

        {/* Preferences Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIconBg, { backgroundColor: Colors.tertiary + '15' }]}>
              <Ionicons name="notifications" size={16} color={Colors.tertiary} />
            </View>
            <Text style={styles.cardTitle}>Reminder Preferences</Text>
          </View>
          <Text style={styles.prefLabel}>Remind me this many minutes before a deadline:</Text>
          <View style={styles.prefRow}>
            <TextInput
              style={styles.prefInput}
              keyboardType="number-pad"
              value={leadMinutes}
              onChangeText={setLeadMinutes}
              maxLength={5}
            />
            <Pressable onPress={handleSave} style={({ pressed }) => [pressed && { opacity: 0.8 }]}>
              <LinearGradient
                colors={saved ? [Colors.success + '30', Colors.success + '15'] : [Colors.primary, Colors.primaryContainer]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.saveBtn}
              >
                <Ionicons name={saved ? 'checkmark-circle' : 'save'} size={16} color={saved ? Colors.success : Colors.onPrimary} />
                <Text style={[styles.saveText, saved && { color: Colors.success }]}>{saved ? 'Saved!' : 'Save'}</Text>
              </LinearGradient>
            </Pressable>
          </View>
        </View>

        {/* Danger Zone */}
        <View style={[styles.card, { marginBottom: Spacing.xxxl }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIconBg, { backgroundColor: Colors.error + '15' }]}>
              <Ionicons name="warning" size={16} color={Colors.error} />
            </View>
            <Text style={[styles.cardTitle, { color: Colors.error }]}>Danger Zone</Text>
          </View>
          <Text style={styles.dangerText}>Disconnecting Gmail will revoke access and stop processing your emails.</Text>
          <Pressable onPress={handleDisconnect}
            style={({ pressed }) => [styles.dangerBtn, pressed && { opacity: 0.8 }]}>
            <Ionicons name="unlink" size={16} color={Colors.error} />
            <Text style={styles.dangerBtnText}>Disconnect Gmail</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: Spacing.xl, paddingBottom: Spacing.xxxl },
  header: { marginTop: Spacing.lg, marginBottom: Spacing.xxl },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  pageTitle: { fontSize: FontSize.xxxl, fontWeight: '700', color: Colors.onSurface, letterSpacing: -0.5 },
  pageSubtitle: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, marginTop: 4, marginLeft: 28 },
  card: {
    backgroundColor: Colors.surfaceContainer, borderRadius: Radius.lg,
    padding: Spacing.xl, marginBottom: Spacing.lg,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, marginBottom: Spacing.xl },
  cardIconBg: {
    width: 32, height: 32, borderRadius: Radius.sm,
    backgroundColor: Colors.surfaceContainerHigh,
    justifyContent: 'center', alignItems: 'center',
  },
  cardTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.onSurface },
  infoRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: Spacing.md,
  },
  infoLabel: { fontSize: FontSize.md, color: Colors.onSurfaceVariant },
  infoValue: { fontSize: FontSize.md, color: Colors.onSurface, fontWeight: '500' },
  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.surfaceContainerHigh,
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderRadius: Radius.sm, marginTop: Spacing.lg, alignSelf: 'flex-start',
  },
  logoutText: { fontSize: FontSize.md, fontWeight: '500', color: Colors.onSurfaceVariant },
  prefLabel: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, marginBottom: Spacing.lg },
  prefRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  prefInput: {
    backgroundColor: Colors.surfaceContainerHigh, color: Colors.onSurface,
    borderRadius: Radius.sm, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    fontSize: FontSize.md, width: 100, textAlign: 'center', fontWeight: '600',
  },
  saveBtn: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: Radius.sm,
  },
  saveText: { fontSize: FontSize.md, fontWeight: '700', color: Colors.onPrimary },
  dangerText: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, marginBottom: Spacing.lg, lineHeight: 20 },
  dangerBtn: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.error + '15',
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md,
    borderRadius: Radius.sm, alignSelf: 'flex-start',
  },
  dangerBtnText: { fontSize: FontSize.md, fontWeight: '600', color: Colors.error },
});
