import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { useChatStore } from '../store/chatStore';
import { useQuoteStore } from '../store/quoteStore';
import { streamChat } from '../services/api';
import { Message, ToolCallEvent, Source } from '../types';
import { ChatBubble } from '../components/ChatBubble';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';

let msgCounter = 0;
const uid = () => `msg_${++msgCounter}_${Date.now()}`;

const SIMULATION_CUSTOMERS = [
  {
    id: "CUST-IST-001",
    name: "Mavi Kırmızı Market A.Ş.",
    city: "İstanbul",
    ruleInfo: "Stok Katı Kural (allow_backorder: false)"
  },
  {
    id: "CUST-ANK-002",
    name: "Ankara Toptan Depo Ltd.",
    city: "Ankara",
    ruleInfo: "Beklemeli Sipariş Serbest (allow_backorder: true)"
  },
  {
    id: "CUST-IZM-003",
    name: "İzmir Fresh Gıda",
    city: "İzmir",
    ruleInfo: "Standart Fiyatlandırma (allow_backorder: false)"
  }
];

const QUICK_QUESTIONS = [
  'Kablosuz barkod okuyucu var mı?',
  'İade politikası nedir?',
  'Teklif durumumu göster',
  '500 TL altı el terminali öner',
];

export default function ChatScreen() {
  const [input, setInput] = useState('');
  const listRef = useRef<FlatList>(null);
  const abortRef = useRef<AbortController | null>(null);

  const {
    messages,
    isStreaming,
    customerId,
    quoteId,
    addMessage,
    updateLastMessage,
    setStreaming,
    setSessionId,
    setQuoteId,
    setCustomerId,
  } = useChatStore();

  const { fetchQuote } = useQuoteStore();

  useEffect(() => {
    if (!customerId && setCustomerId) {
      setCustomerId(SIMULATION_CUSTOMERS[0].id);
    }
  }, [customerId, setCustomerId]);

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages.length]);

