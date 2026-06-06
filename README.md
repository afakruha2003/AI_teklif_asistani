# The Blue Red — AI-Powered Quote Assistant

An AI-driven quotation system for a sales platform selling barcodes scanners, handheld terminals, printers, software licenses, and installation services to B2B customers.

---

## Quick Start

```bash
git clone https://github.com/afakruha2003/AI_teklif_asistani
cd tai-backend
cp .env.example .env
# Optional: add OPENAI_API_KEY (fallback mode works if missing)

# Copy JSON files to seed_data/ directory:
# products.json, knowledge_entries.json, customers.json,
# quotes.json, quote_items.json, price_rules.json

docker compose up --build
```

- **Backend API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

---

## Running Tests

```bash
pip install -r requirements.txt aiosqlite
pytest -v
```

Expected output: **24 passed**

---

## API Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| GET | `/api/v1/products/` | List products |
| POST | `/api/v1/products/` | Add product |
| GET/PATCH/DELETE | `/api/v1/products/{id}` | Read/update/delete product |
| GET | `/api/v1/knowledge/` | List knowledge entries |
| POST | `/api/v1/knowledge/` | Add knowledge entry |
| GET/PATCH/DELETE | `/api/v1/knowledge/{id}` | Read/update/delete knowledge entry |
| GET | `/api/v1/quotes/` | List quotes |
| POST | `/api/v1/quotes/` | Create quote |
| GET | `/api/v1/quotes/{id}` | Read quote |
| GET | `/api/v1/sessions/` | List sessions |
| GET | `/api/v1/sessions/{id}/messages` | Session messages |
| GET | `/api/v1/sessions/{id}/tool-calls` | Tool-call logs |

### Chat Streaming — Request Example

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you recommend a wireless barcode scanner under 2000 TL?",
    "quote_id": "quote-001",
    "customer_id": "customer-001",
    "max_price_try": 2000
  }'
