# TAI Web — Admin Dashboard

React + TypeScript admin dashboard for AI Quote Assistant platform.

## Features

 **Product Management** — List, create, edit, and delete products  
 **Knowledge Base** — Manage policy information and FAQs  
 **Quote Viewer** — Monitor quotes with real-time sync from mobile app  
 **Session Monitoring** — View chat sessions and tool-call logs  
 **Real-time Updates** — See mobile-made mutations instantly on web  

## Setup

```bash
cd tai-web

# Install dependencies
npm install

# Create .env from example
cp .env.example .env

# Development server (with HMR)
npm run dev
```

**Browser:** http://localhost:5173

The dev server proxies `/api/*` requests to `http://localhost:8000` (backend).

## Build

```bash
npm run build
```

Production-optimized build in `dist/` folder.

## Linting

```bash
npm run lint
```

ESLint configuration included. Fixes auto-fixable issues with:

```bash
npm run lint -- --fix
```

## Project Structure

```
src/
├── components/
│   ├── Common.tsx           # Modal, Nav, Loading, Error, Success
│   ├── ProductForm.tsx      # Product create/edit form
│   └── KnowledgeForm.tsx    # Knowledge entry form
├── pages/
│   ├── Dashboard.tsx        # Stats overview
│   ├── Products.tsx         # Product CRUD
│   ├── Knowledge.tsx        # Knowledge base CRUD
│   ├── Quotes.tsx           # Quote viewer (real-time polling)
│   └── Sessions.tsx         # Chat sessions & tool-call logs
├── services/
│   └── api.ts               # API client (fetch wrapper)
├── types/
│   └── index.ts             # TypeScript interfaces
├── App.tsx                  # Main routing
└── App.css                  # Global styles
```

## API Integration

All API calls go through `src/services/api.ts`:

- `productApi` — Products CRUD
- `knowledgeApi` — Knowledge entries CRUD
- `quoteApi` — Quote queries + polling
- `sessionApi` — Sessions, messages, tool-call logs

**Real-time Quote Sync:**  
When viewing a quote, the page polls the backend every 2 seconds for updates (e.g., items added/removed from mobile app). Updates appear instantly in the quote view.

## Responsive Design

Mobile-friendly layout. On small screens:
- Single-column quote/session viewer
- Collapsed navbar
- Stack form fields



## TypeScript

Fully typed with strict mode. Main types in `src/types/index.ts`:

- `Product`, `ProductCreate`
- `KnowledgeEntry`, `KnowledgeEntryCreate`
- `Quote`, `QuoteItem`
- `ChatSession`, `ChatMessage`, `ToolCallLog`

## Error Handling

Errors show in red banner at top of page. Dismiss with ×. Network errors, validation errors, and API errors all handled.

## Environment

Create `.env` file:

```
VITE_API_URL=http://localhost:8000/api/v1
```

If not set, defaults to `http://localhost:8000/api/v1`.

## Browser Support

Modern browsers (Chrome, Firefox, Safari, Edge). Requires ES2020+ support.

## Notes

- No external CSS framework (no Bootstrap, Tailwind). Pure CSS with custom design.
- No state management library. React hooks only.
- Forms submit immediately (no "Discard" after failed submit).
- Confirm dialogs for destructive actions (delete).
- Session polling updates list every 2 seconds in Quote and Sessions pages.
