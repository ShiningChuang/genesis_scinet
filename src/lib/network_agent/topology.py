"""网络拓扑:节点、链路、候选路径。

拓扑描述的是物理链路(无向,如光纤 L2 连接 esnet-chi 与 esnet-atl)。链路是全双工的,
两个方向各有一份完整容量,所以内部把每条物理链路拆成两条**有向链路**,
账本也按有向链路记账:A→B 方向占满,不影响 B→A。

有向链路 id 形如 ``L2:esnet-chi>esnet-atl``,一条路径 = 有向链路 id 的元组。
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, PositiveFloat, model_validator


class LinkSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    a: str
    b: str
    capacity_gbps: PositiveFloat   # 每个方向各自的配置容量(全双工、假设对称);来自 slide 14 的 WfPlatform 静态快照,用来初始化账本


class TopologySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: list[str]
    links: list[LinkSpec]

    @model_validator(mode="after")
    def _consistent(self):
        if len(set(self.nodes)) != len(self.nodes):
            raise ValueError("duplicate node id")
        if len({link.id for link in self.links}) != len(self.links):
            raise ValueError("duplicate link id")
        for link in self.links:
            if link.a == link.b:
                raise ValueError(f"link {link.id} is a self-loop")
            if not {link.a, link.b} <= set(self.nodes):
                raise ValueError(f"link {link.id} references an unknown node")
        return self


@dataclass(frozen=True)
class DirectedLink:
    id: str            # "L2:esnet-chi>esnet-atl"
    link_id: str       # 物理链路 "L2"
    src: str
    dst: str
    capacity_gbps: float


Path = tuple[str, ...]  # 有向链路 id 序列


class Topology:
    def __init__(self, spec: TopologySpec):
        self.nodes = list(spec.nodes)
        self.links: dict[str, DirectedLink] = {}
        self._out: dict[str, list[DirectedLink]] = {n: [] for n in spec.nodes}
        for s in spec.links:
            for src, dst in ((s.a, s.b), (s.b, s.a)):
                d = DirectedLink(f"{s.id}:{src}>{dst}", s.id, src, dst, s.capacity_gbps)
                self.links[d.id] = d
                self._out[src].append(d)

    @classmethod
    def from_dict(cls, d: dict) -> "Topology":
        return cls(TopologySpec.model_validate(d))

    def paths(self, src: str, dst: str, k: int) -> list[Path]:
        """src → dst 的无环路径,按 (跳数, 链路 id) 排序,最多 k 条;没有路径时返回空列表。

        穷举所有无环路径,只适合 demo 规模的拓扑;拓扑变大后换成 Yen 的 k 最短路径。
        """
        for n in (src, dst):
            if n not in self._out:
                raise KeyError(f"unknown node {n!r}")
        found: list[Path] = []

        def walk(node: str, visited: set[str], path: list[str]) -> None:
            if node == dst:
                found.append(tuple(path))
                return
            for d in self._out[node]:
                if d.dst not in visited:
                    walk(d.dst, visited | {d.dst}, path + [d.id])

        walk(src, {src}, [])
        return sorted(found, key=lambda p: (len(p), p))[:k]
