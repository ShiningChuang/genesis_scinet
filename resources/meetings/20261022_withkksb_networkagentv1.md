# 2026-10-22 与 KK、SB 的 Network Agent v1 代码讨论

> **日期与参会者**：2026-10-22；Linxuan Zhong（用户）、KK、SB。参会者简称依据用户指定的文件名整理，不补全 SB 姓名。
>
> **材料与可靠性**：用户提供的英文自动转录，无时间戳及 speaker labels，包含大量术语、人名和数字误识别。发言归属按问答关系整理，未经回听确认；代码实现、外部仓库情况均只记录会上说法，未另行审计。
>
> **拆分位置**：本篇从转录开头保留到三人讨论结束的告别；随后“should we discuss now or again, I can share quickly what I have worked on.”起的两人讨论见[会后记录](20261022_withsbafter.md)。对应原文保留在附录 B。

## 核心摘要

Linxuan 展示了 Network Agent 的首版代码，当前重点是 **quote 执行图**，配有消息 schema、topology、ledger、mock network、mock telemetry 和 mock SENSE 等支撑组件。当前采用内部模拟拓扑，尚未接入独立 digital twin；故障修复部分也尚未实现。

KK 重点追问两件事：**slides 中的协议、执行图怎样一一落到代码，以及 LLM 自动生成的 placement 逻辑如何被独立验证。** 目前代码和测试由同一 coding agent 生成；会上没有形成独立测试方案，也没有据此确认代码已充分验证。

近期展示按“总体架构 → 消息及 Python schema → LangGraph → 一两个节点代码 → 测试示例”组织。Telemetry Agent 先基于 mock network 开发，通过查询与异步通知两个方向对接；KK 明确表示近期不必投入真实 digital twin 接口。对外协作 GitHub 仓库的代码提交先缓一缓，需注意访问权限范围。

## 一 从协议和执行图解释代码

KK 多次要求先回到之前的 PowerPoint，说明 Network Agent 原有协议图、任务图与当前代码结构之间的对应关系，再进入具体函数。

Linxuan 说明当前主要实现的是 quote 功能：Scheduling Agent 发来请求，Network Agent 校验消息，检查并刷新过时观测，寻找 placement，估计完成时间，最后生成报价响应。各阶段对应图中的函数节点，再由图构建代码声明节点及连接关系。

关于消息，会上查看了 transfer request、quote request、offer、quote response 等 Python schema。Transfer request 中展示的内容包括 ID、priority、source、destination、bytes 和 time window。KK 建议展示时逐条说明：**slides 上某个消息是什么、包含哪些字段、在 schema 中如何定义。** 转录中部分类型名不清，本文不据此补写精确类名清单。

## 二 Placement 的含义与搜索逻辑

Placement 描述某次传输的候选安排，包括 transfer ID、path、start/end time、rate、strategy，以及受何种流量限制的说明。KK 追问 `blocked_by` 是否意味着必须等待其他工作完成；Linxuan 解释，它用于说明容量受本工作流流量或其他流量占用的限制。会上举例：链路总容量为 100 Gbps，但当前只能分到约 40 Gbps。

双方还澄清请求允许开始的时间与最晚完成时间：不能早于允许的 start time，完成时间应满足 deadline。**请求的 deadline 与候选 placement 算出的 completion time 需要分别理解**；转录里对 end time 的指代来回切换，精确字段语义仍应以 schema 和 slides 核对。

展示的三种策略大致为 earliest start、max rate、min rate；其中第二种名称的转写不稳定，也讨论了等待容量释放、以更高速率完成的效果。Min rate 的目标是在 deadline 内以较低速率完成。本文保留策略含义，不把转录中的名称当作已核对的代码标识符。

Linxuan 介绍搜索函数：输入候选路径、请求、当前时间等，搜索可行开始时间与速率，检查 ledger 的时间范围及 deadline，并根据路径沿途链路的容量约束确定可用速率。KK 希望看到的是这些定义背后**真正寻找候选安排的计算过程**。

## 三 LLM 生成代码与独立验证问题

KK 看到 placement 搜索中读取 topology、ledger 并取路径瓶颈容量的代码后，追问是谁写的，以及生成时给了什么提示。

