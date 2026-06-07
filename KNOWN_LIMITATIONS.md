# Known Limitations

---

## Fallback Mode

**Composite multi-step requests are partially handled.**
`stream_chat_fallback()` runs a single-pass intent detection. A message like "remove that product, add this one, and show the total" triggers at most one intent branch per pass. Only the first detected intent is acted on; the rest are ignored.

**Quantity parsing is limited to simple patterns.**
Turkish number words (`bir`, `iki`, `üç`, `dört`, `beş`) and digit patterns (`\d+ adet`) are recognized. Compound numbers (`yirmi beş adet`, `iki yüz`) are not parsed; they fall back to quantity=1.

**Price extraction from natural language is regex-based.**
The pattern `\d[\d.,]* (tl|try|lira|₺)` is matched. Prices expressed without a currency token (`"two-thousand-limit scanner"`) are not detected.

---

## Retrieval

**Semantic synonyms without a defined alias are not matched.**
`search_products` and `get_knowledge_entries` use token-based scoring, not embeddings. If a user writes a term that does not appear in the product name, description, tags, or `aliases` field, the product will not be found. In LLM mode the model typically normalizes queries to standard terms; in fallback mode, adding the synonym to the `aliases` field is the only remedy.

**Category filter is case-sensitive at the SQL level before lowercasing.**
`func.lower(Product.category) == params.category.lower()` is applied, but categories stored with inconsistent casing in the seed data may not match if `lower()` is not applied consistently during seeding.

---

## Idempotency

**The idempotency key must be resent on streaming reconnect.**
If a client connection drops after the mutation was committed but before the `done` event was received, reconnecting without the original `idempotency_key` will apply the mutation a second time. The server has no way to detect the retry without the key.

**Idempotency only covers `add_to_quote`.**
`update_quote_item` and `replace_with_alternative` do not check `ToolCallLog` for duplicate keys. Retrying these calls will apply the mutation again.

---

## LLM Mode

**The model can still hallucinate a `quote_id` despite prompt instructions.**
The system prompt and user message injection both instruct the model to use the provided `quote_id`. As a backend safeguard, `dispatch_tool()` overwrites any wrong `quote_id` with the session's actual value. If `quote_id` is absent from the tool call entirely, the overwrite does not fire and the tool will return an error.

**Multi-turn context is rebuilt from `ChatMessage` rows on every request.**
Messages stored with `role="tool"` are excluded from the reconstructed context sent to the model. Tool results are included only via the `tool_results` list appended after each tool-call round. This means very long sessions with many tool calls may lose early context as the context window fills.

**Conversation history reconstruction skips assistant messages that fail JSON parsing.**
If a stored assistant message looks like a tool-call list (`[` or `{`) but fails `json.loads`, it is passed as plain text. This can cause the model to misinterpret prior turns in edge cases.

---

## Quote Mutations

**`replace_with_alternative` requires the alternative product to have stock > 0.**
If the alternative is also out of stock, the operation returns an error and the original item remains active. There is no fallback-of-fallback chain.

**Stock is decremented immediately on `add_to_quote` for non-backorder items.**
If the transaction is rolled back after the decrement (e.g. due to a later constraint violation in the same request), the stock count may be inconsistent until the next seed or manual correction.

**Soft-deleted items (`status=removed` or `status=replaced`) are never purged.**
`get_quote` filters to `status=active` only, so old rows are invisible to users. For very active quotes with many replacements, the `quote_items` table will accumulate historical rows indefinitely.

---

## Testing

**Tests run against SQLite in-memory, not PostgreSQL.**
`conftest.py` patches `SQLiteTypeCompiler` to accept `JSONB` as `JSON`. Behavior differences between SQLite and PostgreSQL (e.g. JSON operator support, `func.lower` on indexed columns, concurrent writes) are not covered by the test suite.

**`test_add_to_quote_creates_item` asserts `action == "item_added"`.**
The current `add_to_quote` implementation returns `action = "add"` (not `"item_added"`). This test will fail against the current code. The schema mismatch between test assertions and implementation exists in the submitted version.
