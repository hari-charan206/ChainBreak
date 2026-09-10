# ChainBreak — Run Doc (v4)

Two processes: FastAPI backend (:8089) and Vite frontend (:5173). No build
step needed for dev. All commands run from the project root
(`CODE MERGE/chainbreak`).

## 1. Reproduce artifacts (fresh checkout)

```bash
# Backend deps (Python 3.14 venv already at backend/.venv; recreate with:
#   python -m venv backend/.venv)
backend/.venv/Scripts/pip install -r backend/requirements.txt

# Frontend deps
cd frontend && npm install
```

- `backend/chainbreak.db` is created automatically on first backend start
  (do not copy it between machines; delete it to reset all demo data).
- No `.env` files are used. The only optional env var is
  `CHAINBREAK_MQTT_BROKER` (see section 4).

## 2. Run the backend

```bash
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --port 8089 \
  --timeout-keep-alive 120
```
(from `backend/` as working directory). Health check:
`curl http://127.0.0.1:8089/api/health` → `{"ok":true}`.

## 3. Run the frontend

```bash
cd frontend && npm run dev     # Vite on http://localhost:5173
```

## 4. MQTT / live data

- Default broker: `broker.hivemq.com:1883` (locked, Section 12.5). No setup.
- **Wokwi**: open `wokwi/diagram.json` + `sketch.ino` at wokwi.com, edit the
  `TOPIC_*` defines to match the `mqtt_topic` values bound in the
  Environment Builder, and press play. The backend subscribes with a
  wildcard, so new bindings work with no restart.
- **Operator fallback** (kept off-screen during demos, Section 6.3):
  ```bash
  CHAINBREAK_MQTT_BROKER=127.0.0.1 backend/.venv/Scripts/python.exe \
    ops/fallback_publish.py --topic chainbreak/demo/cooling/temp --value 82
  ```
  (`--sweep TOPIC START END` loops a range; drop the env var to use HiveMQ.)
- **Locked-down networks** (this dev box blocks outbound 1883): run a local
  broker, then start BOTH the backend and the fallback script with
  `CHAINBREAK_MQTT_BROKER=127.0.0.1`:
  ```bash
  backend/.venv/Scripts/amqtt.exe -c .freebuff/broker.yaml
  ```

## 5. Tests

```bash
cd backend && ./.venv/Scripts/python.exe test_v4_smoke.py
# 12 tests: auth, ownership, builder, MQTT ingestion, AI layer, disclosures.
# The HiveMQ round-trip test skips automatically when 1883 is unreachable.
```

## 6. Demo flow (rehearsed order)

1. Briefing page (`/`) → "Launch ChainBreak" → sign up/in.
2. Environment picker → builder: create env, add 2-3 nodes, connect with
   criticality slider, bind topics with baselines (cold-start thresholds
   are baseline ×1.2 / ×1.5 — locked).
3. Dashboard (`/dashboard/:id`) — nodes show **offline** until real MQTT
   data arrives; then healthy. No simulate button exists anywhere.
4. Drive values past the failure threshold (Wokwi slider or fallback
   script) and hold them there (5-sample sustain) — node flips to failed,
   cascade + FOCUS HERE FIRST appear within ~2s.
