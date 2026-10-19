"""SciNet Network Agent。

设计来源:resources/slides/Agent Orchestration.pptx(slides 6–8, 12, 19–24)、
resources/notes/20261014_networkagent.md(三张图)、
resources/meetings/20261015_network_agent_prototype.md(与 KK 的修订)。

三张执行图共用同一组业务模块;图里的节点只做编排,逻辑写在普通模块里,
便于被其他图或其他 agent 复用(10/15 会议)。计划中的模块:

    config.py      参数(全部来自 config 文件,代码里不写魔法数字)
    schemas.py     agent 间消息(TransferRequest、QuoteRequest/Response、Offer …)
    topology.py    站点、链路、路径
    ledger.py      逐链路、逐时间槽的容量账本:available = observed − own
    sim.py         模拟网络(digital twin 的替身:他人占用、链路中断)
    telemetry.py   TelemetrySource 接口 + mock
    sense.py       SenseAdapter 接口 + mock(SENSE-O / NDT / Mininet 可替换)
    graphs/        protocol(图 A)、runtime(图 B)、learning(图 C)

约定:
- 用 ``reserve`` 指代 slides 中的 ``hold``(KK 建议,10/15)。
- 单位:带宽 Gbps(float),数据量 bytes(int),时间为带时区的 UTC datetime。
- 账本按单条链路建账,而不是 slides 23 的 (src, dst) 对:这样才能定位拥塞的那一跳,
  并支持多路径增容。
"""
