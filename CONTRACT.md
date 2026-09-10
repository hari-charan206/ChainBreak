# CONTRACT.md — ChainBreak Integration Contract

This document is the binding contract between frontend and backend agents/developers working on ChainBreak. It is derived directly from the locked build prompt (v3 — Fully Locked). Nothing here should be reinterpreted without flagging the change to the whole team first.

---

## 1. Project Rules

- Every decision in the build prompt is final. Do not substitute alternatives, invent numbers, or "improve" on locked choices without asking first.
- `attack.csv` contains **no `Normal`-labeled rows** — every row is labeled `Attack`. All threshold/baseline logic must use the corrected proxy-baseline method (Section 9), not a percentile-of-normal approach.
- Any deviation from this contract (endpoint shape, node list, weights, thresholds) must be called out explicitly in a PR description or commit message — silent drift is not allowed.
- Local-only hosting for v1. No deployment step is part of this contract.
- Polling is the only frontend↔backend transport for v1. WebSocket is out of scope unless MVP + MQTT + landing page are all complete with a full day of buffer remaining — and even then, it requires a new version of this contract.

---

## 2. Agent Ownership

> **v4 note:** the rows below marked ~~struck~~ are retired by the v4 amendment (Section 17). New v4 ownership rows follow the table. Section 17 supersedes this table and Sections 4-9, 12 and 15 where they conflict.

| Area | Owner | Notes |
|---|---|---|
| ~~Dataset replay pipeline (`dataset_replay.py`)~~ | Backend | RETIRED in v4 — file deleted |
| ~~Threshold derivation (`threshold_derivation.py`)~~ | Backend | RETIRED in v4 — replaced by user-set + cold-start thresholds and the live per-binding Isolation Forest |
| Anomaly detection (`anomaly_detection.py`) | Backend | Isolation Forest, ~~dataset-agnostic loader interface~~ live per-binding training (v4) |
| Propagation estimation (`propagation.py`) | Backend | Probabilistic/trend model over sensor + dependency strength |
| Intervention ranking (`intervention_ranking.py`) | Backend | Hardcoded heuristic weights (Section 11) |
| Explanation payload (`explanation.py`) | Backend | Must match ExplanationDrawer schema (Section 7) |
| Validation metrics (`validation.py`) | Backend | ~~Scoped precision/recall (Section 12)~~ v4: cross-detector agreement with mandatory scope label (Section 17) |
| ~~MQTT ingestion (`mqtt_subscriber.py`)~~ | Backend | v3: built last, time-boxed. v4: built and load-bearing — dynamic topic→node lookup |
| Dependency graph UI | Frontend | React Flow, ~~fixed N1–N6 layout only~~ v4: renders any environment's nodes/edges from the polled payload |
| Sensor trend charts | Frontend | Recharts, ~~per-node mapped sensors~~ v4: per-bound-sensor trends + thresholds from the payload |
| Explanation drawer | Frontend | Renders heuristic score breakdown verbatim from backend payload |
| Before/after view | Frontend | Renders backend-computed impact number, does not compute it client-side |
| Validation metrics panel | Frontend | Must display backend's scope label, not just the number |
| Polling hook | Frontend | ~2s interval, all state sync |
| Auth API (`api/auth.py`, `security.py`) | Backend | v4 — JWT signup/login/logout (Section 17) |
| Environment API (`api/environments.py`, `api/deps.py`) | Backend | v4 — ownership-scoped CRUD + `/state` (Section 17) |
| Data models (`models/users.py`, `environments.py`, `nodes.py`, `edges.py`, `sensor_bindings.py`, `db.py`) | Backend | v4 — SQLite schema per Section 17 |
| Evaluation engine (`engine.py`) | Backend | v4 — assembles the generic `/state` payload |
| Auth pages + auth context (`pages/Login|Signup`, `hooks/useAuth`) | Frontend | v4 |
| Environment picker + builder (`pages/EnvironmentsPage`, `EnvironmentBuilderPage`) | Frontend | v4 — simple forms, no drag-and-drop graph editor |
| Router + guards (`App.tsx`) | Frontend | v4 — react-router-dom, per Section 12.3 confirmation |
| Briefing page (`pages/Briefing`, `components/Briefing/*`) | Frontend | v4 — Framer Motion whileInView + GSAP ScrollTrigger (scrub) + Lenis, briefing route only |
| Operator fallback (`ops/fallback_publish.py`) | Operator | v4 — external to the app UI, rehearsed, never a product feature |
| Wokwi sketch (`wokwi/sketch.ino`) | Operator | v4 — configurable topics bound via the builder |

