"""ChainBreak backend — FastAPI app (v4).

Run (from backend/):  .venv/Scripts/python.exe -m uvicorn app.main:app --port 8089

v4: dataset replay and the fixed N1-N6 graph are gone. Live data arrives
only via MQTT (Wokwi) into user-defined environments (Section 6). There is
no simulate-failure endpoint anywhere in the product — the operator
fallback is an external script (Section 6.3, ops/fallback_publish.py).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as auth_api
from app.api import environments as env_api
from app.db import init_db
from app.ingestion import mqtt_subscriber

logging.basicConfig(level=logging.INFO)

# Honesty labels for all three AI components (v3 Section 10 standard, v4
# wording per build prompt Section 7).
METHODS = {
    "components": [
        {"name": "Anomaly detection",
         "method": ("trained Isolation Forest (scikit-learn) per sensor "
                    "binding, trained live after a disclosed warm-up of "
                    "~30 readings; user-set thresholds until then")},
        {"name": "Propagation estimation",
         "method": ("probabilistic model over anomaly score x edge "
                    "criticality (not trained); assumed 300s per hop, "
                    "disclosed in every payload")},
        {"name": "Intervention ranking",
         "method": ("heuristic scoring model with locked v1 weights "
                    "0.35/0.30/0.20/0.15 (not trained/learned)")},
    ]
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    mqtt_subscriber.start()
    yield
    mqtt_subscriber.stop()


app = FastAPI(title="ChainBreak API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router)
app.include_router(env_api.router)


@app.get("/api/methods")
def get_methods():
    """Honesty labels for all three AI components (Section 7)."""
    return METHODS


@app.get("/api/health")
def health():
    return {"ok": True}
