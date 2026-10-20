第 3 步拆成了两半，前一半 3a 做完了，60 个测试全部通过。[PLAN.md](http://PLAN.md) 已更新，本步还没提交。

## 为什么拆成两半

第 3 步原来包含两个接口，图 A 用到它们的时间不同：

- **3a（这次）：Telemetry 一侧。** 下一步 quote 的 `refresh_if_stale` 要靠它把观测值刷进账本。
- **3b（下次）：SENSE 一侧。** 第 5a 步 reserve/commit 时才用到。

## 新增和修改了什么


| 文件                                  | 作用                                                                                                                                        |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [sim.py](http://sim.py)             | **模拟网络**，代替 digital twin。它保存"真实情况"：他人在各时段占用了多少容量、哪条链路什么时候中断。mock telemetry 从这里读；3b 的 mock SENSE 也会读写这里，所以两者看到的是同一个网络。以后接 Mininet，替换的就是这一层 |
| [telemetry.py](http://telemetry.py) | `TelemetrySource` 是一个接口：network agent 只认这个接口，背后是 mock、另一位同学做的 Telemetry Agent 还是 Prometheus，它都不关心。`MockTelemetry` 是它的一个实现                 |
| [schemas.py](http://schemas.py) 末尾  | 新增 `LinkSample`：一条有向链路在一段时间内的观测，包括是否 up、可用容量、采样时间、过期时间                                                                                    |
| [ledger.py](http://ledger.py)       | 去掉 `set_observed`，改为 `apply(samples)`，直接接收 telemetry 样本；观测值多了 `valid_until`，并新增 `is_stale()` 判断是否过期                                       |




## 读代码时注意三点

**1. 上一步的待决项，用"接口约定"解决了**

`LinkSample` 的文档字符串把 `available_gbps` 的口径写死为"**不算我们自己的预订时**可用的容量"：他人的占用算进 observed，我们自己的预订只算在 own 里，各扣一次。

测试 `test_end_to_end_no_double_counting` 走通了整条链：

```
模拟网络：他人占 40
   → telemetry 样本：available = 60
   → 账本 observed = 60
我们预订 30 → own = 30
available = 60 − 30 = 30 ✓（如果他人的 40 和我们的 30 都被扣了两次，结果就不对了）

```

以后接真实 SENSE，如果它返回的数已经扣掉了我们的预留，就由 SENSE 的 adapter 负责加回来。账本和图都不用改。

**2. 样本边界落在槽中间时取较小值**（[ledger.py:119-137](../../src/lib/network_agent/ledger.py#L119-L137)）

例如 09:00–09:20 可用 80，09:20–10:00 可用 30。09:15 这个槽同时被两段覆盖，取 30：槽内任何时刻的可用容量都不能被高估，否则会给出兑现不了的 offer。

**3. 拓扑初值一开始就是"过期"的**

账本用拓扑容量初始化时，`valid_until = origin`，意思是这些值只是静态快照，不是实测。所以第一次报价之前，`refresh_if_stale` 一定会先向 telemetry 拉一次真实值。

模拟网络里，`add_foreign` 只影响一个方向；`add_outage` 针对物理链路，一断就是两个方向都不通。这和你之前问的全双工是同一个道理。

**下一步是 3b：SENSE 接口加 mock。** 这一步要写 `ServiceIntent` 和 `ServiceState`，以及 propagate/commit/cancel 三个操作。mock SENSE 会对照模拟网络的真实容量做检查，还能人为注入失败，供第 5a 步测试 rollback 用。

---

> 你哪个步骤会接入langgraph？

**第 4 步开始接入 LangGraph**，就是 3b 的下一步。第 4 步写图 A 的 quote 分支，这是第一张真正的执行图。


| 步骤      | 是否用 LangGraph | 做什么                                                                                             |
| ------- | ------------- | ----------------------------------------------------------------------------------------------- |
| 0–3b    | 否             | 准备图节点要调用的"零件"：消息、拓扑、账本、telemetry、SENSE                                                          |
| **4**   | **是，第一次**     | 图 A quote 分支：`validate_bundle → refresh_if_stale → find_placements → estimate_finish → respond` |
| 5a / 5b | 是             | 图 A 的 reserve/commit/modify/release 分支，加在同一张图上                                                  |
| 6       | 是             | demo 驱动图 A 跑通整个 planning 闭环                                                                     |
| 7、9     | 是             | 图 B（Runtime）、图 C（Learning）                                                                      |


第 0 步的冒烟测试里只跑过一个一节点的玩具图，那是为了确认环境装好了，不算正式接入。

## 为什么放到第 4 步才用

这是 10/15 会议定的原则："逻辑写在普通模块里，图节点只做编排。"到了第 4 步，每个节点基本上就是几行代码，调用前面已经写好、测试过的模块：

```python
def refresh_if_stale(state, runtime):      # 节点
    ...ledger.is_stale(...)                 # ← 第 2、3a 步
    ...telemetry.link_samples(...)          # ← 第 3a 步
    ...ledger.apply(samples)                # ← 第 3a 步
    return {"refreshed": [...]}

```

这样安排有两个好处：

1. **你读第 4 步时，只需要关心 LangGraph 本身**：state 怎么定义、节点怎么连、条件边怎么分支、账本和 telemetry 怎么作为 context 注入。业务逻辑你在前几步已经读过了。
2. **业务逻辑不绑定 LangGraph。** 图 B 的 runtime 修复、第 6 步的 demo，都能直接复用这些模块；以后换框架或接入 Academy，也不用重写。

如果你希望早点看到图跑起来，可以把 3b 挪到第 4 步之后。quote 分支用不到 SENSE，这样下一步就直接进入 LangGraph。你决定。

---

> 带我过一遍sim

[sim.py](http://sim.py) 很短，分三块：**数据结构 → 往网络里"制造情况" → 把一段时间切成若干段报告出去**。下面用一个贯穿的例子：L2 方向 esnet-chi→esnet-atl，容量 100 Gbps。

## 1. 数据结构（第 14–29 行）

`Interval`**（第 14–18 行）** 表示"一段时间内的一件事"：起止时间，外加一个速率。`gbps` 默认是 0.0，因为表示中断时用不到速率，只需要起止时间。

`MockNetwork`**（第 21–29 行）** 存三样东西：


| 字段         | 内容                      | 例子                                                              |
| ---------- | ----------------------- | --------------------------------------------------------------- |
| `topology` | 第 2 步的拓扑，提供每条链路的容量      | L2 方向 100 Gbps                                                  |
| `_foreign` | 每条**有向**链路上，他人占用容量的时段列表 | `{"L2:esnet-chi>esnet-atl": [Interval(09:45, 10:30, 40)], ...}` |
| `_outages` | 每条有向链路的中断时段列表           | `{"L2:esnet-chi>esnet-atl": [Interval(10:00, 10:15)], ...}`     |


`__post_init__` 给每条有向链路建一个空列表。第 28 行的 `for link in self.topology.links` 遍历的是 dict 的 key，也就是有向链路 id。

这个类**不记录我们自己的预订**。我们的预订记在 ledger 的 own 里，模拟网络只负责"外部世界"的情况。这和 3a 定的口径一致：observed 是不算我们自己预订时的可用容量。

## 2. 制造情况（第 31–41 行）

测试和 demo 用这两个方法设置场景：

- `add_foreign`：在**某一个方向**上加一段他人占用。比如 `add_foreign("L2:esnet-chi>esnet-atl", 09:45, 10:30, 40)` 表示这段时间有人占了 40 Gbps，反方向不受影响。
- `add_outage`：传入的是**物理链路** id（如 `"L2"`）。第 37 行在拓扑里找出属于这条物理链路的两条有向链路，两个方向都记上中断。光纤断了，两个方向自然都不通。找不到就报错，防止拼错 id 后被悄悄忽略。



## 3. `segments`：把时间切成"状态不变"的段（第 43–53 行）

这是核心方法：问它"L2 在 09:00–11:00 是什么情况"，它返回若干段，每段内状态不变。

假设已经设置了：他人 09:45–10:30 占 40，链路 10:00–10:15 中断。

**第一步，找切点（第 46–47 行）。** 把所有事件的起止时间收集起来，只保留落在查询范围内部的，再加上查询本身的起点和终点：

```
事件的时间点：09:45, 10:30（他人占用）  10:00, 10:15（中断）
cuts = [09:00, 09:45, 10:00, 10:15, 10:30, 11:00]

```

第 47 行用了集合 `{...}`，作用是去重：如果两个事件恰好在同一时刻开始，就不会切出一个零长度的段。最后再 `sorted` 排序。

**第二步，逐段计算状态（第 49–52 行）。** `zip(cuts, cuts[1:])` 把相邻的切点两两配对，得到每一段的起止 `(a, b)`：

```
cuts       = [09:00, 09:45, 10:00, 10:15, 10:30]
cuts[1:]   = [09:45, 10:00, 10:15, 10:30, 11:00]
配对后：    (09:00,09:45) (09:45,10:00) (10:00,10:15) (10:15,10:30) (10:30,11:00)

```

每一段做两个判断：

- 第 50 行：这段时间是否碰到了任何中断？碰到了就是 down。
- 第 51 行：把这段时间内所有他人占用加起来。

两处都用了同一个判断"两个时间段是否有重叠"：`iv.start < b and a < iv.end`，意思是"事件在这段结束前开始，并且在这段开始后才结束"。

**第三步，算可用容量（第 52 行）。** 链路 down 时可用容量为 0；否则是"容量 − 他人占用"，最低为 0。

结果：


| 段           | up  | 他人占用 | 可用容量  |
| ----------- | --- | ---- | ----- |
| 09:00–09:45 | ✓   | 0    | 100   |
| 09:45–10:00 | ✓   | 40   | 60    |
| 10:00–10:15 | ✗   | 40   | **0** |
| 10:15–10:30 | ✓   | 40   | 60    |
| 10:30–11:00 | ✓   | 0    | 100   |


`MockTelemetry` 会把这里的每一行包装成一个 `LinkSample`，交给账本的 `apply()`。

## 它的局限，以及 3b 要处理的一点

- **一切都是预先设定的。** 他人占用就是"已经登记的预留"，没有随机波动，也没有"传输逐渐变慢"这种情况。第 7 步做 Runtime 需要拥塞、渐慢等场景时，要再扩充这个模拟网络。
- **3b 要处理我们自己的预订。** mock SENSE 接受我们的预订时，模拟网络必须知道这部分容量被占用了，否则它会把同一份容量又卖给别人。但这部分占用**不能算进** `_foreign`，否则 telemetry 报给账本时，我们的预订会被扣两次。所以 3b 会在模拟网络里单独加一份"我们在 SENSE 上的预留"：SENSE 检查容量时算它，telemetry 报告时不算它。

---

> 带我过一遍telemetry

[telemetry.py](../../src/lib/network_agent/telemetry.py) 只有两样东西：

- `TelemetrySource`**（第 15–19 行）：一份接口约定**，规定 network agent 需要 telemetry 提供什么。
- `MockTelemetry`**（第 22–37 行）：这份约定的一个实现**，数据来自模拟网络。

## 1. `TelemetrySource`：接口（第 15–19 行）

```python
class TelemetrySource(Protocol):
    def link_samples(self, link_ids, start, end, now) -> list[LinkSample]:
        ...

```

`Protocol` 来自 Python 标准库 `typing`，用来声明"一个对象必须有哪些方法"，本身不包含实现。方法体里的 `...` 是 Python 的省略号对象，在这里的意思就是"这里不写实现"。

它的含义是：**任何一个对象，只要有一个参数和返回值都对得上的** `link_samples` **方法，就算作** `TelemetrySource`**。**

注意第 23 行的 `MockTelemetry` 并**没有**写成 `class MockTelemetry(TelemetrySource)`，它没有继承这个接口，只是恰好有一个形状相同的方法。这叫**结构化类型**："长得像就算"，不要求声明继承关系。

这对我们的好处是：以后另一位同学做的 Telemetry Agent 客户端，或者一个读 Prometheus 的 adapter，都不需要 import 我们的代码去继承什么，只要提供同样的方法就能接进来。network agent 的图里只写"我要一个 `TelemetrySource`"，背后换成谁都不用改。

**方法的四个参数：**


| 参数             | 含义                                     |
| -------------- | -------------------------------------- |
| `link_ids`     | 要查哪些有向链路，通常是一条候选路径上的所有链路               |
| `start`, `end` | 查哪段时间                                  |
| `now`          | 当前时刻，用来生成 `sampled_at` 和 `valid_until` |


`now` 由调用方显式传入，而不是在函数内部调用 `datetime.now()`。这样做是为了：

- **测试可重复：** 测试里可以固定为 09:00，每次跑结果都一样。
- **能跑模拟时间：** 第 6 步的 demo 可以用一个虚拟时钟快进，几秒钟就模拟完一整天，不必真的等。

## 2. `MockTelemetry`：mock 实现（第 22–37 行）

两个字段：

- `network`：从哪个模拟网络读取"真实情况"。
- `validity_seconds`：样本的有效期，比如 300 秒。真实的数据源会自己给出有效期；mock 没有，就由外部传入，最终来自 config。代码里不写死数字。

`link_samples` **做了两件事：**

第 31 行：算出这批样本统一的过期时间：`valid_until = now + validity_seconds`。

第 32–37 行：一个**双层列表推导式**，相当于两层嵌套循环：

```python
result = []
for link in link_ids:                                            # 外层：每条链路
    for a, b, up, gbps in self.network.segments(link, start, end):  # 内层：这条链路的每一段
        result.append(LinkSample(link_id=link, start=a, end=b, up=up,
                                 available_gbps=gbps, sampled_at=now,
                                 valid_until=valid_until, source="mock"))
return result

```

内层的 `segments` 就是 sim.py 那个"按状态切段"的方法，它返回的四元组 `(a, b, up, gbps)` 在 `for` 语句里被直接拆开成四个变量。`MockTelemetry` 自己不做任何计算，只负责把 `segments` 的结果包装成标准消息 `LinkSample`。

**为什么要包装成** `LinkSample`**，而不是直接返回元组？** 因为 `LinkSample` 是 pydantic 消息，包装时会自动校验。比如"链路 down 却报告有可用容量"这种矛盾的数据，在这一步就会被拦下，进不了账本。

## 数据怎么流动

```
MockNetwork.segments()     模拟网络的"真实情况"           sim.py
        ↓
MockTelemetry.link_samples()   包装成 LinkSample，带上时间戳和来源    telemetry.py
        ↓
CapacityLedger.apply()     写进 observed                  ledger.py

```

第 4 步的 `refresh_if_stale` 节点做的就是：发现账本里某些值过期了，就调用这条链路去拉新的。因为节点只认 `TelemetrySource` 接口，以后把 `MockTelemetry` 换成真实数据源，图本身不用改。

---

> link_samples是用于向telemetry一次性问询多条链路状况的接口吗

**对。** `link_samples` 一次问多条链路在同一段时间 `[start, end)` 内的情况，返回一个**平铺的列表**。每条链路可能对应多段样本，每个样本都用 `link_id` 标明属于哪条链路：

```python
tele.link_samples(["L1:anl-dtn01>esnet-chi", "L2:esnet-chi>esnet-atl"], 09:00, 11:00, now=09:00)
# → [
#   LinkSample(link_id="L1:...", 09:00–11:00, 100),     # L1 全程无变化，一段
#   LinkSample(link_id="L2:...", 09:00–09:45, 100),     # L2 有他人占用，切成三段
#   LinkSample(link_id="L2:...", 09:45–10:30, 60),
#   LinkSample(link_id="L2:...", 10:30–11:00, 100),
# ]

```

返回结果不按链路分组，不同链路的样本混在一个列表里。分组由账本的 `apply()` 自己根据 `link_id` 处理。

**为什么设计成一次问多条：** 第 4 步的 `refresh_if_stale` 刷新的单位是"一条候选路径"，要一次拉齐路径上所有链路的数据。真实数据源（比如 Prometheus）支持一次请求查询多条时间序列，批量问能减少往返次数，也能让这一批样本的采样时间一致。

**它是"拉"，不是"推"。** 这个接口是 network agent 有需要时主动去问。slide 10 里 Telemetry Agent 还有"订阅"的方式：链路断了或者变慢了，由对方主动推送事件。图 B（Runtime，第 7 步）是事件驱动的，那时还要再加一个推送接口。现在 planning 只需要拉。



> 带我过一遍shemas和ledger的变更

3a 对两个文件都只做了增量修改。下面按"改了什么 → 为什么"来讲。

# [schemas.py](http://schemas.py)：新增 `LinkSample`

改动只有三处：


| 位置          | 改动                              |
| ----------- | ------------------------------- |
| 第 3 行       | 文档字符串补了一句：本文件现在也包含 telemetry 样本 |
| 第 16 行      | import 新增 `NonNegativeFloat`    |
| 第 229–256 行 | 新增 `LinkSample` 类               |


`LinkSample` 是 **telemetry 报给 network agent 的消息**：一条有向链路在 `[start, end)` 这段时间里的状况。之前的消息都是 scheduling agent 和 network agent 之间的，这是第一个来自另一侧的消息。

**文档字符串（第 230–237 行）是这次最重要的部分。** 它把 `available_gbps` 的口径写成了契约："**不算我们自己的预订时**可用的容量"。这正是上一步的待决项：只要所有数据源都按这个口径报，账本里的 observed − own 就不会重复扣减。数据源如果做不到，由它自己的 adapter 负责换算。

最后一句"未来时段的值……不是流量预测"是在提醒：telemetry 无法测量未来。所以对 10:00 以后的报告，只能是"目前已知的他人预留"，而不是对未来流量的预测。

**字段（第 239–246 行）：**


| 字段               | 说明                                                                            |
| ---------------- | ----------------------------------------------------------------------------- |
| `link_id`        | 有向链路 id，和 topology 里的格式一致                                                     |
| `start`, `end`   | 这份观测覆盖的时间段                                                                    |
| `up`             | 链路是否可用                                                                        |
| `available_gbps` | 用 `NonNegativeFloat`**（≥ 0）**，而不是 `PositiveFloat`（> 0）。因为 0 是合法值：链路断了，或者被他人占满 |
| `sampled_at`     | 什么时候测的                                                                        |
| `valid_until`    | 过了这个时间，这个数就不可信了。对应 slide 8 里 CapacitySample 的 `validUntil`                    |
| `source`         | 谁报的。账本里的每个数都能追溯来源                                                             |


**三条自洽检查（第 248–256 行）：**

1. 时间段不能颠倒。
2. `valid_until` 不能早于 `sampled_at`，不能"还没测就过期了"。注意用的是 `<`，所以两者**相等是允许的**，表示"测完立刻过期"。
3. 链路 down 时可用容量必须为 0。反过来不检查：up 而容量为 0 是合法的，说明被占满了。

# [ledger.py](http://ledger.py)：从"手动设值"改为"接收样本"


| 位置          | 改动                                                  |
| ----------- | --------------------------------------------------- |
| 第 3–5 行     | 文档字符串：observed 的口径引用 `LinkSample`，并说明由 `apply()` 写入 |
| 第 22 行      | import `LinkSample`                                 |
| 第 47 行      | `Observation` 增加 `valid_until`                      |
| 第 71 行      | 拓扑初值的 `valid_until = origin`                        |
| 第 111–112 行 | 新增 `is_stale()`                                     |
| 第 119–137 行 | 用 `apply()` **替换**了原来的 `set_observed()`             |


## 1. 观测值有了过期时间（第 47、71、111–112 行）

`Observation` 原来是 `(gbps, source, at)`，现在多了 `valid_until`。

拓扑初值（第 71 行）的 `valid_until` 设成了 `origin`，即**账本一建好就已经过期**。这是有意为之：拓扑里的容量只是静态快照（slide 14 的 WfPlatform），不是实测值。所以第一次报价之前，`refresh_if_stale` 一定会先拉一次真实值，不会拿配置数字直接报价。

`is_stale(link, i, now)` 判断 `valid_until <= now`。同样用 `<=`：到了过期那一刻就算过期，和 `LinkSample` "相等即立刻过期"的语义一致。

## 2. `apply()` 替换了 `set_observed()`（第 119–137 行）

原来的 `set_observed(link, start, end, gbps, source, at)` 是一次设一个值的低层操作。现在 `apply(samples)` 直接吃一批 `LinkSample`，和 telemetry 的输出对上了，调用方不用再拆字段。

分两段执行：

**第一段：先算好要写什么，不加锁（第 125–134 行）。**

```python
per_slot: dict[tuple[str, int], Observation] = {}   # (链路, 槽号) → 要写入的观测值

```

对每个样本依次做三件事：

- **裁剪（第 127–129 行）：** 只保留落在账本范围内的部分。比如样本是 08:00–09:15，而账本从 09:00 开始，就只取 09:00–09:15。完全落在范围外的样本直接跳过（`continue`）。之所以不像 `pending` 那样直接报 `OutOfHorizon`，是因为 telemetry 往往一次给出很长的时间段，超出部分丢掉即可，不算错误。
- **换算（第 131 行）：** 用你之前读过的 `slots_covering` 算出样本覆盖了哪些槽。
- **取最小（第 132–134 行）：** 同一个 `(链路, 槽)` 如果被这批里多个样本覆盖，保留较小的值。

举例：L2 收到两段样本，09:00–09:20 可用 80，09:20–10:00 可用 30：

```
槽:            0(09:00)  1(09:15)  2(09:30)  3(09:45)
样本 80 覆盖:     ✓         ✓
样本 30 覆盖:               ✓         ✓         ✓
结果:            80        30        30        30     ← 槽 1 取 min(80, 30)

```

09:15 这个槽里，09:20 之后只有 30 可用；如果记成 80，报出的 offer 就兑现不了。宁可低估，不能高估。

**第二段：一次性写入，加锁（第 135–137 行）。** 加锁是为了防止别的请求在 `pending()` 检查容量时，看到一半新值、一半旧值。锁只包住真正写入的那几行，计算放在锁外面，锁占用的时间尽量短。

**有一点要注意：** "取最小"只在**同一批**样本内部生效。**不同批**之间是后来的覆盖先来的：09:00 拉到 60，09:05 再拉到 80，槽里就变成 80。这符合"用最新观测"的直觉，但也意味着测量值偶尔跳高，就会马上被采用。要不要做平滑或者取保守值，属于观测刷新策略，10/15 会议上 KK 讨论过它可能是一个 AI 决策点，留到以后再定。

## 3. 第 2 步测试的连带修改

`test_slide23_table` 原来用 `set_observed` 把 09:45–10:30 设为 40，现在改成构造一个 `LinkSample` 交给 `apply()`。测试结果不变，仍然复现 slide 23 的整张表。

