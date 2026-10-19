"""Network Agent 参数。

所有影响结果的参数都在这里声明类型,值只能来自 config 文件(CLAUDE.md §6),
因此字段不设默认值:漏写或拼错都会在加载时报错,而不是悄悄用上某个默认数字。
后续步骤需要新参数时再往这里加。
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, PositiveInt


class NetAgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot_seconds: PositiveInt         # 账本时间槽长度;越小越精确,装箱开销越大(slide 23)
    horizon_seconds: PositiveInt      # 账本向前看多远
    reserve_ttl_seconds: PositiveInt  # reserve 未 commit 时自动释放的期限(slide 19)


def load_config(source: dict | str | Path) -> NetAgentConfig:
    """从 dict 或 yaml 文件加载。yaml 可以是完整实验 config,此时读其中的 ``network_agent`` 段。"""
    if not isinstance(source, dict):
        source = yaml.safe_load(Path(source).read_text())
    return NetAgentConfig.model_validate(source.get("network_agent", source))
