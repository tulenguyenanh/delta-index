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

## Smoke test

After starting both sides, verify the wired chat end-to-end without the browser:

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I pair my player with a screen?"}'
```

You should see `event: token` lines streaming the answer, then an
`event: citations` line carrying a JSON list of up to 3 grounding URLs, then a
closing `event: done`. If the store has no grounding metadata for the question,
`citations` is an empty list (`[]`) — that's the safe fallback, not an error.

In the browser, the same question streams into the assistant bubble token-by-token
and a cited answer shows a "Searched {n} sources" line with clickable `Article URL:`
links. With the backend stopped, the UI shows a friendly "unreachable" bubble
instead of a stack trace.
