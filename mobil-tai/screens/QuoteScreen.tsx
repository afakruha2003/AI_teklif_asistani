import React, { useCallback, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useQuoteStore } from '../store/quoteStore';
import { useChatStore } from '../store/chatStore';
import { QuoteItemCard } from '../components/QuoteItemCard';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';
import { QuoteItem } from '../types';

export default function QuoteScreen() {
  const { quote, isLoading, fetchQuote } = useQuoteStore();
  const { quoteId } = useChatStore();
  const isValidQuoteId = !!(quoteId && quoteId !== 'null' && quoteId !== 'None');

  const load = useCallback(() => {
    if (isValidQuoteId) {
      fetchQuote(quoteId);
    }
  }, [quoteId, isValidQuoteId, fetchQuote]);

  useEffect(() => {
    load();
  }, [quoteId, load]);

  const activeItems = quote?.items?.filter((i: QuoteItem) => i.status === 'active') ?? [];
  const inactiveItems = quote?.items?.filter((i: QuoteItem) => i.status !== 'active') ?? [];

  const renderItem = ({ item }: { item: QuoteItem }) => (
    <QuoteItemCard item={item} />
  );

  const renderHeader = () => (
    <View style={styles.summaryCard}>
      <View style={styles.summaryRow}>
        <Text style={styles.summaryLabel}>Teklif No</Text>
        <Text style={styles.summaryValue} numberOfLines={1}>
          {quote?.id ?? '—'}
        </Text>
      </View>
      <View style={styles.summaryRow}>
        <Text style={styles.summaryLabel}>Müşteri</Text>
        <Text style={styles.summaryValue}>{quote?.customer_name ?? '—'}</Text>
      </View>
      <View style={styles.summaryRow}>
        <Text style={styles.summaryLabel}>Durum</Text>
        <View style={styles.statusPill}>
          <Text style={styles.statusPillText}>{quote?.status ?? '—'}</Text>
        </View>
      </View>
      <View style={styles.divider} />
      <View style={styles.summaryRow}>
        <Text style={styles.totalLabel}>Toplam</Text>
        <Text style={styles.totalValue}>
          {quote ? `${quote.total_try.toLocaleString('tr-TR')} ${quote.currency ?? 'TRY'}` : '—'}
        </Text>
      </View>
      {quote?.updated_at && (
        <Text style={styles.updatedAt}>
          Son güncelleme: {new Date(quote.updated_at).toLocaleString('tr-TR')}
        </Text>
      )}
    </View>
  );

  if (!isValidQuoteId && !quote) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Teklif</Text>
        </View>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyTitle}>Henüz Teklif Yok</Text>
          <Text style={styles.emptyDesc}>
            Chat ekranından ürün ekleyince teklif burada görünür.
            Web paneli ile aynı veriyi paylaşır.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Teklif</Text>
        {isValidQuoteId && (
          <TouchableOpacity onPress={load} style={styles.refreshBtn}>
            <Text style={styles.refreshText}>↻ Yenile</Text>
          </TouchableOpacity>
        )}
      </View>

      {isLoading && !quote ? (
        <View style={styles.loading}>
          <ActivityIndicator color={Colors.primary} size="large" />
        </View>
      ) : (
        <FlatList
          data={activeItems}
          renderItem={renderItem}
          keyExtractor={(i: QuoteItem) => i.id}
          ListHeaderComponent={renderHeader}
          ListFooterComponent={
            inactiveItems.length > 0 ? (
              <View>
                <Text style={styles.sectionTitle}>Pasif / Değiştirilmiş Kalemler</Text>
                {inactiveItems.map((item: QuoteItem) => (
                  <QuoteItemCard key={item.id} item={item} />
                ))}
              </View>
            ) : null
          }
          ListEmptyComponent={
            quote ? (
              <View style={styles.emptyItems}>
                <Text style={styles.emptyDesc}>Teklife henüz ürün eklenmedi.</Text>
              </View>
            ) : null
          }
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={load}
              tintColor={Colors.primary}
              enabled={isValidQuoteId}
            />
          }
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    backgroundColor: Colors.bgCard,
  },
  headerTitle: {
    ...Typography.h2,
    color: Colors.primary,
  },
  refreshBtn: {
    backgroundColor: Colors.bgInput,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  refreshText: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
  },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listContent: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxxl,
  },
  summaryCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.sm,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  summaryLabel: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
  },
  summaryValue: {
    ...Typography.body,
    fontWeight: '500',
    maxWidth: '60%',
    textAlign: 'right',
  },
  statusPill: {
    backgroundColor: 'rgba(76, 201, 240, 0.15)',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
  },
  statusPillText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.accent,
    textTransform: 'uppercase',
  },
  divider: {
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: Spacing.xs,
  },
  totalLabel: {
    ...Typography.h3,
  },
  totalValue: {
    ...Typography.h2,
    color: Colors.accentGreen,
  },
  updatedAt: {
    ...Typography.caption,
    textAlign: 'right',
    marginTop: 4,
  },
  sectionTitle: {
    ...Typography.bodySmall,
    color: Colors.textMuted,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: Spacing.sm,
    marginTop: Spacing.lg,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xxl,
    gap: Spacing.md,
  },
  emptyItems: {
    padding: Spacing.xl,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
  },
  emptyTitle: {
    ...Typography.h2,
    textAlign: 'center',
  },
  emptyDesc: {
    ...Typography.body,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
  },
});