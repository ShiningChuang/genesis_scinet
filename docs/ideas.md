# 项目思考 (Ideas)

> 关于项目方向的思考、点子、待办与推测(**允许过期**)。过期的内容手动剪切-粘贴进 `archive/ideas.md` 备份。
> **纯人工维护,agent 不写、不改**(可读、可引用、可在对话里提议,但不动手写)。
> 本文件里的东西**都还不是结论**:方向未定期间尤其如此,证实后才进最新一卷 `findings_{YYYYMMDD}.md`(带 run 证据)或 `knowledge_{YYYYMMDD}.md`(通用知识,人工维护)。
> 下面的候选与判断多来自 [对话记录](../resources/meetings/20260727.md),其中含语音转写误识别与 AI 推断,引用前须核对。

# **computing 和 ML 混合负载的系统问题**。

科学计算大量依赖 FP64/FP32,ML 依赖低精度 Tensor Core,未来国家实验室和 HPC 中心的典型负载就是 simulation + surrogate model 混跑——这恰好是你 multiplexing 工作的自然延伸场景。换句话说,你不需要二选一:做 "infra for AI4Science" 既保留了 systems 的下限,又蹭到了科学计算的 funding 和叙事(NSF/DOE 对这个交叉的钱不少)。

---

有没有哪个论文沿着这条线讲agent的分工、角色