# mobil-tai

React Native / Expo mobile app for The Blue Red quote assistant. Provides a streaming chat interface and a shared quote view that stays in sync with the web panel.

---

## Setup

```bash
npm install
npx expo start
```

### Environment Variables

Create a `.env` file in the `mobil-tai/` directory:

```env
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
```

On a physical device, replace `localhost` with your machine's local network IP address. The device must be on the same network as the backend.

---

## Running

| Target | Command |
|--------|---------|
| Expo Go (scan QR) | `npx expo start` |
| iOS Simulator | `npx expo run:ios` |
| Android Emulator | `npx expo run:android` |

iOS requires Xcode 14+ on macOS. Android requires Android Studio with Java 17.

---

## Project Structure

```
mobil-tai/
├── app/
│   ├── _layout.tsx              # Root navigator, tab bar setup
│   ├── index.tsx                # Entry point, redirects to chat tab
│   ├── quote.tsx                # Quote screen route
│   ├── products.tsx             # Products screen route
│   └── settings.tsx             # Settings screen route
├── screens/
│   ├── ChatScreen.tsx           # Streaming chat UI, SSE event handling
│   ├── QuoteScreen.tsx          # Quote line items, totals, item status
│   ├── ProductsScreen.tsx       # Product browser
│   └── SettingsScreen.tsx       # API URL and session configuration
├── components/
│   ├── ChatBubble.tsx           # User and assistant message bubbles
│   ├── StreamingDots.tsx        # Animated indicator while response streams
│   ├── SourcesPanel.tsx         # Displays product_id / knowledge_id sources
│   ├── ToolCallBadge.tsx        # Shows tool name and success / error status
│   ├── QuoteItemCard.tsx        # Single quote line item card
│   └── ui/                      # Low-level UI primitives (icon-symbol, collapsible)
├── store/
│   ├── chatStore.ts             # Chat message state and session ID
│   └── quoteStore.ts            # Quote state, updated from tool_result events
├── services/
│   └── api.ts                   # Fetch wrappers for backend endpoints
├── types/
│   └── index.ts                 # Shared TypeScript types
├── constants/
│   └── theme.ts                 # Color tokens and spacing
├── hooks/
│   ├── use-color-scheme.ts
│   └── use-theme-color.ts
└── utils/
    └── theme.ts
```

---

## Chat Screen

`screens/ChatScreen.tsx` connects to `POST /api/v1/chat/stream` and reads the SSE response. Events are handled as follows:

| Event | Behavior |
|-------|----------|
| `session_start` | Stores `session_id`, sets mode label (llm / fallback) |
| `tool_start` | Renders a `ToolCallBadge` with the tool name |
| `tool_result` | Updates the badge status; if `quote_delta` is present, updates `quoteStore` |
| `text_chunk` | Appends text to the assistant bubble; `StreamingDots` shows while streaming |
| `sources` | Renders `SourcesPanel` below the message with product and knowledge links |
| `done` | Marks streaming complete |
| `error` | Shows error text in the chat |

---

## Quote Screen

`screens/QuoteScreen.tsx` calls `GET /api/v1/quotes/{quote_id}` and renders `QuoteItemCard` for each active line item. Items with `status=replaced` or `status=removed` are not shown. The quote ID comes from `chatStore` (set when the session starts).

This screen reads the same data as the web Quotes page. Both surfaces show the same state for the same `quote_id`.

---

## Reset

To reset Expo's generated files and start from a clean `app/` directory:

```bash
npm run reset-project
```


