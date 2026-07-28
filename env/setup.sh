#!/usr/bin/env bash
# 重建本项目运行环境(venv 路线)。幂等:可重复运行。
# 用法:bash env/setup.sh
#
# 起项目时按实际依赖补齐 [3/4](系统级前置)与 [4/4](external/ 第三方源码,commit 钉死),
# 并与 env/external_deps.md 保持一致 —— 那里是配方文档,这里是可跑版本。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY=python3
VENV="$REPO_ROOT/.venv"

echo "==> [1/4] git hooks(版本化 pre-commit:重写 IDE webview 链接为相对路径)"
git config core.hooksPath scripts/git-hooks
chmod +x scripts/git-hooks/* 2>/dev/null || true

echo "==> [2/4] venv (.venv)"
[ -d "$VENV" ] || "$PY" -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip setuptools wheel
"$VENV/bin/pip" install -r env/pip/requirements.txt

echo "==> [3/4] 系统级前置(按项目补:编译器 / CUDA / protoc / apt 包 …)"
# 例:
# command -v cmake >/dev/null || { echo "ERROR: 缺 cmake"; exit 1; }

echo "==> [4/4] external/ 第三方源码(按项目补,commit 必须钉死;见 env/external_deps.md)"
# 例:
# DEP_DIR="$REPO_ROOT/external/<dep>"
# DEP_URL="https://github.com/<org>/<repo>.git"
# DEP_COMMIT="<完整 commit hash>"
# [ -d "$DEP_DIR/.git" ] || git clone "$DEP_URL" "$DEP_DIR"
# git -C "$DEP_DIR" checkout "$DEP_COMMIT"
# "$VENV/bin/pip" install -e "$DEP_DIR"

echo "==> 验证"
"$VENV/bin/python" -c "import sys, yaml; print('python', sys.version.split()[0], '| pyyaml', yaml.__version__)"

echo "==> 完成(近似环境:直接依赖按 requirements.txt,传递依赖按当下解析)。"
echo "    需要精确复现(钉死全部传递依赖)时改用锁文件:"
echo "        '$VENV/bin/pip' install -r env/pip/pip-freeze.lock"
