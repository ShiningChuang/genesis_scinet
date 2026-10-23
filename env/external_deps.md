# External Dependencies

**git 之外、需在新机器精确重建的外部依赖**都记在这里——既包括第三方源码(`external/`),也包括外部 **artifact(模型权重、数据集、系统工具等)**(通常在缓存目录如 `~/.cache/huggingface` 或 `data/`,均不进 git)。
所有版本必须**钉死**:源码钉到 commit hash、artifact 钉到 revision hash,禁止写 `latest` 或浮动分支名。

**登记时机**:一旦某个复现要用到的东西不在 git 里(哪怕是工具自动下载的),立刻在这里补一节。日后"换机器跑不起来"几乎全部源于漏登记。

每个依赖按下面的模板记录一节。

---

## <依赖名称>

- **类型**:第三方源码 / 模型权重 / 数据集 / 系统工具
- **仓库地址(或来源)**:`<git url / HF repo / 下载地址>`
- **固定 commit(或 revision)**:`<完整 hash>`
- **安装位置**:`<external/xxx/ 或缓存路径>`(是否进 git)
- **安装命令**:
  ```bash
  <clone / checkout / build / install 命令>
  ```
- **构建前置**:`<非 pip 的系统依赖,缺了会怎样>`
- **是否有本地改动**:无 / 有(若有,说明改了什么,并记录 patch 位置)

---

## SciNetGenesis(SciNet 项目共享代码仓库)

- **类型**:第三方源码(合作方共享仓库,Mariam Kiran 建立;以 git submodule 接入)
- **仓库地址(或来源)**:`git@github.com:SelfDrivingNetworkLab/SciNetGenesis.git`
- **固定 commit(或 revision)**:`1f4ef5230c367459e99b599bde841d7d8cffc08d`(由 submodule gitlink 钉死;升级时在 submodule 内 checkout 新 commit 并提交 gitlink,同步更新此处)
- **安装位置**:`external/SciNetGenesis/`(submodule;`external/*` 被 .gitignore 忽略,故用 `git submodule add -f` 加入,gitlink 与 `.gitmodules` 进 git)
- **安装命令**:
  ```bash
  git submodule update --init external/SciNetGenesis
  ```
- **构建前置**:需对该 GitHub 仓库有访问权限(SSH key);仓库可能改为 private
- **是否有本地改动**:无
