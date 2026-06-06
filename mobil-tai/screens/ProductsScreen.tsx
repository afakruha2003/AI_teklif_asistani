import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  SafeAreaView,
  TextInput,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { productApi } from '../services/api';
import { Product } from '../types';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';

export default function ProductsScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filtered, setFiltered] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const q = search.toLowerCase();
    let list = products;
    if (selectedCategory) list = list.filter((p) => p.category === selectedCategory);
    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.sku.toLowerCase().includes(q) ||
          (p.aliases ?? []).some((a) => a.toLowerCase().includes(q)),
      );
    }
    setFiltered(list);
  }, [search, products, selectedCategory]);

  const load = async () => {
    setIsLoading(true);
    try {
      const data = await productApi.list();
      setProducts(data);
      setFiltered(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const categories = Array.from(new Set(products.map((p) => p.category)));

  const renderProduct = ({ item }: { item: Product }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
        <View style={[styles.stockBadge, item.stock === 0 && styles.stockOut]}>
          <Text style={[styles.stockText, item.stock === 0 && styles.stockOutText]}>
            {item.stock === 0 ? 'Stok Yok' : `${item.stock} adet`}
          </Text>
        </View>
      </View>
      <Text style={styles.sku}>{item.sku}</Text>
      {item.description ? (
        <Text style={styles.desc} numberOfLines={2}>{item.description}</Text>
      ) : null}
      <View style={styles.footer}>
        <View style={styles.categoryPill}>
          <Text style={styles.categoryText}>{item.category}</Text>
        </View>
        <Text style={styles.price}>{(item.price_try ?? 0).toLocaleString('tr-TR')} ₺</Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Ürünler</Text>
        <Text style={styles.headerCount}>{filtered.length} ürün</Text>
      </View>

      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Ürün ara..."
          placeholderTextColor={Colors.textMuted}
        />
      </View>

      <View style={styles.categoryBar}>
        <TouchableOpacity
          style={[styles.catBtn, !selectedCategory && styles.catBtnActive]}
          onPress={() => setSelectedCategory(null)}
        >
          <Text style={[styles.catText, !selectedCategory && styles.catTextActive]}>
            Tümü
          </Text>
        </TouchableOpacity>
        {categories.map((c) => (
          <TouchableOpacity
            key={c}
            style={[styles.catBtn, selectedCategory === c && styles.catBtnActive]}
            onPress={() => setSelectedCategory(c === selectedCategory ? null : c)}
          >
            <Text style={[styles.catText, selectedCategory === c && styles.catTextActive]}>
              {c}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {isLoading ? (
        <View style={styles.loading}>
          <ActivityIndicator color={Colors.primary} size="large" />
        </View>
      ) : (
        <FlatList
          data={filtered}
          renderItem={renderProduct}
          keyExtractor={(p) => p.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
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
  headerTitle: { ...Typography.h2, color: Colors.primary },
  headerCount: { ...Typography.bodySmall, color: Colors.textMuted },
  searchBar: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.bgCard,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  searchInput: {
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    ...Typography.body,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  categoryBar: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
    flexWrap: 'wrap',
    backgroundColor: Colors.bgCard,
  },
  catBtn: {
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  catBtnActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  catText: { ...Typography.caption, color: Colors.textSecondary, fontWeight: '500' },
  catTextActive: { color: '#fff' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { padding: Spacing.md, gap: Spacing.sm, paddingBottom: Spacing.xxxl },
  card: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  name: { ...Typography.h3, flex: 1, lineHeight: 22 },
  sku: { ...Typography.caption, fontFamily: 'monospace', color: Colors.textMuted },
  desc: { ...Typography.bodySmall, color: Colors.textSecondary, lineHeight: 18 },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  categoryPill: {
    backgroundColor: 'rgba(76,201,240,0.1)',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: 'rgba(76,201,240,0.2)',
  },
  categoryText: { fontSize: 10, color: Colors.accent, fontWeight: '600' },
  price: { ...Typography.h3, color: Colors.accentGreen, fontWeight: '700' },
  stockBadge: {
    backgroundColor: 'rgba(6,214,160,0.1)',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: 'rgba(6,214,160,0.2)',
  },
  stockOut: {
    backgroundColor: 'rgba(230,57,70,0.1)',
    borderColor: 'rgba(230,57,70,0.2)',
  },
  stockText: { fontSize: 10, fontWeight: '600', color: Colors.accentGreen },
  stockOutText: { color: Colors.error },
});