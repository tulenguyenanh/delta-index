# OptiBot UI

React + Vite + TypeScript chat panel for OptiBot. The send path streams grounded,
cited answers from the Python assistant over `POST /api/chat` (Server-Sent Events).

## Run in dev

Both sides run from the repo root.

**Backend** (requires `GOOGLE_API_KEY` in the environment):

```bash
uvicorn src.assistant.api:app --reload --port 8000
```

**Frontend:**

```bash
cd ui && npm run dev
```

Vite serves http://localhost:5173 and proxies `/api` to `http://localhost:8000`.

The API key lives only on the backend — the UI never sees it.
