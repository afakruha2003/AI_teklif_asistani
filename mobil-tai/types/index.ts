export type MessageRole = 'user' | 'assistant';

export interface Source {
  type: 'product' | 'knowledge';
  id: string;
  name: string;
  detail?: string;
}

export interface QuoteDelta {
  action: 'add' | 'update' | 'replace' | 'item_removed' | 'item_replaced' | 'quantity_updated';
  item_id?: string;
  product_id?: string;
  product_name?: string;
  quantity?: number;
  unit_price?: number;
  unit_price_try?: number;
  quote_id?: string;
  old_item_id?: string;
  new_item_id?: string;
  old_quantity?: number;
  new_quantity?: number;
}

export interface ToolCallEvent {
  tool: string;
  input_summary: string;
  sequence: number;
  status: 'running' | 'success' | 'error';
  quote_delta?: QuoteDelta;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[];
  toolCalls?: ToolCallEvent[];
  quoteDelta?: QuoteDelta;
  isStreaming?: boolean;
  timestamp: Date;
}

export type QuoteItemStatus = 'active' | 'replaced' | 'passive' | 'removed';

export interface QuoteItem {
  id: string;
  item_id?: string;
  product_id: string;
  product_name: string;
  sku?: string;
  quantity: number;
  unit_price_try: number;
  line_total_try: number;
  discount_pct: number;
  status: QuoteItemStatus;
  is_backorder?: boolean;
}

export interface Quote {
  id: string;
  customer_id: string;
  customer_name?: string;
  status: string;
  items: QuoteItem[];
  total_try: number;
  currency?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  price_try: number;
  stock: number;
  description?: string;
  aliases?: string[];
  tags?: string[];
}

export interface KnowledgeEntry {
  id: string;
  title: string;
  category: string;
  content: string;
  tags?: string[];
}

export type SSEEventType =
  | 'session_start'
  | 'message_start'
  | 'tool_start'
  | 'tool_result'
  | 'sources'
  | 'text_chunk'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  session_id?: string;
  tool?: string;
  input_summary?: string;
  sequence?: number;
  status?: 'success' | 'error';
  quote_delta?: QuoteDelta;
  sources?: Source[];
  text?: string;
  error?: string;
}

export interface ChatStore {
  messages: Message[];
  sessionId: string | null;
  isStreaming: boolean;
  customerId: string;
  quoteId: string | null;
  addMessage: (message: Message) => void;
  updateLastMessage: (updater: (msg: Message) => Message) => void;
  setStreaming: (val: boolean) => void;
  setSessionId: (id: string) => void;
  setQuoteId: (id: string) => void;
  clearChat: () => void;
  setCustomerId: (id: string) => void;
}

export interface QuoteStore {
  quote: Quote | null;
  isLoading: boolean;
  fetchQuote: (quoteId: string) => Promise<void>;
  setQuote: (quote: Quote) => void;
}