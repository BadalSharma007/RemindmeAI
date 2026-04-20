import { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable, RefreshControl } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Colors, FontSize, Radius, Spacing } from '../../constants/theme';
import { apiFetch } from '../../api/client';
import { MOCK_STATS } from '../../api/mock';
import type { DashboardStats } from '../../api/types';

function StatCard({ label, value, icon, color = Colors.primary }: {
  label: string; value: number; icon: keyof typeof Ionicons.glyphMap; color?: string;
}) {
  return (
    <View style={styles.statCard}>
      <View style={[styles.statIcon, { backgroundColor: color + '15' }]}>
        <Ionicons name={icon} size={16} color={color} />
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

export default function DashboardScreen() {
  const [stats, setStats] = useState<DashboardStats>(MOCK_STATS);
  const [isDemo, setIsDemo] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = async () => {
    try {
      const data = await apiFetch<DashboardStats>('/stats/dashboard');
      setStats(data);
      setIsDemo(false);
    } catch {
      setIsDemo(true);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchStats();
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <View style={styles.titleRow}>
              <Text style={styles.pageTitle}>Dashboard</Text>
              {isDemo && <View style={styles.demoBadge}><Text style={styles.demoText}>Demo</Text></View>}
            </View>
            <Text style={styles.pageSubtitle}>Your command center at a glance.</Text>
          </View>
        </View>

        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          <StatCard label="Total" value={stats.total_deadlines} icon="calendar" />
          <StatCard label="Pending" value={stats.pending_deadlines} icon="time" color={Colors.tertiary} />
          <StatCard label="Reminders" value={stats.upcoming_reminders} icon="notifications" color={Colors.tertiary} />
          <StatCard label="Emails" value={stats.emails_processed_today} icon="mail" />
        </View>

        {/* AI Assistant Card */}
        <View style={styles.aiCard}>
          <View style={styles.aiHeader}>
            <Ionicons name="sparkles" size={16} color={Colors.primary} />
            <Text style={styles.aiLabel}>AI ASSISTANT</Text>
          </View>
          <View style={styles.aiInput}>
            <Text style={styles.aiPlaceholder}>Ask AI to manage your reminders...</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          <Pressable style={({ pressed }) => [styles.actionCard, pressed && { opacity: 0.8 }]}>
            <LinearGradient
              colors={[Colors.primary + '20', Colors.primaryContainer + '10']}
              style={styles.actionGradient}
            >
              <Ionicons name="add-circle" size={24} color={Colors.primary} />
              <Text style={styles.actionLabel}>Add Deadline</Text>
            </LinearGradient>
          </Pressable>
          <Pressable style={({ pressed }) => [styles.actionCard, pressed && { opacity: 0.8 }]}>
            <LinearGradient
              colors={[Colors.tertiary + '20', Colors.tertiaryContainer + '10']}
              style={styles.actionGradient}
            >
              <Ionicons name="mail" size={24} color={Colors.tertiary} />
              <Text style={styles.actionLabel}>Scan Emails</Text>
            </LinearGradient>
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
  pageSubtitle: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, marginTop: 4 },
  demoBadge: { backgroundColor: Colors.tertiary + '15', paddingHorizontal: 10, paddingVertical: 3, borderRadius: Radius.full },
  demoText: { fontSize: FontSize.xs, fontWeight: '700', color: Colors.tertiary },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.md, marginBottom: Spacing.xxl },
  statCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
  },
  statIcon: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  statValue: { fontSize: FontSize.xxxl, fontWeight: '800', color: Colors.onSurface },
  statLabel: { fontSize: FontSize.xs, fontWeight: '600', color: Colors.onSurfaceVariant, marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.5 },
  aiCard: {
    backgroundColor: Colors.surfaceContainerHigh,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    marginBottom: Spacing.xxl,
  },
  aiHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.md },
  aiLabel: { fontSize: FontSize.xs, fontWeight: '700', color: Colors.primary, letterSpacing: 1 },
  aiInput: {
    backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
  },
  aiPlaceholder: { fontSize: FontSize.md, color: Colors.onSurfaceVariant + '60' },
  sectionTitle: { fontSize: FontSize.lg, fontWeight: '700', color: Colors.onSurface, marginBottom: Spacing.lg },
  actionsGrid: { flexDirection: 'row', gap: Spacing.md },
  actionCard: { flex: 1 },
  actionGradient: {
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    alignItems: 'center',
    gap: Spacing.sm,
  },
  actionLabel: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.onSurface },
});
