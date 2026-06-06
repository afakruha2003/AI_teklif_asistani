import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  LayoutAnimation,
} from 'react-native';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';
import { Source } from '../types';

interface Props {
  sources: Source[];
}

export const SourcesPanel: React.FC<Props> = ({ sources }) => {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  const toggle = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((v) => !v);
  };

  const products = sources.filter((s) => s.type === 'product');
  const knowledge = sources.filter((s) => s.type === 'knowledge');

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.header} onPress={toggle} activeOpacity={0.7}>
        <Text style={styles.icon}>📎</Text>
        <Text style={styles.label}>
          {sources.length} kaynak
          {products.length > 0 && ` · ${products.length} ürün`}
          {knowledge.length > 0 && ` · ${knowledge.length} bilgi`}
        </Text>
        <Text style={styles.chevron}>{expanded ? '▲' : '▼'}</Text>
      </TouchableOpacity>

      {expanded && (
        <View style={styles.list}>
          {products.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Ürünler</Text>
              {products.map((s) => (
                <SourceChip key={s.id} source={s} />
              ))}
            </>
          )}
          {knowledge.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Bilgi Kaynakları</Text>
              {knowledge.map((s) => (
                <SourceChip key={s.id} source={s} />
              ))}
            </>
          )}
        </View>
      )}
    </View>
  );
};

const SourceChip: React.FC<{ source: Source }> = ({ source }) => {
  const isProduct = source.type === 'product';
  return (
    <View style={[styles.chip, isProduct ? styles.chipProduct : styles.chipKnowledge]}>
      <Text style={styles.chipIcon}>{isProduct ? '📦' : '📄'}</Text>
      <View style={styles.chipText}>
        <Text style={styles.chipName} numberOfLines={1}>
          {source.name}
        </Text>
        <Text style={styles.chipId}>{source.id}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: Spacing.sm,
    borderRadius: Radius.md,
    backgroundColor: Colors.bgInput,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    gap: Spacing.xs,
  },
  icon: {
    fontSize: 12,
  },
  label: {
    flex: 1,
    ...Typography.caption,
    color: Colors.textSecondary,
    fontWeight: '500',
  },
  chevron: {
    fontSize: 10,
    color: Colors.textMuted,
  },
  list: {
    paddingHorizontal: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.xs,
  },
  sectionTitle: {
    ...Typography.caption,
    color: Colors.textMuted,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: Spacing.xs,
    marginBottom: 4,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 6,
    gap: Spacing.sm,
    marginBottom: 4,
  },
  chipProduct: {
    backgroundColor: 'rgba(76, 201, 240, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(76, 201, 240, 0.2)',
  },
  chipKnowledge: {
    backgroundColor: 'rgba(244, 162, 97, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(244, 162, 97, 0.2)',
  },
  chipIcon: {
    fontSize: 14,
  },
  chipText: {
    flex: 1,
  },
  chipName: {
    ...Typography.bodySmall,
    color: Colors.textPrimary,
    fontWeight: '500',
  },
  chipId: {
    ...Typography.caption,
    color: Colors.textMuted,
    fontFamily: 'monospace',
  },
});
