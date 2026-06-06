export interface Product {
  id: string
  name: string
  description?: string
  category: string
  price_try: number
  stock: number
  sku?: string
  aliases: string[]
  tags: string[]
  is_active: boolean
  alternative_product_id?: string
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  id?: string
  name: string
  description?: string
  category: string
  price_try: number
  stock?: number
  sku?: string
  aliases?: string[]
  tags?: string[]
  is_active?: boolean
  alternative_product_id?: string
}

export interface KnowledgeEntry {
  id: string
  title: string
  content: string
  category: string
  tags: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface KnowledgeEntryCreate {
  id?: string
  title: string
  content: string
  category: string
  tags?: string[]
  is_active?: boolean
}

export interface QuoteItem {
  id: string
  quote_id: string
  product_id: string
  quantity: number
  unit_price_try: number
  discount_pct: number
  status: string
  is_backorder: boolean
  replaced_by_item_id?: string
  created_at: string
  updated_at: string
  product?: Product
}

export interface Quote {
  id: string
  customer_id?: string
  status: string
  notes?: string
  created_at: string
  updated_at: string
  items: QuoteItem[]
  total_try: number
}

export interface ChatSession {
  id: string
  quote_id?: string
  customer_id?: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  session_id: string
  role: string
  content: string
  created_at: string
}

export interface ToolCallLog {
  id: string
  session_id: string
  tool_name: string
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  status: string
  quote_delta?: Record<string, unknown>
  sequence_num: number
  duration_ms?: number
  idempotency_key?: string
  created_at: string
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}
