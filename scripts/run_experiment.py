"""实验入口。所有实验必须通过本脚本启动:

    python scripts/run_experiment.py <config.yaml>

入口负责:校验 config → 建立 run 目录 → 跑实验 → 存 config/metrics/环境快照
→ 写 description → 登记 EXPERIMENTS.md → 自动 commit+push。
即使实验失败也会登记并 push(失败也是数据)。

实验代码只需实现一个入口函数,签名与返回值约定:

    def entry(config: dict, run_dir: Path) -> dict:
        return {
            "metrics": {...},        # 存成 run_dir/metrics.json(进 git 的小文件)
            "conclusion": "一句话结果",  # 进 description.txt 与 EXPERIMENTS.md 的 Key Result
            "verdict": "✅" | "❌" | "🔍",
        }

本脚本刻意保持领域无关:除 pyyaml 外不 import 任何第三方库,项目特有的
测量/profiling 逻辑放 `src/lib/`,环境快照采什么由 configs/defaults.yaml 声明。
"""

import importlib
import json
import platform
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # 让 config 的 entry 能 import src.experiments.*
RUNS_DIR = ROOT / "runs"
EXPERIMENTS_MD = ROOT / "EXPERIMENTS.md"
DEFAULTS_PATH = ROOT / "configs" / "defaults.yaml"


def ensure_git_repo():
    """本框架把项目记忆存在 git 仓库里:不在仓库里就拒跑,而不是悄悄跑一个记不住的实验。"""
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], cwd=ROOT, stderr=subprocess.STDOUT
        )
    except Exception:
        sys.exit(
            "[run_experiment] 拒绝运行:当前目录不是 git 仓库。项目记忆靠 git 迁移,"
            "请先 `git init && git add -A && git commit -m 'init'`(见 TEMPLATE_SETUP.md)。"
        )


def git_short_hash():
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT
    ).decode().strip()


def _deep_merge(base, override):
    """递归深度合并两个 dict:override 覆盖 base 的对应字段。

    嵌套 dict 递归合并(不是整块替换);其他类型直接用 override 的值。
    不修改入参,返回新 dict。
    """
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path):
    """读 configs/defaults.yaml 与实验 config,深度合并后返回完整配置。

    实验 config 覆盖 defaults 的对应字段(嵌套递归合并)。返回的完整配置
    即后续 save_config 存进 run 目录的内容,确保历史 run 自包含,不依赖
    defaults.yaml 的后续改动。
    """
    with open(DEFAULTS_PATH) as f:
        defaults = yaml.safe_load(f) or {}
    with open(config_path) as f:
        experiment = yaml.safe_load(f) or {}
    return _deep_merge(defaults, experiment)


