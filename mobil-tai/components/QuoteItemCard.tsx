import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';
import { QuoteItem } from '../types';

interface Props {
  item: QuoteItem;
}

const STATUS_CONFIG = {
  active: { label: 'Aktif', color: Colors.statusActive },
  replaced: { label: 'Değiştirildi', color: Colors.statusReplaced },
  passive: { label: 'Pasif', color: Colors.statusPassive },
};

export const QuoteItemCard: React.FC<Props> = ({ item }) => {
  const statusCfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.passive;
  const isActive = item.status === 'active';

  return (
    <View style={[styles.card, !isActive && styles.cardInactive]}>
      <View style={styles.header}>
        <View style={styles.nameRow}>
          <Text style={[styles.name, !isActive && styles.nameInactive]} numberOfLines={2}>
            {item.product_name}
          </Text>
          <View style={[styles.statusBadge, { backgroundColor: statusCfg.color + '20' }]}>
            <Text style={[styles.statusText, { color: statusCfg.color }]}>
              {statusCfg.label}
            </Text>
          </View>
        </View>
        <Text style={styles.sku}>{item.sku}</Text>
      </View>

      <View style={styles.footer}>
        <View style={styles.qtyRow}>
          <Text style={styles.label}>Adet</Text>
          <Text style={styles.value}>{item.quantity}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.qtyRow}>
          <Text style={styles.label}>Birim Fiyat</Text>
          <Text style={styles.value}>
            {item.unit_price.toLocaleString('tr-TR')} ₺
          </Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.qtyRow}>
          <Text style={styles.label}>Toplam</Text>
          <Text style={[styles.value, styles.total, !isActive && styles.lineThrough]}>
            {item.total_price.toLocaleString('tr-TR')} ₺
          </Text>
        </View>
      </View>

      {item.discount && item.discount > 0 ? (
        <View style={styles.discountBadge}>
          <Text style={styles.discountText}>%{item.discount} indirim uygulandı</Text>
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    marginVertical: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardInactive: {
    opacity: 0.55,
    borderStyle: 'dashed',
  },
  header: {
    marginBottom: Spacing.md,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  name: {
    ...Typography.h3,
    flex: 1,
    lineHeight: 22,
  },
  nameInactive: {
    color: Colors.textMuted,
  },
  sku: {
    ...Typography.caption,
    fontFamily: 'monospace',
    marginTop: 4,
  },
  statusBadge: {
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  qtyRow: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
  },
  label: {
    ...Typography.caption,
    color: Colors.textMuted,
  },
  value: {
    ...Typography.body,
    fontWeight: '600',
    color: Colors.textPrimary,
  },
  total: {
    color: Colors.accentGreen,
    fontSize: 15,
  },
  lineThrough: {
    textDecorationLine: 'line-through',
    color: Colors.textMuted,
  },
  divider: {
    width: 1,
    height: 32,
    backgroundColor: Colors.border,
  },
  discountBadge: {
    marginTop: Spacing.sm,
    backgroundColor: 'rgba(244, 162, 97, 0.1)',
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  discountText: {
    fontSize: 11,
    color: Colors.accentOrange,
    fontWeight: '500',
  },
});
