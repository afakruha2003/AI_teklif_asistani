import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  ScrollView,
} from 'react-native';
import { useChatStore } from '../store/chatStore';
import { useQuoteStore } from '../store/quoteStore';
import { API_BASE_URL } from '../services/api';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';

export default function SettingsScreen() {
  const { customerId, quoteId, clearChat, setQuoteId } = useChatStore();
  const { fetchQuote, quote } = useQuoteStore();

  const [draftQuoteId, setDraftQuoteId] = useState(quoteId ?? '');

  const applyQuoteId = async () => {
    if (!draftQuoteId.trim()) return;
    const id = draftQuoteId.trim();
    setQuoteId(id);
    await fetchQuote(id);
    Alert.alert('Başarılı', `Teklif #${id} yüklendi.`);
  };

  const clearAll = () => {
    Alert.alert('Sohbeti Temizle', 'Tüm mesajlar silinecek.', [
      { text: 'İptal', style: 'cancel' },
      {
        text: 'Temizle',
        style: 'destructive',
        onPress: () => clearChat(),
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Ayarlar</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* API Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Backend Bağlantısı</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>API URL</Text>
            <Text style={styles.value} numberOfLines={1}>{API_BASE_URL}</Text>
          </View>
          <Text style={styles.hint}>
            EXPO_PUBLIC_API_URL env değişkeniyle değiştirilebilir.
          </Text>
        </View>

        {/* Customer */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Müşteri</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Customer ID</Text>
            <Text style={styles.value}>{customerId}</Text>
          </View>
        </View>

        {/* Quote */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Teklif</Text>
          {quote && (
            <View style={styles.infoRow}>
              <Text style={styles.label}>Aktif Teklif</Text>
              <Text style={styles.value}>{quote.id}</Text>
            </View>
          )}
          <Text style={styles.inputLabel}>Teklif ID'si ile yükle</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              value={draftQuoteId}
              onChangeText={setDraftQuoteId}
              placeholder="quote_001"
              placeholderTextColor={Colors.textMuted}
              autoCapitalize="none"
            />
            <TouchableOpacity style={styles.applyBtn} onPress={applyQuoteId}>
              <Text style={styles.applyText}>Yükle</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.hint}>
            Web panelindeki teklif ID'sini girerek aynı durumu mobilde görüntüleyin.
          </Text>
        </View>

        {/* Danger zone */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Sohbet</Text>
          <TouchableOpacity style={styles.dangerBtn} onPress={clearAll}>
            <Text style={styles.dangerText}>🗑 Sohbeti Temizle</Text>
          </TouchableOpacity>
        </View>

        {/* Version */}
        <Text style={styles.version}>TAI Mobil v1.0.0 · The Blue Red</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    backgroundColor: Colors.bgCard,
  },
  headerTitle: { ...Typography.h2, color: Colors.primary },
  content: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxxl },
  section: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sectionTitle: {
    ...Typography.bodySmall,
    fontWeight: '700',
    color: Colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: Spacing.xs,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.xs,
  },
  label: { ...Typography.body, color: Colors.textSecondary },
  value: {
    ...Typography.body,
    fontWeight: '600',
    color: Colors.textPrimary,
    maxWidth: '55%',
    textAlign: 'right',
  },
  inputLabel: { ...Typography.bodySmall, color: Colors.textSecondary },
  inputRow: { flexDirection: 'row', gap: Spacing.sm },
  input: {
    flex: 1,
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    ...Typography.body,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  applyBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.lg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  applyText: { ...Typography.body, color: '#fff', fontWeight: '600' },
  hint: { ...Typography.caption, color: Colors.textMuted, lineHeight: 16 },
  dangerBtn: {
    backgroundColor: 'rgba(230,57,70,0.1)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(230,57,70,0.3)',
  },
  dangerText: { ...Typography.body, color: Colors.error, fontWeight: '600' },
  version: {
    ...Typography.caption,
    textAlign: 'center',
    color: Colors.textMuted,
    marginTop: Spacing.lg,
  },
});
