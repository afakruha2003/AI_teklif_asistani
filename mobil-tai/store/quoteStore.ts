import { create } from 'zustand';
import { QuoteStore, Quote } from '../types';
import { quoteApi } from '../services/api';

export const useQuoteStore = create<QuoteStore>((set) => ({
  quote: null,
  isLoading: false,

  fetchQuote: async (quoteId: string) => {
    set({ isLoading: true });
    try {
      const quote = await quoteApi.get(quoteId);
      set({ quote, isLoading: false });
    } catch (err) {
      console.error('Quote fetch error:', err);
      set({ isLoading: false });
    }
  },

  setQuote: (quote: Quote) => set({ quote }),
}));
