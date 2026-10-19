"""测试共用的参数、时间函数和 demo 拓扑。"""

from datetime import datetime, timezone

UTC = timezone.utc

CFG = {"slot_seconds": 900, "horizon_seconds": 86400, "reserve_ttl_seconds": 60, "max_paths": 3}


def t(hh, mm=0, day=20):
    return datetime(2026, 10, day, hh, mm, tzinfo=UTC)


# slide 3 的数据路径 APS → ANL → ESnet → ORNL,只保留与网络相关的端点。
# esnet-nash 及 L4/L5 是为多路径测试虚构的第二条 transit 路径,不在 slide 中。
TOPO = {
    "nodes": ["aps-beamline-8id", "anl-dtn01", "esnet-chi", "esnet-atl", "esnet-nash", "ornl-esgf"],
    "links": [
        {"id": "L0", "a": "aps-beamline-8id", "b": "anl-dtn01", "capacity_gbps": 100},
        {"id": "L1", "a": "anl-dtn01", "b": "esnet-chi", "capacity_gbps": 100},
        {"id": "L2", "a": "esnet-chi", "b": "esnet-atl", "capacity_gbps": 100},
        {"id": "L3", "a": "esnet-atl", "b": "ornl-esgf", "capacity_gbps": 100},
        {"id": "L4", "a": "esnet-chi", "b": "esnet-nash", "capacity_gbps": 40},
        {"id": "L5", "a": "esnet-nash", "b": "esnet-atl", "capacity_gbps": 40},
    ],
}
