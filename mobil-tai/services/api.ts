import { Quote, Product, KnowledgeEntry, QuoteItem } from '../types';
import { Platform } from 'react-native';
import Constants from 'expo-constants';

const isEmulator = !Constants.isDevice;

const LOCAL_IP_URL = Platform.select({
  android: isEmulator
    ? 'http://10.0.2.2:8000/api/v1'
    : 'http://192.168.1.100:8000/api/v1',
  ios: isEmulator
    ? 'http://localhost:8000/api/v1'
    : 'http://192.168.1.100:8000/api/v1',
  default: 'http://localhost:8000/api/v1',
})!;

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? LOCAL_IP_URL
).replace(/\/$/, '');

const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, { headers: DEFAULT_HEADERS, ...options });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

function normalizeQuoteItem(raw: any): QuoteItem {
  const resolvedId: string = raw.id ?? raw.item_id ?? '';
  return {
    ...raw,
    id: resolvedId,
    item_id: resolvedId,
    unit_price_try: raw.unit_price_try ?? raw.unit_price ?? 0,
    line_total_try:
      raw.line_total_try ??
      (raw.unit_price_try ?? raw.unit_price ?? 0) * (raw.quantity ?? 0),
    discount_pct: raw.discount_pct ?? 0,
  };
}

function normalizeQuote(raw: any): Quote {
  return {
    ...raw,
    id: raw.id ?? raw.quote_id ?? '',
    items: Array.isArray(raw.items) ? raw.items.map(normalizeQuoteItem) : [],
  };
}

export const quoteApi = {
  get: async (quoteId: string): Promise<Quote> => {
    const raw = await apiFetch<any>(`/quotes/${quoteId}`);
    return normalizeQuote(raw);
  },
  list: async (): Promise<Quote[]> => {
    const raw = await apiFetch<any[]>('/quotes/');
    return raw.map(normalizeQuote);
  },
};

export const productApi = {
  list: (params?: { category?: string; search?: string }) => {
    const qs = new URLSearchParams(
      (params ?? {}) as Record<string, string>,
    ).toString();
    return apiFetch<Product[]>(`/products/${qs ? `?${qs}` : ''}`);
  },
};

export const knowledgeApi = {
  list: () => apiFetch<KnowledgeEntry[]>('/knowledge/'),
};

export interface ChatStreamCallbacks {
  onSessionStart?: (sessionId: string, quoteId?: string) => void;
  onToolStart?: (tool: string, inputSummary: string, sequence: number) => void;
  onToolResult?: (
    tool: string,
    status: 'success' | 'error',
    sequence: number,
    quoteDelta?: any,
  ) => void;
  onSources?: (sources: any[]) => void;
  onTextChunk?: (text: string) => void;
  onDone?: () => void;
  onError?: (error: string) => void;
}

export function streamChat(
  question: string,
  customerId: string,
  quoteId: string | null,
  sessionId: string | null,
  callbacks: ChatStreamCallbacks,
): AbortController {
  const ctrl = new AbortController();
  const xhr = new XMLHttpRequest();

  xhr.open('POST', `${API_BASE_URL}/chat/stream`, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('Accept', 'text/event-stream');

  let seenBytes = 0;
  let lineBuffer = '';

  xhr.onprogress = () => {
    const chunk = xhr.responseText.slice(seenBytes);
    seenBytes = xhr.responseText.length;

    const text = lineBuffer + chunk;
    const lastNewline = text.lastIndexOf('\n');
    if (lastNewline === -1) {
      lineBuffer = text;
      return;
    }
    lineBuffer = text.slice(lastNewline + 1);
    const completeText = text.slice(0, lastNewline + 1);

    const blocks = completeText.split('\n\n');
    for (const block of blocks) {
      if (!block.trim()) continue;
      let eventName = '';
      let dataStr = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataStr = line.slice(5).trim();
        }
      }
      if (!dataStr || dataStr === '[DONE]') {
        if (dataStr === '[DONE]') callbacks.onDone?.();
        continue;
      }
      try {
        const payload = JSON.parse(dataStr);
        const type: string = payload.type || eventName || '';
        handleSSEEvent(type, payload, callbacks);
      } catch (_e) {
        // Yarım JSON chunk — bir sonraki onprogress'te tamamlanacak
      }
    }
  };

  xhr.onload = () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      callbacks.onDone?.();
    } else {
      callbacks.onError?.(`Sunucu hatası: ${xhr.status} ${xhr.statusText}`);
    }
  };

  xhr.onerror = () => {
    if (ctrl.signal.aborted) return;
    callbacks.onError?.('Ağ hatası oluştu. Backend çalışıyor mu?');
  };

  ctrl.signal.addEventListener('abort', () => xhr.abort());

  // SCN-010: idempotency_key her mesaj için benzersiz üretiliyor
  const idempotencyKey = sessionId
    ? `${sessionId}_${Date.now()}`
    : `anon_${Date.now()}`;

  xhr.send(
    JSON.stringify({
      message: question,
      customer_id: customerId,
      quote_id: quoteId,
      session_id: sessionId,
      idempotency_key: idempotencyKey,
    }),
  );

  return ctrl;
}

function handleSSEEvent(type: string, event: any, cb: ChatStreamCallbacks) {
  switch (type) {
    case 'session_start':
    case 'message_start':
      if (event.session_id) {
        cb.onSessionStart?.(event.session_id, event.quote_id ?? undefined);
      }
      break;

    case 'tool_start':
    case 'tool_call':
      cb.onToolStart?.(
        event.tool ?? '',
        event.input_summary ?? (event.input ? JSON.stringify(event.input) : ''),
        event.sequence ?? 0,
      );
      break;

    case 'tool_result':
      cb.onToolResult?.(
        event.tool ?? '',
        event.success === false ? 'error' : (event.status ?? 'success'),
        event.sequence ?? 0,
        event.quote_delta,
      );
      break;

    case 'sources':
      cb.onSources?.(event.sources ?? []);
      break;

    case 'text_chunk':
    case 'text':
    case 'content': {
      const text = event.text ?? event.content ?? event.chunk ?? event.delta ?? '';
      if (text) cb.onTextChunk?.(text);
      break;
    }

    case 'done':
    case 'final':
      cb.onDone?.();
      break;

    case 'error':
      cb.onError?.(event.error ?? 'Bilinmeyen hata');
      break;

    default:
      if (event.text || event.content) {
        cb.onTextChunk?.(event.text ?? event.content);
      }
      break;
  }
}