# wfplatform这个schema是不是不应该由agent来维护。应该由agent去问senseAPI.

> 所以应该删掉？

是的，但**边界不在 "WfPlatform 该不该存在"，而在 "它是输入文档还是派生视图"**。这个区分能同时解释 KK 的反对和你们不愿删它的理由。

## 先按你们草案里的实际字段逐条判

`example.md` 里 WfPlatform 目前是 `sites[].nodes[].id` + `links[]{source, destination, capacityGbps, latencyMs}`，WfCampaign 里还有 `route`。逐个看谁该给：


| 字段                               | 该谁给                             | 处置                                                                                         |
| -------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| `links[].source/destination`（拓扑） | SENSE                           | **删**。而且按上一轮结论，agent 根本不需要 link 粒度                                                         |
| `submissions[].route`            | SENSE                           | **删**。agent 不需要指定 route                                                                    |
| `links[].capacityGbps`           | SENSE                           | **改成查**，且不能查静态值——见下面第 3 节                                                                  |
| `sites[].nodes[].id`             | **workflow**                    | **保留**。这是名字，不是拓扑                                                                           |
| node id → terminal URI           | SENSE `/discover/lookup/{name}` | 查，但 `example.md:597` 已经指出 response schema 引用 `DomainDescription` 而非 mapping object，**需实测** |
| `links[].latencyMs`              | ⚠️ **没人给**                      | SENSE northbound 无 latency（5.2.5）                                                          |
| node 的主机能力（NIC/存储/PCIe/TCP 栈）    | ⚠️ **没人给**                      | SENSE 不管；workflow 也不该声明                                                                    |


删完之后，WfPlatform 里**真正属于 workflow 的只剩一样东西：一个可被解析的 endpoint 名字**。薄到那一层，它就不该再叫 "Platform" 了——叫 `endpoints[]` 更诚实，也直接消解了 KK 的质疑（workflow 说"我要从 A 到 B"，A 和 B 是名字，不是网络描述）。

## 但 "agent 维护" 和 "agent 缓存" 是两回事

即使所有内容都来自 SENSE，agent **仍然必须在内部物化一份 platform 形状的数据结构**，因为：

- SENSE 是点查询，没有批量、没有曲线；时间轴容量要靠多次查询拼出来
- 一次调度决策必须在**一致的快照**上做，不能边算边变
- achievability 校准要历史数据，历史必须落在某个结构上

所以 WfPlatform 这个数据结构会活下来——但活成 **agent 内部的派生视图（就是我上次说的 Network Fact Base），每个字段带 source / timestamp / TTL / 语义标注**，而不是 **Rafael WfFormat 里一份用户填的输入文档**。

这就是关键：**只要它留在 WfFormat 里，它在结构上就是输入**，KK 说的"要不断用实时 SENSE 数据更新一份 workflow-side schema，既重复又容易失效"就无法避免。不是纪律问题，是位置问题。



## achievability 校准是啥

一句话：**学"预约到的带宽"和"实际跑出来的吞吐"之间差多少。**

SENSE 说这条路能给你 100 Gbps，实际传完文件一算只有 62 Gbps——差的那部分来自 TCP、RTT、丢包、DTN 网卡、存储读写、并行流数，全都不在 SENSE 的模型里（5.2.6）。

所以 agent 每传完一次就记一条：

```
(src, dst, 预约 100G, 实测 62G, RTT, 流数, 文件大小) → factor = 0.62

```

攒够了就能对下一次做预测：要 80 Gbps 吞吐，得预约 80 / 0.62 ≈ 129 Gbps。

**冷启动时只能拍一个保守常数（比如 0.6），随历史数据慢慢校准**——这个"慢慢修正系数"的过程就是 achievability 校准。

没有它，agent 按 100 Gbps 承诺 deadline，实际按 62 Gbps 跑，**每一次承诺都是空头支票**。