Neither side invents fields, node IDs, or scoring logic the other side didn't publish here first.

---

## 3. Tech Stack (locked)

| Layer | Choice |
|---|---|
| Frontend framework | React + Vite |
| Styling | Tailwind CSS |
| Dependency graph | React Flow |
| Sensor trend charts | Recharts |
| Landing page animation (optional, last) | GSAP + ScrollTrigger + Lenis |
| Backend | Python + FastAPI |
| ML / anomaly detection | scikit-learn (Isolation Forest) |
| Data handling | pandas |
| MQTT client | paho-mqtt |
| MQTT broker | HiveMQ public broker (`broker.hivemq.com`) |
| IoT simulation | Wokwi (virtual ESP32) |
| Frontend↔backend transport | Periodic polling only (~2s) |
| Database | SQLite |
| Hosting | None — local-only |

---

## 4. Fixed N1–N6 Nodes (do not regenerate)

| Node ID | Display Name | SWaT Tag(s) | Role |
|---|---|---|---|
| N1 | Intake / Power-Equivalent System | FIT101, LIT101, MV101, P101, P102 | Upstream origin point |
| N2 | Dosing / Chemical System | AIT201–203, FIT201, MV201, P201–206 | First dependent system |
| N3 | Cooling-Equivalent (Ultrafiltration) System | DPIT301, FIT301, LIT301, MV301–304, P301–302 | "Cooling System" in narrative |
| N4 | Production / Treatment Machine (De-chlorination) | AIT401–402, FIT401, LIT401, P401–404, UV401 | "Production Machine" |
| N5 | Control System (Reverse Osmosis) | AIT501–504, FIT501–504, P501–502, PIT501–503 | "Control System" |
| N6 | Safety / Backwash System | FIT601, P601–603 | Final downstream / safety-critical |

Node IDs, tag mappings, and display names are fixed strings. Frontend must key all graph/state logic off `Node ID` (`N1`...`N6`), never off `Display Name`.

---

## 5. Fixed Dependency Edges (hardcoded, no auto-generation)

```
N1 → N2 → N3 → N4 → N5 → N6
```

| Edge | Criticality (0–1) |
|---|---|
| N1 → N2 | 0.5 |
| N2 → N3 | 0.7 |
| N3 → N4 | 0.9 |
| N4 → N5 | 0.8 |
| N5 → N6 | 1.0 (safety-critical) |

Criticality values feed directly into the Section 11 intervention-scoring formula. Any adjustment must be made once, after seeing the populated graph, and noted in this file's changelog (Section 15 equivalent in project docs) — not silently.

---

## 6. API Endpoints

