"""Step 3b:SENSE 接口与 mock。两阶段生命周期、对照模拟网络的准入、VLAN 分配、注入失败。"""

import pytest
from pydantic import ValidationError

from src.lib.network_agent.schemas import ServiceIntent, Terminal
from src.lib.network_agent.sense import MockSense, SenseError
from src.lib.network_agent.sim import MockNetwork
from src.lib.network_agent.telemetry import MockTelemetry
from src.lib.network_agent.topology import Topology
from src.lib.network_agent.tests.helpers import TOPO, t

L2 = "L2:esnet-chi>esnet-atl"
MAIN = ["L1:anl-dtn01>esnet-chi", L2, "L3:esnet-atl>ornl-esgf"]


@pytest.fixture
def net():
    return MockNetwork(Topology.from_dict(TOPO))


@pytest.fixture
def sense(net):
    return MockSense(net, vlan_range=(3001, 3002))


def intent(mbps=40_000, **over):
    base = dict(alias="scinet-c1", terminals=[Terminal(uri="urn:anl"), Terminal(uri="urn:ornl")],
                capacity_mbps=mbps, qos_class="guaranteedCapped", start=t(9), end=t(10), path_inclusion=MAIN)
    return ServiceIntent(**(base | over))


# ── ServiceIntent 校验 ────────────────────────────────────────────────────

@pytest.mark.parametrize("over", [
    {"terminals": [Terminal(uri="urn:anl")]},                                  # 只有一个端点
    {"terminals": [Terminal(uri="urn:anl"), Terminal(uri="urn:anl")]},         # 两端相同
    {"start": t(10), "end": t(9)},                                             # 时段颠倒
    {"qos_class": "premium"},                                                  # 不是 SENSE 的四种 QoS 之一
    {"capacity_mbps": 0},
])
def test_bad_intent(over):
    with pytest.raises(ValidationError):
        intent(**over)


# ── 两阶段生命周期 ────────────────────────────────────────────────────────

def test_propagate_commit_cancel(sense):
    s = sense.propagate(intent(), now=t(8))
    assert (s.state, s.vlan, s.alias) == ("reserved", 3001, "scinet-c1")
    s = sense.commit(s.instance_id, now=t(8, 1))
    assert (s.state, s.changed_at) == ("committed", t(8, 1))
    s = sense.cancel(s.instance_id, now=t(8, 2))
    assert (s.state, s.vlan) == ("cancelled", None)
    assert sense.state(s.instance_id).state == "cancelled"


def test_cancel_a_reserved_instance(sense):
    s = sense.propagate(intent(), now=t(8))
    assert sense.cancel(s.instance_id, now=t(8, 1)).state == "cancelled"


@pytest.mark.parametrize("bad", ["commit_twice", "commit_unknown", "cancel_twice"])
def test_invalid_transitions(sense, bad):
    s = sense.propagate(intent(), now=t(8))
    if bad == "commit_twice":
        sense.commit(s.instance_id, now=t(8))
        with pytest.raises(SenseError) as e:
            sense.commit(s.instance_id, now=t(8))
        assert e.value.reason == "invalid_state"
    elif bad == "commit_unknown":
        with pytest.raises(SenseError) as e:
            sense.commit("si-999", now=t(8))
        assert e.value.reason == "not_found"
    else:
        sense.cancel(s.instance_id, now=t(8))
        with pytest.raises(SenseError) as e:
            sense.cancel(s.instance_id, now=t(8))
        assert e.value.reason == "invalid_state"


def test_vlan_pool_and_reuse(sense):
    a = sense.propagate(intent(10_000), now=t(8))
    b = sense.propagate(intent(10_000), now=t(8))
    assert (a.vlan, b.vlan) == (3001, 3002)
    with pytest.raises(SenseError) as e:
        sense.propagate(intent(10_000), now=t(8))                 # 池里只有两个
    assert e.value.reason == "no_vlan"
    sense.cancel(a.instance_id, now=t(8))
    assert sense.propagate(intent(10_000), now=t(8)).vlan == 3001  # 归还后可复用


# ── 对照模拟网络的准入 ────────────────────────────────────────────────────

def test_admission_sees_foreign_traffic(net, sense):
    net.add_foreign(L2, t(9, 30), t(10), 40)                  # 只占后半段,也要算
    with pytest.raises(SenseError) as e:
        sense.propagate(intent(70_000), now=t(8))
    assert e.value.reason == "insufficient_capacity"
    assert sense.propagate(intent(60_000), now=t(8)).state == "reserved"


def test_admission_sees_outage(net, sense):
    net.add_outage("L3", t(9, 50), t(10, 30))
    with pytest.raises(SenseError):
        sense.propagate(intent(1_000), now=t(8))


def test_ours_counts_for_sense_but_not_for_telemetry(net, sense):
    """我们预留 60 后:SENSE 只剩 40 可给;telemetry 仍报 100(口径:不算我们自己)。"""
    s = sense.propagate(intent(60_000), now=t(8))
    with pytest.raises(SenseError):
        sense.propagate(intent(50_000), now=t(8))
    tele = MockTelemetry(net, validity_seconds=300)
    assert tele.link_samples([L2], t(9), t(10), now=t(8))[0].available_gbps == 100
    sense.cancel(s.instance_id, now=t(8))
    assert sense.propagate(intent(50_000), now=t(8)).state == "reserved"   # 归还后容量回来


# ── 注入失败 ──────────────────────────────────────────────────────────────

def test_injected_commit_failure_leaves_reserved(sense):
    s = sense.propagate(intent(), now=t(8))
    sense.fail_next("commit")
    with pytest.raises(SenseError) as e:
        sense.commit(s.instance_id, now=t(8))
    assert e.value.reason == "injected"
    assert sense.state(s.instance_id).state == "reserved"     # 失败不改变状态
    assert sense.commit(s.instance_id, now=t(8)).state == "committed"   # 只失败一次


def test_injected_propagate_failure_takes_nothing(net, sense):
    sense.fail_next("propagate")
    with pytest.raises(SenseError):
        sense.propagate(intent(100_000), now=t(8))
    assert net.headroom(tuple(MAIN), t(9), t(10)) == 100
