# The Blue Red — AI-Powered Quote Assistant

An AI-driven quotation system for a B2B sales platform selling barcode scanners, handheld terminals, printers, software licenses, and installation services. The system consists of three layers: a FastAPI backend, a React web admin panel, and a React Native mobile app — all sharing a single persistent quote state.

---

## Repository Structure

```
AI_teklif_asistani/
├── tai-backend/                         # FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/endpoints/
│   │   │   ├── chat.py                  # SSE streaming endpoint
│   │   │   ├── products.py              # Product CRUD
│   │   │   ├── knowledge.py             # Knowledge entry CRUD
│   │   │   ├── quotes.py                # Quote read
│   │   │   └── sessions.py              # Sessions & tool-call logs
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic settings
│   │   │   └── database.py
│   │   ├── db/session.py                # Async engine, get_db
│   │   ├── models/models.py             # SQLAlchemy ORM models
│   │   ├── schemas/schemas.py           # Pydantic I/O schemas
│   │   ├── tools/tool_implementations.py  # 6 tool contracts
│   │   └── services/
│   │       ├── chat_service.py          # LLM + fallback orchestrator
│   │       └── seed_service.py          # JSON seed loader
│   ├── seed_data/
│   │   ├── products.json                # 48 products
│   │   ├── knowledge_entries.json       # 22 knowledge entries
│   │   ├── customers.json               # 6 customers
│   │   ├── quotes.json                  # 10 quotes
│   │   ├── quote_items.json             # 8 quote items
│   │   ├── price_rules.json             # 6 price/discount rules
│   │   ├── tool_contracts.json          # Required tool-call contracts
│   │   ├── tool_call_coverage.json      # Coverage matrix
│   │   └── golden_test_scenarios.json   # 22 reference scenarios
│   ├── tests/
│   │   ├── conftest.py                  # SQLite in-memory fixtures
│   │   └── test_tools.py                # 24 tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── tai-web/                             # React admin panel (Vite)
│   ├── src/
│   │   ├── api/client.js                # Axios base client
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── UI.jsx
│   │   │   ├── ProductForm.tsx
│   │   │   └── KnowledgeForm.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Products.jsx
│   │   │   ├── Knowledge.jsx
│   │   │   ├── Quotes.jsx
│   │   │   └── Sessions.jsx
│   │   ├── services/api.ts
│   │   └── types/index.ts
│   ├── .env.example
│   ├── Dockerfile
│   └── package.json
│
├── mobil-tai/                           # React Native / Expo
│   ├── app/
│   │   ├── _layout.tsx
│   │   ├── index.tsx                    # Entry / redirect
│   │   ├── quote.tsx
│   │   ├── products.tsx
│   │   └── settings.tsx
│   ├── screens/
│   │   ├── ChatScreen.tsx               # Streaming chat UI
│   │   ├── QuoteScreen.tsx              # Shared quote view
│   │   ├── ProductsScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── components/
│   │   ├── ChatBubble.tsx
│   │   ├── QuoteItemCard.tsx
│   │   ├── SourcesPanel.tsx             # product_id / knowledge_id refs
│   │   ├── StreamingDots.tsx
│   │   └── ToolCallBadge.tsx
│   ├── store/
│   │   ├── chatStore.ts
│   │   └── quoteStore.ts
│   ├── services/api.ts
│   ├── types/index.ts
│   └── package.json
│
├── docker-compose.yml                   # Backend + PostgreSQL + Web
├── .env.example
├── AI_USAGE.md
├── KNOWN_LIMITATIONS.md
└── README.md
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- OpenAI API key 

### 1. Environment Setup

```bash
cp .env.example .env
# Optionally add your OPENAI_API_KEY — leave empty to run in fallback mode
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://tai:tai_secret@db:5432/tai_db` | Async PostgreSQL |
| `OPENAI_API_KEY` | *(empty)* | If empty, fallback mode activates |
| `OPENAI_MODEL` | `gemini-1.5-flash` | Model to use |
| `SECRET_KEY` | `changeme` | Change in production |
| `SEED_ON_STARTUP` | `true` | Auto-load seed data on boot |

### 2. Backend + Web (Docker Compose)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Web Admin Panel | http://localhost:3000 |

### 3. Mobile App (Expo)

```bash
cd mobil-tai
npm install
npx expo start
```

On a **physical device**, update the API base URL to your machine's local IP:

```bash
# mobil-tai/.env
EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:8000
```

| Option | Command |
|--------|---------|
| Expo Go (scan QR) | `npx expo start` |
| iOS Simulator | `npx expo run:ios` |
| Android Emulator | `npx expo run:android` |

**Platform requirements:**

| Platform | Requirement |
|----------|-------------|
| iOS | Xcode 14+, macOS |
| Android | Android Studio, Java 17 |
| Physical device | Expo Go app |

---

## Running Tests

```bash
cd tai-backend
pip install -r requirements.txt aiosqlite
pytest -v
```

Expected: **24 passed**

Test coverage includes:

- Retrieval & grounding — correct product/knowledge sources returned
- Tool-call selection — correct function called per scenario
- Mutation behavior — add, update, replace correctly modify DB state
- Duplicate & idempotency — repeated requests do not double-increment quantity
- Price & stock rules — over-limit or out-of-stock products are not added
- Fallback mode — sourced response without an API key
- Web/mobile shared state — same quote consistent across both surfaces

---