Linxuan 说明，代码由 coding agent 生成，主要输入是此前讨论的想法与三种策略，没有逐行指定搜索细节；代码结构说明也来自与 LLM 多轮讨论。这里说的是**开发时使用 LLM 写代码**，这段交流本身不足以说明 placement 在运行时调用了 LLM。

KK 随后问：怎样知道生成的 placement 逻辑正确？Linxuan 表示已有自动生成的测试，但尚未仔细完成全面验证，并确认当前代码与测试由同一 agent 编写。

KK 用软件开发中不同团队分别写实现和测试作类比，提出应考虑独立生成或设计测试，避免测试只重复实现者的理解。**这是会上明确提出的验证缺口；独立验证尚未完成，具体采用何种工具或流程也未确定。**

## 四 Mock network 与可替换接口

### Telemetry 接口

当前 quote 流程会检查观测是否 stale，需要时查询 telemetry 并更新 ledger。Linxuan 展示了 `link_samples` 接口思路：提供需要刷新的 link IDs 及起止时间，返回所需链路信息。当前是 mock telemetry，SB 可以实现相同接口，再替换该 mock。

SB 表示已设计 Telemetry Agent 的 northbound 和 southbound API：前者服务 Network Agent 等调用方，后者从 Prometheus endpoints 获取指标，具体设计留到与 Linxuan 进一步对齐。

### SENSE 与 digital twin

当前 SENSE 部分也有 adapter/interface 和 mock 实现。双方讨论未来可能接 digital twin adapter，期望其接口与实际系统相似，以便替换实现；这只是预期接口方向，尚未证明两者可以直接互换。Digital twin 的名字转写为 `VIT` 等，无法确认。

KK 在会议末尾明确说，目前不希望把精力放在实际 digital twin 接口上。先让 Telemetry Agent 从 mock network 获取信息，真实系统接入留待后续。

## 五 示例拓扑、背景流量与报价结果

Linxuan 用模拟拓扑展示两条候选路径、链路容量、背景流量占用和链路故障等信息。KK 建议把 `foreign traffic` 称为 **background traffic**，表示不属于当前工作流的其他流量。

示例中一条路径的 L2 在约 09:00–12:00 受到背景流量占用，可用速率较低；之后容量释放，可以采用更高的速率。报价结果展示了立即以较低速率开始、稍后以较高速率开始，以及采用较低速率但在约 15:00 deadline 前完成等不同安排。

KK 对“较晚开始但传输更快、较早开始但持续更久”的结果做了基本合理性检查。转录中的具体速率、完成时刻和拓扑站点名有明显歧义，**不据此登记精确数值结果，也不把口头合理性检查视为完整正确性证明**。Linxuan 还说明代码中的拓扑与 slides 并非完全一致，其中另一条路径经过额外节点。

## 六 单请求 state 与共享 context

Linxuan 将 graph state 比作每个请求的“草稿纸”：校验、刷新、路径计算、placement 和响应等节点读取和更新这次请求的中间结果。

Context 则用于跨请求共享 topology、ledger、offer book 等对象，不是每次请求各有一份的临时结果。讨论认为 topology 和 ledger 等应放在数据库中；会上是在解释共享与持久化的设计意图，不能据此认定当前 mock 已实现数据库持久化。

## 七 故障处理需要异步通知入口

KK 问，如果 telemetry 报告某条链路失效，当前实现应该在哪里扩展以重新计算。Linxuan 表示故障修复还没有实现，预期 Network Agent 先尝试局部修复，无法解决时反馈给 Scheduling Agent，由后者重排 workflow。

KK 要求考虑 Telemetry Agent 主动发来的异步通知，例如基于事件的 publish/subscribe。双方认可应有两个方向：

- Network Agent 主动查询 telemetry。
- Telemetry Agent 在链路故障等事件发生时主动通知 Network Agent。

本次没有定下事件 schema、订阅机制或完整修复流程；这是后续接口需要覆盖的能力。

## 八 对外展示、仓库与近期安排

### 展示顺序

