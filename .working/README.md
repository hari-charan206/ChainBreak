# ChainBreak — IoT + AI cascade failure dashboard

ChainBreak is a real-time IoT + AI web application for identifying and analyzing cascading failures in interconnected industrial systems. The core promise: "We do not just tell you what failed. We tell you what the failure can affect next, and where to act first to stop the chain." Category: AI for Safety & Security — The Chain Reaction.

### Build status
- Loop closure: replay → isolation forest early warning → failure detection → cascade animation → "FOCUS HERE FIRST" intervention ranking → apply → before/after impact 3→1 + validation metrics panel.
- Locked demo window: `2015-12-28 11:22:00` (SWaT attack.csv segment #3, the real LIT301/MV301 attack). Relay from that timestamp at 30x; recompute upstream at `_static/roster.sqlite`.
- Lightning-fast blog-loop claims made data-driven: actual impact reduction number = 3→1.

### Startup
From this thread's workspace root (`C:\Users\Hari_\OneDrive\Documents\CODE MERGE\chainbreak`):

1. Start the Python backend first (pick a free port if 8000 is taken):
   ```powershell
   cd backend
   # if you want the default 8000:
   .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
   ```
   Replay starts at the locked demo window by default. Adjust replay speed with `/api/replay/start` `{ "multiplier": <int> }` during dry-run rehearsal, but keep the default locked at 30x until you've rehearsed twice.

2. Start the Vite dev server in a separate terminal (package.json lives in `frontend/`):
   ```powershell
   cd frontend
   npm run dev
   ```
   Vite prints a URL like `http://localhost:5173` or `http://localhost:5174`. Open that URL in the browser.

3. The frontend fetches from `http://127.0.0.1:8000/api/*` (see `frontend/src/lib/api.ts`). If your local 8000 is occupied, point the client at the free backend port: edit `frontend/src/lib/api.ts` `const BASE = ...` and restart the dev server.

### Demo script (build-prompt Section 9)
0. Reset state: POST `/api/replay/reset`.
1. Start replay from locked window: POST `/api/replay/start`.
2. Watch N3 detection fire → N4 warning → N4 failed, with the cascade animation tracing N3→N4→N5→N6.
3. Read the "FOCUS HERE FIRST" recommendation from the intervention ranking panel; open the explanation drawer to confirm the heuristic score breakdown.
4. Apply the intervention (POST `/api/intervention/apply` with the focus node_id). Replay stops and the before/after view shows `3 → 1`.
5. If needed, trigger `/api/failure/simulate` as the guaranteed-timing fallback.
6. Dry-run the script twice against the live build before the judged slot.

### Data notes (contract)
- `backend/data/attack.csv` is the SWaT export; every row is labeled `Attack`. The Isolation Forest is the anomaly model (NO autoencoders). Baselines and thresholds are derived by `backend/app/ai/threshold_derivation.py` and persisted to `backend/app/ai/derived_thresholds.json`.
- The fixed demo graph is N1→N2→N3→N4→N5→N6 with locked criticality values (see `CONTRACT.md`). Do not add / remove / rename nodes or edges without flagging the change.
- The propagation beyond the real N3 anomaly is model-predicted and flagged `synthetic: true` in API payloads; the UI discloses it exactly as the heuristic ranking is disclosed.

### Files of note
- `frontend/src/lib/api.ts` — typed API client mirroring the CONTRACT.md schemas.
- `frontend/src/hooks/usePolling.ts` — 2s polling hook; no WebSocket/SSE in v1.
- `frontend/src/styles/theme.css` — theme tokens + status cue classes (color + non-color cue always paired).
- `backend/app/ai/threshold_derivation.py` — offline derivation; run once to regenerate artifacts.
- `backend/app/engine.py` — cascade engine (latching per-run detection).
- `CONTRACT.md` — the binding frontend/backend contract.

### Ethics/honesty
This build is explicitly heuristic in v1. Intervention ranking is a weighted heuristic with locked starting weights; propagation estimation is a probabilistic/trend model, NOT trained. The validation panel always shows the scope label alongside the number; the full-dataset fact is available on judge request but never the headline. Any `synthetic: true` flag is surfaced, never swallowed.
