import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';
import { ToolCallEvent } from '../types';

const TOOL_LABELS: Record<string, string> = {
  search_products: '🔍 Ürün Arama',
  get_knowledge_entries: '📖 Bilgi Tabanı',
  get_quote: '📋 Teklif Okuma',
  add_to_quote: '➕ Teklife Ekle',
  update_quote_item: '✏️ Miktar Güncelle',
  replace_with_alternative: '🔄 Alternatif ile Değiştir',
};

interface Props {
  toolCall: ToolCallEvent;
}

export const ToolCallBadge: React.FC<Props> = ({ toolCall }) => {
  const label = TOOL_LABELS[toolCall.tool] ?? toolCall.tool;
  const isRunning = toolCall.status === 'running';
  const isError = toolCall.status === 'error';

  const borderColor = isError
    ? Colors.error
    : isRunning
    ? Colors.accent
    : Colors.accentGreen;

  return (
    <View style={[styles.container, { borderLeftColor: borderColor }]}>
      <View style={styles.header}>
        {isRunning && (
          <ActivityIndicator size={10} color={Colors.accent} style={styles.spinner} />
        )}
        <Text style={[styles.label, { color: borderColor }]}>{label}</Text>
        <Text style={styles.seq}>#{toolCall.sequence}</Text>
      </View>

      {toolCall.input_summary ? (
        <Text style={styles.summary} numberOfLines={2}>
          {toolCall.input_summary}
        </Text>
      ) : null}

      {toolCall.quote_delta ? (
        <QuoteDeltaBadge delta={toolCall.quote_delta} />
      ) : null}
    </View>
  );
};

const QuoteDeltaBadge: React.FC<{ delta: NonNullable<ToolCallEvent['quote_delta']> }> = ({
  delta,
}) => {
  
  const actionLabel =
    delta.action === 'add'
      ? '📥 Eklendi'
      : delta.action === 'update' || delta.action === 'quantity_updated'
      ? '✏️ Güncellendi'
      : delta.action === 'item_removed'
      ? '🗑️ Kaldırıldı'
      : '🔄 Değiştirildi';

  const rawPrice =
    delta.unit_price != null
      ? delta.unit_price
      : (delta as any).unit_price_try != null
      ? (delta as any).unit_price_try
      : null;

  const displayPrice =
    rawPrice != null ? Number(rawPrice).toLocaleString('tr-TR') : '—';

  // Miktar: add'de "quantity", update'de "new_quantity" olabilir
  const displayQty =
    delta.quantity != null
      ? delta.quantity
      : delta.new_quantity != null
      ? delta.new_quantity
      : '?';

  return (
    <View style={styles.deltaBadge}>
      <Text style={styles.deltaAction}>{actionLabel}</Text>
      {delta.product_name ? (
        <Text style={styles.deltaName} numberOfLines={1}>
          {delta.product_name}
        </Text>
      ) : null}
      <Text style={styles.deltaDetail}>
        {displayQty} adet
        {rawPrice != null ? ` · ${displayPrice} ₺` : ''}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgCard,
    borderLeftWidth: 3,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    marginVertical: Spacing.xs,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  spinner: {
    marginRight: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
  },
  seq: {
    ...Typography.caption,
    color: Colors.textMuted,
  },
  summary: {
    ...Typography.caption,
    color: Colors.textSecondary,
    marginTop: 4,
    fontFamily: 'monospace',
  },
  deltaBadge: {
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.sm,
    padding: Spacing.sm,
    marginTop: Spacing.xs,
  },
  deltaAction: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.accentGreen,
  },
  deltaName: {
    ...Typography.bodySmall,
    color: Colors.textPrimary,
    fontWeight: '500',
    marginTop: 2,
  },
  deltaDetail: {
    ...Typography.caption,
    color: Colors.textSecondary,
    marginTop: 2,
  },
});