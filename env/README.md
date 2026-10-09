# env/ — 环境重建配方

本目录是**重建运行环境的配方**(进 git,随仓库走;换机器 = `git clone` 后按本目录重建)。
实际依赖装在仓库根的 `.venv/`(或 conda 环境),那些**不进 git**。

## 两条路线,每个项目只选一条

| 路线 | 目录 | 说明 |
|---|---|---|
| **venv**(模板默认) | `env/pip/` | 系统 python venv + pip。`requirements.txt`(直接依赖)、`pip-freeze.lock`(全量精确快照,首次装完后 `pip freeze > env/pip/pip-freeze.lock` 生成)。(目录名用 `pip/` 而非 `venv/`,避开 `.gitignore` 的 `venv/` 规则。) |
| conda | `env/conda/` | conda 管系统级/二进制依赖(编译器、CUDA、MKL 等)。`environment.yml`。 |

> **本项目路线:`venv`(暂定)。** 目前只有框架自身依赖(pyyaml),用系统 python venv 足够。
> **待重新确认的时点**:一旦确定 digital twin 的实际技术栈(如 Containerlab/Docker、Mininet、P4 工具链、ns-3,或需要 CUDA/NCCL 的 GPU 侧实验),若其中出现难用 pip 装的二进制依赖,再决定是否切到 conda 路线并同步更新本表与 `setup.sh`。
> `env/conda/` 目前为「模板/未用」。
> 切换路线时,更新本表与 `setup.sh`。

## 跨路线共用

- `env/external_deps.md` —— git 之外、复现要依赖的一切 artifact 的重建配方:第三方源码(`external/`)、模型权重、数据集、系统工具。**版本一律钉死**(commit hash / revision hash),禁止 `latest` 或浮动分支名。凡是工具自动拉取的东西(缓存到 `~/.cache/…` 的模型、数据集)同样要登记——它不在 git 里,换机器就没有。

## 一键重建

```bash
bash env/setup.sh
```

`setup.sh` 把重建顺序写成可跑脚本:装 git hooks → 建 venv → 装依赖 → 取 `external/` 第三方源码(钉死 commit)→ 验证。
需要**精确**复现(钉死全部传递依赖版本)时改用锁文件:

```bash
.venv/bin/pip install -r env/pip/pip-freeze.lock
```