KK 建议架构图、执行图与代码来回对应，先讲整体，再看一两个节点，最后用测试示例让行为更清楚。无需逐段遍历全部代码，但应能解释提示输入、结构与生成结果之间的关系。

### 合作方代码与 GitHub 权限

Linxuan 提到查看过合作方分享的代码，认为它与另一项 OFC 工作有关，尚不完整，其中引用了 LangChain；双方认为这为当前 LangGraph 路线提供了一些兼容性上的信心。这是会上观察，未核对对方仓库、实现状态或框架依赖。

KK 表示，次日讨论时会建议**暂缓往合作方协作 GitHub 仓库提交代码**。他提到 Mariam 的邮件涉及更谨慎地管理访问权限，拟限制在 proposal 相关人员范围内；对其他人添加成员的动机及对象，KK 自己也表示不确定。本文仅记录权限管理顾虑，不将这些推测写成事实。

这与组内向 SB 分享代码、以 mock network 开始开发是两件事；本次未落实共享仓库的具体地址或权限配置。

### 时间与分工

SB 先与 Linxuan 对齐设计，再与 KK 讨论，并争取接下来几天做出基于 mock network 的 Telemetry Agent。KK 提到次日下午约 15:00–17:00 有空，具体时区未在转录中说明。

按会议日期推算，“明天”为 **2026-10-23（周五）**，“下周一”为 **2026-10-26**，“下周二”为 **2026-10-27**。会上分别谈到次日 walkthrough/hackathon 与下周二较完整的进展说明，不应合并为同一场活动。Linxuan 因准备 compiler 相关考试希望减少会议时间，KK 同意其跳过周一组会；Linxuan 表示周二仍可做一些说明。次日 hackathon 预计最多参加约一小时，随后有约 11:00–12:00 的 colloquium。以上均为口头安排，尚未核对日历。

## 九 行动项与开放问题

| 事项 | 负责人 / 状态 | 边界 |
| --- | --- | --- |
| 按架构、消息 schema、graph、节点代码、测试的顺序组织展示 | Linxuan | 展示现有局部实现，不要求完成全部功能 |
| 解决代码与测试同源带来的验证缺口 | KK 提出；具体方法未定 | 未形成独立验证结论 |
| 先对齐 Telemetry Agent 设计，再与 KK 讨论 | SB 与 Linxuan；随后 SB 与 KK | 先用 mock network，近期不做真实 twin 接入 |
| 为运行期预留 telemetry 异步事件入口 | 两个 agent 后续对接 | 与主动查询并存；事件契约未定 |
| 谨慎处理向合作方仓库提交代码 | KK 提出暂缓 | 不等于停止组内代码开发或分享 |

仍需明确：三种 placement 策略的准确语义与独立测试标准；异步通知触发后如何定位受影响请求并局部修复；从 mock 切换到真实 telemetry / SENSE / digital twin 时的接口差异。

## 附录 A 转写存疑点

| 原转写 / 项目 | 整理口径 |
| --- | --- |
| `theang graph`、`long graph` 等 | 按执行图语境整理为 LangGraph |
| `quot`、`court`、`cold` 等 | 仅在报价上下文整理为 quote；其他位置按 code 等语义辨别 |
| `later`、`nature` 等 | 按共享预留账本语境整理为 ledger |
| `mark`、`Mac network` | 按模拟实现语境整理为 mock network |
| `foreign traffic` | 记录 KK 建议的术语 background traffic |
| `VIT` 等 | 疑似 digital twin 名称，不补全 |
| 合作方人名、`HP guys`、`OFT/UFC` 等 | 人名及团队不强行补全；会议名按后续明确的 OFC 记载，仍待核对 |
| 速率与完成时刻 | 只记录定性关系，精确值回查 slides、测试输出或录音 |

## 附录 B 原始转录（本场部分）

以下保留用户提供转录的对应片段，不改正术语、语法或发言归属。与会后讨论的切分位于同一原始段落内；前后两篇附录按顺序拼接可还原输入转录。

<!-- BEGIN RAW TRANSCRIPT -->
Because I think she was in the hospital or something she just got out of the hospital today so hm Okay.


Let's start.


What can we do about this network agent and theang graph that you had shot shall we walk through that and see how it's encoded up orward?


