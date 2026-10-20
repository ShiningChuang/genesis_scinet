3b 做完了，76 个测试全部通过。[PLAN.md](http://PLAN.md) 已更新：3b 标为完成，第 4 步标为下一步，新增三条待决。还没提交。

## 新增和修改了什么


| 文件                                 | 改动                                        |
| ---------------------------------- | ----------------------------------------- |
| [sense.py](http://sense.py)（新）     | `SenseAdapter` 接口和 `MockSense`            |
| [schemas.py](http://schemas.py) 末尾 | `Terminal`、`ServiceIntent`、`ServiceState` |
| [sim.py](http://sim.py)            | 模拟网络新增一份"我们经 SENSE 的预留"，以及 `headroom()`   |


## 读代码时注意四点

**1. 两阶段流程，和 SENSE 实际的接口对齐**（[sense.py:1-12](../../src/lib/network_agent/sense.py#L1-L12)）

字段和操作名取自你之前 Exp2 对 SENSE-O Intent API 2.0.4 的调研：

```
propagate  预留资源，不下发配置       ← 对应我们的 reserve（slides 里的 hold）
commit     下发配置                 ← commit
cancel     归还资源                 ← release，或 reserve 到期未 commit

```

`SenseAdapter` 和 telemetry 的接口一样是 `Protocol`：以后接真实 SENSE-O、NDT 或 Mininet，只要提供这几个方法即可，图不用改。所有失败统一抛 `SenseError`，并附带原因（容量不足、状态不对、找不到实例、VLAN 用完、人为注入）。第 5a 步的 `sense_call` 节点捕获到它，就走 rollback 分支。

**2.** `ServiceIntent` **只有一个带宽值**（[schemas.py](http://schemas.py) 末尾）

一个 intent 表示"一段时间内、两个端点之间一条恒定带宽的连接"，对应 slide 24 里的一个 circuit。但我们的 offer 可能有多段不同的速率，比如先 40 后 100。多段速率怎么落到 intent 上，留给第 5a 步决定。这一条已记进待决。

两处简化：只支持一条连接、恰好两个端点；带宽用整数 Mbps，SENSE 实际要求的是 Mbps 字符串，由真实 adapter 负责转换。

**3. 模拟网络里"他人"和"我们"分开存**（[sim.py](http://sim.py)）

这是上一轮讲 [sim.py](http://sim.py) 时提过的问题，这次实现了：


| 用途           | 算他人占用 | 算我们的预留 | 调用方式                                                 |
| ------------ | ----- | ------ | ---------------------------------------------------- |
| telemetry 报告 | ✓     | ✗      | `segments(..., include_ours=False)`                  |
| SENSE 准入检查   | ✓     | ✓      | `headroom()`，内部调用 `segments(..., include_ours=True)` |


测试 `test_ours_counts_for_sense_but_not_for_telemetry` 验证的就是这一点：我们预留 60 Gbps 后，SENSE 只剩 40 可给，但 telemetry 仍然报 100。所以账本拿到的 observed 是 100，再减去自己的 own 60，得到 40，和 SENSE 一致，没有重复扣减。

**4.** `MockSense` **可以注入失败**

`fail_next("commit")` 会让下一次 commit 失败。失败之后实例保持原状态，比如仍是 reserved，并且只失败这一次。第 5a 步就用它来测试"SENSE 失败时，账本能正确 rollback"。

`MockSense` 还会对照模拟网络的真实容量做准入检查。所以除了人为注入的失败，"账本以为够、实际上不够"这种真实的不一致也能被它发现。

## 新增的三条待决

- **SENSE 路径的语义未确认。** SENSE 的 `inclusion_list` 是强制路径，还是只是偏好？这是 Exp2 遗留的问题。mock 把它当作强制路径。如果真实 SENSE 实际走了别的路径，逐链路账本就和实际不符。
- **多段速率怎么映射到 intent**：第 5a 步决定。
- **VLAN 池被简化成了一个全局池。** 真实情况是每个端点各有自己可用的 VLAN，两端需要同时空闲。

**下一步是第 4 步：第一次接入 LangGraph**，写图 A 的 quote 分支，并复现 slide 7 的 a1/a2/a3 三个 offer。

---

> sense

[sense.py](http://sense.py) 分三块：**错误类型和接口（第 23–37 行）→** `MockSense` **的四个对外操作（第 40–78 行）→ 内部辅助函数（第 82–105 行）**。

## 1. 错误类型和接口（第 23–37 行）

`Op`**（第 23 行）** 是一个类型别名，列出可能出错的三种操作。和 `Path` 一样，只是给 `Literal[...]` 起了个名字，后面引用起来短一点。

`SenseError`**（第 26–30 行）** 带两个属性：`op` 是哪个操作出错，`reason` 是为什么出错。五种原因：


| reason                  | 什么时候                               |
| ----------------------- | ---------------------------------- |
| `insufficient_capacity` | 网络里实际容量不够                          |
| `invalid_state`         | 状态不对，比如对一个已经 committed 的实例再 commit |
| `not_found`             | 实例 id 不存在                          |
| `no_vlan`               | VLAN 池用完了                          |
| `injected`              | 人为注入的失败，测试用                        |


第 30 行的 `.rstrip()` 去掉末尾空格：没传 `detail` 时，消息末尾会多出一个空格。

和 ledger 的 `InsufficientCapacity` 一样，原因作为属性带出去，调用方可以按 `e.reason` 分别处理，不需要去解析报错文字。

`SenseAdapter`**（第 33–37 行）** 和 telemetry 的 `TelemetrySource` 一样是 `Protocol`。四个方法，每个都以 `...` 结尾表示没有实现。写在同一行是 Python 允许的简写。


| 方法                  | 输入                          | 输出                   |
| ------------------- | --------------------------- | -------------------- |
| `propagate`         | 一个 `ServiceIntent`（要什么样的连接） | 新实例的 `ServiceState`  |
| `commit` / `cancel` | 实例 id                       | 更新后的 `ServiceState`  |
| `state`             | 实例 id                       | 当前 `ServiceState`，只读 |


注意只有 `propagate` 接收完整的 intent。之后的操作都只用实例 id，因为 SENSE 已经记住了这个实例是什么。这对应 SENSE 实际 API 的 `PUT /instance/{siUUID}/{action}`。

## 2. `MockSense` 的字段（第 44–48 行）


| 字段           | 内容                              |
| ------------ | ------------------------------- |
| `network`    | 模拟网络，准入检查时查它，预留时写它              |
| `vlan_range` | VLAN 池，比如 `(3001, 3002)`        |
| `_states`    | 实例 id → 当前状态，相当于 SENSE 自己的记录    |
| `_fail`      | 操作名 → 还要失败几次，比如 `{"commit": 1}` |
| `_ids`       | 一个计数器，用来生成实例 id                 |


第 48 行的 `count(1)` 来自 `itertools`，是一个从 1 开始无限递增的迭代器：每调用一次 `next(self._ids)`，就依次得到 1、2、3……写成 `default_factory=lambda: count(1)`，是为了让每个 `MockSense` 对象各有一个独立的计数器。

## 3. 四个对外操作（第 50–78 行）

`fail_next`**（第 50–52 行）** 是测试专用的操作。"接下来 n 次这个操作直接失败"。用 `+=` 的语义累加，所以连续调用两次 `fail_next("commit")`，等于失败两次。

`propagate`**（第 54–64 行）：预留。** 步骤：

```
1. 如果注入了失败，直接抛错                      第 55 行
2. Mbps 换算成 Gbps                             第 56 行
3. 问模拟网络：这条路径在这段时间还能给多少？      第 57 行  → headroom，算他人 + 我们已有的预留
4. 不够就抛 insufficient_capacity               第 58–59 行
5. 分配 VLAN、生成实例 id（"si-1"、"si-2"……）   第 60–61 行
6. 在模拟网络里登记"我们占了这些"               第 62 行   → 下一次 headroom 就能看到
7. 记下状态 reserved，返回                      第 63–64 行

```

顺序很重要：**所有检查（第 55–60 行）都在第 62 行修改网络之前完成。** 只要中途失败，网络就保持原样，不会出现"占了容量却没生成实例"的情况。测试 `test_injected_propagate_failure_takes_nothing` 验证的就是这一点。这和 ledger `pending()` "先全部检查、再写入"是同一个原则。

`commit`**（第 66–69 行）：确认。** 先确认实例存在、而且处于 reserved 状态，然后检查是否注入了失败，最后把状态改成 committed。

第 69 行的 `s.model_copy(update={...})` 是 pydantic 的方法：`ServiceState` 是不可变的（frozen），不能直接改字段，所以复制一份，只替换指定的字段。旧对象保持不变。

commit 不需要再动模拟网络：容量在 propagate 时已经占了。这和 ledger 里 `confirm()` 只改状态、不改容量是一个道理。

`cancel`**（第 71–75 行）：归还。** reserved 和 committed 两种状态都允许取消。第 72 行用 `*allowed` 接收不定个数的参数，所以可以一次传入两个允许的状态。取消时从模拟网络中移除我们的预留（第 74 行），容量就回来了；`vlan` 设为 `None`，表示这个 VLAN 也还回池里了。

`state`**（第 77–78 行）** 只查不改。

## 4. 内部辅助函数（第 82–105 行）


| 函数                       | 作用                                                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `_maybe_fail`（第 82–85 行） | 计数大于 0 就减 1 并抛 `injected`，所以注入的失败用一次就少一次                                                                                 |
| `_expect`（第 87–93 行）     | 检查实例存在，并且当前状态在允许的范围内。commit 和 cancel 共用它                                                                                 |
| `_free_vlan`（第 95–101 行） | 先找出所有仍在使用的 VLAN（cancelled 的 `vlan` 已经是 `None`，自然不算），再从池的开头找第一个空闲的。所以归还的 VLAN 会被优先复用，测试 `test_vlan_pool_and_reuse` 验证了这一点 |
| `_set`（第 103–105 行）      | 存入新状态，同时把它返回。这样 propagate/commit/cancel 都能一行写完"存下并返回"                                                                    |


## 有两个细节值得注意

1. **注入失败的检查位置不一样。** `propagate` 在最开头就检查（第 55 行），`commit` 和 `cancel` 则先校验状态、再检查注入。效果是：对一个状态不合法的实例做 commit，报的是 `invalid_state`，并且不会消耗掉一次注入的失败。这样测试结果更可预测。
2. `state()` **找不到实例时抛** `KeyError`**，不是** `SenseError`（第 78 行）。这和其他方法不一致。它目前只在测试里用于查询，影响不大，但第 5a 步如果节点里要调用它，最好统一改成 `SenseError("not_found")`。要不要现在顺手改掉？

---

> 1. “vlan_range: tuple[int, int]                       # VLAN 池 [first, last]”这是啥，VLAN是啥 
>
> 2. _fail什么是“还要失败几次”
>
> 3. ServiceState是整个sense的state吗‘
>
> 4. 为什么propagate、commit、cancel都没对_state操作

**1. VLAN 是什么，**`vlan_range` **又是什么**

**VLAN（Virtual LAN，虚拟局域网）是贴在以太网数据帧上的一个编号标签，取值 1–4094。交换机按这个标签把同一套物理网络划分成互相隔离的多个逻辑网络。**

打个比方：一条物理线路是一条高速公路，VLAN 编号是车道号。贴着 3001 标签的帧只在 3001 车道上跑，不会和别的车道混在一起。

**它和 SENSE 的关系：** SENSE 建的二层 circuit，实际交付方式就是一个 VLAN。commit 之后，沿途交换机都被配置成"VLAN 3001 的帧走这条预留好的路径"，端点主机的网卡上也会建一个带 3001 标签的子接口（比如 `eth1.3001`）。这就是你之前问的 `EndpointBinding`：WMS 必须把数据从这个 VLAN 发出去，数据才会走上预留的路径；不带标签发，就走默认路由。

**为什么需要一个池：** 同一个端点上同时存在的多个 circuit，必须用**不同的** VLAN 编号，否则流量会串到一起。站点通常会预先划出一段编号专门给 SENSE 动态分配，比如 3001–3100，这就是 VLAN 池。

`vlan_range: tuple[int, int]` 用两个整数表示这个池的首尾编号，两端都包含：

```python
MockSense(net, vlan_range=(3001, 3002))   # 池里只有 3001 和 3002 两个

```

测试里故意只给两个，第三个 propagate 就会报 `no_vlan`，用来验证池用完的情况。

前面记进待决的那条也是这个意思：真实情况下，每个端点各有自己的池，一个 circuit 要两端都有空闲的编号；mock 简化成了一个全局池。

**2.** `_fail` **的"还要失败几次"是什么意思**

`_fail` 是一个**失败计数器**：key 是操作名，value 是"接下来还有几次调用要故意失败"。用来测试 SENSE 出错时，我们的代码能不能正确处理。

一个例子：

```python
sense.fail_next("commit", times=2)   # _fail = {"commit": 2}

sense.commit("si-1", now)   # 计数 2 > 0 → 减为 1，抛 SenseError("injected")
sense.commit("si-1", now)   # 计数 1 > 0 → 减为 0，抛 SenseError("injected")
sense.commit("si-1", now)   # 计数 0     → 正常执行，状态变为 committed

```

每次调用对应的操作时，`_maybe_fail` 都会看一下计数：大于 0 就减 1 并抛错，等于 0 就放行。所以"还要失败几次"就是这个数还剩多少。

之所以要按次数计，而不是一个"永远失败"的开关，是为了模拟真实世界里常见的**偶发**失败：第一次失败、重试成功。第 5a 步会用它来测：

- commit 失败一次 → 账本是否正确 rollback；
- 之后正常 commit → 账本和 SENSE 两边的状态是否仍然一致。

1. **ServiceState是整个sense的state吗**

**不是。**`ServiceState` **是 SENSE 里一个 service instance 的状态，也就是一条 circuit 的状态，不是整个 SENSE 的状态。**

```python
ServiceState(instance_id="si-1", alias="scinet-c1", state="reserved", vlan=3001, changed_at=...)

```

它只描述一个实例：编号是什么、目前处于哪个阶段（reserved / committed / cancelled）、分到了哪个 VLAN、什么时候变成这个状态。

**整个 mock SENSE 的状态**是第 46 行的 `_states` 这个 dict，里面装着所有实例各自的 `ServiceState`：

```python
_states = {
    "si-1": ServiceState(..., state="committed", vlan=3001),
    "si-2": ServiceState(..., state="reserved",  vlan=3002),
    "si-3": ServiceState(..., state="cancelled", vlan=None),
}

```

名字的来源是 slide 8 里 network agent 从 SENSE 拉取的三种样本之一：`ServiceState { serviceInstanceUuid, circuitId, state, provisioned, changedAt }`，指的同样是单个实例。

**另外要注意，它和 LangGraph 的 state 也没有关系。** 到第 4 步，代码里会同时出现三种"state"：


| 名字                                        | 是什么              | 范围                               |
| ----------------------------------------- | ---------------- | -------------------------------- |
| `ServiceState`                            | SENSE 返回的一个实例的状态 | 一条 circuit                       |
| `ServiceState.state` 字段                   | 这个实例处于哪个阶段       | reserved / committed / cancelled |
| LangGraph 的 state（第 4 步的 `ProtocolState`） | 图 A 处理一次请求时的工作记录 | 一次图执行                            |


LangGraph 的 state 里可能会装着一个 `ServiceState`，比如 `sense_call` 节点把 SENSE 的返回结果存进去。但这两者是不同层次的东西。

**4. 为什么propagate、commit、cancel都没对_state操作**

**它们都操作了** `_states`**，只是写入这一步统一交给了** `_set` **去做。** 三个方法的最后一行都是 `return self._set(...)`，而 `_set`（第 103–105 行）就是写 `_states` 的地方：

```python
def _set(self, s: ServiceState) -> ServiceState:
    self._states[s.instance_id] = s    # ← 写入 _states
    return s

```

逐个看三个方法对 `_states` 的读写：


| 方法          | 读 `_states`                                                  | 写 `_states`                               |
| ----------- | ------------------------------------------------------------ | ----------------------------------------- |
| `propagate` | 间接读：`_free_vlan()` 第 96 行遍历 `_states`，找出已用的 VLAN             | 第 63 行 `self._set(...)` 新增一条，状态为 reserved |
| `commit`    | 第 67 行 `_expect(...)`，在第 88 行用 `self._states.get(...)` 取出旧状态 | 第 69 行 `self._set(...)` 覆盖成 committed     |
| `cancel`    | 第 72 行 `_expect(...)`，同上                                     | 第 75 行 `self._set(...)` 覆盖成 cancelled     |


之所以写成 `self._set(...)` 而不是直接写 `self._states[...] = ...`，是因为每个方法都要做"存下新状态，再把它返回给调用方"这两件事。合成一个辅助函数后，每处只要一行，而且以后如果想在写入时加点什么（比如记日志、记录状态变化历史），只需要改 `_set` 一个地方。

代价是读代码时，写入不是一眼就能看到。这就是你会觉得它们"没操作 `_states`"的原因。

---

> 带我过一遍schema和sim的变动

3b 对这两个文件也都是增量修改。

# schemas.py：新增 SENSE 一侧的三个消息（第 259 行起）

之前的消息分属两条边界：scheduling ↔ network（quote/reserve/commit），以及 telemetry → network（`LinkSample`）。这次补上第三条：**network ↔ SENSE**。

**开头的注释（第 259–262 行）** 写明了字段的出处（Exp2 调研的 SENSE-O Intent API 2.0.4），以及两处简化：只有一条连接、恰好两个端点；带宽用整数 Mbps。

`QosClass`**（第 264 行）** 是类型别名，列出 SENSE 的四种 QoS 类。你之前问过 `Literal`：写错成别的值就会被拒绝，测试里的 `"premium"` 就是这样被拦下的。

这四种类具体保证什么，Exp2 里还没查清。比如 `guaranteedCapped` 到底是"最低保证"还是"上限"，SENSE 的 schema 里没写。所以现在只限定取值范围，语义暂时不依赖。

`Terminal`**（第 267 行起）**：一个连接端点。

- `uri`：SENSE 的端点 URI。
- `vlan_tag`：默认 `"any"`，意思是让 SENSE 从池里分配。这就是上一轮讲的 VLAN：我们不指定编号，由 SENSE 选好后在 `ServiceState.vlan` 里告诉我们。

`ServiceIntent`**（第 272 行起）**：network agent 向 SENSE 提交的请求。每个字段后面的注释写着它在 SENSE 真实 API 里的路径：


| 字段               | SENSE 里的位置                     | 说明                                                       |
| ---------------- | ------------------------------ | -------------------------------------------------------- |
| `alias`          | `alias`                        | 我们起的名字，比如 `scinet-c1`，方便在 SENSE 那边追溯                     |
| `terminals`      | `terminals`                    | 两个端点                                                     |
| `capacity_mbps`  | `bandwidth.capacity`           | 整个时段内**只有一个**带宽值                                         |
| `qos_class`      | `bandwidth.qos_class`          |                                                          |
| `start`, `end`   | `schedule.start/end`           |                                                          |
| `path_inclusion` | `path_tprofile.inclusion_list` | 我们选定的路径。这里存的是我们的有向链路 id，真实 adapter 要转换成 SENSE 的 Path URI |


校验（第 289 行起）：必须恰好两个不同的端点，时段不能颠倒。

文档字符串里强调了一点：一个 intent 对应一条带宽恒定的连接，也就是 slide 24 的一个 circuit。多段速率的 offer 怎么映射到 intent，留到第 5a 步决定。

`ServiceState`**（第 297 行起）**：SENSE 的回复，上一轮已经讲过，是一个实例的状态。`state` 的三个值对应两阶段流程：propagate 之后是 `reserved`，commit 之后是 `committed`，cancel 之后是 `cancelled`。

**还改了文件开头的说明（第 3–5 行）：** "ServiceIntent / ServiceState → 第 3b 步"这条预告删掉了，因为已经写了。

# [sim.py](http://sim.py)：多了一份"我们的预留"

3a 版的模拟网络只有"他人占用"和"中断"两份数据。3b 加了第三份，一共五处改动：

**1. 文档字符串（第 7–8 行）** 新增一段，说明为什么"他人"和"我们"要分开存。这是这次改动的核心理由。

**2. 新字段** `_ours`**（第 29 行）**

```python
_ours: dict[str, tuple[Path, Interval]]   # SENSE 实例 id → (路径, 预留时段与速率)

```

它和 `_foreign` 的组织方式**不一样**：


|            | key             | 原因                                       |
| ---------- | --------------- | ---------------------------------------- |
| `_foreign` | 有向链路            | 他人占用只在测试和 demo 里设置，按链路存方便查询              |
| `_ours`    | **SENSE 实例 id** | 我们的预留要能按实例整体撤销：cancel 时一次删掉一个实例在整条路径上的预留 |


value 里带着路径，所以要回答"某条链路上有哪些我们的预留"，就去检查哪些实例的路径经过这条链路（第 64 行）。这和 ledger `own()` 里的 `if link_id in b.path` 是同一个写法。

**3.** `add_ours` **/** `remove_ours`**（第 47–52 行）** 由 mock SENSE 在 propagate 和 cancel 时调用，也就是上一轮讲的 [sense.py](http://sense.py) 第 62 行和第 74 行。

**4.** `segments` **多了一个参数** `include_ours`**（第 54–72 行）**

默认是 `False`，所以 3a 的 `MockTelemetry` 一行都不用改，行为也不变。

改动集中在第 62–64 行：

```python
used = list(self._foreign[link_id])      # 先复制一份他人占用的列表
if include_ours:
    used += [我们经过这条链路的预留]        # 需要时再加上我们的

```

之后的计算从原来的"只算 `_foreign`"改成"算 `used`"（第 65、70 行），切段的逻辑和你上次读的完全一样。变量名也从 `foreign` 改成了 `taken`，因为它不再只是他人占用。

第 62 行的 `list(...)` **很关键**：它复制出一个新列表。如果直接写 `used = self._foreign[link_id]`，`used` 和存储里的那个列表就是同一个对象，下一行的 `+=` 会把我们的预留永久追加进 `_foreign`。之后 telemetry 再查询，就会把我们的预留也报出去，正好违反了 3a 定的口径。

**5. 新方法** `headroom`**（第 74–76 行）** 是 SENSE 准入检查专用的。它回答：这条路径在 `[start, end)` 内，**任何时刻**都还能再给出的最大速率是多少。

```python
min(gbps for link in path for *_, gbps in self.segments(link, start, end, include_ours=True))

```

这是一个双层生成器：外层遍历路径上的每条链路，内层遍历这条链路的每一段，取所有段里可用容量的最小值。`*_, gbps` 的意思是：`segments` 返回的四元组 `(起, 止, up, 容量)` 里只要最后一个，前三个用 `*_` 收起来丢掉。

取最小值等于同时在两个维度上取瓶颈：沿路径取最窄的那一跳，沿时间取最紧的那一刻。SENSE 要提供的是整个时段内带宽恒定的连接，所以只要有一个时刻、一跳不够，就不能准入。上一轮讲过的测试 `test_admission_sees_foreign_traffic` 就是这种情况：他人只占了后半段，但 70 Gbps 的请求仍被拒绝。

---

> _ours本质就是我们的预留吗，但是预留只针对某个workflow，为什么这个属性挂在了MockNetwork这整个网络上？

**是的，**`_ours` **就是"我们经 SENSE 做的所有预留"。它挂在整个网络上，是因为预留占用的是链路容量，而链路是所有 workflow 共用的。**

## 一条预留属于某个 workflow，但它占的是公共的链路

`_ours` 是一个 dict，**每一项**才是某一个预留：

```python
_ours = {
    "si-1": (MAIN 路径, 09:00–10:00, 60 Gbps),   # 可能服务 WF-1
    "si-2": (MAIN 路径, 09:30–11:00, 30 Gbps),   # 可能服务 WF-2
}

```

这两条预留属于不同的 workflow，但都经过 L2。SENSE 判断"L2 在 09:30 还能不能再给 20 Gbps"时，必须**同时**看到两者：60 + 30 = 90，只剩 10，不能再给 20。

如果把预留分别挂在各自的 workflow 上，网络就要先找出所有 workflow，再逐个询问"你在 L2 上占了多少"，才能做准入检查。容量是链路的属性，所以"谁占了这条链路"的记录就该放在网络这一层。账本的 `_bookings` 也是同样的道理：它挂在整个账本上，而不是挂在某个 workflow 上。

## 网络这一层根本不知道 workflow

各层只认识自己那一层的概念：

```
workflow（WF-1）                    ← scheduling agent 的概念
   ↓ 包含
commitment（c_T1，带 workflow_id）   ← network agent 的概念（schemas.Commitment）
   ↓ 落在
circuit = SENSE 实例（si-1）          ← SENSE 的概念
   ↓ 占用
链路 L1、L2、L3 的容量                ← 网络的概念（MockNetwork）

```

`MockNetwork` 只模拟最底下这一层：哪些 circuit 占了哪些链路的多少容量。"si-1 是为哪个 workflow 建的"这层关系，记在上一层的 `Commitment` 里：它同时带着 `workflow_id` 和 `circuit_id`。

真实世界也是这样：SENSE 和网络设备只知道 circuit 和 VLAN，并不知道 1000 Genome 或 HEP workflow 是什么。

## 一个 circuit 甚至不一定只属于一个 workflow

slide 24 的设计里，circuit 是像连接池一样复用的：一条 circuit 上可以同时承载**多个** workflow 的 commitment。

```
Circuit C1（si-1）· ANL→ORNL · 100 Gbps · 09:00–18:00
   ├── commitment A · WF-1
   ├── commitment B · WF-2
   └── commitment C · WF-1

```

所以在网络这一层，预留天然就不按 workflow 划分。第 5a 步做 `place_on_circuit` 时，就会出现"把 WF-2 的 commitment 放到已经为 WF-1 建好的 warm circuit 上"的情况。