GET state endpoints are polled by the frontend at ~2s intervals. POST endpoints are user-triggered actions and are not polled. Base path: `/api`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/graph` | Returns fixed N1–N6 nodes + edges + current status/color/border state |
| GET | `/api/sensors/{node_id}` | Returns latest sensor readings + short trend window for a node's mapped tags |
| GET | `/api/replay/state` | Returns current replay position, playback multiplier, and whether it's running |
| POST | `/api/replay/start` | Starts replay from the locked demo-window timestamp (or resumes) |
| POST | `/api/failure/simulate` | Manual "Simulate Failure" trigger — guaranteed-timing fallback (Section 9 step 5) |
| GET | `/api/anomaly/status` | Current Isolation Forest firing status per node |
| GET | `/api/cascade` | Current cascade propagation trace (which edges are "live"/pulsing) |
| GET | `/api/intervention/ranking` | Ranked interventions with scores + breakdown (Section 11) |
| POST | `/api/intervention/apply` | Applies the selected recommendation |
| GET | `/api/impact/before-after` | Before/after comparison payload with impact-reduction number |
| GET | `/api/validation/metrics` | Scoped precision/recall panel data (Section 12) |

No endpoint outside this list may be assumed by the frontend without adding it here first.

---

## 7. JSON Response Schemas

### `GET /api/graph`
```json
{
  "nodes": [
    { "id": "N3", "display_name": "Cooling-Equivalent (Ultrafiltration) System",
      "status": "warning", "border_style": "dashed" }
  ],
  "edges": [
    { "from": "N2", "to": "N3", "criticality": 0.7, "active_cascade": false }
  ]
}
```

### `GET /api/sensors/{node_id}`
```json
{
  "node_id": "N3",
  "tags": {
    "LIT301": { "value": 812.4, "trend": [ /* recent values */ ], "unit": "mm" }
  },
  "timestamp": "2026-09-10T12:00:00Z"
}
```

### `GET /api/anomaly/status`
```json
{
  "node_id": "N3",
  "anomaly_score": 0.83,
  "state": "warning",
  "threshold_warning": 0.62,
  "threshold_failure": 0.91
}
```

### `GET /api/cascade`
```json
{
  "active_edges": ["N3->N4", "N4->N5"],
  "synthetic": false
}
```
`synthetic` is `true` when the shown propagation beyond the confirmed anomaly node is the model's predicted trajectory rather than raw sensor coincidence (the disclosed fallback in Section 9). The frontend must surface this flag whenever it is `true`.

### `GET /api/intervention/ranking`
```json
{
  "ranked": [
    {
      "node_id": "N4",
      "score": 0.71,
      "breakdown": {
        "downstream_count_norm": 0.60,
        "propagation_prob": 0.75,
        "time_to_impact_inv_norm": 0.80,
        "criticality": 0.90
      },
      "label": "FOCUS HERE FIRST"
    }
  ]
}
```

### `GET /api/impact/before-after`
```json
{
  "before": { "downstream_systems_affected": 3 },
  "after": { "downstream_systems_affected": 1 },
  "headline": "Downstream systems affected: 3 → 1"
}
```

### `GET /api/validation/metrics`
```json
{
  "scope": "Model accuracy shown for the demonstrated subsystem (Stage 3–4 sensors)",
  "precision": 0.0,
  "recall": 0.0,
  "full_dataset_available": true
}
```
`precision`/`recall` values are placeholders until Section 12 derivation completes — schema is locked, numbers are not.

---

## 8. Status Definitions

| Status | Color | Border/Cue (colorblind-safe, mandatory) |
|---|---|---|
| Healthy | `#00E5FF` | Solid border |
| Warning | `#FFB800` | Dashed border |
| Failed | `#FF3B3B` | Thick red border + icon badge |
| Offline | `#5A6472` | Dotted/grey border |

Background: `#0B0E14`. Typeface: Inter. Color must never be the only signal — every status carries a non-color cue.

---

## 9. Replay Behavior

- `dataset_replay.py` hardcodes the **locked demo-window start timestamp** derived from the Section 5.2-equivalent baseline procedure (excluding the 8 near-zero-variance actuator columns: `P202, P301, P401, P403, P404, P502, P601, P603`).
- Default playback multiplier: **30x**, tuned so the full demo sequence (steps 2–9) fits under ~90 seconds. Adjust the multiplier during rehearsal, not the script or the endpoints.
- Replay must always be able to restart from the locked timestamp by default — live firing timing is not guaranteed, so `/api/failure/simulate` is the fallback and must always be available in the UI.
- If the natural six-node cascade isn't cleanly present in the locked window, the semi-synthetic fallback (real N3 anomaly + predicted N4–N6 trajectory) is permitted, but the API response for `/api/cascade` and any related payload must be able to carry a `"synthetic": true` flag so the frontend can disclose it in the UI exactly as transparently as the heuristic ranking is disclosed.

---

## 10. AI Outputs (three components, must be labeled distinctly in UI)

1. **Anomaly detection** — trained Isolation Forest. Validated against flagged-vs-manually-confirmed windows (no real `Normal` labels exist in `attack.csv`).
2. **Propagation estimation** — probabilistic/trend-based model over sensor behavior + dependency strength. Never described as "trained" unless it actually is.
3. **Intervention ranking** — heuristic score (Section 11), explicitly labeled "heuristic scoring model" in UI/pitch, never "trained" or "learned" for v1.

Backend responses must include enough metadata (e.g., a `"method"` field) for the frontend to render the correct label per component — the frontend must not hardcode assumptions about which component produced a given number.

---

## 11. Intervention Scoring (locked starting weights)

```
score = 0.35 × downstream_count_norm
      + 0.30 × propagation_prob
      + 0.20 × time_to_impact_inv_norm
      + 0.15 × criticality
```

