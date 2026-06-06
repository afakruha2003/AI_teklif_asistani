import type { Product, ProductCreate, KnowledgeEntry, KnowledgeEntryCreate, Quote, ChatSession, ChatMessage, ToolCallLog, ApiResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API Error: ${response.status} - ${error}`)
  }
  const json = await response.json()
  // Eğer backend veriyi direct [] veya {} yerine ApiResponse sarmalı { data: ... } ile dönüyorsa onu çıkartıyoruz
  if (json && typeof json === 'object' && 'data' in json) {
    return json.data as T
  }
  return json as T
}

// Products
export const productApi = {
  list: async (): Promise<Product[]> => {
    const res = await fetch(`${API_BASE}/products/`)
    return handleResponse(res)
  },

  get: async (id: string): Promise<Product> => {
    const res = await fetch(`${API_BASE}/products/${id}`)
    return handleResponse(res)
  },

  create: async (data: ProductCreate): Promise<Product> => {
    const res = await fetch(`${API_BASE}/products/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  update: async (id: string, data: Partial<ProductCreate>): Promise<Product> => {
    const res = await fetch(`${API_BASE}/products/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  delete: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/products/${id}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error(`Failed to delete product: ${res.status}`)
  },
}

// Knowledge Entries
export const knowledgeApi = {
  list: async (): Promise<KnowledgeEntry[]> => {
    const res = await fetch(`${API_BASE}/knowledge/`)
    return handleResponse(res)
  },

  get: async (id: string): Promise<KnowledgeEntry> => {
    const res = await fetch(`${API_BASE}/knowledge/${id}`)
    return handleResponse(res)
  },

  create: async (data: KnowledgeEntryCreate): Promise<KnowledgeEntry> => {
    const res = await fetch(`${API_BASE}/knowledge/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  update: async (id: string, data: Partial<KnowledgeEntryCreate>): Promise<KnowledgeEntry> => {
    const res = await fetch(`${API_BASE}/knowledge/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  delete: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/knowledge/${id}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error(`Failed to delete knowledge entry: ${res.status}`)
  },
}

// Quotes
export const quoteApi = {
  list: async (): Promise<Quote[]> => {
    const res = await fetch(`${API_BASE}/quotes/`)
    return handleResponse(res)
  },

  get: async (id: string): Promise<Quote> => {
    const res = await fetch(`${API_BASE}/quotes/${id}`)
    return handleResponse(res)
  },

  create: async (customerId?: string): Promise<Quote> => {
    const res = await fetch(`${API_BASE}/quotes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId }),
    })
    return handleResponse(res)
  },
}

// Sessions
export const sessionApi = {
  list: async (): Promise<ChatSession[]> => {
    const res = await fetch(`${API_BASE}/sessions/`)
    return handleResponse(res)
  },

  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`)
    return handleResponse(res)
  },

  getToolCalls: async (sessionId: string): Promise<ToolCallLog[]> => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/tool-calls`)
    return handleResponse(res)
  },
}

// Polling for quote updates (for real-time sync with mobile)
export const pollQuoteUpdates = async (
  quoteId: string,
  interval: number = 2000,
  maxAttempts: number = 150, // 5 minutes
  onUpdate: (quote: Quote) => void
): Promise<void> => {
  let lastUpdate = new Date()
  let attempts = 0

  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(timer)
        resolve()
        return
      }

      try {
        const quote = await quoteApi.get(quoteId)
        if (new Date(quote.updated_at) > lastUpdate) {
          lastUpdate = new Date(quote.updated_at)
          onUpdate(quote)
        }
      } catch (err) {
        clearInterval(timer)
        reject(err)
      }
    }, interval)
  })
}