const sendMessage = useCallback(
    async (text?: string) => {
      const question = (text ?? input).trim();
      if (!question || isStreaming) return;

      setInput('');

      // State kilitlenmesini çözmek için store'un güncel anlık durumlarını doğrudan çekiyoruz:
      const currentStore = useChatStore.getState();
      const currentCustomerId = currentStore.customerId;
      const currentQuoteId = currentStore.quoteId;

      addMessage({
        id: uid(),
        role: 'user',
        content: question,
        timestamp: new Date(),
      });

      const assistantId = uid();
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        toolCalls: [],
        sources: [],
        timestamp: new Date(),
      });

      setStreaming(true);

      // streamChat'e anlık ve taze ID değerlerini parametre olarak paslıyoruz:
      abortRef.current = streamChat(question, currentCustomerId, currentQuoteId, {
        onSessionStart: (sessionId: string, newQuoteId?: string) => {
          setSessionId(sessionId);
          // Store'daki güncel taze quoteId'yi tekrar kontrol et
          const freshQuoteId = useChatStore.getState().quoteId;
          if (newQuoteId && !freshQuoteId) {
            setQuoteId(newQuoteId);
            fetchQuote(newQuoteId);
          }
        },

        onToolStart: (tool, inputSummary, sequence) => {
          updateLastMessage((msg: Message) => {
            const newTool: ToolCallEvent = {
              tool,
              input_summary: inputSummary,
              sequence,
              status: 'running',
            };
            return {
              ...msg,
              toolCalls: [...(msg.toolCalls ?? []), newTool],
            };
          });
        },

        onToolResult: (tool, status, sequence, quoteDelta) => {
          updateLastMessage((msg: Message) => {
            const toolCalls = (msg.toolCalls ?? []).map((tc) =>
              tc.sequence === sequence
                ? { ...tc, status, quote_delta: quoteDelta }
                : tc,
            );
            return { ...msg, toolCalls };
          });

          // FIX: closure'a düşmemek için store'dan en güncel quoteId'yi çekiyoruz
          const activeQuoteId = useChatStore.getState().quoteId || quoteDelta?.quote_id;
          
          if (activeQuoteId) {
            if (quoteDelta?.quote_id && useChatStore.getState().quoteId !== quoteDelta.quote_id) {
              setQuoteId(quoteDelta.quote_id);
            }
            fetchQuote(activeQuoteId);
          }
        },

        onSources: (sources: Source[]) => {
          updateLastMessage((msg: Message) => ({ ...msg, sources }));
        },

        onTextChunk: (chunk) => {
          updateLastMessage((msg: Message) => ({
            ...msg,
            content: msg.content + chunk,
            isStreaming: true,
          }));
        },

        onDone: () => {
          updateLastMessage((msg: Message) => ({ ...msg, isStreaming: false }));
          setStreaming(false);
          abortRef.current = null;
          
          // Akış başarıyla tamamlandığında güncel teklifi bir kez daha tazeleyelim
          const finalQuoteId = useChatStore.getState().quoteId;
          if (finalQuoteId) {
            fetchQuote(finalQuoteId);
          }
        },

        onError: (error) => {
          updateLastMessage((msg: Message) => ({
            ...msg,
            content: msg.content || `⚠️ Hata oluştu: ${error}`,
            isStreaming: false,
          }));
          setStreaming(false);
          abortRef.current = null;
        },
      });
    },
    [input, isStreaming, addMessage, setStreaming, setSessionId, updateLastMessage, fetchQuote, setQuoteId]
  );

  const cancelStream = () => {
    abortRef.current?.abort();
    updateLastMessage((msg: Message) => ({ ...msg, isStreaming: false }));
    setStreaming(false);
  };

  const renderItem = ({ item }: { item: Message }) => (
    <ChatBubble message={item} />
  );

  const currentCustomer = SIMULATION_CUSTOMERS.find(c => c.id === customerId) || SIMULATION_CUSTOMERS[0];

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>TAI Asistan</Text>
            <Text style={styles.headerSub}>{currentCustomer.name} ({currentCustomer.city})</Text>
          </View>
          {isStreaming && (
            <TouchableOpacity style={styles.cancelBtn} onPress={cancelStream}>
              <Text style={styles.cancelText}>Durdur</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Müşteri Simülasyon Seçici */}
        {messages.length === 0 && (
          <View style={styles.selectorBar}>
            <Text style={styles.selectorTitle}>Test Etmek İstediğiniz Müşteriyi Seçin:</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.customerScroll}>
              {SIMULATION_CUSTOMERS.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.customerBtn, customerId === c.id && styles.activeBtn]}
                  onPress={() => setCustomerId && setCustomerId(c.id)}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.customerBtnText, customerId === c.id && styles.activeText]}>
                    {c.name}
                  </Text>
                  <Text style={[styles.customerBtnSub, customerId === c.id && styles.activeSubText]}>
                    {c.ruleInfo}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Messages */}
        {messages.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>🤖</Text>
            <Text style={styles.emptyTitle}>Merhaba!</Text>
            <Text style={styles.emptyDesc}>
              Seçili müşterinin kurallarına göre ürün, stok, fiyat ve teklif yönetimi yapabilirsiniz.
            </Text>
            <View style={styles.quickList}>
              {QUICK_QUESTIONS.map((q) => (
                <TouchableOpacity
                  key={q}
                  style={styles.quickBtn}
                  onPress={() => sendMessage(q)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.quickText}>{q}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            renderItem={renderItem}
            keyExtractor={(m) => m.id}
            contentContainerStyle={styles.messageList}
            showsVerticalScrollIndicator={false}
          />
        )}

        {/* Input bar */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder={`${currentCustomer.name} için bir şeyler yazın...`}
            placeholderTextColor={Colors.textMuted}
            multiline
            maxLength={1000}
            onSubmitEditing={() => sendMessage()}
            editable={!isStreaming}
          />
          <TouchableOpacity
            style={[styles.sendBtn, (isStreaming || !input.trim()) && styles.sendBtnDisabled]}
            onPress={() => sendMessage()}
            disabled={isStreaming || !input.trim()}
            activeOpacity={0.8}
          >
            <Text style={styles.sendIcon}>↑</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  container: {
    flex: 1,
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
    ...Typography.h3,
    color: Colors.primary,
    fontWeight: '700',
  },
  headerSub: {
    ...Typography.caption,
    marginTop: 2,
    color: Colors.textSecondary,
  },
  selectorBar: {
    padding: Spacing.md,
    backgroundColor: Colors.bgCard,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  selectorTitle: {
    ...Typography.caption,
    fontWeight: 'bold',
    color: Colors.textSecondary,
    marginBottom: Spacing.sm,
  },
  customerScroll: {
    flexDirection: 'row',
    gap: Spacing.sm,
    paddingRight: Spacing.md,
  },
  customerBtn: {
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    minWidth: 180,
  },
  activeBtn: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  customerBtnText: {
    ...Typography.bodySmall,
    fontWeight: '600',
    color: Colors.textPrimary,
  },
  customerBtnSub: {
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 2,
  },
  activeText: {
    color: '#fff',
  },
  activeSubText: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  cancelBtn: {
    backgroundColor: Colors.bgInput,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cancelText: {
    ...Typography.bodySmall,
    color: Colors.textSecondary,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.xxl,
    gap: Spacing.md,
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
  quickList: {
    width: '100%',
    gap: Spacing.sm,
    marginTop: Spacing.md,
  },
  quickBtn: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  quickText: {
    ...Typography.body,
    color: Colors.textSecondary,
  },
  messageList: {
    paddingVertical: Spacing.md,
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    gap: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.bgCard,
  },
  input: {
    flex: 1,
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.lg,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    ...Typography.body,
    color: Colors.textPrimary,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    backgroundColor: Colors.bgInput,
  },
  sendIcon: {
    fontSize: 20,
    color: '#fff',
    fontWeight: '700',
  },
});