| Factor | Weight | Normalization |
|---|---|---|
| Downstream node count | 0.35 | ÷ total reachable nodes in graph |
| Propagation probability | 0.30 | Normalized anomaly/trend score, 0–1 |
| Time-to-impact (inverse) | 0.20 | Normalized inverse of estimated seconds-to-impact |
| Dependency criticality | 0.15 | Manually set per edge (Section 5) |

Highest score = `"FOCUS HERE FIRST"`. Weights may be tuned after seeing the populated graph, but any change must be flagged in this file, not silently changed in code.

---

## 12. Validation Metrics

- Precision/recall are computed **per the fixed demo subsystem's sensors** (N1–N6 tag list, Section 4), not as an unqualified whole-dataset number.
- The panel must display the scope label alongside the number — e.g. `"Model accuracy shown for the demonstrated subsystem (Stage 3–4 sensors)"`.
- The full-dataset number must be computed and available as a secondary fact if a judge asks directly — backend should keep it accessible (e.g. `full_dataset_available: true` plus a way to fetch it), but it is never the headline number.

---

## 13. Frontend/Backend Boundaries

- **Backend computes; frontend renders.** No scoring, thresholding, normalization, or precision/recall math happens client-side. If a displayed number isn't in a schema above, it doesn't get displayed.
- **Frontend never invents nodes/edges.** The graph is always exactly N1–N6 with the fixed edges (Sections 4–5), sourced from `/api/graph`, never generated client-side.
- **Frontend owns transitions/animation only** (~300–500ms status transitions, pulse/glow along active cascade edges) — the *timing/state* of what's active comes from the backend.
- **Polling only.** No WebSocket, no SSE, no client-side timers driving business logic beyond the ~2s poll interval.
- **Disclosure flags (e.g. `"synthetic": true`)** must be surfaced in the UI, not swallowed — the frontend is contractually required to render any honesty/disclosure field the backend sends.

---

## 14. Forbidden Changes

Without an explicit flag-and-agree step from both sides, no one may:
- Add, remove, or rename N1–N6 nodes or their SWaT tag mappings.
- Change the fixed edge order or add new edges.
- Change the intervention scoring weights or formula.
- Switch the anomaly model away from Isolation Forest for v1.
- Introduce WebSocket before the stated buffer conditions are met.
- Present the heuristic ranking as "trained" or "learned."
- Report validation metrics without the scope label.
- Silently change the locked demo-window timestamp or the 30x multiplier without re-running the full dry-run.
- Hide the `"synthetic": true` disclosure flag in any UI surface that shows cascade state.

---

## 15. Integration Checklist

- [ ] `/api/graph` returns exactly N1–N6 with fixed edges and correct criticality values
- [ ] Every status has both a color and a non-color cue in the frontend render
- [ ] `/api/replay/start` reliably begins from the locked timestamp at 30x
- [ ] `"Simulate Failure"` button always visible and wired to `/api/failure/simulate`
- [ ] `/api/intervention/ranking` breakdown renders in the ExplanationDrawer using the exact four factors and weights (Section 11)
- [ ] `/api/impact/before-after` headline number renders large and bold
- [ ] `/api/validation/metrics` panel shows the scope label, not just a bare number
- [ ] Any `"synthetic": true` flag is visibly disclosed in the cascade UI
- [ ] Polling interval is ~2s across all consumers, no faster
- [ ] Full demo script (build-prompt Section 9) dry-run twice against these live endpoints before the judged slot

---

## 16. Multi-Agent Build Workflow

This contract is the single shared source of truth between two independent build agents. Neither agent rewrites this file during their first build pass.

```
                    CONTRACT.md
                   /           \
                  /             \
          Claude/Codex          Bolt
             BACKEND           FRONTEND
                |                 |
                |                 |
           FastAPI API  <--------> React UI
                |
         SWaT / Isolation
         Propagation
         Intervention
```

Give the exact same `CONTRACT.md` to both agents, then scope each one explicitly:

**Backend agent (Claude/Codex):**
> You own `backend/`. Implement the API exactly according to CONTRACT.md. Do not modify frontend architecture.

**Frontend agent (Bolt):**
> You own `frontend/`. Implement the UI exactly against CONTRACT.md. Do not create, replace, or modify the Python backend.

If either agent needs a change to the contract itself (a new field, a renamed endpoint, a different schema), that change is proposed and made once, centrally, in this file — then re-shared with both agents. It is not patched independently inside `frontend/` or `backend/`.

---

## 17. v4 Amendment — Generic Platform + Auth + Briefing Page