Uh Okay, I'm sure my screen.


I can see it uh Is this code that you have already written or what?


Yes, this is a there is like one uh uh this is all the person files I I got.


Currently, I implement the therology.


The simulation was sense and the tet tomerent and the later and the of course the graph graph meaning for the network agent task.


Yes.


This part is a cold router overview.


We can see that we can see that we have the orchestration layer start from the bottom, I think, right?


By the way, go from the top.


It's okay.


We have the little work agent graph.


The graph is coming from the the HM I sorry, where is that?


I'm.


You heard some slides, right, that you walked me through the other day from the network agent architecture and then the Lang that you had for that network agent down down there the up, up, up, slow slow the down, two steps three steps down, down, down, one more. Ah, there, no?


Just stop.


Don't don't keep going.


Just stop.


Okay.


What is this?


They see the card of the car in the code.


I thought I'm I'm finding the graph.


Sorry, the midery is the graph.


Here, broke Gallia.


Okay.


Yeah, just what you showed me before.


Yeah, currently I implemented the the photograph.


It's a scheduler to the schedul sends a request to this network agent?


Yes.


Where here.


Ah, there.


Yeah, it's part.


And including ord the scale Yeah, so we can walk through this tomorrow, okay?


Yeah, okay let's start.


It's the thing.


Okay, let's start.


Let me start on the code.


Okay.


And uh first, let's see the uh this is a graph.


First, we have the stage.


Remember the network agent task graph that you had before?


Is there a one to one between that graph and this graph that you have here?


On that slide for the network agent, the protocol craft that you drew, right on that slide on the poweroint, as that got anything to do with this sorry, what what do you mean?


This is the coron code overview, cold stoucher.


Okay.


And the current, the Kouter I implemented the little the code graph one of the function of network agent.


Should I go through the code?


Okay.


Uh, so we have a val.


This one two, three, four, five, function function respond to the node the quote node are are the validated node?


Yes, are theivated bo, to the request.


And so different aspects of the request are being validated is it We check here if the request be the format of our quot request.


This is the schemas we defined here, or or all the messages I define in schemas we can see including transfer request, quot request an offero the reason, transfer code, and theotersponse, all of the messages adified in the schemer'siser.


Okay. And they are the um uh defined as the we mention in the slides.


For example, the format for example, for the transfer required, we can we can check the lights.


We have ID ID, priority, source, destination, bites, and a window, so here we hobble all the same Okay.


So my suggestion is that you go to the slide, you tell me each of the messages and you show me the how those messages are defined in your schema, right?


So you've got a transfer request, you've got a qu court request, you've got a qu court response.


Great.


You've got a where is the offer um uh skate.


This is not offered.


I mean, offering here. Uh operate here.


Okay.


So these are the ones that you have defining the schema.


Okay.


All right.


Yes.


So I got the so how I understand now that for each of the protocol messages and the formats that you' defined your guard schemas defined in Python.


Yes. Then then what?


After that..


After loud we can go through the work floor of the functionalote.


So first we validated the trans transfer request the message, if it meet our if it meet the go go back to the PowerPoint switch to the PowerPoint.


So go to the next slide where you had the graph. Mean.


Right?


So your first validating and in that validation you're also saying if it is tailed then you'll refresh it right?


Yes.


Okay. Uh I'm assuming that you have some procedure that is defined for deciding if it is still, right?


And then if it is tale, then you have some procedure for refreshing.


Yes.


Okay.


Then while the next step is to find placements, so show me the work uh that the agent does for finding the available time slots and capacity to support this request. Shall you look you the code?


Yeah, the finding of placements.


Okay.


Here.


Our let's probably make it this this songi means, give me a pass I will give you the offer which it contains a third high and the under the tie and the and the requirement and the rate Only the rate we can see the definition of placements.


Here.


Okay.


The placement contains a transfer ID, the pass, the startheight untie under the reed of strategy and the blocked by who. Or does blocked by the means if this We are to wait for something else to be done before you do this place.


That means I didn't uh you utize the whole capacity of this link.


