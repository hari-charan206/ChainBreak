# ChainBreak (v4)

**We tell you where to act first to stop the chain.**

ChainBreak watches a live industrial dependency graph, detects anomalies in
real sensor data, predicts how a failure will propagate across *your* graph,
and ranks the single best intervention point — the FOCUS HERE FIRST node.

## The idea

- **You define the environment.** Nodes (pumps, sensors, valves, control
  units), dependency edges with a criticality slider, and an MQTT topic
  bound to each node's sensor. No fixed graph, no dataset replay.
- **Live data only.** A Wokwi virtual ESP32 (or any MQTT publisher)
  publishes values to your bound topics. There is no simulate button —
  node state changes only when real data says so. (An operator-only
  fallback script exists for demo rescues; it is external to the app.)
- **Three AI components, honestly labeled:**
  1. *Anomaly detection* — trained Isolation Forest per sensor, trained
     live after a disclosed warm-up (~30 readings); your user-set
     thresholds (cold-start defaults: baseline ×1.2 / ×1.5) guard the node
     from the first reading.
  2. *Propagation prediction* — probabilistic model over anomaly score ×
     edge criticality (not trained; assumed 300 s per hop, disclosed).
  3. *Intervention ranking* — heuristic scoring model with locked v1
     weights `0.35 / 0.30 / 0.20 / 0.15` (downstream reach / propagation
     probability / time-to-impact / criticality). Never "learned".

## Architecture

```
Wokwi ESP32 ──MQTT──▶ broker.hivemq.com ──▶ FastAPI backend (:8089)
                                            ├─ JWT auth (bcrypt, pyjwt)
                                            ├─ SQLite: users/environments/
                                            │  nodes/edges/sensor_bindings
                                            ├─ per-binding Isolation Forest
                                            ├─ propagation + ranking
                                            └─ GET /state  ◀── 2s poll
                                                    │
                                          React + Vite (:5173)
                                          briefing → auth → env picker →
                                          builder → dashboard (React Flow,
                                          Recharts, Framer Motion + GSAP
                                          on the briefing page only)
```

## Quickstart

```bash
# backend (Python 3.14)
backend/.venv/Scripts/pip install -r backend/requirements.txt
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8089

# frontend
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Then: briefing page → sign up → create an environment → add nodes → connect
them → bind MQTT topics (with a baseline; thresholds default to ×1.2 / ×1.5)
→ open the dashboard → publish values to a bound topic and watch it go live.

## Wokwi

Open `wokwi/diagram.json` + `wokwi/sketch.ino` at wokwi.com. Set the
`TOPIC_*` defines to your bound `mqtt_topic` strings and press play. Heat
the DHT22 past a node's failure threshold (hold it — 5 consecutive samples
sustain the state) and the cascade fires.

## Operator fallback (demo rescue, NOT part of the product)

```bash
backend/.venv/Scripts/python.exe ops/fallback_publish.py \
  --topic chainbreak/env1/cooling/temp --value 82
# or loop a range:  --sweep TOPIC START END
```

Same broker as the backend by default; `CHAINBREAK_MQTT_BROKER=127.0.0.1`
points the whole stack at a local broker on locked-down networks (see
`.freebuff/run.md`).

## Tests

```bash
cd backend && ./.venv/Scripts/python.exe test_v4_smoke.py
```

12 end-to-end tests: auth, ownership scoping, builder, MQTT ingestion,
threshold + IF detection, propagation, locked-weight ranking arithmetic,
validation disclosures, recovery. The real-broker round trip skips itself
when outbound 1883 is blocked.

## Contract

`CONTRACT.md` is the binding frontend/backend contract. v3 history is
preserved below the v4 amendment (Section 17).
