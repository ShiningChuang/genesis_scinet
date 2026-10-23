"""Parameters, time helper and demo topology shared by the tests."""

from datetime import datetime, timezone

UTC = timezone.utc

CFG = {"slot_seconds": 900, "horizon_seconds": 86400, "reserve_ttl_seconds": 60, "max_paths": 3,
       "rate_step_gbps": 10}


def t(hh, mm=0, day=20):
    return datetime(2026, 10, day, hh, mm, tzinfo=UTC)


# The physical network of slide 3: aps-beamline-8id ─APS-LCRC─ anl-n01 ─L0─ anl-n02 ─L1─ esnet-atl ─L2─ esnet-chi ─L3─ ornl-n01
# Link names are from slide 3; the slide gives no capacities, so all are assumed to be 100 Gbps.
# esnet-nash and L4 / L5 (40 Gbps each) are a made-up second transit path for multi-path tests; not in the slide.
TOPO = {
    "nodes": ["aps-beamline-8id", "anl-n01", "anl-n02", "esnet-atl", "esnet-chi", "esnet-nash", "ornl-n01"],
    "links": [
        {"id": "APS-LCRC", "a": "aps-beamline-8id", "b": "anl-n01", "capacity_gbps": 100},
        {"id": "L0", "a": "anl-n01", "b": "anl-n02", "capacity_gbps": 100},
        {"id": "L1", "a": "anl-n02", "b": "esnet-atl", "capacity_gbps": 100},
        {"id": "L2", "a": "esnet-atl", "b": "esnet-chi", "capacity_gbps": 100},
        {"id": "L3", "a": "esnet-chi", "b": "ornl-n01", "capacity_gbps": 100},
        {"id": "L4", "a": "esnet-atl", "b": "esnet-nash", "capacity_gbps": 40},
        {"id": "L5", "a": "esnet-nash", "b": "esnet-chi", "capacity_gbps": 40},
    ],
}

# Endpoints of the test transfers: anl-n02 (the ANL node next to ESnet) → ornl-n01 at ORNL
SRC, DST = "anl-n02", "ornl-n01"
L1 = "L1:anl-n02>esnet-atl"
L2 = "L2:esnet-atl>esnet-chi"                 # the hop used by foreign traffic in the slide-7 scenario
L2_BACK = "L2:esnet-chi>esnet-atl"
L3 = "L3:esnet-chi>ornl-n01"
L4 = "L4:esnet-atl>esnet-nash"
L5 = "L5:esnet-nash>esnet-chi"
MAIN = (L1, L2, L3)                           # main path, 3 hops
ALT = (L1, L4, L5, L3)                        # detour via esnet-nash, 4 hops; shares L1 and L3 with MAIN