Maybe this link the marks the capacity is where 100 GPPS is, but I only use the 40 GBPAs so why it's blocked by my own in my if it's blocked by my own traffic or it's blocked by the foreign traffic.


My own my own requirement are blocked by somebody else sending higher rate.


Okay, yeah.


What about deadline?


Dead line So is is end the completion time?


Yes this is complet yes.


Is that the deadline then uh that the the big line is transferred must be complete by that time yeah for the contending in the in the transfermary case.


Yes.


I'm asking that this is the maximum time that you can take and that the transfer must be complete before this and time. The other high will consider the the and there are three strategies, including early star maxed or meanrid, the meanrid wheel will run as a meanrid and finish it it before the daylight.


Okay.


And you're saying that it it cannot start before the start time. And you're saying earlier start means you cannot start before the start daytime, correct?


Yes that is that is here.


It means yes you as as as the part of meetings, but it cannot exceed the third time . Okay, so this is all the definition.


What is the work that it does for figuring out where to place it?


See these are all the definitions, but let's see how does it find out o' all the candidates and then figure out how to place it?


This function search in the placement.


We have the capacity.


We have one pass and we have the request and the start the current high, and the restable restape means uh we will try we will try to find the syable rate from zero to the maximumid. Dipped past Dave by the tape so we get the earliest time I didn't lie first and uh to see if uh beyond the horizon that means the it's beyond the horizon of the lure and they've except the line we will reject and then we got the uh cup comings uh the maximer uh link carposity in the pass, we need to find the mean capacity in this link so for doing this did somebody did you give what guidance did you give to uh this lineraph or whatever took cord this line, uh so we need to come back to this graph.


Oh, I'm sorry, which line?


Sorry. The scamp lane.


How did it determine to quote the come up with a code for that to say that it is a minimum of the ledger it takes the topologies, things, it takes the capacity of those links.


All that you didn't write this piece of cord rate?


You made this agent agent cod system create thisord, correct Yes.


How did it know to create this?


You mean uh how did it no how did it this network agent and know the how to call the search function?


No, no.


How did who wrote the search function?


You didn't write the search function, right?


You gave some prompt to cause the search function to be coded up.


Yes So what prompt did you give to create this these things what how did all this court get created?


That's what I'm trying to understand.


I think if the based on the strategies that were mentioned so where uhction, can you go to those three strategies that you mentioned uh the minimum rate?


Yeah, yeah.


So if we give these this earliest start back mid rate. Uh based on this, I think the AI can determine that for earliest start it has to get the uh it has to read the link capacities and based on the capacities uh availability has to perform some but I'm asking whether you give anything more than this strategy specification for it to be able to create that piece of code for the agent.


No I didn't too much details.


I just gave it the ideas we mentioned before. Just like this threeies now or finish first or shifts and capacity, they are accordingly accordingly equal to the it.


So you that creates these three strategies.


Yes.


And then all this code is automatically generated yes yes. . Okay, yeah I say.


I see.


Okay.


Should that continue this part or, so the main thing then is, how do we verify?


That the c that is generated like what you said the court that it was doing for placement how do we know that the placement code is correct?


We can verify to using some tales to test code, I think.


Current I'm not uh I'm not uh carefully treated treated, but I later like when that go through the following steps like complete all the code I will , I will completely to some tested samples.


So will it be can you ask it to jet a bunch of tests?


Yes, of over the act actually no, currently we have the taste. Uh should I introduce the test now?


No, no, no no.


I'm I you you can go through but but you're saying those tests are also automatically generated.


Yes.


My my question is whether those tests are generated by the same LLM that created theord or du find a independent way of generating those tests, so that you don't really have a good knowledge of the code to cause you to then gener generate those tests.


See if you look at software development, right , some group generates the old, a different group generates the tests.


Right.


And in your case, how do you do itenerating the testing?


Currently, they are right now writing bio theme agent..


That because the current quality is a very simple, so you can move that you can sy so I think the taste is is is uh is okay currently.


But this thisord structure overview is also given out by the LLM. Yes, I just talked to you the agent and give my explanations and I would talk for multi terms and we get with kind of a review.


