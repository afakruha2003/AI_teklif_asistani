# tai-web

React admin panel for The Blue Red quote assistant. Connects to the `tai-backend` API and displays products, knowledge entries, quotes, and session logs.

---

## Setup

```bash
cp .env.example .env
npm install
npm run dev
```

The app runs at `http://localhost:3000` by default.

If you are running the full stack via Docker Compose from the project root, the web panel starts automatically and you do not need to run it separately.

### Environment Variables

`.env` (copy from `.env.example`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Project Structure

```
tai-web/
├── src/
│   ├── api/
│   │   └── client.js           # Axios base client, reads VITE_API_BASE_URL
│   ├── components/
│   │   ├── Layout.jsx           # Sidebar navigation shell
│   │   ├── UI.jsx               # Shared UI primitives (buttons, badges, tables)
│   │   ├── ProductForm.tsx      # Add / edit product form
│   │   └── KnowledgeForm.tsx    # Add / edit knowledge entry form
│   ├── pages/
│   │   ├── Dashboard.jsx        # Overview stats
│   │   ├── Products.jsx         # Product list + CRUD
│   │   ├── Knowledge.jsx        # Knowledge entry list + CRUD
│   │   ├── Quotes.jsx           # Quote viewer
│   │   └── Sessions.jsx         # Session list + tool-call log viewer
│   ├── services/
│   │   └── api.ts               # Typed wrappers around the backend endpoints
│   └── types/
│       └── index.ts             # Shared TypeScript types
├── public/
│   ├── favicon.svg
│   └── icons.svg
├── Dockerfile
├── .env.example
└── vite.config.ts
```

---

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Product count, active quote count, recent session activity |
| Products | `/products` | List all products; add, edit, delete |
| Knowledge | `/knowledge` | List knowledge entries; add, edit, delete |
| Quotes | `/quotes` | View quote line items, totals, and item status (active / replaced / removed) |
| Sessions | `/sessions` | Browse chat sessions; click a session to see its tool-call log with inputs, outputs, and quote deltas |

The Quotes page reads from the same `quote_id` used by the mobile app. Mutations made from the mobile chat screen appear here without a page refresh (manual reload required — there is no WebSocket push).

---

## Build

```bash
npm run build
```

Output goes to `dist/`. The `Dockerfile` builds and serves the static output via nginx.

---

## API

All requests go through `src/api/client.js`. The base URL is set from `VITE_API_BASE_URL` at build time. Endpoints used:

- `GET/POST/PATCH/DELETE /api/v1/products/`
- `GET/POST/PATCH/DELETE /api/v1/knowledge/`
- `GET /api/v1/quotes/` and `/api/v1/quotes/{id}`
- `GET /api/v1/sessions/` and `/api/v1/sessions/{id}/tool-calls`