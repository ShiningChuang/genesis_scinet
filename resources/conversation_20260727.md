# AI for Science 新项目背景问答(2026-07-27)

> 与 AI 的对话记录,共 7 轮问答:第 1 轮是对组会录音的重述,其余为围绕项目背景的追问。
> **原文一字未改**,仅做结构化排版(统一标题层级、清理转写残留的空代码块与多余空格)。
> 其中 Q7 与 Q2 是同一个问题——在锁定 SciNet 与 Mariam Kiran 之后再问一次,答案已不同,两版都保留。

> [!NOTE]
> 本文来自语音转写 + AI 整理,人名、项目名有误识别风险(如 Miriam / Mariam),
> 文中多处标注了「录音未提供答案」「这是推断」,引用前请回到原始出处核对。

## 目录

- [Q1 组会录音重述:导师介绍的 AI for Science 新项目](#q1-组会录音重述导师介绍的-ai-for-science-新项目)
- [Q2 这个项目到底在做什么:是要做 auto research platform 吗](#q2-这个项目到底在做什么是要做-auto-research-platform-吗)
- [Q3 Genesis Mission 是什么](#q3-genesis-mission-是什么)
- [Q4 合作方研究人员是谁,digital twin 如何获取](#q4-合作方研究人员是谁digital-twin-如何获取)
- [Q5 digital twin 和 ns-3、OMNeT++ 有何区别](#q5-digital-twin-和-ns-3omnet-有何区别)
- [Q6 这段 ORNL 项目经历对 AI infra 求职的价值](#q6-这段-ornl-项目经历对-ai-infra-求职的价值)
- [Q7 二次追问:锁定 SciNet 后,这个项目到底在做什么](#q7-二次追问锁定-scinet-后这个项目到底在做什么)

---

## Q1 组会录音重述:导师介绍的 AI for Science 新项目

> **问**:(本轮无显式提问文本;下文是 AI 对组会录音的重述)

**答**:

下面只重述录音中 **AI for Science 新项目**的内容，不延伸到外部资料，也不把导师尚未明确的部分补成确定事实。由于转写对人名和项目名称有少量误识别，我会标出不确定处。

### 一、这个新项目为什么在会议中被提出

当导师判断当前 GPU multiplexing 项目风险较高、不适合继续作为你唯一的博士主线后，他马上提到：

> 组里有一个 Department of Energy 项目即将正式启动，需要学生参与。

导师认为，这个项目比当前 GPU 微体系结构方向更符合你们组的优势，因为它可以包含：

- 系统研究；
- 科学计算；
- 分布式环境；
- 网络与计算的结合；
- GPU 之间的数据传输；
- 可靠性和韧性；
- AI 驱动的科学实验。

他的原话所表达的意思是：如果这个项目第一阶段做得好，研究组可能因此获得一条持续很久的研究和资助“跑道”。

因此，导师不是让你单纯换一个小题目，而是希望你逐渐进入一个可能发展成研究组长期主线的大项目。

### 二、项目所属的更大计划：Genesis Mission

导师说，这个项目属于美国能源部新近宣布的一个计划，录音中称为：

- **Genesis Mission**
- 有时又被转写成 **Genesis Machine**

从上下文看，正式名称更可能是 Genesis Mission，但录音转写并不完全可靠。

导师将这个计划描述为当前美国政府重点推动的方向之一，其核心目标是：

> 用 AI 驱动科学实验，探索新的科学知识和新的研究路径。

也就是说，AI 不只是用于：

- 训练一个模型；
- 优化某个 ML benchmark；
- 帮研究人员写代码；

而是进入整个科学研究过程，帮助：

- 设计实验；
- 选择下一步实验；
- 调整参数；
- 分析中间结果；
- 控制实验流程；
- 在大量可能性中搜索更有价值的方向。

导师还强调，这不只是某个 DOE 小项目，而是一个具有更高层政府战略色彩的计划。他用比较夸张的表达说，美国政府正在把大量资源集中到这个方向上。

### 三、竞争非常激烈：约 8000 个申请，约 200 个入选

导师提到：

- 整个计划大约收到 **8000 份项目申请**；
- 最终大约有 **200 个项目获得支持**；
- 你们组参与的项目是其中之一。

因此，导师认为团队能够入选是非常幸运的。

他反复强调这个数字，不只是为了说明竞争激烈，也是在说明：

1. AI for Science 正在得到很高层级的重视；
2. 这是一个可能迅速升温的研究领域；
3. 当前阶段虽然资金和时间有限，但它可能通往规模非常大的第二阶段。

你也回应说，AI for Science 很可能成为热门方向，因为目前 AI 已经可以自动化不少机器学习流程，而让 AI 更深入地参与科学研究，还没有被充分开发。

### 四、项目此前处于保密状态

你问导师是否可以看看 proposal，以及项目什么时候正式开始。

导师解释说：

- 他们此前已经知道项目被选中；
- 但 DOE 设置了 embargo；
- 在美国能源部长正式宣布之前，项目组不能公开谈论；
- 如果提前泄露，可能会惹麻烦。

导师说，直到前一个星期三，能源部长公开宣布这些项目后，他们才可以正式讨论。

因此，在这次会议以前，导师没有把项目完整告诉你，并不是项目不存在，而是因为当时仍处于保密期。

### 五、现有 proposal 很高层，尚不是清晰的研究方案

导师很坦率地评价目前的 proposal：

> 它是一个非常高层的 proposal，你看了以后甚至可能觉得有很多“bullshit”。

这里不是说项目没有价值，而是说当前材料中包含大量：

- 宏观愿景；
- 政策语言；
- 战略目标；
- AI for Science 的宽泛描述；
- 为了获得政府项目支持而加入的包装。

导师认为，大型政府项目往往都是：

- 一部分真正的技术内容；
- 一部分高层愿景；
- 一部分现实政治和资源分配因素。

因此，项目“被资助”不等于技术路线已经全部确定。

真正的研究问题、系统设计和创新点，还需要接下来由团队逐步做实。

### 六、导师认为当前真正具体的技术内容并不多

导师说，现有 proposal 中比较具体的技术部分，主要是他自己加入的内容，包括：

- **reliability**；
- **resilience**；
- 更高效的 **GPU-to-GPU data transfer**；
- 使用 **6G** 或下一代通信技术；
- 网络与计算的结合；
- 分布式环境中的系统支持。

而其他大量内容，目前更多还是关于：

- AI 自动驱动科学实验；
- 科学发现；
- digital twin；
- 智能科研平台；

这些部分还比较抽象。

导师的判断是：

> 现在项目缺少的不是愿景，而是需要把愿景转化成可以实现、可以评估、可以演示的系统技术。

所以你们接下来并不是简单按照 proposal 写好的步骤执行，而是要参与定义：

- 究竟解决什么问题；
- 技术创新在哪里；
- 系统如何构建；
- demo 展示什么；
- 什么结果能支撑第二阶段申请。

### 七、当前是一个六个月的加速阶段

导师称现在是一个 **accelerated six-month effort**。

这六个月的主要目的不是直接完成一个成熟、完整的大系统，而是：

1. 快速确定有价值的技术方向；
2. 做出 proof of concept；
3. 构建若干可展示的 demo；
4. 证明团队具备继续推进的能力；
5. 为年底的 Phase 2 proposal 准备材料。

导师说，在现在到 12 月之间，团队可能需要展示几次 demo。

到 12 月时，他们需要提交或准备第二阶段 proposal。

因此，这六个月的成功标准不只是“写一篇论文”，而是：

- 能否形成清晰的新想法；
- 能否展示可运行的原型；
- 能否证明这个方向值得大规模投入；
- 能否让第二阶段申请看起来包含大量新的技术思考。

### 八、Phase 2 是导师最看重的目标

导师对第二阶段非常看重。

他的说法是：

> 如果 12 月能进入 Phase 2，那么团队就“gold”了。

这里的意思是，如果第一阶段表现良好、成功进入第二阶段：

- 项目规模会显著扩大；
- 可能获得数百万美元级别的长期资助；
- 可以支持更多人员；
- 可以做更大规模的系统研究；
- 研究组未来几年可能都有稳定的研究资源和题目。

所以六个月第一阶段的意义并不是它本身规模有多大，而是它是一个进入大型长期项目的入口。

导师希望你们认真对待，因为一旦错过，可能就失去这条长期研究路线。

### 九、第一阶段的核心实验平台：digital twin

导师特别提到了 **digital twin，数字孪生**。

项目合作方中有一位叫 **Miriam** 的研究人员，她已经拥有一个可以利用的 digital twin。

导师希望团队先在这个 digital twin 上开展工作。

这里的基本逻辑是：

- 真实科学实验系统可能昂贵、复杂、危险或难以频繁修改；
- 直接修改完整硬件或真实实验设施，六个月内不现实；
- digital twin 提供一个对真实系统的虚拟模拟；
- 团队可以在虚拟环境中尝试大量不同配置和实验策略。

可以在 digital twin 中做的事情包括：

- 改变实验参数；
- 测试不同控制方案；
- 模拟故障；
- 研究可靠性和恢复；
- 比较不同数据传输方式；
- 尝试 AI 自动选择实验；
- 在不破坏真实设施的情况下反复迭代。

导师认为，这使项目成为一个更现实的 **system effort**。

### 十、为什么 digital twin 对你们组尤其合适

导师把它和当前 GPU multiplexing 项目做了隐含对比。

在 GPU 项目里，你们可能需要：

- 理解不公开的 SMSP 细节；
- 修改编译器；
- 修改 runtime；
- 证明非常底层的硬件行为；
- 甚至提出 GPU 架构改动。

而在 digital twin 项目中：

- 不需要修改 GPU architecture；
- 不需要一开始就碰真实科学仪器；
- 不需要先构建一个完整的物理平台；
- 可以在模拟环境中快速做系统设计和实验；
- 可以更好地发挥组里在系统、网络、可靠性和分布式计算方面的能力。

导师明确说，通过 digital twin，可以进行大量变化和实验，而不必先完成很多重型系统实现。

这也是他认为新项目更像“顺流而下”，而不是“游上瀑布”的原因之一。

### 十一、你提到的方向：AI 自动开展研究

在听完导师介绍后，你提出，已经有人开始研究：

- AI 自动进行研究；
- 自动运行机器学习实验；
- 自动调优训练过程；
- AI 根据结果继续设计下一轮实验；
- 构建 autonomous research platform。

你似乎还提到：

- 某个自动调优框架；
- 某位研究者的工作；
- MIT 的一个相关演讲。

但录音中这些人名和平台名识别得很差，无法可靠还原，不能确定具体指的是哪个系统或哪位研究者。

导师一开始没有听清你说的“auto research platform”，还反复问你具体是什么。

你解释说，这不是一个纯粹的未来概念，已经有人开始尝试让 AI 参与整个研究流程。

你认为，类似的 pipeline 以后也可以应用到 AI for Science 中：

1. AI 观察实验状态；
2. 选择下一组参数；
3. 启动实验；
4. 分析实验结果；
5. 调整模型或策略；
6. 继续下一轮实验。

导师接受了这一判断，并认为你可以从这些已有工作开始调研。

### 十二、导师把项目链接发给了你

会议中，导师把一个网页链接发到了你们平时讨论 LLM tuning 的聊天中。

他说：

- 这个网页是公开宣布你们项目的页面；
- 你可以先通过这个页面了解背景；
- 先围绕 Genesis Mission、AI for Science 和项目描述开始探索。

但导师也提醒：

> 这个链接本身不会提供很多具体技术细节。

因为当前项目还在形成过程中，真正的研究任务不会直接从公告网页里完整得到。

你需要把它当成：

- 背景入口；
- 政策和项目定位；
- 合作方和大方向说明；

而不是一份已经写好的技术 specification。

### 十三、你近期最直接的任务：两三天内快速补背景

导师对你接下来两三天的安排很明确：

> 尽可能多地了解人们现在如何使用 AI for Science。

具体来说，你应该调研：

- AI 如何用于科学实验；
- autonomous experimentation；
- self-driving laboratory；
- digital twin；
- AI 如何选择实验；
- AI 如何控制实验设备；
- AI 如何做自动调参和实验规划；
- 科学计算工作流；
- AI agent 如何参与科研 pipeline；
- 相关系统论文和平台。

导师此时没有要求你马上提出最终方案，因为他承认：

- 项目仍会继续演化；
- 未来一到三周会逐渐变得具体；
- 下周还有新的项目会议；
- 他会从合作方那里获得更多信息；
- 然后再把新的信息逐步传递给你们。

所以当前任务不是“立即完成设计”，而是先建立足够背景，使你能够参与后续项目定义。

### 十四、未来一到三周，项目内容会继续变化

导师多次说：

- 当前项目不会保持现在这个模糊状态；
- 接下来一周、两周、三周内会逐渐演化；
- 每次合作会议后，技术方向都会更清楚。

他的计划大致是：

1. 你先学习 AI for Science 的背景；
2. 导师下周参加项目会议；
3. 从其他合作方获得更多信息；
4. 把信息反馈给你和另一位组内同学；
5. 共同确定可做的系统问题；
6. 开始搭建 proof of concept。

因此，导师暂时没有给你一个特别具体的题目，不是因为他不准备让你参与，而是因为整个项目组本身还没有完全确定最终技术方案。

### 十五、你需要和另一位组内同学合作六个月

导师确认，你将和另一位组内学生一起参与这个项目。

录音前文中的学生是 Songyu，但这一段自动转写有时把名字识别成“Sauraba”或类似形式，因此无法百分之百确定具体是哪位同学。不过，从上下文看，大概率是会议中一直在场并与你合作的那位同学。

导师问你们：

- 是否能够一起工作；
- 是否互相讨厌；
- 是否存在合作障碍。

他用开玩笑的方式说：

> 不需要你们一定互相喜欢，只要不互相讨厌、能够正常合作就行。

你回答说合作没有问题。

导师随后明确表示，他预计你们两个人会在未来六个月共同推进该项目。

### 十六、合作团队中还有哪些人

导师提到项目中还有多位合作人员。

录音能够相对确认或部分确认的包括：

- **Miriam**：拥有或能够提供 digital twin；
- Miriam 的 manager；
- 一位来自 **HP** 的合作者，名字转写不清；
- **Harvey Newman**，导师说他来自 Caltech；
- 至少一位 programmer；
- 可能还会再有另一位 programmer。

但导师认为，这些高级合作方中的许多人会主要忙于：

- 项目协调；
- 开会；
- 对外沟通；
- 管理；
- 合作方之间的讨论。

程序员则主要负责：

- 实现；
- 工程开发；
- 把方案落地。

因此，项目最缺的不是“有人写代码”，而是有人提出真正的新系统想法。

### 十七、导师对你们的定位：负责“thinking work”

导师说得非常直接：

> 真正的 thinking effort，需要主要来自你、另一位学生和导师三个人。

他开玩笑说：

- 自己不会编程；
- 不能贡献很多实现；
- 能做的主要是思考。

所以你们三个人需要共同负责：

- 定义研究问题；
- 提出创新点；
- 设计系统架构；
- 决定数字孪生中做哪些实验；
- 规划 demo；
- 选择评价指标；
- 确定哪些结果能够支持 Phase 2；
- 把项目从宽泛愿景变成有技术含量的研究。

这意味着你在项目中不只是一个执行者。

导师希望你承担研究型角色，而不是等别人把完整任务写好后再让你实现。

### 十八、到 12 月时，proposal 必须显示“有很多新的思考”

导师反复强调最终目标：

- 现在到 12 月之间，会有几次 demo；
- 12 月要形成 Phase 2 proposal；
- 第二阶段 proposal 必须让评审看到，项目中加入了大量新的技术思考。

也就是说，不能只是：

- 把原 proposal 换一种说法；
- 做一个表面 demo；
- 把已有数字孪生运行起来；
- 加一个现成 LLM 接口。

必须展示：

- 新系统设计；
- 新的实验自动化方法；
- 新的可靠性或通信方案；
- AI 与 scientific workflow 的真正结合；
- 可验证的效果；
- 足以支撑大规模后续投入的路线。

导师把这视为你们三个人未来六个月的核心责任。

### 十九、DOE 项目也被导师用来说明“表达清晰”的重要性

虽然这部分主要发生在导师批评你 slides 时，但它也与项目直接相关。

导师说：

- 这个 DOE 计划有约 8000 份申请；
- 从提交到宣布结果，大约只有两个月；
- 不可能每份 proposal 都被人非常仔细地阅读；
- 很可能会使用自动工具甚至 LLM 进行初步筛选。

因此，proposal 必须：

- 结构清晰；
- 目标明确；
- 让人快速理解；
- 很快说明创新在哪里；
- 不要求评审花大量时间替作者补逻辑。

导师把这一点与你当前 presentation 的问题联系起来：

> 如果连 LLM 都无法从 slides 或 proposal 中正确理解你想做什么，那么材料本身就不够清楚。

这也意味着，未来你参与 Phase 2 proposal 时，除了做技术，还需要显著改善研究表达和材料组织能力。

### 二十、它与当前 GPU multiplexing 项目的关系

导师没有要求你立即完全停止 GPU 项目。

最后形成的安排更接近：

- GPU multiplexing 项目继续做有限收尾；
- 补齐理论分析和必要实验；
- 争取形成一个 workshop 或探索性投稿；
- 但不再占用你的全部精力。

与此同时：

- AI for Science 项目将逐渐成为更主要的工作；
- 你先调研背景；
- 随着项目在未来数周变得具体，投入会增加；
- 接下来六个月，你需要与组内同学共同完成 proof of concept 和 demo。

因此，两者不是立即一刀切，而是发生主次转换：

> GPU 项目从主线降为高风险 side project；DOE AI for Science 项目逐步成为新的主要方向。

### 二十一、目前仍然没有确定的内容

从录音本身来看，以下问题当时都还没有答案：

- 具体是哪一种科学实验；
- digital twin 模拟的到底是什么物理系统；
- AI 的输入和输出是什么；
- AI 是否直接控制实验；
- 使用哪一种模型或 agent；
- 是否需要训练新模型；
- 数据从哪里来；
- 系统的具体 architecture；
- 网络和 6G 在项目里承担什么角色；
- GPU-to-GPU transfer 的具体问题是什么；
- reliability 和 resilience 要应对哪些故障；
- 六个月内每个 demo 的具体内容；
- 你与另一位学生的具体任务分工；
- 最终投稿方向和论文题目。

导师当时只确定了：

1. 项目已经获得第一阶段支持；
2. 目标属于 AI for Science；
3. 会利用 digital twin；
4. 当前是六个月加速阶段；
5. 12 月要争取 Phase 2；
6. 你需要立即开始做背景调研；
7. 你和另一位学生将承担主要的研究思考工作。

其余部分需要在之后一到三周的项目会议中逐步确定。

### 整体概括

导师对这个新项目的判断是：

> 这是一个刚获批、当前技术细节仍然比较模糊，但战略地位高、竞争激烈、后续资助潜力巨大的 AI for Science 项目。第一阶段只有六个月，要依托合作方已有的 digital twin，快速提出系统创新、做出 proof of concept 和若干 demo，并在 12 月争取进入规模大得多的第二阶段。

而他对你的期待是：

> 不只是帮忙实现，而是尽快学习 AI for Science、自动实验和 digital twin，随后与另一位学生及导师一起，负责把一个高层 proposal 转化成真正的新系统问题和技术方案。

---

## Q2 这个项目到底在做什么:是要做 auto research platform 吗

> **问**:这个项目主要内容是什么？说是AI for science，但是感觉和我想的不一样（比如用AI去分析蛋白质结构）我们是要做一个auto research platform的平台，还是要干嘛

**答**:

你的感觉是对的：**这个项目不是“用 AI 解决某个具体科学问题”那一类 AI for Science**，至少从这次会议透露的信息看，它更接近：

> **为 AI 自动驱动科学实验提供系统基础设施，并先在一个现有的 digital twin 上做闭环实验原型。**

所以它和 AlphaFold 这类“AI 直接预测蛋白质结构”的工作处在不同层级。

### 先区分两种 AI for Science

#### 第一种：面向具体科学领域的 AI 模型

这就是你原先理解的类型，例如：

- 预测蛋白质结构；
- 设计新药或新材料；
- 预测分子性质；
- 求解流体或气候模型；
- 从天文数据中识别现象；
- 用神经网络替代昂贵的物理模拟。

它的核心研究问题通常是：

> 怎样设计一个更好的模型，更准确地预测某个科学对象？

这里往往需要很强的领域科学知识，比如生物、化学、材料、物理。

#### 第二种：AI 驱动科学实验的系统

你们这个项目更像这一类。

它关注的不是某个蛋白质预测模型本身，而是：

> 怎样让 AI 参与“提出实验—执行实验—获得数据—分析结果—选择下一次实验”的完整循环？

导师对 Genesis Mission 的概括就是：使用 AI 驱动科学实验，探索新的知识和研究方向；你们的项目则要为这种 AI 能力运行科学实验提供支持。

### 你们项目最可能是什么

从会议中的信息看，它可以理解成一个三层结构。

#### 第一层：科学实验或者它的 digital twin

合作方 Miriam 已经有一个 digital twin。

这个 digital twin 应该代表某个真实科学系统、实验装置或实验流程，但会议里**没有说它到底模拟什么**。

可能是：

- 某种物理实验设施；
- 科学仪器；
- 分布式实验系统；
- 某种需要动态控制的科学流程。

但目前不能说是蛋白质、材料、粒子物理还是其他领域，因为录音没有提供答案。

第一阶段不是直接改造真实设施，而是在这个 digital twin 上：

- 改变参数；
- 模拟实验；
- 尝试不同决策；
- 观察输出；
- 模拟异常和故障；
- 快速重复大量实验。

导师明确说，这是一个以 digital twin 为基础的 system effort，可以在虚拟环境中尝试许多变化，而不用先修改真实系统或 GPU 架构。

#### 第二层：AI 实验决策循环

理想情况下，AI 会参与这样的闭环：

```
科学目标
   ↓
AI 选择下一项实验或参数
   ↓
在 digital twin 中执行
   ↓
收集数据和状态
   ↓
AI 分析结果
   ↓
决定下一轮实验
   ↺
```

这里的 AI 可能承担：

- 实验参数选择；
- 实验规划；
- 搜索候选方案；
- 根据历史结果决定下一次实验；
- 异常检测；
- 实验结果解释；
- 资源需求预测。

这确实与 **auto research platform、self-driving lab、autonomous experimentation** 的概念接近。

但一个关键细节是：

> “auto research platform”是你在会议里首先提出来的概念，并不是导师明确宣布的既定项目名称或已经确定的最终方案。

当你提到自动研究平台时，导师一开始还在追问你具体指什么。之后他认可这是值得探索的方向，但没有说：“对，我们的项目就是构建一个完整的 auto research platform。”

因此，目前更准确的说法是：

> 你们可能会构建一个 **AI 驱动实验闭环的原型或平台雏形**，但还不能断定目标是开发一个通用的、完整的 autonomous research platform。

#### 第三层：你们组真正负责的系统基础设施

这应该是你们组最核心的部分。

导师说，当前 proposal 中真正具体的技术内容，主要是他加入的：

- reliability；
- resilience；
- 更好的 GPU-to-GPU 数据传输；
- 6G；
- 网络与计算结合；
- 分布式环境中的系统支持。

而 proposal 的其他部分目前还比较高层，甚至被导师自己称为“fluff”。

所以，你们可能不是负责发明那个最核心的科学 AI 模型，而是负责回答：

> 当 AI 要持续控制复杂科学实验时，底层系统怎样可靠、高效地支撑它？

可能涉及的系统问题包括：

##### 1. 实验编排

- AI 给出的实验任务怎样提交；
- 实验如何排队；
- 多个实验怎样并行；
- 如何处理任务之间的依赖；
- 下一轮实验怎样根据上一轮结果动态生成。

##### 2. 计算资源管理

- CPU、GPU、边缘设备和科学仪器怎样协同；
- 哪些任务在哪里运行；
- 资源不足时怎样调度；
- 实验的计算和通信怎样共同优化。

##### 3. 数据移动

- digital twin、AI 模型和科学设备之间会产生大量数据；
- 如何高效做 GPU-to-GPU 传输；
- 如何减少数据复制；
- 如何让计算与通信重叠；
- 跨节点、跨站点时怎样传输数据。

##### 4. 可靠性与恢复

科学实验可能运行很久，任何组件都可能失败：

- GPU 故障；
- 网络断开；
- 节点退出；
- digital twin 状态丢失；
- AI agent 给出异常操作；
- 某轮实验执行到一半失败。

系统需要支持：

- checkpoint；
- retry；
- rollback；
- state recovery；
- fault detection；
- 结果一致性；
- 可重复性。

##### 5. 网络和远程控制

导师特别提到 6G 和分布式环境，这说明项目可能涉及：

- 远程科学设施；
- 边缘设备；
- 无线连接；
- 跨地域计算；
- 实验设备与数据中心之间的协同。

不过，6G 在这里具体承担什么角色，会议里也没有确定。

### 所以，它是不是 auto research platform？

我的判断是：

#### 从长期愿景看：很可能有这个方向

它可能最终表现成一个类似这样的系统：

```
科学家提出目标
       ↓
AI planner / agent
       ↓
实验工作流与资源编排平台
       ↓
digital twin 或真实实验装置
       ↓
数据采集、分析和状态管理
       ↓
AI 生成下一轮实验
```

这确实可以叫：

- autonomous science platform；
- autonomous experimentation platform；
- AI-driven scientific workflow；
- self-driving laboratory infrastructure；
- auto research platform。

#### 从当前六个月任务看：不太可能直接做完整平台

六个月内的目标更现实：

- 利用 Miriam 已有的 digital twin；
- 选择一个具体场景；
- 打通一个端到端闭环；
- 加入少数几个系统创新；
- 做出 proof of concept；
- 展示一到数个 demo；
- 为 12 月的 Phase 2 proposal 提供证据。

也就是说，很可能不是：

> 从零做一个支持所有科学领域的通用自动科研平台。

而是：

> 在一个具体 digital twin 场景中，做一个 AI 驱动实验系统的可运行原型，并重点展示系统、网络、可靠性或资源管理方面的创新。

导师明确称这是一个六个月的 accelerated effort，近期目标是在 digital twin 上展示 proof of concept；做出效果后，再申请规模大得多的 Phase 2。

### 一个具体例子

假设 Miriam 的 digital twin 模拟的是一个大型科学设备。

传统流程可能是：

1. 科学家手工设定 20 个参数；
2. 运行模拟；
3. 等待结果；
4. 人工查看；
5. 再手工设置下一轮参数。

你们可能要做成：

1. 科学家只给一个目标，例如最大化某种产出；
2. AI 根据历史实验选择下一组参数；
3. 系统把实验任务部署到 digital twin；
4. 自动分配 GPU、网络和其他资源；
5. 收集输出和遥测数据；
6. AI 判断实验结果；
7. 如果节点失败，系统自动恢复；
8. AI 决定下一轮；
9. 反复迭代，最后给出最优配置和实验记录。

其中：

- 领域科学家负责什么参数有意义；
- AI 人员负责实验选择策略；
- Miriam 提供 digital twin；
- 你们组可能负责中间的 runtime、workflow、网络、数据传输和可靠性。

这比“训练一个蛋白质模型”更像你的 systems 背景。

### 你的研究工作可能落在哪里

根据导师强调的内容，你最可能不是马上去学习蛋白质结构，而是从以下系统问题中选一个切入：

#### 方向一：可靠的 autonomous experimentation runtime

研究：

- AI agent 发起的实验如何可靠执行；
- 失败后怎样恢复；
- 怎样保证实验状态不丢失；
- 如何避免重复或不一致的实验；
- 如何提供可复现记录。

#### 方向二：digital twin 与 AI 之间的高效数据通路

研究：

- 仿真数据如何直接进入 GPU；
- 多 GPU 间怎样传输；
- 怎样减少 CPU 中转；
- 怎样 overlap simulation、communication 和 AI inference。

这与导师提到的 GPU-to-GPU transfer 最直接。

#### 方向三：分布式实验调度

研究：

- AI 产生大量候选实验时怎样调度；
- 哪些实验并行；
- 如何根据价值、成本和紧迫程度分配资源；
- 如何动态终止低价值实验。

#### 方向四：网络—计算联合优化

研究：

- 实验设施、digital twin 和 AI 集群分散在不同位置时；
- 怎样根据网络状态调整模型、采样率和任务放置；
- 在带宽不足或连接不稳定时如何继续运行。

#### 方向五：AI 驱动实验的可观测性和安全控制

研究：

- 如何知道 AI 为什么选择这个实验；
- 如何审计每一次决策；
- 怎样设置安全约束；
- AI 出现异常行为时如何阻止；
- 怎样让人类随时接管。

### 最准确的一句话定位

目前最准确的理解不是：

> “我们要用 AI 分析某种科学对象。”

也不能直接确定为：

> “我们要从零开发一个通用 auto research platform。”

而是：

> **你们要依托合作方已有的 digital twin，构建并研究一个 AI 驱动科学实验闭环的系统原型；你们组重点负责支撑这个闭环的分布式系统、资源管理、数据传输、网络、可靠性与韧性。**

至于这个原型最终会不会包装成一个完整的 auto research platform，要等接下来一到三周的合作会议，把以下内容确定下来：

- digital twin 究竟是什么；
- AI 控制实验的具体方式；
- 六个月 demo 的场景；
- 你们组负责的技术模块；
- Phase 2 想主打的系统创新。

所以你目前觉得“项目内容和我想的不一样”，不是你理解错了，而是 **AI for Science 是一个很大的伞状概念**。你原先想到的是“科学 AI 模型”，而导师这个项目目前更偏“自主科学实验的系统基础设施”。

---

## Q3 Genesis Mission 是什么

> **问**:Genesis Mission是什么

**答**:

你在 **AI for Science** 语境里听到的 **Genesis Mission（创世纪任务）**，指的是美国政府启动的一项国家级科研计划。

它**不是一个具体模型、软件或单独项目**，而是一个类似“国家科研基础设施 + 大规模资助计划”的总框架：把美国能源部国家实验室的超级计算机、科学数据、实验设施、AI模型、大学和科技公司连接起来，让 AI 深度参与科学研究。该计划于 **2025年11月24日**通过行政命令启动，由美国能源部 DOE 负责主要建设和实施。

### 它具体想做什么？

传统科学研究一般是：

> 科学家提出假设 → 写模拟程序 → 运行实验 → 分析数据 → 修改假设

Genesis Mission 希望把它变成一个高度自动化的闭环：

> 科学数据
> → 科学基础模型
> → AI Agent 提出假设
> → 运行模拟
> → 控制机器人实验室做实验
> → 分析实验结果
> → 自动调整下一轮实验

因此，AI不只是用来写论文或聊天，而是作为一个 **scientific collaborator（科学研究协作者）**，执行数据分析、代码生成、模拟、实验设计和实验控制。官方计划包括科学基础模型、AI agents、预测模型、设计优化工具，以及由 AI 控制的自动化实验设施。

### 底层平台是什么？

Genesis Mission 的核心基础设施叫：

**American Science and Security Platform**
**美国科学与安全平台**

它试图统一连接：

- DOE 国家实验室的超级计算机；
- 云端 AI 算力；
- 大规模联邦科学数据集；
- 科学基础模型和 AI Agent；
- 模拟软件；
- 机器人和自动化实验室；
- 大学与企业的科研资源。

例如，Argonne 的 Aurora 超级计算机、AI inference service，以及用于跨实验室连接数据、模型和算力的 **American Science Cloud**，都属于这套生态。

你可以把它粗略理解成：

> **一个面向科学研究的国家级 AI 云平台 + 超算平台 + 自动实验平台。**

### 研究哪些问题？

涵盖的领域非常广，包括：

- 核裂变与核聚变；
- 新材料和关键矿物；
- 半导体与芯片设计；
- 量子计算；
- 生物技术和药物发现；
- 电网与能源系统；
- 数字孪生；
- 自动驾驶实验室；
- 航天和天文数据；
- 国家安全。

例如，官方提出用 AI 和数字孪生优化电网，用物理信息模型发现材料，让机器人实验室自动执行实验，以及用 AI 分析 NASA 超过 150 PB 的历史数据。

### 规模有多大？

截至 **2026年7月22日**，美国政府宣布为 Genesis Mission 提供超过 **50亿美元**的联邦投入，参与范围已经从 DOE 扩展到超过 15 个联邦机构。第一批选出了 **278个项目**，其中：

- 168个由大学牵头；
- 87个由国家实验室牵头；
- 19个由企业牵头；
- 4个由非营利机构牵头。

这些项目目前是进入资助谈判阶段，并不等于所有资金已经最终发放。

---

## Q4 合作方研究人员是谁,digital twin 如何获取

> **问**:根据线索能否知道这个研究人员是谁，digital twin如何获取

**答**:

### 基本可以锁定是谁

这位研究人员几乎肯定是 **Mariam Kiran**，不是转写文本里的 “Miriam”。她是 **Oak Ridge National Laboratory（ORNL）量子通信与网络组负责人**，研究方向包括 self-driving networks、科学数据的高速分布式传输、WAN、5G/后 5G 网络和网络智能。

这不是单纯依靠名字猜测，而是项目内容几乎逐句对应：

- DOE 名单中，Mariam Kiran 是 **Science-Aware Network Operations for Research Networks（SciNet）** 的 PI。
- SciNet 官方页面恰好写到：
- reliability and resilience；
- GPU-to-GPU transfers；
- 6G and accelerated network technology；
- 合作方包括 **UC Riverside、Caltech 和 HPE Labs**。
- 你们会议里，导师也是在说完“可靠性、韧性、GPU-to-GPU transfer 和 6G”后，马上提到利用 “Miriam 的 digital twin” 做六个月的 proof of concept。

所以我对人物身份的置信度在 **95% 以上**：

> **Mariam Kiran，ORNL，SciNet 项目负责人。**

### 她说的 digital twin 到底是什么？

能确定它**不是 GPU 微架构模拟器**，而更可能是一个：

> **科学网络 / 分布式科学基础设施的 digital twin**

也就是用虚拟环境复制真实科研网络中的：

- 网络拓扑；
- 路由器和交换机；
- network operating system；
- 链路带宽、延迟、拥塞和故障；
- 数据中心、GPU 节点及科学仪器之间的数据流；
- telemetry 和 workload；
- 路由、调度及故障恢复控制逻辑。

Mariam 参与撰写的 ORNL digital twin 报告专门描述了 **A Digital Twin of Science Ecosystem**：它会模拟 instruments、computing resources 和 network elements，集成 instrument simulator、network emulator，并用于在不占用真实物理资源的情况下开发、调试和测试科学 workflow。

#### 最有可能对应的具体环境

目前公开材料无法唯一证明会议中指的是哪一个内部仓库，但最可能是下面两部分的组合。

##### 1. Global P4 Lab 的 network digital twin

Global P4 Lab 已经开发过一种 **on-demand digital twin**，主要基于：

- NetBox：保存真实网络拓扑，作为 source of truth；
- NetReplica；
- Containerlab；
- 容器化或虚拟机形式的 network OS；
- P4、SONiC、RARE/freeRtr 等网络环境。

它可以从实际多域网络抓取拓扑，自动生成一个高保真的虚拟网络，再先在虚拟环境里测试路由、故障、拥塞和新协议，之后迁移到真实网络。

##### 2. Mariam 团队的 Hecate + PolKA 环境

Mariam 团队已经公开了一个 **Hecate + PolKA** 原型：

- Mininet 生成网络和流量；
- iperf3 收集 bandwidth、throughput、RTT；
- 将网络拓扑、健康状态和 flow 数据提供给 GNN；
- Hecate 预测最佳路径；
- PolKA 将流量切换到相应路径；
- 可以按不同 application 的 bandwidth/latency 需求选择主路径和备用路径。

ORNL 对相关技术的官方描述称，它是在一个**模拟真实 P4 testbed 的 emulated ecosystem** 中测试的，这与会议里所说的“在 digital twin 上做各种 variation，而不用立即修改真实系统”非常吻合。

我的判断是：

> **底层 digital twin 很可能是 Global P4 Lab／Containerlab 类型的网络副本；Hecate + PolKA 则是运行在这个 twin 上的 AI 路由与控制系统。**

但这最后一步仍是基于公开资料作出的推断；SciNet 官方页面没有公布会议里所指 digital twin 的正式名称、仓库或内部访问地址。

### 现在可以直接获取哪些东西？

Mariam 维护的 Self-driving Network Research Lab 有公开 GitHub 仓库。你现在可以先拿到两个最相关的部分：

```
git clone https://github.com/SelfDrivingNetworkLab/hecatepolka.git

git clone https://github.com/SelfDrivingNetworkLab/P4fabricAIexperiments.git
```

第一个包含 Hecate、PolKA、测试代码、数据集和运行脚本；第二个包含 P4 网络实验、traffic data、数据采集、ML sandbox、SRv6 和拓扑测试代码。

不过需要强调：

> **这两个公开仓库很可能只是 digital twin 的部分控制与实验组件，不一定就是导师口中的完整环境。**

其中缺少一个整理完善的“一键部署完整 SciNet digital twin”的公开说明，也未看到公开的完整 topology snapshot、容器镜像、真实 telemetry trace 或项目级访问凭据。

---

## Q5 digital twin 和 ns-3、OMNeT++ 有何区别

> **问**:digital twin听起来就像个模拟器，跟我印象中的NS3和omnet++有何区别？

**答**:

### 1. Digital twin 和 ns-3、OMNeT++ 到底有什么区别？

你的直觉没错：**digital twin 的底层通常确实包含模拟器或仿真环境**。区别在于，它不是一种和 ns-3 并列的“新仿真算法”，而更像是围绕一个特定真实系统搭建的完整虚拟副本。

可以先分成三层：

| 概念                 | 本质                     | 是否对应某个真实系统 | 是否接入真实数据 | 常见例子                 |
| ------------------ | ---------------------- | ---------- | -------- | -------------------- |
| Simulator          | 用抽象模型模拟系统行为            | 不一定        | 通常不需要    | ns-3、OMNeT++         |
| Emulator / testbed | 尽可能运行真实软件、协议栈和数据包      | 可能         | 不一定      | Mininet、Containerlab |
| Digital twin       | 特定真实系统的、经过校准并持续更新的虚拟副本 | 通常需要       | 理想情况下需要  | 某科研网络、工厂、超算中心的 twin  |

#### ns-3 和 OMNeT++ 是“通用建模工具”

ns-3 的官方定位是 **discrete-event network simulator**：你创建节点、链路、协议和流量，模拟事件按虚拟时间发生，然后观察吞吐、时延、丢包等结果。它也支持实时调度、连接真实网络设备以及运行部分真实协议代码，但核心仍是一个通用网络仿真平台。

OMNeT++ 同样是模块化的离散事件模拟框架，而且比 ns-3 更通用：通信网络、片上网络、排队网络甚至其他系统都可以建模；具体网络协议通常由 INET 等外部模型库提供。

你可以在 ns-3 里随便构造：

> 100 个节点、400 Gbps 链路、某种拥塞控制协议。

它不必对应世界上某个真实存在的网络。

#### Digital twin 强调“它是谁的孪生”

比较严格的定义要求 digital twin 是：

> 某个真实实体或系统的虚拟表示，并按照指定频率和精度与真实系统同步。

它通常使用实时及历史数据表示真实系统的当前状态，并预测未来行为；有些系统还会把优化结果反馈给真实系统。

例如 Mariam 团队的网络 digital twin，理想情况下不是泛泛地模拟“一个科研网络”，而是复制：

- 真实实验室和计算中心的拓扑；
- 具体交换机、路由器和链路容量；
- 真实或接近真实的 network OS；
- 真实 telemetry、故障和流量分布；
- GPU 节点、科学仪器和计算设施；
- 真实 workflow 的数据传输需求。

然后进行：

- 如果某条链路故障，会发生什么？
- GPU-to-GPU traffic 应该走哪条路径？
- 网络拥塞时怎样改变调度？
- 一项控制策略部署到真实网络前是否安全？
- 哪些 workflow 会违反 latency 或 reliability 要求？

ORNL 对 “Digital Twin of Science Ecosystem” 的描述里明确说，这类环境应当包括仪器模拟器、网络 emulator、HPC 和 GPU 计算环境，并用于开发、调试和测试分布式科学 workflow。也就是说，**network simulator/emulator 是 digital twin 里面的一个部件，而不是 digital twin 的全部。**

#### 一个具体例子

假设要复制 UCR 到 ORNL 的科研网络。

**用 ns-3：**

```
创建节点 A 和 B
设置 100 Gbps 链路
设置 30 ms RTT
生成若干 TCP/UDP 流
测量吞吐和丢包
```

**用 digital twin：**

```
从真实网络系统导入拓扑
导入交换机配置和路由策略
导入近期 telemetry 和流量 traces
运行真实或容器化的 network OS
重放实际 GPU transfer workload
模拟交换机故障或链路拥塞
预测真实网络部署后的结果
把优化策略部署回物理 testbed
```

但这里有一个很重要的现实问题：

> **“Digital twin” 这个词经常被过度包装。**

如果一个所谓的 digital twin：

- 没有明确对应的真实系统；
- 不导入真实 telemetry；
- 没有经过真实系统校准；
- 不持续更新；
- 没有 simulation-to-reality validation；

那它本质上可能只是：

> 一个网络 emulator、testbed，或者配置得比较逼真的 simulator。

NIST 也明确指出，digital twin 与普通建模之间并没有一条特别清晰的界线，这个术语有时会被用于描述普通模拟或数据追踪系统。

所以你第一次接触 Miriam 的环境时，最应该问的不是“用了什么 digital twin”，而是：

1. 它对应哪个真实网络？
2. 拓扑和参数从哪里来？
3. 是否导入真实 telemetry？
4. 底层是 ns-3、Mininet、Containerlab，还是虚拟 network OS？
5. 怎样验证模拟结果与真实系统一致？
6. 能否连接真实 GPU、NCCL workload 或 testbed？

这些问题能迅速判断它到底是真正的 twin，还是只是一个换了名字的 simulator。

---

## Q6 这段 ORNL 项目经历对 AI infra 求职的价值

> **问**:这段 ORNL 项目经历对我的 AI infra 求职价值如何？

**答**:

#### 先说我的判断

对于你想做的：

> **LLM inference 系统、GPU 利用率、吞吐、调度、kernel/runtime 优化**

这项 ORNL 网络项目是一个**相关但不完全对口的相邻方向**。

它不是没用，但也不能因为带有 “Genesis Mission”“ORNL”“AI for Science” 就认为它天然等价于 AI infra 经历。

更现实的排序是：

1. **Meta/Google/NVIDIA 的直接相关 AI infra 实习**
2. **有明确个人所有权、真实 GPU 实验和高质量产出的 ORNL 项目**
3. 普通的大厂系统/SWE 实习
4. 只做网络模拟、缺少真实系统和个人产出的 ORNL 项目

也就是说：

> 如果你同时得到一个 Meta/Google 的 LLM serving、GPU runtime、distributed ML 或 AI networking 实习，通常应该优先选择大厂实习。

但 ORNL 项目完全可以作为你获得这种实习的跳板。

#### ORNL 是什么级别的机构？

ORNL 不是普通大学实验室或小型研究机构。它是美国能源部体系中规模最大的多领域科学技术国家实验室之一，在超级计算、先进制造、材料、能源和国家安全方面地位很高。Frontier 超算也位于 ORNL。

因此，在这些圈子中，ORNL 的名字很有分量：

- HPC；
- supercomputing；
- scientific computing；
- high-performance networking；
- distributed systems；
- national laboratories；
- AI for Science。

但是在普通工业界招聘中，品牌信号大致是：

```
Meta / Google / NVIDIA
        >
ORNL
        >
普通学校实验室或不知名研究机构
```

尤其面对普通 recruiter，Meta/Google 几乎不需要解释，而 ORNL 可能需要你在简历里补一句：

> U.S. Department of Energy national laboratory; home of the Frontier exascale supercomputer.

真正懂 HPC、系统和网络的 hiring manager 通常会认识 ORNL；普通软件招聘人员不一定能准确判断它的级别。

#### 你的目标方向和这个项目差在哪里？

可以把 AI infra 粗略分成以下层次：

```
模型与算法
    ↓
Serving system
vLLM、SGLang、TensorRT-LLM
batching、KV cache、prefill/decode
    ↓
Runtime / compiler / kernels
CUDA、Triton、Tensor Core、quantization
    ↓
Distributed communication
NCCL、RDMA、GPUDirect、collectives
    ↓
Cluster scheduler / network
placement、routing、congestion、fault tolerance
    ↓
Datacenter infrastructure
```

你目前最感兴趣的是中间几层：

- serving scheduler；
- GPU resource sharing；
- computation overlap；
- kernel concurrency；
- inference throughput；
- GPU utilization。

SciNet 主要在更下面：

- GPU-to-GPU communication；
- high-speed network；
- adaptive routing；
- congestion；
- telemetry；
- reliability/resilience；
- network-aware workflow orchestration。

SciNet 的官方描述确实把 GPU-to-GPU transfer、拥塞避免、6G/accelerated networking 和跨机构 scientific workflows 作为核心问题，而且 UCR 是合作方。

所以两者不是毫无关系，而是：

> **你想研究 GPU 里面和节点内部怎样提高利用率；SciNet 更关注 GPU 节点之间、计算中心之间怎样传输和协调。**

#### 网络其实是 AI infra 的一部分

你担心“网络项目对 AI infra 没帮助”，这个判断有一部分过于悲观。

在单卡 inference 中，网络可能不重要；但到了：

- tensor parallelism；
- pipeline parallelism；
- expert parallelism / MoE；
- disaggregated prefill-decode；
- remote KV-cache transfer；
- multi-node serving；
- distributed training；

网络往往直接决定 GPU 是否空等。

Meta 当前的 AI Networking 研究职位就明确把 NCCL、GPU 集群、分布式 ML 和高性能网络放在同一个 AI infrastructure 问题里。Google 的 AI infrastructure 岗位也把 distributed execution、跨主机 performance debugging、GPU/TPU acceleration、runtime 和 serving benchmarks 视为同一套系统能力。

因此，你可以把这段经历做成两种完全不同的结果。

##### 弱版本

> 使用 digital twin 模拟几个网络拓扑，改变时延和带宽，生成一些曲线。

对 inference infra 求职的帮助比较有限，因为 recruiter 会看到：

- 偏网络模拟；
- 缺少真实 GPU；
- 缺少 LLM workload；
- 缺少 production-like implementation；
- 与 CUDA/runtime/serving 联系不明显。

##### 强版本

> 在 network digital twin 和真实 GPU testbed 上研究分布式 LLM inference 中的 GPU-to-GPU traffic，通过 network-aware scheduling 或 routing 降低 communication stall，提高 tokens/s 和 GPU utilization。

这就非常接近 AI infra：

- NCCL；
- RDMA/GPUDirect；
- network-aware inference scheduling；
- communication-computation overlap；
- prefill/decode disaggregation；
- GPU cluster utilization；
- fault-aware serving。

这类经历可以同时投：

- AI infrastructure；
- distributed ML systems；
- ML networking；
- GPU cluster scheduling；
- LLM serving；
- HPC systems。

### 和 Meta/Google 暑期实习直接比较

#### 直接相关的大厂 AI infra 实习明显更强

假设 Meta/Google 的实习团队就是：

- LLM serving；
- distributed inference；
- GPU runtime；
- accelerator performance；
- ML compiler；
- AI networking；
- cluster scheduling；

那么它通常在以下方面胜过 ORNL 合作项目。

##### 1. 招聘信号更直接

简历上写：

> Software Engineer Intern, Meta — AI Infrastructure

几乎所有 recruiter 都能立刻理解。

而：

> Research collaboration with ORNL on SciNet digital twin

还需要解释：

- ORNL 是什么；
- SciNet 是什么；
- 你本人到底做了什么；
- digital twin 是否只是模拟。

##### 2. 有生产系统经验

大厂实习更容易接触：

- 大规模内部集群；
- production workload；
- 成熟代码库；
- code review；
- on-call/reliability 思维；
- 实际性能目标；
- 跨团队协作；
- 部署和回归测试。

这是工业界非常看重，而学术项目往往较弱的部分。

##### 3. 转正和推荐链路

实习本身就是一条招聘渠道：

- return offer；
- 内部推荐；
- manager feedback；
- 同团队全职机会；
- 之后申请其他公司的可信经历。

ORNL 合作研究通常没有这么直接的工业转化链路。

#### 但 ORNL 项目也有大厂实习不一定具备的优势

##### 1. 你可能拥有更大的研究所有权

在大厂实习里，你可能只是实现一个已经定义好的子模块。

ORNL 项目里，你有机会参与：

- 定义研究问题；
- 设计系统；
- 建设实验平台；
- 做完整 evaluation；
- 写论文；
- 成为主要作者。

对于 Ph.D. 来说，这一点很重要。

##### 2. 更可能公开发表

若产出：

- NSDI；
- OSDI；
- SOSP；
- ASPLOS；
- ATC；
- EuroSys；
- SC；
- HPDC；
- MLSys；

或者形成可用的开源系统，这段经历的长期价值可能超过一次普通实习。

##### 3. 能构建差异化

现在许多候选人都会写：

- vLLM；
- CUDA；
- Triton；
- quantization；
- LLM serving。

但同时理解：

- GPU；
- distributed systems；
- high-performance networking；
- telemetry；
- fault tolerance；
- scheduling；

的人相对少。你已有 GPU concurrency 背景，再增加 networking，可能形成：

> 跨 GPU microarchitecture、runtime、distributed communication 和 cluster scheduling 的全栈 AI infra 叙事。

这个组合其实很有竞争力。

### 一个比较现实的评分

以下不是绝对分数，而是针对你申请 **AI infra 实习或全职** 的相对价值。

| 经历                                     | 求职价值     |
| -------------------------------------- | -------- |
| Meta/Google/NVIDIA 直接相关 AI infra 实习    | 9–10/10  |
| ORNL 项目：你主导，真实 GPU + NCCL/RDMA + 论文/开源 | 8–9/10   |
| ORNL 项目：有实质系统实现和个人贡献，但偏网络              | 6.5–8/10 |
| Meta/Google 普通但有系统含量的 SWE 实习           | 7–8.5/10 |
| ORNL 项目：主要搭模拟器、跑配置、画图                  | 4–6/10   |
| 只在简历上写“参与 Genesis Mission”，说不清个人贡献     | 3–4/10   |

真正决定它价值的，不是 **ORNL vs Meta** 四个字，而是：

> 你最终能够用多少句话清楚地证明自己设计并实现了什么，以及它提高了什么指标。

### 你应该怎样把它主动改造成 AI infra 项目？

我建议你争取把自己的工作包定义成：

> **Network-aware resource scheduling for distributed LLM inference using a digital-twin testbed**

或者：

> **Digital-twin-guided optimization of GPU-to-GPU communication for distributed AI workloads**

#### 工作负载不要只用普通 iperf

至少加入一种真实 AI workload：

- NCCL all-reduce / all-gather；
- tensor-parallel inference；
- MoE all-to-all；
- disaggregated prefill-decode；
- KV-cache transfer；
- multi-node vLLM/SGLang；
- GPU-to-GPU RDMA transfer。

#### 指标不要只有网络吞吐

同时测：

- tokens/s；
- TTFT；
- TPOT；
- request throughput；
- P99 latency；
- GPU utilization；
- communication stall；
- network utilization；
- workflow completion time；
- failure recovery time。

#### 必须有 simulation-to-real validation

不要让全部结果停留在 digital twin：

1. 先在 twin 上探索大量配置；
2. 选出若干策略；
3. 在真实 GPU/testbed 上验证；
4. 测量 twin 和真实系统的误差；
5. 解释什么时候 twin 可信、什么时候不可信。

这一步会让它从“网络模拟作业”提升为真正的 systems project。

#### 争取一个明确的系统贡献

例如：

- network-aware GPU job placement；
- congestion-aware inference scheduler；
- GPU transfer telemetry pipeline；
- NCCL workload replay framework；
- automated fault injection；
- digital-twin calibration system；
- routing policy controller；
- communication/computation overlap optimizer。

### 我的最终建议

**不要把这个 ORNL 项目当作 Meta/Google 实习的替代品。**

更好的定位是：

> 用 ORNL 项目迅速补齐 distributed AI networking 和大型合作项目经历，同时继续申请 Meta、Google、NVIDIA、Microsoft、Amazon、ByteDance 等公司的 AI infra 实习。

对于你现在的研究轨迹，最理想的组合是：

```
现有 GPU concurrency / Tensor Core 项目
        +
ORNL 的 GPU-to-GPU / networking / digital twin 项目
        +
下一次大厂 AI infra 实习
```

这样你的故事会非常完整：

> 我先研究单 GPU 内部不同执行资源怎样并发；
>  然后研究多 GPU 和跨站点 AI workflow 怎样高效传输与调度；
>  最后在工业界大规模 AI infra 中验证这些能力。

但你需要警惕一个风险：

> **项目名称很大、合作方很多，最后你个人只负责搭环境和跑实验。**

所以项目开始时就应当争取明确：

- 你负责哪个独立问题；
- 你是否拥有核心代码；
- 是否能使用真实 GPU workload；
- 是否有论文和 authorship；
- 是否允许开源；
- 能否在六个月后形成可展示系统。

只要做到这些，它不会把你“带偏到纯网络”，反而可以把你从单卡/GPU 微观优化扩展成更完整的 AI infrastructure researcher。

---

## Q7 二次追问:锁定 SciNet 后,这个项目到底在做什么

> **问**:这个项目主要内容是什么？说是AI for science，但是感觉和我想的不一样（比如用AI去分析蛋白质结构）我们是要做一个auto research platform的平台，还是要干嘛

**答**:

你的感觉是对的：**这个项目不是你最初理解的那种“用 AI 直接解决某个科学问题”**，例如：

- 用模型预测蛋白质结构；
- 用生成模型设计新材料；
- 用 AI 求解物理方程；
- 用机器学习分析显微镜或天文数据。

你们参加的 **SciNet** 属于 AI for Science 的另一层——**支撑自动化科学研究的系统与网络基础设施**。

### 一句话定位

> **你们不是负责制造“会研究蛋白质的 AI 科学家”，而是负责让分布在不同实验室、仪器、GPU 集群和 AI Agent 之间的自动科研流程能够可靠、快速地通信和运行。**

更准确地说：

> **整个大方向是 autonomous research platform；你们的项目只负责其中的智能网络与数据传输层。**

### AI for Science 其实有三层

#### 第一层：直接解决科学问题

这是你原本想到的 AI for Science：

```
蛋白质序列
    ↓
AI 模型
    ↓
蛋白质三维结构
```

或者：

```
材料组成与实验数据
    ↓
AI 模型
    ↓
预测新材料性能
```

AlphaFold、天气模型、材料生成模型、分子设计模型都属于这一层。

**SciNet 不负责这一层。**

#### 第二层：自动科研平台

再往上一层，是所谓的：

- autonomous laboratory；
- self-driving laboratory；
- auto research platform；
- agentic scientific workflow。

理想流程大概是：

```
AI Agent 提出实验方案
        ↓
远程实验仪器执行实验
        ↓
传感器产生大量数据
        ↓
GPU/超算进行实时分析
        ↓
AI 判断实验结果
        ↓
决定下一轮实验参数
        ↓
再次执行实验
```

ORNL 对 autonomous science 的官方描述就是这种闭环：AI 提出实验条件，自动仪器制备或测试样品，分析工具测量结果，机器学习系统决定下一步实验，形成 design–build–test–learn 循环。

这才是会议中“auto research platform”指向的**整体愿景**。

但你们并不是独立建设整个系统。

#### 第三层：支撑上述流程的基础设施

假设一个实验发生在 Caltech：

1. 显微镜连续产生 TB 级数据；
2. 数据要传到 ORNL 的 GPU；
3. GPU 实时运行模型；
4. 分析结果传回实验室；
5. AI Agent 根据结果改变仪器参数；
6. 同时还有很多其他科研项目争抢网络和算力。

这时会出现：

- 网络拥塞；
- GPU 数据传输延迟；
- 链路故障；
- 数据跨机构传输失败；
- 敏感数据不能经过某些节点；
- 一部分科研任务有实时 deadline；
- 普通网络不知道哪个数据流更重要；
- 一个环节出问题，整个实验闭环可能中断。

**SciNet 就是解决这些问题的。**

ORNL 对 SciNet 的官方定位非常明确：它是一个 **science-aware autonomous platform for research network operations**，负责协调跨机构的 agentic 和 scientific workflows。具体目标包括自适应路由、避免拥塞、支持 GPU-to-GPU transfer、利用 6G/加速网络、处理敏感数据，并降低实验延迟和 workflow 失败率。

### SciNet 实际可能长什么样？

可以把它理解为一套**面向科学工作流的智能网络控制系统**。

#### 输入

SciNet 可能接收：

```
科学工作流信息
- 这是哪个科研项目
- 当前处于哪个实验阶段
- 数据量多大
- latency deadline 是多少
- 是否允许重传
- 数据是否敏感
- 目的地是哪台 GPU / 哪个实验室

网络实时状态
- 链路带宽
- 当前拥塞
- packet loss
- 节点故障
- GPU-to-GPU transfer 进度
- 队列长度
- 历史 telemetry
```

官方项目说明特别提到，要整理多模态网络运维数据，并给数据包附加科学项目信息，从而把异构数据与具体 scientific workflow 关联起来。

#### 控制与决策

平台再决定：

```
这个 flow 走哪条路径？
是否需要预留带宽？
是否应该改变路由？
故障后切换到哪条备用路径？
哪个 scientific workflow 优先？
是否提前迁移数据？
怎样避免两次大规模 GPU transfer 相互拥塞？
```

这里的 “AI” 更可能用于：

- 预测即将出现的流量需求；
- 识别网络异常；
- 预测链路或 workflow 失败；
- 根据历史 telemetry 选择路由；
- 为不同科学工作流动态分配网络资源；
- 让 agent/controller 自动执行网络操作。

它不是主要拿来预测蛋白质结构的。

#### 输出

最终目标是：

- 更短的 experiment completion time；
- 更少的 workflow failure；
- 更稳定的 GPU-to-GPU transfer；
- 网络故障时快速恢复；
- 科学仪器、AI Agent 和 GPU 集群之间形成可靠闭环。

### Digital twin 在这里扮演什么角色？

因为不能一开始就在真实 DOE 网络上随便：

- 断开链路；
- 修改路由；
- 制造拥塞；
- 改变交换机配置；
- 注入故障；
- 让 AI controller 自动控制真实网络。

所以先把科研网络和工作流复制到 digital twin 中。

然后可以在 twin 上测试：

```
实验一：某条跨机构链路突然失效
实验二：两个 GPU workload 同时传输大量数据
实验三：某个实时实验需要最高优先级
实验四：背景流量突然增长
实验五：网络 telemetry 存在延迟或错误
实验六：控制器错误预测了流量
```

再比较不同策略：

```
普通最短路径
vs.
拥塞感知路由
vs.
science-aware 路由
vs.
AI 预测驱动的路由
```

测量：

- GPU transfer throughput；
- flow completion time；
- 实验闭环延迟；
- workflow success rate；
- 故障恢复时间；
- 网络利用率；
- 控制策略稳定性。

### 你们六个月内究竟要交付什么？

从会议原话来看，**项目的具体技术方案还没有完全确定**。

你导师实际上说得很直接：

> 目前 proposal 很 high-level；真正写得比较具体的技术内容，是 reliability、resilience、更好的 GPU-to-GPU transfer 和 6G；其他很多内容现在还是 “fluff”。

他接着说，近期目标是在 Mariam 的 digital twin 上完成一个六个月的 proof of concept，通过试验多种 variation，证明这个方向值得进入资金规模更大的 Phase 2。

因此，现在不能把任务理解成：

> 六个月做出一套通用的全自动科研平台。

那几乎不可能，而且也不是你们 UCR 小组单独承担的范围。

更合理的交付物大概是下面这个规模：

#### 一个代表性的 scientific workflow

例如：

```
实验室 / AI Agent
       ↓
发送大量实验数据
       ↓
远程 GPU 执行分析
       ↓
结果返回
       ↓
决定下一步操作
```

不一定真的连接蛋白质实验室；第一阶段甚至可能采用合成工作负载或 trace replay。

#### 一个 digital-twin 实验环境

包括：

- 模拟科研网络拓扑；
- GPU 节点或 GPU traffic model；
- network telemetry；
- workflow metadata；
- congestion 和 fault injection。

#### 一个或少数几个控制机制

例如：

- science-aware adaptive routing；
- GPU-transfer-aware traffic engineering；
- failure-aware rerouting；
- network demand prediction；
- workflow-priority-aware scheduling。

#### 一套评估结果

证明相较于普通网络策略：

- workflow 更少失败；
- transfer 更快；
- 故障恢复更快；
- 科研闭环延迟更低。

这就是足够有说服力的 Phase 1 proof of concept。

### 所以“auto research platform”这个说法哪里容易误导？

会议里师兄先把它概括为 “auto research platform”，这个说法描述的是**最终应用场景**，不是你们的具体研究模块。

更准确的结构是：

```
完整 autonomous research ecosystem
│
├── 科学 AI 模型
│   ├── 蛋白质模型
│   ├── 材料模型
│   └── 物理预测模型
│
├── Scientific agents
│   ├── 提出实验
│   ├── 分析结果
│   └── 选择下一步实验
│
├── 实验与计算资源
│   ├── 自动化实验室
│   ├── 仪器
│   ├── GPU
│   └── 超级计算机
│
└── SciNet：你们这个项目
    ├── 网络 telemetry
    ├── GPU-to-GPU transfer
    ├── adaptive routing
    ├── reliability/resilience
    ├── workflow-aware traffic control
    └── 跨机构协调
```

SciNet 是最下面的**通信基础设施和控制层**。

一个形象的类比：

> 蛋白质模型是负责做研究的“科学家大脑”；
>  自动实验室是“手和眼睛”；
>  SciNet 是连接大脑、手、仪器和超算的“神经系统”。

你们不是开发整个科学家，而是在避免它因为“神经传输堵塞或断线”而无法工作。

### 这和你的 GPU/AI infra 方向可能怎样连接？

对你来说，最值得争取的切入点不是普通路由协议，而是：

> **GPU-aware / AI-workload-aware networking。**

例如：

- 识别 distributed inference 的通信阶段；
- 区分 tensor parallel、all-reduce、KV-cache transfer 等 flow；
- 根据 GPU stall 和 network telemetry 调整路由；
- 改善跨 GPU、跨节点乃至跨站点的数据传输；
- 让 network scheduling 与 GPU scheduling 联动；
- 在故障和拥塞下保障 latency-sensitive AI workflow。

这样你做的就不是泛泛的：

> 用 AI 优化科研网络。

而是更加具体的：

> **为分布式 AI 与 autonomous science workflow 建设 GPU-aware network control system。**

这个角度和你想做的 AI infra 仍然能够连起来。

#### 最终结论

**大项目的愿景**确实接近 auto research platform，即把 AI Agent、仪器、实验、GPU 和超算连成自动科研闭环。

**SciNet 的实际任务**不是构建整个自动科研平台，更不是直接分析蛋白质结构，而是建设这个闭环所依赖的：

> **science-aware、autonomous、reliable network operations platform。**

**你们六个月的近期任务**很可能是在 Mariam 已有的 digital twin 上，实现并评估一个围绕 GPU-to-GPU transfer、adaptive routing、reliability/resilience 的 PoC。至于具体采用什么 scientific workload、训练什么预测模型、你个人负责哪个模块，会议里其实还没有定下来；导师明确承认当前 proposal 除少数技术点外仍然很高层。