And then once you get this overview and you look at it, you say, okay, uh, as far as the decision logic is concerned, you have to find the placement and then you have to estimate uh when this thing will finish once you place it , correct?


So then you know that that is the cord it'll generate for these two pieces.


Yeah.


So how will you be able to explain to the HP guys tomorrow about the structure of your network agent and uh I think you have a network agent, you have something for the telementary also from what I saw and then you have something to generate the topology also, correct?


Yes.


So you are not interfacing with a separate digital twin for the topology you are creating an internal topology here.


Yes, I didn't use that here or a sense.


I I just uh get a interface.


This or this is interface.


And if the ser will compliment the to compliment the tenement agent and as an thermac can use this kind of interface and implement the examples. Actually for teletary agent, I developed those graphs which you had.


So I have like the protocol overview, like what North part API is the teletter agent can give to the network agent. And what Southbound AI is the telemet regent will use to actually syn the data from the Prometheus endpoints.


I actually came up with that design.


I can go go through the designer in case it's fine.


I can actually generate the code.


So, you know, it should be possible for for this part, uh it uh for telementary agent, the interface to the tele agent is out we will just a cor here, resh you stay you still.


If it's still, so it will use the later to write her the new data to the later, and here it will core tenmentary and the linkos samples, and that gave you the least of link link ID, which link ID Ieared you know andeared to updated so sorar just can implement the link samples.


I give you the id . I give you third hand and tie, and you give me the information I need, so this is the interface and here adjusted with a implement the mark telementary, is assimilated for taste, partly, but he he can instead create the actual telemetary agent.


Yes, just a replace replace this is function. And implement it is the interface.


So I think it's okay.


And the for sense part, we also has a an adapter and another interface here.


And the very mag sense just for haste currently.


And if you want to you turn extend it, it can also uh implement the interface.


So we might end up having instead of having a sense adapter, we might have a adapter to the VIT, correct?


Yes, for the one, yes.


So this part should be saved for next phase.


Puddenly we can just to, but as that he should also provide the same api right.


Yes, yes.


So I think it's that is the intent of beingital twin right?


Yes that it should look exactly like the actual yes so there is no difference. And uh currently we also have uh the Mac network.


It's written po justology and the record the simululator the typology and the record the link booked and the current date.


So we can see here in the taste we have the topology.


It's the same as our flight shoot here.


It's a seems it's the same topology here.


And if a sample and uh we have the link linkn name source destation and the capacity GPSs and uh for the taste we can get the kind of result.


Here is a node. Note one, two, five six this note and we have the link and the link capacity and the foreign traffic is simulated if we have for example, we have the foreign traffic in L2 here uh foreign meaning background traffic.


Yes, if not if not it's not just of our current work low.


Right.


So it's the background traffic..


So we call it background traffic.ground traffic and it's and Egy in the link.


The means it's touring night 12th and the wrestling will be up that specific link in that quality, , yes.


And out here there is no.


That means the link is uh failure failure.


And we have a requilt request is from is from uh AR and there are two here. From here to NRNL there let's not.


Okay.


Some two times two time values this start time to the same time.rect then no that is wrong are names from here sorry from here to here okay so it will go through a one and uh gate arrive AT and goes through L2 the chi and get you the next node and it goes through L three.


This is the pass.


Okay, okay.


So, okay so in this request, it comes relate it uh the the little agent gave the candidate pass that one andu Pass means if the if the pass we may just this pass.


And the part too actually is because we is not the same topology.


We we have here.


In the topology of this code, they will go through another node. This is another note.


So this is the part two.


So we get pass one and a pass two So, you know what you should do when drawing, so you go up uh for drawing, right?


The second choice in the draw.


Okay, it's called a vanishing pen.


Okay?


So you can draw to highlight and little after a few seconds it'll go away.


Okay, I see I call it.


Okay.


I got it.


So we got the pasta and the past two. Uh either will say is for example for a pass, it will goes from nine to 12 at the 4 GPS because because L2 eats occupied by a foreign traffic by the wrong. Background traffic and so with the the battle link is O2.


And the front two, uh 15, it will after the maximum capacityer rate hundred after after in no power make, but they stay the first to link in the battle capacity and the first link has the capacity of hundred g Yes, yes, okay.