def set_all_seeds(seed):
    """统一设置 python random / numpy / torch 的随机源(未安装的库静默跳过)。

    注意:并行/GPU 计算即使固定 seed 也不保证 bit-level 完全可复现(浮点累加顺序、
    非确定性 kernel、线程调度等)。本函数目标是控制可控的随机源,而非保证逐位相同。
    """
    import random
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def make_run_dir(tag):
    """创建 runs/{timestamp}_{tag}_{git_short_hash}/ 并返回路径。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"{timestamp}_{tag}_{git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def capture_env_snapshot(run_dir, config, seed=None):
    """采集环境快照到 run_dir/env_snapshot.txt(小文件,进 git,用于事后 diff)。

    采什么由 config 的 `env_snapshot` 段声明(defaults.yaml 里维护):
        commands:  要跑的命令行列表(不经 shell,shlex 拆词),记录其 stdout。
        libraries: 要记录 __version__ 的 python 包名列表。
        pip_freeze: 是否附 `pip freeze` 全量快照。
    单项采集失败不影响实验:失败项在快照里留下 <error: ...> 痕迹。
    seed 为本次实际生效的随机种子,记录下来便于事后核对。
    """
    def run_cmd(cmd):
        try:
            return subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, cwd=ROOT
            ).decode().strip()
        except Exception as e:
            return f"<error: {e}>"

    def lib_version(name):
        try:
            return getattr(__import__(name), "__version__", "<no __version__>")
        except Exception as e:
            return f"<error: {e}>"

    spec = config.get("env_snapshot") or {}

    lines = []
    lines.append(f"timestamp: {datetime.now().isoformat()}")
    lines.append(f"effective_seed: {seed}")
    lines.append(f"git_hash: {run_cmd(['git', 'rev-parse', 'HEAD'])}")
    lines.append(f"python_version: {platform.python_version()}")
    lines.append(f"platform: {platform.platform()}")

    for cmd in spec.get("commands") or []:
        argv = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
        lines.append("")
        lines.append(f"# $ {' '.join(argv)}")
        lines.append(run_cmd(argv))

    libraries = spec.get("libraries") or []
    if libraries:
        lines.append("")
        lines.append("# key libraries")
        for name in libraries:
            lines.append(f"{name}: {lib_version(name)}")

    if spec.get("pip_freeze", True):
        lines.append("")
        lines.append("# pip freeze")
        lines.append(run_cmd([sys.executable, "-m", "pip", "freeze"]))

    with open(run_dir / "env_snapshot.txt", "w") as f:
        f.write("\n".join(lines) + "\n")


def save_config(run_dir, config):
    """存 config.yaml。"""
    with open(run_dir / "config.yaml", "w") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)


def save_metrics(run_dir, metrics):
    """存 metrics.json。"""
    with open(run_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)


def load_entry(entry_spec):
    """解析 config 的 entry='模块路径:函数名',返回可调用 entry(config, run_dir)->dict。

    返回的 dict 约定含 metrics / conclusion / verdict 字段。
    """
    mod_path, sep, func_name = entry_spec.partition(":")
    if not sep:
        raise ValueError(f"entry 格式应为 '模块:函数',收到 {entry_spec!r}")
    module = importlib.import_module(mod_path)
    return getattr(module, func_name)


def write_description(run_dir, config, result, verdict):
    """存 description.txt = 做了什么 + 结果/结论 + Verdict。

    三要素由结构产出,不靠执行者记忆:'做了什么'来自 config.description(开跑前已校验),
    '结果/结论'来自实验 entry 返回的 conclusion。
    """
    what = (config.get("description") or "").strip()
    conclusion = (result.get("conclusion") or "").strip() or "(实验未返回 conclusion)"
    text = (
        f"做了什么: {what}\n"
        f"结果/结论: {conclusion}\n"
        f"Verdict: {verdict}\n"
    )
    with open(run_dir / "description.txt", "w") as f:
        f.write(text)


def append_to_experiments_md(run_dir, config, result, verdict):
    """往 EXPERIMENTS.md 追加一行(Key Result 取实验返回的 conclusion)。"""
    date = datetime.now().strftime("%Y-%m-%d")
    tag = config.get("tag", "")
    hypothesis = (config.get("hypothesis") or "").replace("\n", " ")
    key_result = (result.get("conclusion") or "").strip().replace("\n", " ")
    dir_name = run_dir.name
    row = f"| {date} | {tag} | {hypothesis} | {key_result} | {verdict} | {dir_name} |\n"
    with open(EXPERIMENTS_MD, "a") as f:
        f.write(row)


MAIN_BRANCH = "main"


def git_commit_and_push(message):
    """自动 git add 小文件 + commit + push。

    安全防御:仅在正常的主分支(MAIN_BRANCH)上才提交推送。若处于 detached HEAD 或
    非主分支(典型为 checkout 历史 hash 复现旧实验),跳过 commit/push——本次 run
    的产出仍正常落盘到 runs/,只是不进入 git 历史,以免污染或推坏历史。
    仅防御性跳过,不自动建分支、不强制 push。

    push 失败(没配 remote / 网络不通)只告警不抛错:本地 commit 已经把记忆存住了,
    不该因为推不上去而让一个已跑完的实验以异常收尾。
    """
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT
    ).decode().strip()
    if branch != MAIN_BRANCH:
        where = "detached HEAD" if branch == "HEAD" else f"非主分支 '{branch}'"
        print(
            f"[run_experiment] 检测到{where}状态,推测为复现历史实验,"
            f"已跳过自动提交与推送;本次 run 的产出仍会正常落盘到 runs/ "
            f"但不会进入 git 历史。"
        )
        return
    subprocess.run(
        ["git", "add", "EXPERIMENTS.md", "configs", "runs"], cwd=ROOT, check=True
    )
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    if subprocess.run(["git", "push"], cwd=ROOT).returncode != 0:
        print(
            "[run_experiment] 警告:git push 失败(未配 remote 或网络不通)。"
            "本次 run 已 commit 到本地,联网后请手动 push。"
        )


def main():
    if len(sys.argv) < 2:
        sys.exit("用法:python scripts/run_experiment.py <configs/xxx.yaml>")
    ensure_git_repo()
    config_path = sys.argv[1]
    config = load_config(config_path)  # defaults + 实验 config 深度合并

    # 结构强制(不靠记忆):缺 description / entry 直接拒跑,从源头保证
    # 每个 run 都说明"做了什么"且有可执行入口。
    if not (config.get("description") or "").strip():
        sys.exit("[run_experiment] 拒绝运行:config 缺 description(一句话说明要做什么)。")
    if not config.get("entry"):
        sys.exit("[run_experiment] 拒绝运行:config 缺 entry(实验代码入口 '模块:函数')。")
    tag = (config.get("tag") or "").strip()
    if not tag:
        sys.exit("[run_experiment] 拒绝运行:config 缺 tag。")
    # 结构强制:实验代码必须按 tag 分类(src/experiments/{tag}/),不裸露平铺。
    entry_mod = config["entry"].split(":")[0]
    if entry_mod != f"src.experiments.{tag}" and not entry_mod.startswith(
        f"src.experiments.{tag}."
    ):
        sys.exit(
            f"[run_experiment] 拒绝运行:entry 须在 src/experiments/{tag}/ 下"
            f"(按 tag 分类),收到 {entry_mod}。"
        )
    # 假设是软要求(探路 probe 可以先没有),但缺了要出声——没有假设的实验容易白跑。
    if not (config.get("hypothesis") or "").strip():
        print("[run_experiment] 警告:config 缺 hypothesis,EXPERIMENTS.md 该列将留空。")

    seed = config.get("seed")
    set_all_seeds(seed)

    run_dir = make_run_dir(tag)
    save_config(run_dir, config)  # 存合并后的完整配置,run 自包含
    capture_env_snapshot(run_dir, config, seed=seed)
    print(f"[run_experiment] run_dir = {run_dir}")

    verdict = "🔍"
    result = {}
    try:
        entry_fn = load_entry(config["entry"])
        result = entry_fn(config, run_dir) or {}  # 约定返回 metrics/conclusion/verdict
        save_metrics(run_dir, result.get("metrics", {}))
        verdict = result.get("verdict", "🔍")
    except Exception as e:
        # 失败也是数据
        verdict = "❌"
        result.setdefault("conclusion", f"实验失败: {e}")
        raise
    finally:
        write_description(run_dir, config, result, verdict)
        append_to_experiments_md(run_dir, config, result, verdict)
        # 完成提交前缀:失败标 [EXP FAILED],其余(成功/🔍)标 [EXP COMPLETE]。
        # 实验进行中(计划/前期)的提交由人按需让 AI 代做,message 自由格式,不走这里。
        prefix = "[EXP FAILED]" if verdict == "❌" else "[EXP COMPLETE]"
        git_commit_and_push(f"{prefix} {run_dir.name}")


if __name__ == "__main__":
    main()
