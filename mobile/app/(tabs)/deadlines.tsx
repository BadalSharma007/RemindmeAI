import { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable, RefreshControl, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Colors, FontSize, Radius, Spacing } from '../../constants/theme';
import { apiFetch } from '../../api/client';
import { MOCK_DEADLINES } from '../../api/mock';
import type { Deadline } from '../../api/types';

const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: keyof typeof Ionicons.glyphMap; label: string }> = {
  pending: { bg: Colors.tertiary + '15', text: Colors.tertiary, icon: 'time', label: 'Pending' },
  reminded: { bg: Colors.primary + '15', text: Colors.primary, icon: 'alert-circle', label: 'Reminded' },
  completed: { bg: Colors.success + '15', text: Colors.success, icon: 'checkmark-circle', label: 'Completed' },
  dismissed: { bg: Colors.onSurfaceVariant + '15', text: Colors.onSurfaceVariant, icon: 'close-circle', label: 'Dismissed' },
};

const FILTERS = ['all', 'pending', 'reminded', 'completed', 'dismissed'];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${months[d.getMonth()]} ${d.getDate()} · ${h % 12 || 12}:${m} ${ampm}`;
}

export default function DeadlinesScreen() {
  const [deadlines, setDeadlines] = useState<Deadline[]>(MOCK_DEADLINES);
  const [isDemo, setIsDemo] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const fetchDeadlines = async () => {
    try {
      const data = await apiFetch<Deadline[]>('/deadlines');
      if (Array.isArray(data) && data.length > 0) {
        setDeadlines(data);
        setIsDemo(false);
      } else { setIsDemo(true); }
    } catch { setIsDemo(true); }
  };

  useEffect(() => { fetchDeadlines(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchDeadlines();
    setRefreshing(false);
  };

  const handleAction = (id: string, status: 'completed' | 'dismissed') => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setDeadlines(prev => prev.map(dl => dl.id === id ? { ...dl, status } : dl));
    if (!isDemo) {
      apiFetch(`/deadlines/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }).catch(() => {});
    }
  };

  const filtered = deadlines.filter(dl => {
    if (filter !== 'all' && dl.status !== filter) return false;
    if (search && !dl.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

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
            <Ionicons name="calendar" size={20} color={Colors.primary} />
            <Text style={styles.pageTitle}>Deadlines</Text>
            {isDemo && <View style={styles.demoBadge}><Text style={styles.demoText}>Demo</Text></View>}
          </View>
          <Text style={styles.pageSubtitle}>Track and manage your upcoming deadlines.</Text>
        </View>

        {/* Search */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color={Colors.onSurfaceVariant + '60'} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search deadlines..."
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
              <Ionicons name="calendar-outline" size={32} color={Colors.onSurfaceVariant + '40'} />
            </View>
            <Text style={styles.emptyTitle}>{search ? 'No matches' : 'All clear'}</Text>
            <Text style={styles.emptySubtitle}>
              {search ? `No deadlines matching "${search}"` : 'No pending deadlines right now.'}
            </Text>
          </View>
        ) : (
          filtered.map((dl) => {
            const cfg = STATUS_CONFIG[dl.status] || STATUS_CONFIG.pending;
            const isActionable = dl.status === 'pending' || dl.status === 'reminded';
            return (
              <View key={dl.id} style={styles.card}>
                <Text style={[styles.cardTitle, dl.status === 'completed' && styles.cardTitleDone]}>
                  {dl.title}
                </Text>
                {dl.source_text && (
                  <Text style={styles.cardSource} numberOfLines={1}>{dl.source_text}</Text>
                )}
                <View style={styles.cardMeta}>
                  <View style={styles.metaItem}>
                    <Ionicons name="time-outline" size={13} color={Colors.onSurfaceVariant + '60'} />
                    <Text style={styles.metaText}>{formatDate(dl.due_at)}</Text>
                  </View>
                  <View style={[styles.statusChip, { backgroundColor: cfg.bg }]}>
                    <Ionicons name={cfg.icon} size={11} color={cfg.text} />
                    <Text style={[styles.statusText, { color: cfg.text }]}>{cfg.label}</Text>
                  </View>
                  <Text style={styles.confidence}>{Math.round(dl.confidence_score * 100)}%</Text>
                </View>

                {isActionable && (
                  <View style={styles.actions}>
                    <Pressable onPress={() => handleAction(dl.id, 'completed')}
                      style={({ pressed }) => [styles.actionBtn, styles.doneBtn, pressed && { opacity: 0.8 }]}>
                      <Ionicons name="checkmark" size={14} color={Colors.success} />
                      <Text style={[styles.actionText, { color: Colors.success }]}>Done</Text>
                    </Pressable>
                    <Pressable onPress={() => handleAction(dl.id, 'dismissed')}
                      style={({ pressed }) => [styles.actionBtn, styles.dismissBtn, pressed && { opacity: 0.8 }]}>
                      <Ionicons name="close" size={14} color={Colors.onSurfaceVariant} />
                      <Text style={styles.actionText}>Dismiss</Text>
                    </Pressable>
                  </View>
                )}
              </View>
            );
          })
        )}

        {filtered.length > 0 && (
          <Text style={styles.footer}>
            {filtered.length} deadline{filtered.length !== 1 ? 's' : ''} · {deadlines.filter(d => d.status === 'pending').length} pending
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
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceContainerHigh,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  searchInput: { flex: 1, fontSize: FontSize.md, color: Colors.onSurface },
  filtersScroll: { marginBottom: Spacing.lg },
  filtersContent: { gap: Spacing.sm },
  filterChip: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    backgroundColor: Colors.surfaceContainer,
  },
  filterChipActive: { backgroundColor: Colors.primary },
  filterText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.onSurfaceVariant },
  filterTextActive: { color: Colors.onPrimary },
  emptyState: {
    backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.xl,
    padding: Spacing.xxxl,
    alignItems: 'center',
    marginTop: Spacing.lg,
  },
  emptyIcon: {
    width: 64, height: 64, borderRadius: Radius.lg,
    backgroundColor: Colors.surfaceContainerHigh,
    justifyContent: 'center', alignItems: 'center', marginBottom: Spacing.xl,
  },
  emptyTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.onSurface, marginBottom: Spacing.sm },
  emptySubtitle: { fontSize: FontSize.md, color: Colors.onSurfaceVariant, textAlign: 'center' },
  card: {
    backgroundColor: Colors.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    marginBottom: Spacing.md,
  },
  cardTitle: { fontSize: FontSize.lg, fontWeight: '600', color: Colors.onSurface, marginBottom: 4 },
  cardTitleDone: { color: Colors.onSurfaceVariant + '60', textDecorationLine: 'line-through' },
  cardSource: { fontSize: FontSize.xs, color: Colors.onSurfaceVariant + '50', marginBottom: Spacing.md },
  cardMeta: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: Spacing.sm },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { fontSize: FontSize.sm, color: Colors.onSurfaceVariant },
  statusChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radius.full,
  },
  statusText: { fontSize: FontSize.xs, fontWeight: '700' },
  confidence: { fontSize: FontSize.xs, color: Colors.onSurfaceVariant + '50' },
  actions: { flexDirection: 'row', gap: Spacing.sm, marginTop: Spacing.lg },
  actionBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, borderRadius: Radius.sm,
  },
  doneBtn: { backgroundColor: Colors.success + '15' },
  dismissBtn: { backgroundColor: Colors.surfaceContainerHigh },
  actionText: { fontSize: FontSize.sm, fontWeight: '600', color: Colors.onSurfaceVariant },
  footer: { textAlign: 'center', fontSize: FontSize.xs, color: Colors.onSurfaceVariant + '50', marginTop: Spacing.lg },
});