So similarly the two will use another pass.


So and then the will say links refrehed this lift, and finally wake the result with the cold result, the after computing wake is the first offer, staff wrong nigh, and at the kick at of the rate of 42 p and a finish at this time, and the daylight the day line is is 3 pm so it makes it before that it.


And it four and the rule is already starred, yes, so it's a star at the as the pass. And the p is pulled by the background traffic. And it give that the second offer.


It's from tiled to is a thor adult 12th, and other speed of 100 and this is finish at 1 p.m. So that's what bugs me.


How come if you or you starting at 12 when it's done by 12 some 13 something the other one started at nine and went till 1145.


OK all right. Lower bend width it took you longer.


I was just doing a simple validity check that it is doing it correctly . Yes.


Okay, yes.


Yes.


So currently asking it works well.


Okay, let's minimum rate you're saying if I start at nine and I'm only using 20 gig, I can finish by 2:45.5. Or 230, whatever.


Yes, yes. 3 o'clock deadline.


Yes, they say is a current example. And come back to the code So yes, so we have this survive stage and here we' build a graph.


What will the graph?


Build the build the work floor. Build the this graph.


We implement the function for each stage.


Right?


And the build the.


But I thought the graph was that function graph was specified.


What do you mean by build it now?


Oh, what you with the prompts?


You said what the function graph is and that's what this is different making the definition of that all the different functions of the function graph, and how there connected . Yes, that's what this is defining.


Okay.


Yeah, so this is a workflow of code and uh and the cost state, we can see it's like the paper dropped and the it goes through all the work flow.


And before each node, for example, a four less valid pango, they will it will modify the response. And the request and the refreshive tale will use the request and the generate then repass and the refreshed here right and before the placemement van the placemans will use the request and the will use the pass here use the use the pass and the generator placement. And the feel it choos the state so the state just like the paper draft, it records each it will record each each for each request.


Unfortunately we get the response.


And the followed taste forotes demo, we can doubt to make the network. Goes onitterook, build some persistent data, electropology, like the later, both are those are in the context context here . What do you mean by context?


Context, is here.


This is a context. Context means is a persistent uh persistent data.


We'll go through we'll give the third of the four different requests like topology, that the later like the offer book, they areore, the the o serve for a different requests, not for yes. And the topology and the nature abbit should be all of the all of the requests.


Yes, yes.


And the topology and the lead should be stored in the datahouse database.


So this is the context.


Context is like if it's like the rare exam.


You write you write down your answer to the to the exam. And that and the state is just like theraft paper, you write down for each record, for each recording, for each request. For each request.


Yes..


And fair it's a rare also right.


We cape right the book modify the later, Yes, so Now, one of the things that we will want to know how to do is what happens if there's a failure.


How do you recompute?


You mean if there is a fenure in the network, the network agent, we talk will fix it locally and the or, or feed back to the techn agent and schedule agent reschedule the flo in schedule.


Yeah.


Current I didn't implemented this part.


I know.


I know.


I I don't expect that you would have been if you were to think about doing it, where would you think about going and changing to be able to accommodate that kind of It comes from the telemeary to say some link is done, right let us say then you have to go through this whole process of rescheduling.


Yes.


So will you allow for the telemeary agent to give you a synchron's notifications?


I think it should be yeah.


So there should be an interface from themittery to Europe.


Yes, you should actively get the information from the element agent and also proact and in how you say. Passively, poor uh like subs I was scrabishing for subscription information from you for information from the telemitary agent the telemitary agent publishes something based on an event.


Yes. Will be too, yes.


Okay.


So if you want to sit and explain this, right, it would be good if you show the slides and then the code slides cord slide cord, right to say here's what I' defined based on the proms this is the code that's generated. So that you have the overall agent chord understood for people, right?


Yes.


And I checked the Karen's code He said that heushed some code in look at the hub and I found Yes, yes. And I found out he she stayed before that it's uh it's the code of OFT it's another conference, not here, and the h and she implementates some agentim work for that and so she she shared the code in theab and they found that it's currently it's not imple it's not a completeed and uh but it's a good news that I see that she used a lung chain in his coat in her good.


