---
name: add-api-endpoint
description: Recipe for adding or changing a backend API endpoint and wiring it through to the React frontend — router, app registration, client.ts, UI, tests. Load before touching api/routers/ or frontend/src/api/.
user-invocable: true
---

# Adding / Changing an API Endpoint (backend → frontend)

The FastAPI backend serves the React renderer over HTTP/WebSocket on port 5000
(port constants: `electron/config.ts`). A feature is not done until every layer
it touches is updated — backend, `client.ts`, and the UI.

## Backend

1. **Router** — `backend/ignition_toolkit/api/routers/<area>.py`. New area →
   new file with `router = APIRouter(prefix="/api/<area>", tags=[…])`; existing
   area → extend its router (24 router modules exist; `executions/` and
   `stackbuilder/` are packages).
2. **Register** — `backend/ignition_toolkit/api/app.py`: import + `app.include_router(...)`
   (only for new router modules).
3. **Models** — Pydantic request/response models in the router module; validate
   all input there, not in the UI.
4. **Auth** — match the auth dependencies of neighbouring routers
   (`api/dependencies.py`; API-key auth + RBAC live in `ignition_toolkit/auth/`).
5. **Live updates** — if the frontend needs push updates, use the existing
   WebSocket channels in `api/routers/websockets.py`, don't poll.

## Frontend

6. **Client** — add a method to the `api` object in
   `frontend/src/api/client.ts` (single central client, typed responses;
   never raw `fetch` in components).
7. **Types** — shared response types in `frontend/src/types/`.
8. **UI** — page in `frontend/src/pages/` or component in `src/components/`;
   cross-page state goes in the Zustand store (`src/store/index.ts`),
   constants in `src/constants/`, timings in `src/config/`.

## Tests (both sides)

- Backend: `backend/tests/test_api/` — FastAPI TestClient, mock services.
- Frontend: `Foo.test.tsx` next to the component (vitest + testing-library).
- Run per `testing-and-verification`; eslint must pass with zero warnings.

## Gotchas

- The renderer never talks to Node/Electron for backend data — only HTTP/WS to
  Python. Electron IPC (`electron/preload.ts` + `ipc/channels.ts`) is only for
  desktop concerns (dialogs, settings, updates, opening paths).
- Anything credential-shaped: load `security-checking` first; credential values
  must never appear in responses, logs, or exports.
