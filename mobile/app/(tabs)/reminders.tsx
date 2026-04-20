import { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable, RefreshControl, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Colors, FontSize, Radius, Spacing } from '../../constants/theme';
import { apiFetch } from '../../api/client';
import { MOCK_REMINDERS } from '../../api/mock';
import type { Reminder } from '../../api/types';

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: keyof typeof Ionicons.glyphMap; label: string }> = {
  pending: { bg: Colors.tertiary + '15', text: Colors.tertiary, icon: 'time', label: 'Pending' },
  sent: { bg: Colors.success + '15', text: Colors.success, icon: 'checkmark-circle', label: 'Sent' },
  failed: { bg: Colors.error + '15', text: Colors.error, icon: 'close-circle', label: 'Failed' },
  snoozed: { bg: Colors.primary + '15', text: Colors.primary, icon: 'alarm', label: 'Snoozed' },
};

const FILTERS = ['all', 'pending', 'sent', 'snoozed', 'failed'];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${months[d.getMonth()]} ${d.getDate()} · ${h % 12 || 12}:${m} ${ampm}`;
}

export default function RemindersScreen() {
  const [reminders, setReminders] = useState<Reminder[]>(MOCK_REMINDERS);
  const [isDemo, setIsDemo] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const fetchReminders = async () => {
    try {
      const data = await apiFetch<Reminder[]>('/reminders');
      if (Array.isArray(data) && data.length > 0) {
        setReminders(data);
        setIsDemo(false);
      } else { setIsDemo(true); }
    } catch { setIsDemo(true); }
  };

  useEffect(() => { fetchReminders(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchReminders();
    setRefreshing(false);
  };

  const handleSnooze = (id: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    const snoozeUntil = new Date(Date.now() + 3600000).toISOString();
    setReminders(prev => prev.map(r => r.id === id ? { ...r, status: 'snoozed' as const, scheduled_at: snoozeUntil } : r));
    if (!isDemo) {
      apiFetch(`/reminders/${id}/snooze`, { method: 'POST', body: JSON.stringify({ snooze_until: snoozeUntil }) }).catch(() => {});
    }
  };

  const filtered = reminders.filter(r => {
    if (filter !== 'all' && r.status !== filter) return false;
    if (search && !r.channel.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const pendingCount = reminders.filter(r => r.status === 'pending').length;
  const sentCount = reminders.filter(r => r.status === 'sent').length;
  const failedCount = reminders.filter(r => r.status === 'failed').length;

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
          <View style={styles.titleRow}>
            <Ionicons name="notifications" size={20} color={Colors.primary} />
            <Text style={styles.pageTitle}>Reminders</Text>
            {isDemo && <View style={styles.demoBadge}><Text style={styles.demoText}>Demo</Text></View>}
          </View>
          <Text style={styles.pageSubtitle}>Scheduled notifications for your deadlines.</Text>
        </View>

        {/* Quick Stats */}
        <View style={styles.quickStats}>
          <View style={styles.qStat}>
            <Text style={styles.qStatVal}>{reminders.length}</Text>
            <Text style={styles.qStatLbl}>Total</Text>
          </View>
          <View style={styles.qStat}>
            <Text style={[styles.qStatVal, { color: Colors.tertiary }]}>{pendingCount}</Text>
            <Text style={styles.qStatLbl}>Pending</Text>
          </View>
          <View style={styles.qStat}>
            <Text style={[styles.qStatVal, { color: Colors.success }]}>{sentCount}</Text>
            <Text style={styles.qStatLbl}>Sent</Text>
          </View>
          <View style={styles.qStat}>
            <Text style={[styles.qStatVal, { color: Colors.error }]}>{failedCount}</Text>
            <Text style={styles.qStatLbl}>Failed</Text>
          </View>
        </View>

        {/* Search */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color={Colors.onSurfaceVariant + '60'} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search reminders..."
            placeholderTextColor={Colors.onSurfaceVariant + '50'}
            value={search}
            onChangeText={setSearch}
          />
        </View>

        {/* Filters */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filtersScroll} contentContainerStyle={styles.filtersContent}>
          {FILTERS.map(f => (
            <Pressable key={f} onPress={() => { setFilter(f); Haptics.selectionAsync(); }}
              style={[styles.filterChip, filter === f && styles.filterChipActive]}>
              <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Text>
            </Pressable>
          ))}
        </ScrollView>

        {/* Cards */}
        {filtered.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Ionicons name="notifications-off-outline" size={32} color={Colors.onSurfaceVariant + '40'} />
            </View>
            <Text style={styles.emptyTitle}>No reminders</Text>
            <Text style={styles.emptySubtitle}>Reminders will appear once AI detects deadlines.</Text>
          </View>
        ) : (
          filtered.map((r) => {
            const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.pending;
            return (
              <View key={r.id} style={styles.card}>
                <View style={styles.cardRow}>
                  <View style={{ flex: 1 }}>
                    <View style={styles.scheduleRow}>
                      <Ionicons name="time-outline" size={13} color={Colors.onSurfaceVariant + '60'} />
                      <Text style={styles.scheduleLabel}>Scheduled: </Text>
                      <Text style={styles.scheduleValue}>{formatDate(r.scheduled_at)}</Text>
                    </View>
                    <View style={styles.chipRow}>
                      <View style={styles.channelChip}>
                        <Ionicons name="send" size={11} color={Colors.onSurfaceVariant} />
                        <Text style={styles.channelText}>{r.channel}</Text>
                      </View>
                      <View style={[styles.statusChip, { backgroundColor: cfg.bg }]}>
                        <Ionicons name={cfg.icon} size={11} color={cfg.text} />
                        <Text style={[styles.statusText, { color: cfg.text }]}>{cfg.label}</Text>
                      </View>
                      {r.sent_at && (
                        <Text style={styles.sentAt}>Sent {formatDate(r.sent_at)}</Text>
                      )}
                    </View>
                  </View>
                  {r.status === 'pending' && (
                    <Pressable onPress={() => handleSnooze(r.id)}
                      style={({ pressed }) => [styles.snoozeBtn, pressed && { opacity: 0.8 }]}>
                      <Ionicons name="alarm" size={14} color={Colors.primary} />
                      <Text style={styles.snoozeText}>1h</Text>
                    </Pressable>
                  )}
                </View>
              </View>
            );
          })
        )}

        {filtered.length > 0 && (
          <Text style={styles.footerText}>
            {filtered.length} reminder{filtered.length !== 1 ? 's' : ''} · {pendingCount} pending · {sentCount} sent
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: Spacing.xl, paddingBottom: Spacing.xxxl },
  header: { marginTop: Spacing.lg, marginBottom: Spacing.xl },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  pageTitle: { fontSize: FontSize.xxxl, fontWeight: '700', color: Colors.onSurface, letterSpacing: -0.5 },
  pageSubtitle: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, marginTop: 4, marginLeft: 28 },
  demoBadge: { backgroundColor: Colors.tertiary + '15', paddingHorizontal: 10, paddingVertical: 3, borderRadius: Radius.full },
  demoText: { fontSize: FontSize.xs, fontWeight: '700', color: Colors.tertiary },
  quickStats: { flexDirection: 'row', gap: Spacing.md, marginBottom: Spacing.xl },
  qStat: {
    flex: 1, backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.lg, paddingVertical: Spacing.lg, alignItems: 'center',
  },
  qStatVal: { fontSize: FontSize.xxl, fontWeight: '800', color: Colors.onSurface },
  qStatLbl: { fontSize: FontSize.xs, fontWeight: '600', color: Colors.onSurfaceVariant, marginTop: 2, textTransform: 'uppercase' },
  searchBox: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: Colors.surfaceContainerHigh, borderRadius: Radius.md,
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, gap: Spacing.sm, marginBottom: Spacing.lg,
  },
  searchInput: { flex: 1, fontSize: FontSize.md, color: Colors.onSurface },
  filtersScroll: { marginBottom: Spacing.lg },
  filtersContent: { gap: Spacing.sm },
  filterChip: {
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm,
    borderRadius: Radius.full, backgroundColor: Colors.surfaceContainer,
  },
  filterChipActive: { backgroundColor: Colors.primary },
  filterText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.onSurfaceVariant },
  filterTextActive: { color: Colors.onPrimary },
  emptyState: {
    backgroundColor: Colors.surfaceContainer, borderRadius: Radius.xl,
    padding: Spacing.xxxl, alignItems: 'center', marginTop: Spacing.lg,
  },
  emptyIcon: {
    width: 64, height: 64, borderRadius: Radius.lg,
    backgroundColor: Colors.surfaceContainerHigh,
    justifyContent: 'center', alignItems: 'center', marginBottom: Spacing.xl,
  },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.onSurface, marginBottom: Spacing.sm },
  emptySubtitle: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, textAlign: 'center' },
  card: {
    backgroundColor: Colors.surfaceContainer, borderRadius: Radius.lg,
    padding: Spacing.xl, marginBottom: Spacing.md,
  },
  cardRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.lg },
  scheduleRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: Spacing.sm },
  scheduleLabel: { fontSize: FontSize.md, color: Colors.onSurfaceVariant },
  scheduleValue: { fontSize: FontSize.md, color: Colors.onSurface, fontWeight: '600' },
  chipRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: Spacing.sm },
  channelChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.surfaceContainerHigh, paddingHorizontal: Spacing.md,
    paddingVertical: 4, borderRadius: Radius.full,
  },
  channelText: { fontSize: FontSize.xs, fontWeight: '500', color: Colors.onSurfaceVariant },
  statusChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radius.full,
  },
  statusText: { fontSize: FontSize.xs, fontWeight: '700' },
  sentAt: { fontSize: FontSize.xs, color: Colors.onSurfaceVariant + '50' },
  snoozeBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.primary + '15', paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm, borderRadius: Radius.sm,
  },
  snoozeText: { fontSize: FontSize.sm, fontWeight: '700', color: Colors.primary },
  footerText: { textAlign: 'center', fontSize: FontSize.xs, color: Colors.onSurfaceVariant + '50', marginTop: Spacing.lg },
});
