"""稳定复用的小工具:分布摘要。

`src/lib/` 放稳定复用代码,需保持整洁(CLAUDE.md §6):一段逻辑第二次被用到时才提炼进来。
本文件是框架自带的唯一示例(领域无关),项目跑起来后按需保留或删除。
"""

import statistics as st


def summarize(vals):
    """返回分布摘要(min/分位/mean/max)。空列表返回 {"n": 0}。

    分位用 nearest-rank(向下取整索引),跨实验口径一致,便于对照。
    """
    if not vals:
        return {"n": 0}
    v = sorted(vals)
    n = len(v)

    def pct(p):
        return v[min(n - 1, int(p / 100 * n))]

    return {
        "n": n, "min": v[0], "p25": pct(25), "median": pct(50),
        "mean": round(st.mean(v), 6), "p75": pct(75), "p90": pct(90),
        "p99": pct(99), "max": v[-1],
    }
