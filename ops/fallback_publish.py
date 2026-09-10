#!/usr/bin/env python
"""ChainBreak operator fallback (build prompt v4 Section 6.3).

NOT part of the product UI — a second-terminal rescue tool for demos when
the Wokwi/MQTT path hiccups (broker latency, venue network). It publishes a
value to a bound topic exactly as if it came from the device, so the normal
pipeline (dynamic topic lookup -> thresholds -> AI layer -> 2s poll) does
all the work. Keep this window off-screen during the demo and REHEARSE
beforehand — per Section 6.3 this must never become a hidden app feature.

Usage (from backend/, using the project venv):
  .venv/Scripts/python.exe ../ops/fallback_publish.py                 # interactive
  .venv/Scripts/python.exe ../ops/fallback_publish.py --topic chainbreak/env1/cooling/temp --value 82
  .venv/Scripts/python.exe ../ops/fallback_publish.py --sweep chainbreak/env1/cooling/temp 50 85 1.5

  --topic + --value : one publish, then exit
  --sweep T A B S   : publish values A..B step S every 1.5s on topic T
                      (hold the failing value to keep the node failed — the
                      sustain rule needs 5 consecutive samples)
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Same broker the backend uses (Section 12.5 default: HiveMQ). The env var
# mirrors the backend's so both halves can be pointed at a reachable
# broker on locked-down networks.
BROKER = os.environ.get("CHAINBREAK_MQTT_BROKER", "broker.hivemq.com")


def _client():
    import paho.mqtt.client as mqtt

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
    c.connect(BROKER, 1883, 30)
    c.loop_start()
    return c


def publish_once(topic: str, value: str) -> None:
    c = _client()
    try:
        # bound topics always resolve via the DB; unbound ones are ignored
        # by the subscriber — print a reminder either way
        info = c.publish(topic, value, qos=0)
        info.wait_for_publish(timeout=5)
        print(f"[{time.strftime('%H:%M:%S')}] {topic} <- {value}")
    finally:
        c.loop_stop()
        c.disconnect()


def sweep(topic: str, start: float, end: float, step: float) -> None:
    c = _client()
    try:
        values = []
        v = start
        while (step > 0 and v <= end) or (step < 0 and v >= end):
            values.append(round(v, 2))
            v += step
        print(f"sweeping {topic}: {values} (Ctrl+C to stop)")
        i = 0
        while True:
            payload = str(values[i % len(values)])
            c.publish(topic, payload, qos=0)
            print(f"[{time.strftime('%H:%M:%S')}] {topic} <- {payload}")
            i += 1
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        c.loop_stop()
        c.disconnect()


def interactive() -> None:
    print("ChainBreak operator fallback — publish to a bound topic.")
    print(f"Broker: {BROKER} (must match the backend's, Section 12.5)")
    while True:
        try:
            topic = input("topic (blank to quit): ").strip()
            if not topic:
                break
            value = input("value: ").strip()
            publish_once(topic, value)
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--topic")
    p.add_argument("--value")
    p.add_argument("--sweep", nargs=3, metavar=("TOPIC", "START", "END"),
                   help="sweep values; pair with --step")
    p.add_argument("--step", type=float, default=1.5)
    args = p.parse_args()

    if args.sweep:
        sweep(args.sweep[0], float(args.sweep[1]), float(args.sweep[2]), args.step)
    elif args.topic and args.value is not None:
        publish_once(args.topic, args.value)
    else:
        interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
