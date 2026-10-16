# OptiBot UI

React + Vite + TypeScript chat panel for OptiBot. The send path streams grounded,
cited answers from the Python assistant over `POST /api/chat` (Server-Sent Events).

## Run with Docker Compose

From the repo root, with `GOOGLE_API_KEY` set in your shell or in the repo-root
`.env`, run the command below, open http://localhost:8080, and stop with
`docker compose down`. Compose reads `.env` only for `${...}` substitution and
refuses to start if the key is missing or empty.

```bash
docker compose up --build
```

What runs:

- `api` is built from the root Dockerfile (the same image as the graded sync job).
  Its entrypoint is overridden at runtime to
  `python -m uvicorn src.assistant.api:app --host 0.0.0.0 --port 8000`, and it is
  not published to the host.
- `ui` is this folder, built with Vite and served by nginx. nginx proxies `/api/`
  to the api with buffering off, so answers stream token by token. UI and API share
  one origin, so there is no CORS setup.

Key handling: the key goes only into the api container's environment at runtime;
neither image contains it. `docker compose config` prints the substituted key, so
validate with `docker compose config --quiet`.

Port: 8080 is bound to 127.0.0.1. Change it with `UI_PORT=9000 docker compose up --build`.
The optional `GEMINI_MODEL`, `GEMINI_STORE_NAME` and `GEMINI_STORE_DISPLAY_NAME`
are passed through.

Store: the API reuses the existing File Search store (found by display name, or by
`GEMINI_STORE_NAME`) and never uploads. On a fresh key, run the sync once first
(`docker run --rm -e API_KEY=<your-gemini-key> optibot-sync`, as in the root
README). Compose does not run the sync job.

Smoke test through nginx (same as below, against port 8080):

```bash
curl -N -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I pair my player with a screen?"}'
```

Expect `event: token` lines, then `event: citations`, then `event: done`.

## Run in dev

Both sides run from the repo root.

**Backend** (requires `GOOGLE_API_KEY` in the environment):

```bash
python -m uvicorn src.assistant.api:app --reload --port 8000
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
