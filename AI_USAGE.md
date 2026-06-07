# AI Usage

This document describes how artificial intelligence is utilized in this project.

---

## Model Configuration

The system employs an OpenAI-compatible API endpoint routed through Groq's infrastructure:

```
base_url: https://api.groq.com/openai/v1
model: configurable via OPENAI_MODEL environment variable (default: llama-3.3-70b-versatile)
```

When `OPENAI_API_KEY` is empty, contains a placeholder value, or when rate limits are exceeded (HTTP 429), the system automatically transitions to **deterministic fallback mode** without invoking any LLM calls.

---

## AI Integration Points

### Function Calling (LLM Mode)

**Location:** `chat_service.py` — `stream_chat_llm()`

The language model receives a comprehensive system prompt along with the complete conversation history. It then determines which of the six available tool functions to invoke and in what sequence. Tool calls are streamed through the OpenAI streaming API and executed sequentially via `dispatch_tool()`.

#### Available Tools

| Tool | Type | Description |
|------|------|-------------|
| `search_products` | Read | Finds products by query, category, price limit |
| `get_knowledge_entries` | Read | Retrieves policy and compliance information |
| `get_quote` | Read | Returns current quote state |
| `add_to_quote` | Mutation | Adds product or increases quantity |
| `update_quote_item` | Mutation | Modifies item quantity |
| `replace_with_alternative` | Mutation | Swaps with alternative product |

> **Important:** The model does not enforce business rules. It only determines which tool to call. All business rules are enforced at the implementation level in `tool_implementations.py`.

---

### Context Awareness

The system maintains conversation context by:

- Loading previous messages into the LLM prompt
- Detecting last mentioned product category from history
- Injecting category context when user asks follow-up questions without specifying category

**Example:** User asks `"500 TL altı el terminali öner"` then `"10000 TL ile alabilirim"`. The system detects `"el terminali"` category from history and injects `[Context: el terminali kategorisinde ara]` into the second query.

---

### System Prompt

`BASE_SYSTEM_PROMPT` in `chat_service.py` instructs the model to:

- Communicate exclusively in Turkish
- Never suggest or add products exceeding `max_price_try`
- Avoid recommending out-of-stock products by default
- Always cite a valid `knowledge_id` when referencing policies
- Never create duplicate product rows; increment quantity instead
- Never generate or modify `quote_id`; use the provided context value
- Check `suggestions` key in search results before reporting "not found"

**Runtime Injection:** The active `quote_id` and price limit are dynamically injected into the user message:

```
[Quote ID: <id>]
[Budget: <amount> TRY]
[Context: <category> kategorisinde ara]
```

---

### Quote ID Protection

Even if the model transmits an incorrect or empty `quote_id` in a tool call, `dispatch_tool()` automatically overwrites it with the session's actual `quote_id` before execution. This backend-level enforcement operates independently of model compliance.

---

### Groq Compatibility

Tool arguments are cleaned before sending to Groq API:

- Empty strings are removed
- `None` values are omitted
- Required parameters are ensured
- `max_price_try` is removed if `None`
- `query` defaults to `"urun"` when missing

This is handled by `_clean_tool_arguments()` in `chat_service.py`.

---

## Non-AI Components

### Fallback Mode

**Location:** `chat_service.py` — `stream_chat_fallback()`

Executes without any LLM invocation. Intent detection uses keyword matching on normalized message content:

| Intent | Keywords |
|--------|----------|
| Add to quote | `ekle`, `add`, `koy`, `ilave` |
| View quote | `teklif`, `sepet`, `goster`, `listele`, `icerik`, `ne var` |
| Policy inquiry | `iade`, `garanti`, `teslimat`, `politika`, `kural`, `uyumluluk` |
| Product search | `urun`, `okuyucu`, `yazici`, `barkod`, `terminal`, `yazilim`, `hizmet` |

**Parsing Capabilities:**

- Turkish number words (`bir`, `iki`, `uc`, `dort`, `bes`)
- Digit patterns (`\d+ adet`, `\d+ tane`)
- Price limit extraction via regex patterns

All six tool implementations are called identically in fallback mode. SSE event format remains consistent with LLM mode.

---

### Retrieval System

**Location:** `tool_implementations.py` — `search_products()` and `get_knowledge_entries()`

No embeddings or vector search are used. The system employs:

1. **Category Detection:** Keywords mapped to categories (`el terminali` → `pos_terminal`, `barkod` → `barcode_scanner`)
2. **Database Pre-filtering:** PostgreSQL filters by price, category, and stock status
3. **In-Memory Scoring:** Token-based scoring with the following weights:

| Match Location | Score |
|----------------|-------|
| Exact category match | +50 |
| Product name match | +10 |
| Turkish alias match | +8 |
| Tag match | +5 |
| Partial word match | +5 |
| Description match | +3 |

**Alternative Suggestions:** When no products are found within the price limit, the system returns same-category products above the limit as suggestions with price difference calculation.

**Token Processing:**

- Query is tokenized and normalized (Turkish character conversion)
- Special phrases preserved (`el terminali` → `elterminali`)
- Turkish stopwords removed
- Results sorted by descending score
- Top N results returned

Knowledge entries use identical token-based scoring:

| Match Location | Score |
|----------------|-------|
| Title match | +10 |
| Tag match | +7 |
| Content match | +5 |

---

## AI Development Assistance

Claude (`claude-sonnet-3.5`) was utilized during development for the following tasks:

- Drafting and iterating on system prompt design
- Debugging token-based scoring logic in `_score_product()` and `_score_knowledge()`
- Writing and maintaining test fixtures
- Identifying SQLite JSONB compatibility requirements
- Optimizing category detection algorithms
- Resolving Groq API compatibility issues (empty string handling)
- Implementing conversation context awareness
- Fixing rate limit handling and fallback triggers

**Quality Assurance:** All AI-generated code underwent:

- Manual review against project requirements
- Execution against the 24-scenario test suite
- Modifications where behavior deviated from tool contracts

---

## Rate Limiting & Fallback Triggers

The system automatically falls back to deterministic mode under these conditions:

- Missing or invalid `OPENAI_API_KEY`
- API rate limit exhaustion (HTTP 429)
- Network timeouts or connection failures
- Malformed API responses
- General API exceptions

Fallback mode maintains identical functionality through rule-based intent detection, ensuring system reliability under all conditions.

---

## SSE Event Types

Both LLM and Fallback modes emit the same Server-Sent Events:

| Event | Description |
|-------|-------------|
| `session_start` | Session initialization with `quote_id` |
| `mode` | Indicates `llm` or `fallback` mode |
| `text_chunk` | Streaming text response |
| `tool_start` | Tool execution begins |
| `tool_result` | Tool execution result with success status |
| `sources` | Product or knowledge sources cited |
| `done` | Response complete |
| `error` | Error occurred |

This consistent format allows the frontend to handle both modes uniformly.

