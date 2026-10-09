> 组会上谈了这个wfformat ppt，我附给了你会议的录音转文字。我重点关心第二部分，这部分是我负责的。本次meeting只进行到17页。请告诉我教授给了我哪些修改意见。



教授对你负责的第二部分（第 11–17 页）的核心意见不是“技术方案错了”，而是：**你没有提前说明自己新增了什么，导致听众看到** `WfPlatform`**、**`WfCampaign`**、**`constraints` **等概念时，不知道哪些是原有设计、哪些是你的贡献。**

## 最重要的总体修改

在第 11 页之后、正式讲 Bandwidth 之前，加一张“我们的扩展/贡献概览”页，明确列出：


| 你的扩展                                         | 作用                                           |
| -------------------------------------------- | -------------------------------------------- |
| 新增 `WfPlatform` schema                       | 描述 domains、sites、nodes、links、routes 等平台/网络拓扑 |
| 新增 `WfCampaign` schema                       | 描述某一次运行特有的 SLA 和资源绑定                         |
| 在 `WfFormat specification` 中新增 `constraints` | 描述应用本身固有、换平台也不变的时间约束                         |
| 在 `WfFormat execution` 中新增 `transfers[]`     | 记录实际文件传输的源、目的地、时间、字节数、RTT 等                  |


教授的原意非常明确：不能第一次使用 `WfPlatform` 时，听众问了才解释“后面会介绍”。可以说细节稍后讲，但必须先告诉大家：

> We introduce two new schemas and extend two existing sections of WfFormat.

这应该是本次最优先的修改。

## 按页修改意见


| 页码                          | 教授的意见                                                              | 建议怎么改                                                                                       |
| --------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| 第 11 页                      | 只说“Adding the Network”不够，没有告诉听众具体新增了什么                             | 将第 11 页改成贡献概览，或者在 11–12 页之间加一页，提前介绍 `WfPlatform`、`WfCampaign`、`constraints`、`transfers[]`   |
| 第 12 页 Bandwidth            | 目前顺序是 Link capacity → Real throughput → Required bandwidth，逻辑不自然   | 改为：①平台提供什么：link capacity；②workflow 需要什么：required bandwidth；③实际运行得到什么：measured throughput    |
| 第 13 页 Latency              | 与 Bandwidth 一样，当前 “link → real → required” 顺序令人困惑                  | 改为：①拓扑中的 link latency；②workflow/SLA 要求的 latency；③运行后测得的 RTT。教授明确说 Bandwidth 页也应采用相同顺序       |
| 第 14 页 SLA                  | 没有明确说哪些字段是已有的、哪些是你新增的                                              | 明确写：`constraints` 是你新增到现有 `WfFormat specification` 的字段；`WfCampaign` 是你提出的新 schema           |
| 第 14 页 SLA                  | 突然使用 `submission`，前面一直使用 `run` 或 `execution`，引入了不必要的新术语            | 全部统一为 `run`；如果一定要用 `submission`，必须先定义它与 run/execution 的关系                                   |
| 第 14 页 SLA                  | 三类 deadline 没有解释清楚                                                 | 明确区分：workflow completion deadline、task completion deadline、file-transfer deadline           |
| 第 14 页 SLA                  | `fileDeadlines` 容易被理解为“文件本身的 deadline”，没有体现传输                      | 改名为 `fileTransferDeadlines`，或者教授建议的 `fileXferDeadlines`                                     |
| 第 14 页 SLA                  | 时间戳格式看起来像你自己定义的，但没有说明                                              | 明确注明这是 proposed timestamp format；同时检查 SENSE 是否已有规定的 timestamp format                        |
| 第 15 页 Endpoints            | “Endpoints: On Files, Not Tasks”不够直接，听众不知道是什么 endpoints            | 直接说成 “Source and Destination of a File Transfer”                                            |
| 第 15 页 Endpoints            | specification 中的 endpoint 看起来像物理位置，与“platform-independent”冲突       | 明确强调 specification 中写的是抽象 role/identity，例如 `primary-detector`，不是具体机器或地址                     |
| 第 15 页 Endpoints            | role、binding、actual location 三层关系没有讲清楚                             | 清楚展示：specification 定义抽象角色 → campaign binding 将角色映射到具体位置 → execution 记录实际 source/destination |
| 第 15 页 Endpoints            | “start and end point”同时可能指空间位置和时间，表达含糊                             | 空间统一用 `source`/`destination`；时间统一用 `startedAt`/`endedAt`                                    |
| 第 15 页 Endpoints            | 示例只展示了 `durationSeconds`，无法支持时间窗口中的流量分析                            | 教授明确要求展示 starting time 和 ending time，不能只给 duration                                          |
| 第 16 页 Spatial Distribution | 页面标题写 Spatial Distribution，但内容实际上是在定义 `WfPlatform` topology schema | 改标题为类似 `WfPlatform: A Schema for Describing the Topology`                                   |
| 第 16 页 Spatial Distribution | schema 本身和使用 schema 计算空间分布混在一起                                     | 这一页只解释 domains/sites/nodes/links/routes；下一页再讲如何用它计算 spatial/temporal distribution           |
| 第 17 页                      | 教授没有具体批评公式，但质疑在进入 SENSE API 之前是否讲了过多细节                             | 主线中只保留输入、输出和一条核心公式；具体循环代码可以移到 backup                                                        |


## 教授希望你讲清楚的三个层次

你现在多页内容都可以统一成下面这条逻辑：

1. **Platform capability**  
平台/网络能提供什么，例如 link capacity、link latency、topology。
2. **Workflow requirement**  
workflow 需要什么，例如 deadline、required bandwidth、required latency、抽象 endpoint role。
3. **Execution observation**  
实际运行发生了什么，例如 bytes transferred、RTT、actual source/destination、start/end time。

教授觉得你现在经常先讲“测到了什么”，再讲“需要什么”，所以听众不容易建立因果关系。

## 与 SENSE API 的关系也要提前讲清楚

会议最后教授专门追问：

> 你们是在替代 SENSE API，还是把 Raphael 的格式转换成 SENSE API？

最终讨论出的定位是：

- 用户使用“WfFormat + 你们的扩展”描述完整 workflow；
- 这个格式包含计算、文件、SLA、网络拓扑和传输需求；
- SENSE API 只负责其中的网络控制/网络服务部分；
- 通过 adapter，把完整 workflow specification 中与网络有关的字段转换成 SENSE API 调用。

因此，在进入 SENSE 部分前，最好加一张非常清楚的关系图或过渡页.

你需要强调的不是“让 SENSE 社区放弃 SENSE”，而是：

> SENSE does not describe the complete workflow. Our extended format describes the workflow end to end, while an adapter maps its network requirements to SENSE.

## 对前半部分的少量意见

虽然你重点负责第二部分，但它会影响整体结构：

- 第 6 页 WfCommons benchmark 生成流程只是背景，教授认为有些 distracting，应快速讲过，不要花太多时间。
- 第 7–9 页有帮助，可以保留。
- 第 10 页完整实例最终决定保留，但要解释它如何进入 WfChef/WfGen 的闭环。
- 整体顺序建议是：  
**现有 WfFormat → 你们新增的扩展 → SENSE API → 完整 examples**
- 过细内容可以移到 backup，避免两套 slide deck 看起来像两个不相干的项目。

一句话总结：**你现在最该做的不是继续补字段，而是先增加一张“我们新增了什么、它们之间是什么关系”的总览页，然后统一术语、重排 capability–requirement–measurement 的顺序，并把第 16 页从 Spatial Distribution 改成明确介绍 WfPlatform schema。**