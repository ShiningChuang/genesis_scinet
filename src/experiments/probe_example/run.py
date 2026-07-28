"""框架自检示例实验(领域无关,起项目后可整包删除)。

作用有二:
1. 让你在写第一个真实验之前,先跑通"入口 → 落盘 → 登记 → commit"整条链路;
2. 作为 entry 契约的活文档 —— 一个实验脚本长什么样、参数从哪来、返回什么。

三条纪律在这里都能看到(CLAUDE.md §6):
- A 类参数(被测对象)从 config 读,不硬编码;
- B 类参数(测量方法)从 defaults.yaml 读,全局统一;
- 大件原始数据写进 run_dir(被 .gitignore 挡下),distill 后的指标进 metrics。
"""

import random

from src.lib.stats import summarize


def entry(config, run_dir):
    """约定入口:entry(config, run_dir) -> {"metrics", "conclusion", "verdict"}。"""
    n = config["n_samples"]              # A 类:被测对象,来自实验 config
    repeat = config["repeat_iters"]      # B 类:测量方法,来自 defaults.yaml
    tol = config["tolerance"]

    # 原始数据落 run_dir(大件,不进 git);只有 distill 后的指标进 metrics.json。
    means = []
    with open(run_dir / "samples.log", "w") as f:
        for _ in range(repeat):
            samples = [random.gauss(0.0, 1.0) for _ in range(n)]
            f.write(" ".join(f"{x:.6f}" for x in samples) + "\n")
            means.append(sum(samples) / n)

    stats = summarize(means)
    max_abs = max(abs(m) for m in means)
    ok = max_abs < tol

    return {
        "metrics": {"n_samples": n, "repeat": repeat, "mean_of_means": stats["mean"],
                    "max_abs_mean": round(max_abs, 6), "tolerance": tol,
                    "mean_distribution": stats},
        "conclusion": (
            f"{repeat} 次 × n={n} 采样,样本均值 max|mean|={max_abs:.4f} "
            f"({'<' if ok else '≥'} tol={tol});框架链路自检"
            f"{'通过' if ok else '未通过'}。"
        ),
        "verdict": "✅" if ok else "❌",
    }
