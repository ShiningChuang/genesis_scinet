"""Step 0:环境与骨架自检。运行:.venv/bin/python -m pytest src/lib/network_agent/tests"""

from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from src.lib.network_agent.config import load_config

CFG = {"slot_seconds": 900, "horizon_seconds": 86400, "reserve_ttl_seconds": 60}


def test_config_from_dict_and_section():
    assert load_config(CFG).slot_seconds == 900
    assert load_config({"tag": "x", "network_agent": CFG}).reserve_ttl_seconds == 60


def test_config_from_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("network_agent:\n  slot_seconds: 900\n  horizon_seconds: 86400\n  reserve_ttl_seconds: 60\n")
    assert load_config(p).horizon_seconds == 86400


@pytest.mark.parametrize("bad", [
    {k: v for k, v in CFG.items() if k != "slot_seconds"},  # 漏写
    {**CFG, "slot_secs": 900},                               # 拼错
    {**CFG, "slot_seconds": 0},                              # 非正
])
def test_config_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        load_config(bad)


def test_langgraph_runs():
    class S(TypedDict):
        n: int

    g = StateGraph(S)
    g.add_node("inc", lambda s: {"n": s["n"] + 1})
    g.add_edge(START, "inc")
    g.add_edge("inc", END)
    assert g.compile().invoke({"n": 1}) == {"n": 2}