## Web Admin Panel

Built with React + Vite. Connects to the backend REST API.

**Local development (without Docker):**

```bash
cd tai-web
cp .env.example .env      # set VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev               # http://localhost:3000
```

**Pages:**

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | System overview |
| Products | `/products` | List, add, edit, delete products |
| Knowledge | `/knowledge` | Manage policy and compliance entries |
| Quotes | `/quotes` | View active quote state in real time |
| Sessions | `/sessions` | Browse chat sessions and tool-call logs |

The Quotes page reflects mutations made from the mobile app in real time — both surfaces read from the same `quote_id`.

---

## Mobile App

Built with React Native + Expo. Shares quote state with the web panel via the backend.

**Screens:**

| Screen | File | Description |
|--------|------|-------------|
| Chat | `screens/ChatScreen.tsx` | Ask product/policy questions, receive streaming AI responses |
| Quote | `screens/QuoteScreen.tsx` | View the shared quote draft; same state as web |
| Products | `screens/ProductsScreen.tsx` | Browse available products |
| Settings | `screens/SettingsScreen.tsx` | API URL and session configuration |

**Key components:**

| Component | Description |
|-----------|-------------|
| `ChatBubble.tsx` | Renders user and assistant messages |
| `StreamingDots.tsx` | Animated indicator while SSE response streams |
| `SourcesPanel.tsx` | Displays `product_id` / `knowledge_id` source references |
| `ToolCallBadge.tsx` | Shows which tool was called and its result |
| `QuoteItemCard.tsx` | Single quote line item with status (active / replaced / removed) |

State is managed via `store/chatStore.ts` and `store/quoteStore.ts`.

---

## API Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| GET | `/api/v1/products/` | List products |
| POST | `/api/v1/products/` | Add product |
| GET/PATCH/DELETE | `/api/v1/products/{id}` | Read / update / delete product |
| GET | `/api/v1/knowledge/` | List knowledge entries |
| POST | `/api/v1/knowledge/` | Add knowledge entry |
| GET/PATCH/DELETE | `/api/v1/knowledge/{id}` | Read / update / delete knowledge entry |
| GET | `/api/v1/quotes/` | List quotes |
| POST | `/api/v1/quotes/` | Create quote |
| GET | `/api/v1/quotes/{id}` | Read quote |
| GET | `/api/v1/sessions/` | List sessions |
| GET | `/api/v1/sessions/{id}/messages` | Session messages |
| GET | `/api/v1/sessions/{id}/tool-calls` | Tool-call logs |

### Chat Streaming — Example Request

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "2000 TL altında kablosuz barkod okuyucu önerir misin?",
    "quote_id": "quote-001",
    "customer_id": "customer-001",
    "max_price_try": 2000
  }'
```

### SSE Event Types

| Event | Description |
|-------|-------------|
| `session_start` | Session ID and mode (llm / fallback) |
| `tool_start` | Tool name, input summary, sequence number |
| `tool_result` | Success / error, quote delta if mutation occurred |
| `text_chunk` | Streamed text chunk to the user |
| `done` | Response complete, sources list |
| `error` | Controlled error event |

---

## Architectural Decisions

### 1. Resource Finding: SQL + In-Memory Text Scoring

Active products are pre-filtered in PostgreSQL by category, price, and stock. Remaining records are scored in memory: name match +10, description +3, Turkish alias +8, tag +5. Top N results are returned sorted by score.

Embeddings were not chosen: cost and latency are disproportionate for 48 products and 22 knowledge entries. The `aliases` field covers most semantic search needs. If needed, `pgvector` can be added without changing the service interface.

### 2. Function Call Orchestration: Hybrid

**With LLM (OPENAI_API_KEY set):** OpenAI function calling + SSE streaming agentic loop. The model decides which tool to call and when. Business rules such as price limits are enforced inside tool implementations — not delegated to the LLM.

**Without LLM:** Deterministic intent detection + direct tool dispatch. "policy" → `get_knowledge_entries`, "product"/"price" → `search_products`; both signals → both tools. `max_price_try` is always injected inside `dispatch_tool()` regardless of mode.

### 3. Fallback Mode

`stream_chat_fallback()` activates when `OPENAI_API_KEY` is empty. Every policy response includes at least one `knowledge_id` source. Out-of-stock products are not recommended; price limits are not exceeded. Mutation tools work identically. The SSE event format is identical to LLM mode — the client does not need to distinguish modes.

### 4. Idempotency Strategy

The client generates its own `idempotency_key`. Recommended format:

```
{session_id}:{sha256(message)[:8]}:{unix_timestamp // 300}
```

The same message within a 5-minute window produces the same key. Server-side, a `UNIQUE` constraint on `ToolCallLog` prevents race conditions. If a key already exists, the mutation is skipped and the current quote state is returned.

### 5. Quote Mutation Model

All mutations execute atomically inside `BEGIN SAVEPOINT`.

| Operation | DB Representation |
|-----------|------------------|
| Add product | `QuoteItem` created with `status=active` |
| Add same product again | Existing `active` row's `quantity` incremented; no new row |
| Update quantity | `quantity` updated |
| Remove (`quantity=0`) | `status=removed` — no physical deletion |
| Replace with alternative | Old row `status=replaced` + `replaced_by_item_id`; new row `status=active` |

Soft-delete preserves the full quote history and audit trail. `get_quote` returns only `status=active` rows.

---

