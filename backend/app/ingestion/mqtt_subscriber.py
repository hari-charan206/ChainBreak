"""MQTT ingestion (v4 Section 6.2): shared broker, dynamically-bound topics.

- One shared connection to broker.hivemq.com (Section 12.5 confirmation);
  all environments' topics are namespaced by convention
  chainbreak/{environmentId}/{nodeId}/... but ANY topic string bound via
  sensor_bindings resolves — the topic->node lookup is the database, not
  a hardcoded tag map.
- On message: resolve binding via sensor_bindings.get_by_topic, record the
  reading, re-derive that node's status immediately (Section 6.2 steps 2-4).
- Topics are subscribed via a wildcard refresh so newly-created bindings
  work without a restart.

paho-mqtt 2.x callback API.
"""

from __future__ import annotations

import logging
import os
import threading

from paho.mqtt import client as mqtt_client

from app.ai import anomaly_detection
from app.db import get_conn
from app.models import nodes as nodes_model
from app.models import sensor_bindings as bindings_model

logger = logging.getLogger("chainbreak.mqtt")

# Locked default (Section 12.5): shared HiveMQ public broker. The env var
# exists ONLY so operators can point the whole stack (backend + fallback
# script) at a reachable broker on locked-down demo networks — documented
# in the run doc, never a UI setting.
BROKER = os.environ.get("CHAINBREAK_MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.environ.get("CHAINBREAK_MQTT_PORT", "1883"))
KEEPALIVE = 60

_state_lock = threading.Lock()
_subscribed_topics: set[str] = set()
_client: mqtt_client.Client | None = None


def _resolve_and_store(topic: str, payload: bytes) -> None:
    """Dynamic topic->node lookup (Section 6.2 step 2). Any of:
    - plain number:            72.5
    - JSON:                    {"value": 72.5}
    - Wokwi/Arduino JSON-ish:  {"value": 72.5, ...} (best-effort regex)
    """
    text = payload.decode("utf-8", errors="replace").strip()
    value: float | None = None
    try:
        value = float(text)
    except ValueError:
        import json
        import re
        m = re.search(r'"value"\s*:\s*(-?\d+(?:\.\d+)?)', text)
        if m:
            value = float(m.group(1))
        else:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, (int, float)):
                    value = float(parsed)
            except Exception:
                value = None
    if value is None:
        logger.debug("unparseable payload on %s: %r", topic, text[:80])
        return

    binding = bindings_model.get_by_topic(topic)
    if binding is None:
        logger.debug("message on unbound topic %s ignored", topic)
        return

    bindings_model.record_reading(binding["id"], value)
    _rederive_node_status(binding["node_id"])


def _rederive_node_status(node_id: int) -> None:
    """Re-evaluate the node from its bindings' trailing values (step 3-4)."""
    node = nodes_model.get(node_id)
    if node is None:
        return
    node_bindings = [b for b in
                     bindings_model.list_for_environment(
                         node["environment_id"])
                     if b["node_id"] == node_id]
    order = {"healthy": 0, "warning": 1, "failed": 2}
    worst = "offline"
    for b in node_bindings:
        values = bindings_model.recent_values(b["id"])
        if not values:
            continue
        det = anomaly_detection.detect_binding_state(b, values)
        state = det["state"] if det["state"] in order else "healthy"
        if worst == "offline" or order[state] > order[worst]:
            worst = state
    if node["status"] != worst:
        nodes_model.set_status(node_id, worst)


def _on_message(_client, _userdata, msg) -> None:
    try:
        _resolve_and_store(msg.topic, msg.payload)
    except Exception:  # never let one bad message kill the loop
        logger.exception("error handling message on %s", msg.topic)


def _on_connect(client, _userdata, _flags, rc, _properties=None) -> None:
    if rc != 0:
        logger.warning("mqtt connect failed rc=%s", rc)
        return
    with _state_lock:
        topics = set(bindings_model.topic_map().keys())
        # HiveMQ public broker: one broad wildcard keeps it simple and
        # still resolves only bound topics at message time.
        try:
            client.subscribe("chainbreak/#", qos=0)
            _subscribed_topics.add("chainbreak/#")
        except Exception:
            logger.exception("subscribe failed")
        for t in topics - {"chainbreak/#"}:
            if not t.startswith("chainbreak/"):
                try:
                    client.subscribe(t, qos=0)
                    _subscribed_topics.add(t)
                except Exception:
                    logger.exception("subscribe %s failed", t)


def _on_disconnect(*_args) -> None:
    logger.warning("mqtt disconnected; paho will auto-reconnect")


def start() -> None:
    """Start the subscriber (idempotent). Called from the app lifespan."""
    global _client
    with _state_lock:
        if _client is not None:
            return
    client = mqtt_client.Client(
        mqtt_client.CallbackAPIVersion.VERSION2,
        client_id=f"chainbreak-{id(object())}",
        protocol=mqtt_client.MQTTv311,
    )
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.on_disconnect = _on_disconnect
    client.connect_async(BROKER, PORT, KEEPALIVE)
    client.loop_start()
    with _state_lock:
        _client = client
    logger.info("mqtt subscriber started -> %s:%s", BROKER, PORT)


def stop() -> None:
    global _client
    with _state_lock:
        client, _client = _client, None
    if client is not None:
        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass


def refresh_subscriptions() -> None:
    """Re-subscribe after new bindings are created (called by the API)."""
    with _state_lock:
        client = _client
    if client is None or not client.is_connected():
        return
    topics = set(bindings_model.topic_map().keys())
    for t in topics - _subscribed_topics:
        try:
            client.subscribe(t, qos=0)
            _subscribed_topics.add(t)
        except Exception:
            logger.exception("subscribe %s failed", t)
