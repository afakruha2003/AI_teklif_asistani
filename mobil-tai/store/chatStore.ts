import { create } from 'zustand';
import { ChatStore, Message } from '../types';

export const useChatStore = create<ChatStore>()((set) => ({
  messages: [],
  sessionId: null,
  isStreaming: false,
  customerId: 'CUST-IST-001', 
  quoteId: null,

  addMessage: (message: Message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateLastMessage: (updater) =>
    set((s) => {
      if (s.messages.length === 0) return s;
      const msgs = [...s.messages];
      msgs[msgs.length - 1] = updater(msgs[msgs.length - 1]);
      return { messages: msgs };
    }),

  setStreaming: (val) => set({ isStreaming: val }),
  setSessionId: (id) => set({ sessionId: id }),
  setQuoteId: (id) => set({ quoteId: id }),
  
  setCustomerId: (id) => set({ customerId: id }), 

  clearChat: () =>
    set({ messages: [], sessionId: null, isStreaming: false, quoteId: null }),
}));