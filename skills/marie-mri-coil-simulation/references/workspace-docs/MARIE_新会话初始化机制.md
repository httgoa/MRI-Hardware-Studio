# MARIE 新会话初始化机制

## 目标

初始化机制解决三类信息断层：对话上下文消失、服务器现场变化、历史报告与当前资产脱节。机制由“稳定入口 + 动态盘点 + 案例证据”组成：

```text
START_HERE.md
  -> tools/session_bootstrap.sh（当前现场，只读）
  -> AGENTS.md / MARIE_Agent_Harness.md（规则）
  -> runs/<CaseTag>/status、manifest、report、logs（案例证据）
  -> docs/ + 当前源码/输入（专项事实）
```

## 使用方法

全局初始化：

```bash
cd /home/<user>/marie-tools
bash tools/session_bootstrap.sh
```

指定案例：

```bash
bash tools/session_bootstrap.sh <CaseTag>
```

脚本输出包括：时间和仓库位置、Git 分支/HEAD/改动计数、关键规范是否存在、runs 案例、最近证据文件、磁盘/内存/CPU/GPU 摘要、MATLAB/TMD/MRGF 进程，以及目标案例的状态和报告开头。

## 安全边界

脚本只调用读取型命令，不会：

- 启动 MATLAB、并行池或求解；
- 修改 JSON、MAT、源码或日志；
- 安装/编译依赖；
- 同步 Windows 与 Linux；
- 终止进程；
- 把历史报告当作当前验证结果。

MATLAB 的实际 `which -all` 仍需在获得相应运行授权后执行。Windows/Linux 同步仍需两端证据，单端脚本不能证明。

## 交接信息维护

每次产生重要正式结果后：

1. 在 `runs/<CaseTag>/` 或其版本化复现目录更新 `status.json`、`manifest.yaml`、`report.md` 和日志；
2. 若“当前主要工作”发生变化，更新根目录 `START_HERE.md` 的交接摘要；
3. 不把大型 MAT 内容复制进文档，只记录路径、大小、时间和哈希；
4. 失败门禁和失败日志保留，并明确哪个日志是最终有效证据；
5. 不手写声称同步、求解或验证已完成，除非存在实际执行证据。

`START_HERE.md` 应保持简短，只放接管顺序、当前主线和关键风险；专题知识继续放入 `docs/`，案例细节继续放入 `runs/`。
