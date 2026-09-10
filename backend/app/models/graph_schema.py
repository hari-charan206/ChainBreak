"""Fixed demo environment schema — CONTRACT.md Sections 4-5.

Node IDs, tag mappings, display names, edge order and criticality values are
LOCKED. Do not add, remove or rename anything here without flagging the
change to the whole team (CONTRACT.md Section 14).
"""

# Near-zero-variance actuator/status columns confirmed in build-prompt v3
# Section 2. Excluded from baseline/threshold derivation.
EXCLUDED_ACTUATOR_COLUMNS = [
    "P202", "P301", "P401", "P403", "P404", "P502", "P601", "P603",
]

# Continuous sensor tag prefixes used for baseline search (build prompt 5.2
# step 1: only FIT/LIT/AIT/DPIT/PIT/UV tags are continuous readings).
CONTINUOUS_TAG_PREFIXES = ("FIT", "LIT", "AIT", "DPIT", "PIT", "UV")

NODES = [
    {
        "id": "N1",
        "display_name": "Intake / Power-Equivalent System",
        "tags": ["FIT101", "LIT101", "MV101", "P101", "P102"],
        "role": "Upstream origin point",
    },
    {
        "id": "N2",
        "display_name": "Dosing / Chemical System",
        "tags": ["AIT201", "AIT202", "AIT203", "FIT201", "MV201",
                 "P201", "P202", "P203", "P204", "P205", "P206"],
        "role": "First dependent system",
    },
    {
        "id": "N3",
        "display_name": "Cooling-Equivalent (Ultrafiltration) System",
        "tags": ["DPIT301", "FIT301", "LIT301", "MV301", "MV302",
                 "MV303", "MV304", "P301", "P302"],
        "role": 'Represents "Cooling System" in the original narrative',
    },
    {
        "id": "N4",
        "display_name": "Production / Treatment Machine (De-chlorination)",
        "tags": ["AIT401", "AIT402", "FIT401", "LIT401",
                 "P401", "P402", "P403", "P404", "UV401"],
        "role": 'Represents "Production Machine"',
    },
    {
        "id": "N5",
        "display_name": "Control System (Reverse Osmosis)",
        "tags": ["AIT501", "AIT502", "AIT503", "AIT504", "FIT501",
                 "FIT502", "FIT503", "FIT504", "P501", "P502",
                 "PIT501", "PIT502", "PIT503"],
        "role": 'Represents "Control System"',
    },
    {
        "id": "N6",
        "display_name": "Safety / Backwash System",
        "tags": ["FIT601", "P601", "P602", "P603"],
        "role": "Final downstream / safety-critical node",
    },
]

# Fixed dependency edges: N1 -> N2 -> N3 -> N4 -> N5 -> N6 (hardcoded).
EDGES = [
    {"from": "N1", "to": "N2", "criticality": 0.5},
    {"from": "N2", "to": "N3", "criticality": 0.7},
    {"from": "N3", "to": "N4", "criticality": 0.9},
    {"from": "N4", "to": "N5", "criticality": 0.8},
    {"from": "N5", "to": "N6", "criticality": 1.0},  # safety-critical edge
]

NODE_BY_ID = {n["id"]: n for n in NODES}
TAG_TO_NODE = {tag: n["id"] for n in NODES for tag in n["tags"]}

CONTINUOUS_TAGS_BY_NODE = {
    n["id"]: [t for t in n["tags"] if t.startswith(CONTINUOUS_TAG_PREFIXES)]
    for n in NODES
}
ALL_CONTINUOUS_TAGS = [
    t for n in NODES for t in CONTINUOUS_TAGS_BY_NODE[n["id"]]
]

NODE_STATUSES = ["healthy", "warning", "failed", "offline"]

# Actuator/status tags (on/off pumps, motorized valves, UV lamp state) are
# DISPLAYED but do not drive node warning/failed state — same principle as
# the file-wide exclusion of the 8 near-zero-variance actuator columns
# (build prompt Section 2): a pump cycling off is plant operation, not a
# sensor anomaly. Continuous FIT/LIT/AIT/DPIT/PIT readings drive status.
STATUS_TAG_PREFIXES = ("P", "MV", "UV")


def is_status_tag(tag: str) -> bool:
    return tag.startswith(STATUS_TAG_PREFIXES)