This amendment supersedes v3 Sections 4–9, 12, 15 and the replay parts of
Section 9 wherever they conflict. v3 text is preserved above for history.
Source: build prompt v4 (Generic Platform + Auth + Briefing Page). The five
Section 12 open items were confirmed before any code was written:

| # | Decision | Locked choice |
|---|---|---|
| 12.1 | Session mechanism | **JWT, stateless** (Authorization: Bearer; 7-day expiry; HS256) |
| 12.2 | Password hashing | **bcrypt directly** (passlib is unmaintained and fragile on Python 3.13+; the venv runs 3.14) |
| 12.3 | Router | **react-router-dom** |
| 12.4 | Cold-start thresholds | **warning = baseline × 1.2, failure = baseline × 1.5** (user-set thresholds always win; with no baseline and no overrides, thresholds stay null and the node stays healthy until the IF calibrates — the warm-up disclosure covers this) |
| 12.5 | Broker topology | **Shared broker.hivemq.com, namespaced topics** (convention `chainbreak/{environmentId}/{nodeId}/...`; ANY bound topic string resolves via the DB lookup — the topic map is the database, not a constant) |

### 17.1 Removed in v4

- `models/graph_schema.py` (fixed N1–N6, SWaT tags) — deleted.
- `ingestion/dataset_replay.py` and all replay endpoints — deleted.
  `backend/data/attack.csv` remains on disk for history only and is not
  imported anywhere in `app/`.
- `/api/failure/simulate` and the "Simulate Failure" button — gone. Node
  state changes ONLY from live MQTT values (Section 6.1). The operator
  fallback (`ops/fallback_publish.py`) is external to the app by design.
- `/api/graph`, `/api/sensors/{node_id}`, `/api/replay/*`, and the
  multi-endpoint polling shape are superseded by the single `/state` payload.
- v3's `full_dataset_available` secondary fact retires with the dataset.

### 17.2 Data model (SQLite)

```
users(id, email UNIQUE, password_hash, created_at)
environments(id, user_id→users, name, industry_template, created_at,
             UNIQUE(user_id, name))
nodes(id, environment_id→environments, display_name, node_type,
      status CHECK healthy|warning|failed|offline, position_x, position_y)
edges(id, environment_id→environments, source_node_id→nodes,
      target_node_id→nodes, relationship_type, criticality 0–1 DEFAULT 0.5,
      UNIQUE(environment_id, source, target))
sensor_bindings(id, node_id→nodes, mqtt_topic UNIQUE, unit,
      warning_threshold, failure_threshold)
sensor_readings(id, binding_id→sensor_bindings, value, created_at)
```

### 17.3 Endpoints (replace v3 Section 6)

```
POST   /api/auth/signup            {email, password} → 201 {token, user}
POST   /api/auth/login             {email, password} → 200 {token, user}
POST   /api/auth/logout            → {ok}

GET    /api/environments           → {environments: [...summaries]}
POST   /api/environments           {name, industry_template} → 201
GET    /api/environments/:id       → detail (nodes, edges, sensor_bindings)
DELETE /api/environments/:id
POST   /api/environments/:id/nodes           {display_name, node_type}
PATCH  /api/environments/:id/nodes/:node_id  {display_name?, node_type?}
DELETE /api/environments/:id/nodes/:node_id
POST   /api/environments/:id/edges           {source, target, relationship_type, criticality}
DELETE /api/environments/:id/edges/:edge_id
POST   /api/environments/:id/sensor-bindings {node_id, mqtt_topic, unit,
                                              warning_threshold?, failure_threshold?,
                                              baseline?}
PATCH  /api/environments/:id/sensor-bindings/:binding_id {warning_threshold?, failure_threshold?}
DELETE /api/environments/:id/sensor-bindings/:binding_id
PATCH  /api/environments/:id                 {name?, industry_template?}   (409 on duplicate name)

GET    /api/environments/:id/state  → the polled payload (17.4), ~2s interval
GET    /api/methods                 → honesty labels for the three components
GET    /api/health
```

All environment routes require `Authorization: Bearer <jwt>` and enforce
exactly one check: the environment's `user_id` must equal the token's
subject (404, not 403, when it does not — no existence leak). No other
permission logic exists in v1.

### 17.4 `GET /api/environments/:id/state` (polled every ~2s)