```

### SSE Event Types

| Event | Description |
|-------|-------------|
| `session_start` | Session ID and mode (llm/fallback) |
| `tool_start` | Tool name, input summary, sequence number |
| `tool_result` | Success/error, quote_delta |
| `text_chunk` | Text chunk streaming to user |
| `done` | Response complete, sources |
| `error` | Controlled error |

---

## Architectural Decisions

### 1. Resource Finding Approach: SQL + In-Memory Text Scoring

**Chosen approach:** PostgreSQL filtering (category, price, stock) + in-memory score-based text matching.

**How it works:**
1. Active products from the database are filtered by SQL based on category, price, and stock status.
2. Remaining records are scored in-memory: product name match +10, description +3, Turkish aliases +8, tags +5.
3. Results are sorted by score and the top N results are returned.

**Why embedding was not chosen:**
- Embedding cost and latency are disproportionate for 48 products and 22 knowledge entries.
- The `aliases` field covers most of the semantic search needs.
- Deterministic score calculation is testable; embedding vectors don't break tests when they change.
- If needed in the future, `pgvector` can be added; service interface remains unchanged.

**Trade-off:** Semantic synonyms without aliases (e.g., "handheld terminal" for scanner) cannot be captured. In LLM mode, the model converts questions to standard terms; in fallback mode, adding aliases is sufficient.

---

### 2. Function Call Orchestration: Hybrid

**If LLM is available (OPENAI_API_KEY set):**
OpenAI function calling + SSE streaming agentic loop. The model decides which tool to call and when. Each call goes through `dispatch_tool()`; business rules like price limits are enforced in tool implementations — not left to LLM discretion.

**If LLM is not available:**
Deterministic intent detection + direct tool calling. If message contains "policy" → `get_knowledge_entries`, if it contains "product"/"price" → `search_products`; if both → both are called.

**Why hybrid:**
- Pure deterministic: insufficient for complex multi-step workflows.
- Pure LLM: business rules become dependent on LLM behavior, untestable.
- Hybrid: tool implementations are identical in both modes; LLM only determines order, cannot bypass rules.

**Guarantee:** `max_price_try` is always injected inside `dispatch_tool()`. The rule is applied whether the LLM passes it or not.

---

### 3. Fallback Mode

`stream_chat_fallback()` is activated when `OPENAI_API_KEY` is empty or not set.

**Guarantees:**
- Every response includes at least one `knowledge_id` source (for policy questions).
- Out-of-stock products are not recommended; price limits are not exceeded.
- Mutation tools (`add_to_quote`, `replace_with_alternative`, etc.) work in fallback mode too.
- SSE event format is identical to LLM mode; client doesn't need to distinguish modes.
- `done` event returns a `sources` list.

**Not guaranteed:**
- Complex multi-step workflows may not be fully interpreted in a single pass. For example, composite requests like "remove that product, add this one, tell me the total" are partially handled in fallback.

---

### 4. Idempotency Strategy

**Key generation:**
The client sends its own generated value in the `ChatRequest.idempotency_key` field. Recommended format:

```
{session_id}:{sha256(message)[:8]}:{unix_timestamp // 300}
```

The same message sent within 5 minutes generates the same key.

**Server-side validation:**
In `add_to_quote` call, if a key exists, it's first looked up in the `ToolCallLog` table (`UNIQUE` constraint). If found, the mutation is skipped and `{"idempotent": true}` is returned. PostgreSQL `UNIQUE` constraint is immune to race conditions.

**SSE retry:**
If the client connection drops, it can reconnect with the same `idempotency_key`. The server won't apply the mutation again; it generates a response by reading the current quote state with `get_quote`.

---

### 5. Quote Mutation Model

All mutations are performed atomically within `BEGIN SAVEPOINT`.

| Operation | DB Representation |
|-----------|------------------|
| Add product | `QuoteItem` created with `status=active` |
| Add same product again | Existing `active` row's `quantity` incremented, no new row |
| Update quantity | `quantity` set |
| Remove product (`quantity=0`) | `status=removed` (no physical deletion) |
| Replace with alternative | Old row `status=replaced` + `replaced_by_item_id`; new row `status=active` |

**Why soft-delete:**
- Quote history and audit trail are preserved.
- `get_quote` returns only `status=active` rows; client doesn't see old state.
- `replace_with_alternative` never leaves two active equivalents in the same quote.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://tbr:tbr_secret@db:5432/tai_db` | Async PostgreSQL |
| `GEMIN_API_KEY` | _(empty)_ | If empty, fallback mode is enabled |
| `GEMINI_MODEL` | `gpt-4o-mini` | Model to use |
| `SECRET_KEY` | `changeme` | Change in production |
| `SEED_ON_STARTUP` | `true` | Load seed on startup |

---

## Project Structure

```
tbr-backend/
├── app/
│   ├── main.py                          # FastAPI app, lifespan
│   ├── core/config.py                   # Pydantic settings
│   ├── db/session.py                    # Async engine, get_db
│   ├── models/models.py                 # SQLAlchemy ORM models
│   ├── schemas/schemas.py               # Pydantic I/O schemas
│   ├── tools/tool_implementations.py    # 6 required tool implementations
│   ├── services/
│   │   ├── chat_service.py              # LLM + fallback orchestrator
│   │   └── seed_service.py              # JSON seed loader
│   └── api/v1/endpoints/
│       ├── chat.py                      # SSE streaming endpoint
│       ├── products.py                  # Product CRUD
│       ├── knowledge.py                 # Knowledge entry CRUD
│       ├── quotes.py                    # Quote reading
│       └── sessions.py                  # Sessions and tool-call logs
├── tests/
│   ├── conftest.py                      # SQLite in-memory fixtures
│   └── test_tools.py                    # 24 tests
├── seed_data/                           # JSON files go here
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── README.md
├── AI_USAGE.md
└── KNOWN_LIMITATIONS.md
```
