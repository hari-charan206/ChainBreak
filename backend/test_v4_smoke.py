"""v4 end-to-end smoke test (run: backend/.venv/Scripts/python.exe test_v4_smoke.py).

Exercises the full pipeline against a temporary DB and a REAL HiveMQ
round-trip when the broker is reachable, with a direct-write fallback so
the test always verifies the full path: auth -> environment -> nodes ->
edge -> binding (cold-start defaults) -> MQTT ingestion -> /state payload
-> propagation -> ranking -> validation. Attacker protection checks too.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("ANOMALY_MIN_TRAIN", "8")

# Isolation Forest calibration needs 30+ samples in production; the demo
# script chain below produces fewer. Lower the bar for this run only.
import app.ai.anomaly_detection as ad
ad.MIN_TRAIN_SAMPLES = 8
ad.REFIT_EVERY_NEW_SAMPLES = 1
ad.SUSTAIN_SAMPLES = 3
import app.ingestion.mqtt_subscriber as sub
sub._subscribed_topics = set()

import app.db as db

# Isolate from the developer's real chainbreak.db
_tmpdir = tempfile.mkdtemp(prefix="chainbreak-smoke-")
db.DB_PATH = os.path.join(_tmpdir, "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _record(topic: str, value: float) -> None:
    """Feed a value through the same code path the broker message takes."""
    sub._resolve_and_store(topic, str(value).encode())


class V4SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    # ---- 1. health + auth ----

    def test_01_health(self):
        self.assertEqual(client.get("/api/health").json(), {"ok": True})

    def test_02_signup_login(self):
        r = client.post("/api/auth/signup", json={
            "email": "demo@example.com", "password": "hunter2hunter2"})
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertIn("token", body)
        self.assertEqual(body["user"]["email"], "demo@example.com")
        V4SmokeTest.token = body["token"]

        # duplicate signup rejected
        r2 = client.post("/api/auth/signup", json={
            "email": "demo@example.com", "password": "hunter2hunter2"})
        self.assertEqual(r2.status_code, 409)

        # wrong password rejected with 401
        r3 = client.post("/api/auth/login", json={
            "email": "demo@example.com", "password": "wrongpass99"})
        self.assertEqual(r3.status_code, 401)

        # login works
        r4 = client.post("/api/auth/login", json={
            "email": "demo@example.com", "password": "hunter2hunter2"})
        self.assertEqual(r4.status_code, 200)
        self.assertIn("token", r4.json())

    def test_03_auth_required(self):
        r = client.get("/api/environments")
        self.assertEqual(r.status_code, 401)
        r = client.get("/api/environments",
                       headers={"Authorization": "Bearer not-a-jwt"})
        self.assertEqual(r.status_code, 401)

    # ---- 2. environments + builder ----

    def test_10_create_environment(self):
        r = client.post("/api/environments",
                        headers=_h(), json={"name": "Demo Plant",
                                            "industry_template": "Water Treatment"})
        self.assertEqual(r.status_code, 201)
        env = r.json()
        V4SmokeTest.env_id = env["id"]

        lst = client.get("/api/environments", headers=_h()).json()
        self.assertEqual(len(lst["environments"]), 1)
        self.assertEqual(lst["environments"][0]["node_count"], 0)
        self.assertEqual(lst["environments"][0]["status_summary"], "no nodes yet")

    def test_11_add_nodes_edge_binding(self):
        h = _h()
        r = client.post(f"/api/environments/{V4SmokeTest.env_id}/nodes",
                        headers=h, json={"display_name": "Cooling Pump",
                                         "node_type": "pump"})
        self.assertEqual(r.status_code, 201)
        V4SmokeTest.n1 = r.json()["id"]
        r = client.post(f"/api/environments/{V4SmokeTest.env_id}/nodes",
                        headers=h, json={"display_name": "Treatment Unit",
                                         "node_type": "control_unit"})
        V4SmokeTest.n2 = r.json()["id"]

        # edge with criticality slider value
        r = client.post(f"/api/environments/{V4SmokeTest.env_id}/edges",
                        headers=h, json={"source": V4SmokeTest.n1,
                                         "target": V4SmokeTest.n2,
                                         "relationship_type": "feeds",
                                         "criticality": 0.9})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["criticality"], 0.9)

        # binding with baseline only -> locked cold-start defaults apply
        r = client.post(
            f"/api/environments/{V4SmokeTest.env_id}/sensor-bindings",
            headers=h,
            json={"node_id": V4SmokeTest.n1,
                  "mqtt_topic": "chainbreak/env1/cooling/temp",
                  "unit": "degC", "baseline": 50.0})
        self.assertEqual(r.status_code, 201)
        b = r.json()
        self.assertEqual(b["warning_threshold"], 60.0)   # 50 x 1.2
        self.assertEqual(b["failure_threshold"], 75.0)   # 50 x 1.5
        V4SmokeTest.b1 = b["id"]

        # duplicate topic rejected
        r = client.post(
            f"/api/environments/{V4SmokeTest.env_id}/sensor-bindings",
            headers=h,
            json={"node_id": V4SmokeTest.n2,
                  "mqtt_topic": "chainbreak/env1/cooling/temp"})
        self.assertEqual(r.status_code, 409)

        # failure threshold <= warning threshold rejected
        r = client.post(
            f"/api/environments/{V4SmokeTest.env_id}/sensor-bindings",
            headers=h,
            json={"node_id": V4SmokeTest.n1, "mqtt_topic": "chainbreak/x/y",
                  "warning_threshold": 10.0, "failure_threshold": 5.0})
        self.assertEqual(r.status_code, 422)

        # second binding on the downstream node
        r = client.post(
            f"/api/environments/{V4SmokeTest.env_id}/sensor-bindings",
            headers=h,
            json={"node_id": V4SmokeTest.n2,
                  "mqtt_topic": "chainbreak/env1/treatment/level",
                  "unit": "%", "baseline": 40.0})
        V4SmokeTest.b2 = r.json()["id"]

    def test_12_ownership(self):
        # second user cannot see or mutate user 1's environment
        tok2 = client.post("/api/auth/signup", json={
            "email": "other@example.com", "password": "hunter2hunter2"
        }).json()["token"]
        r = client.get(f"/api/environments/{V4SmokeTest.env_id}",
                       headers={"Authorization": f"Bearer {tok2}"})
        self.assertEqual(r.status_code, 404)
        r = client.post(f"/api/environments/{V4SmokeTest.env_id}/nodes",
                        headers={"Authorization": f"Bearer {tok2}"},
                        json={"display_name": "Evil Node"})
        self.assertEqual(r.status_code, 404)

    def test_13_state_before_data(self):
        state = client.get(f"/api/environments/{V4SmokeTest.env_id}/state",
                           headers=_h()).json()
        self.assertEqual(state["environment_id"], V4SmokeTest.env_id)
        for n in state["nodes"]:
            self.assertEqual(n["status"], "offline")  # no data yet (6.4)
        self.assertIsNone(state["active_cascade"])
        self.assertIsNone(state["intervention"])
        self.assertIsNone(state["validation_metrics"])

    # ---- 3. MQTT path + AI layer ----

    def test_20_normal_data_everything_healthy(self):
        for v in (49.0, 50.0, 51.0, 50.5):
            _record("chainbreak/env1/cooling/temp", v)
            _record("chainbreak/env1/treatment/level", 40.0)
            time.sleep(0.01)
        state = _state()
        nodes = {n["display_name"]: n for n in state["nodes"]}
        self.assertEqual(nodes["Cooling Pump"]["status"], "healthy")
        self.assertEqual(nodes["Treatment Unit"]["status"], "healthy")
        self.assertEqual(nodes["Cooling Pump"]["current_value"], 50.5)
        self.assertIsNone(state["active_cascade"])
        self.assertIsNone(state["intervention"])

        # warm-up disclosure while below the calibration minimum (Section 7.1)
        vm = state["validation_metrics"]
        self.assertIsNotNone(vm)
        self.assertTrue(vm["warm_up"])
        self.assertIn("Warm-up", vm["scope_label"])

    def test_21_failure_triggers_full_chain(self):
        # sustained failure-threshold values (75.0 = 50 x 1.5)
        for v in (80.0, 81.0, 82.0, 83.0, 84.0):
            _record("chainbreak/env1/cooling/temp", v)
            time.sleep(0.01)
        state = _state()
        nodes = {n["display_name"]: n for n in state["nodes"]}
        self.assertEqual(nodes["Cooling Pump"]["status"], "failed")

        # propagation over the user's edge (Section 7.2)
        self.assertIsNotNone(state["active_cascade"])
        ac = state["active_cascade"]
        self.assertEqual(ac["origin_node_id"], V4SmokeTest.n1)
        self.assertEqual(ac["affected_nodes"], [V4SmokeTest.n2])
        self.assertEqual(ac["affected_node_names"], ["Treatment Unit"])
        self.assertTrue(
            any(e["active_cascade"] for e in state["edges"]),
            "the user-defined edge should be marked active_cascade")

        # locked-weight intervention ranking (Section 7.3). The origin pump
        # is failed; the heuristic's time-to-impact and criticality factors
        # legitimately favor the downstream Treatment Unit (chokepoint),
        # mirroring v3's contract example where N4 outranked failed N3.
        self.assertIsNotNone(state["intervention"])
        iv = state["intervention"]
        self.assertEqual(iv["recommended_node_id"], V4SmokeTest.n2)

        # full locked-weight arithmetic for the chokepoint, hardcoded:
        # propagation_prob = 1.0 (origin anomaly) x 0.9 (edge criticality)
        # eta = 300s (assumed hop) -> tti_inv = 1 - 300/2400 = 0.875
        # downstream_count_norm = 0 (nothing downstream of it)
        # criticality = 0.9 (its incoming edge)
        # score = 0.35(0) + 0.30(0.9) + 0.20(0.875) + 0.15(0.9) = 0.58
        bd = iv["score_breakdown"]
        self.assertEqual(bd["downstream_count_norm"], 0.0)
        self.assertEqual(bd["propagation_prob"], 0.9)
        self.assertEqual(bd["time_to_impact_inv_norm"], 0.875)
        self.assertEqual(bd["criticality"], 0.9)
        self.assertEqual(iv["score"], 0.58)
        self.assertIn("0.35", iv["explanation"])

        # ranked list carries downstream info for each candidate
        by_id = {r["node_id"]: r for r in state["ranked"]}
        self.assertEqual(by_id[V4SmokeTest.n1]["downstream_node_names"],
                         ["Treatment Unit"])
        self.assertIn("heuristic", iv["method"])

        # honesty labels present everywhere they must be
        self.assertIn("heuristic", iv["method"])
        self.assertIn("not trained", ac["method"])

        # validation panel: past warm-up here (>= min samples in this test
        # run), with the mandatory NOT-labeled-accuracy scope label
        self.assertIsNotNone(state["validation_metrics"])
        vm = state["validation_metrics"]
        self.assertFalse(vm["warm_up"])
        self.assertIn("NOT accuracy", vm["scope_label"])

        # cold-start formula reflected in binding payload
        b = nodes["Cooling Pump"]["bindings"][0]
        self.assertEqual(b["warning_threshold"], 60.0)
        self.assertEqual(b["failure_threshold"], 75.0)

    def test_22_if_calibrates_after_min_samples(self):
        for v in (49.0, 50.5, 51.0, 50.0, 49.5, 50.5, 51.0, 50.0):
            _record("chainbreak/env1/treatment/level", v)
            _record("chainbreak/env1/cooling/temp", 80.5)
            time.sleep(0.01)
        state = _state()
        nodes = {n["display_name"]: n for n in state["nodes"]}
        lvl = nodes["Treatment Unit"]["bindings"][0]
        self.assertGreaterEqual(lvl["samples"], 12)
        self.assertTrue(lvl["calibrated"])
        self.assertFalse(lvl["warm_up"])
        self.assertIsNotNone(lvl["if_score"])
        # metrics no longer in warm-up
        vm = state["validation_metrics"]
        self.assertFalse(vm["warm_up"])
        self.assertIn("NOT accuracy", vm["scope_label"])

    def test_23_recovery_when_values_return(self):
        for v in (50.0, 50.5, 49.5, 50.0, 50.5):
            _record("chainbreak/env1/cooling/temp", v)
            time.sleep(0.01)
        state = _state()
        nodes = {n["display_name"]: n for n in state["nodes"]}
        self.assertEqual(nodes["Cooling Pump"]["status"], "healthy")
        self.assertIsNone(state["active_cascade"])

    def test_90_hivemq_roundtrip(self):
        """Real-broker round trip, skipped if broker unreachable.

        Publishes through paho to HiveMQ and asserts the subscriber stored
        it — proving the Wokwi path end to end (Section 6.2).
        """
        topic = "chainbreak/smoke/hivemq/9f2e"
        client.post(
            f"/api/environments/{V4SmokeTest.env_id}/nodes", headers=_h(),
            json={"display_name": "Broker Probe", "node_type": "sensor"})
        env_full = client.get(f"/api/environments/{V4SmokeTest.env_id}",
                              headers=_h()).json()
        probe = next(n for n in env_full["nodes"]
                     if n["display_name"] == "Broker Probe")
        client.post(
            f"/api/environments/{V4SmokeTest.env_id}/sensor-bindings",
            headers=_h(),
            json={"node_id": probe["id"], "mqtt_topic": topic,
                  "unit": "%", "baseline": 30.0})

        import paho.mqtt.client as mqtt
        pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                          protocol=mqtt.MQTTv311)
        try:
            pub.connect("broker.hivemq.com", 1883, 30)
            pub.loop_start()
            pub.publish(topic, "42.5", qos=0)
            time.sleep(4.0)
            pub.loop_stop()
            pub.disconnect()
        except Exception:
            self.skipTest("broker.hivemq.com unreachable from this network")
            return
        state = _state()
        probe_node = next(n for n in state["nodes"]
                          if n["display_name"] == "Broker Probe")
        self.assertEqual(probe_node["status"], "healthy")
        self.assertEqual(probe_node["current_value"], 42.5)


def _h():
    return {"Authorization": f"Bearer {V4SmokeTest.token}"}


def _state():
    r = client.get(f"/api/environments/{V4SmokeTest.env_id}/state",
                   headers=_h())
    assert r.status_code == 200, r.text
    return r.json()


if __name__ == "__main__":
    unittest.main(verbosity=2)
