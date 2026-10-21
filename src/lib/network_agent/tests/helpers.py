"""测试共用的参数、时间函数和 demo 拓扑。"""

from datetime import datetime, timezone

UTC = timezone.utc

CFG = {"slot_seconds": 900, "horizon_seconds": 86400, "reserve_ttl_seconds": 60, "max_paths": 3,
       "rate_step_gbps": 10}


def t(hh, mm=0, day=20):
    return datetime(2026, 10, day, hh, mm, tzinfo=UTC)


# slide 3 的物理网络:aps-beamline-8id ─APS-LCRC─ anl-n01 ─L0─ anl-n02 ─L1─ esnet-atl ─L2─ esnet-chi ─L3─ ornl-n01
# 链路名取自 slide 3;slide 未标容量,这里假设均为 100 Gbps。
# esnet-nash 及 L4 / L5(各 40 Gbps)是为多路径测试虚构的第二条 transit 路径,不在 slide 中。
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

# 测试传输的两端:ANL 里紧挨 ESnet 的 anl-n02 → ORNL 的 ornl-n01
SRC, DST = "anl-n02", "ornl-n01"
L1 = "L1:anl-n02>esnet-atl"
L2 = "L2:esnet-atl>esnet-chi"                 # slide 7 场景里被他人占用的那一跳
L2_BACK = "L2:esnet-chi>esnet-atl"
L3 = "L3:esnet-chi>ornl-n01"
L4 = "L4:esnet-atl>esnet-nash"
L5 = "L5:esnet-nash>esnet-chi"
MAIN = (L1, L2, L3)                           # 主路径,3 跳
ALT = (L1, L4, L5, L3)                        # 经 esnet-nash 绕行,4 跳;与 MAIN 共用 L1、L3