```json
{
  "nodes": [{ "id": 1, "display_name": "...", "node_type": "pump",
              "status": "failed", "current_value": 82.0,
              "last_updated": "...", "anomaly_score": 0.0, "warm_up": false,
              "at_risk": true, "eta_seconds": 300.0,
              "predicted_path": ["Cooling Pump", "Treatment Unit"],
              "position_x": 60.0, "position_y": 160.0,
              "bindings": [{ "topic": "...", "unit": "degC",
                             "warning_threshold": 60.0, "failure_threshold": 75.0,
                             "state": "failed", "if_state": null,
                             "if_score": null, "calibrated": false,
                             "warm_up": true, "samples": 4, "trend": [ ... ] }] }],
  "edges": [{ "id": 1, "source": 1, "target": 2, "relationship_type": "feeds",
              "criticality": 0.9, "active_cascade": true }],
  "active_cascade": { "origin_node_id": 1, "origin_node_name": "...",
                      "affected_nodes": [2], "affected_node_names": ["..."],
                      "active_edges": ["1->2"], "method": "... (not trained)" },
  "intervention": { "recommended_node_id": 2, "recommended_node_name": "...",
                    "score": 0.58, "score_breakdown": { "...": 0.0 },
                    "explanation": "...", "method": "heuristic..." },
  "ranked": [ "...same entries as v3 Section 7 ranking, with node_name and downstream_node_names..." ],
  "before_after": { "before": {"downstream_systems_affected": 1},
                    "after": {"downstream_systems_affected": 1},
                    "headline": "Downstream systems affected: 1 -> 1",
                    "method": "projected footprint..." } ,
  "validation_metrics": { "precision": 0.0, "recall": 0.0,
                          "scope_label": "Detector agreement ... NOT accuracy against labeled failures",
                          "warm_up": false, "bindings_tracked": 2 }
}
```

- `active_cascade`, `intervention`, `before_after` are **null** when there
  is no live cascade. `before_after` is a *projection* computed by the
  backend while a cascade is active (acting on the recommended node contains
  the cascade; already-reached nodes count as affected) — it replaces v3's
  `/api/impact/before-after`.
- `validation_metrics` is **null** before any data exists, carries the
  warm-up disclosure (`warm_up: true`, no numbers) until every tracked
  binding's Isolation Forest has calibrated (>= 30 live samples), then shows
  cross-detector agreement with the mandatory scope label. It is never
  presented as accuracy against labeled failures — no labeled ground truth
  exists in live mode.
- A node with bound topics but no data yet reports `status: "offline"`.
- The IF's warning cutpoint is the 99th percentile of its own training
  scores (data-derived, never invented); failure is beyond the historical
  maximum (normalized score >= 1.0). Thresholds and method labels always
  travel with the payload; the frontend renders them verbatim.

### 17.5 Status definitions, scoring, disclosure — unchanged

v3 Section 8 status colors/cues, Section 11 locked weights
(0.35/0.30/0.20/0.15, "FOCUS HERE FIRST"), and the Section 13 boundaries
(backend computes / frontend renders, polling only, disclosures surfaced,
~300-500ms transitions) carry over **unchanged**.

### 17.6 Routes

```
/                      Briefing (public; Framer Motion whileInView + GSAP
                       ScrollTrigger scrub + Lenis — this route ONLY;
                       dashboard scrolls natively, no scroll-hijacking)
/login, /signup        Auth forms (public; redirect to /environments when
                       already signed in)
/environments          Picker (auth)
/environments/new      Builder (auth; simple forms, no graph editor)
/dashboard/:environmentId  Dashboard (auth; scoped, no simulate controls)
```

### 17.7 Integration checklist (v4)

- [x] Signup → login → environments all return JWTs; wrong password = 401; duplicate email = 409
- [x] Every environment route 401s without a token and 404s for other users' environments
- [x] Cold-start thresholds = baseline ×1.2 / ×1.5 (verified: 50 → 60/75)
- [x] MQTT ingestion resolves topics dynamically from sensor_bindings (no restart needed for new bindings)
- [x] Sustained values above the failure threshold flip the node to failed within one poll
- [x] Propagation marks the user's edges active_cascade; ranking uses the locked weights (0.58 verified for the reference two-node case)
- [x] Warm-up disclosure shows instead of fake metrics; scope label always present
- [x] No simulate/replay control exists anywhere in the UI
- [x] Lenis + ScrollTrigger exist only on `/`; dashboard uses native scrolling
- [x] Backend smoke suite green (12 tests; real-broker test auto-skips when 1883 is blocked)