So I think it's good for us to use long long graph.


Right good good good.


Okay, so compatible.


Yes. But no.


But but currentlylease her call didn't implement her agent actually, I think it's weird.


I see.


Well, I don't know if she's still developing or this is from UFC in 2026, which is which was probably OFC is usually in March or something, right I think I don't know.


I forgot it.


I used to go when I was in A&T before.


No, I don't remember when OFC is the time of year.


Yes.


She, yes she judged.


I see she j imported the lunch land agent, not a long graph, but agent and the Langra are both agent of Remorg, act agent is based on the cord of agent is based on Langraf. And the agent is canals two node large young motto, tu, ai, AI There are two node in long legend.


It's it's is more simple. For graph we can write our own uh workflow Yeah.


I see.


Oh.


So for tomorrow, I I would I am going to say let's wait to check in any code. Right to getub although, you know, I asked her who are all the people who I have access and she said she's going to be a little bit more careful right now Harvey seems to, and everybody randomly or maybe that is my view of what he's doing.


Maybe there is something else more sensible in a strategy I do not know. But uh Mariam uh sent a email saying that she will be more careful in managing who has access to the get up.


I say okay and she will only give it to the people on the proposal rather than every kind of person with Hari, including some high school student and all, I think eh that's the interpretation I had of some Indian guy that he was trying to add to the group I don't know if you saw the email from Harvey or not.


Maybe you guys were in talk with.


No, I'm not sure. So for tomorrow meeting, should I the explained the actually should I explain the code we have not really, right?


How did how to explain is the important part?


Yes, and my feeling is show the architecture first, then say what are the things that uh are defined in terms of message format and so on that goes into the schema just like you were telling me.


And then show theangraph and then use that to say here's the code structure that I have and then walk through maybe one or two pieces of the of the node, yeah.


And the gave the and the show the show the taste to hear.


Yeah.


I think the test will be more making it more clear.


I think the test. So I can you can you both see how over the next few days you can create a teleary agent just like you have here with a mark network actually professor design that I have uh should I discuss with lecture and first like if that is a thing good uh and then I also discuss with you two things that I have planned for is that good and uh I uh I don't know if I should discuss today or if you're free any other tests first talk with Lenhen and then we can talk tomorrow.


Okay, yeah.


For me, I think I'll turn tomorrow's meeting, I need two folks down to prepare my meetingang of competitor.


So the only spend the next Tuesday?


So I have several flight to review, so I want to spend the all of my time doing a lot.


Okay.


Talk a little bit with uh so he can get started and then go first.


And then once he feels comfortable then you can let him go.


But will you be able to attend next Tuesday's meeting?


Because I think that is when we should do the main explanation of what we have done.


I can attend the two days the meeting.


When is when is the compiler Oh, yes it's Tuesday.


After the meeting after the meeting with 12.


Oh but then that's not good.


Let me see how will you be able to study enough that you can spend a little bit of time on Tuesday?


I think I can explain something on Tuesday.


Can I escape to the meeting on monday ? What Monday our grew meeting?


Yeah, go ahead.


Okay thank you.


No problem.


So you can talk withingon and then afterwards you can discuss tomorrow tomorrow um sometime in the afternoon with me.


I think tomorrow I'll be uh in the afternoon it will be like between three to five I will be free uh at this time I have these and office over. Uh it's I can meet youate that time okay.


She's the elementary agent uh get the information wrong fromach network or network right now.


Okay.


I'll see okay.


I wish I will share the hub.


We share the code to withARA, okay.


I would not want us to sit and think about the actual interface to VIT or anything like that no.


I say okay, sure.


Okay.


All right.


Okay, let's I think, you know, even though they sayackaton for three hours and so on, I think we can spend one hour.


That's enough with them at the most tomorrow, okay?


After that we have the cloak here course tomorrow between 11 you 12th So I think we can't just uh attend it unexplained explain something in the meetingory t turned to tend to later.


Right.


Yes.


Okay.


All right.


Okay, guys.


All right?


Okay.


Okay, okay, thanks.


Okay, bye.


Thank you bye bye, sure bye 
<!-- END RAW TRANSCRIPT -->
