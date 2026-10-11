# MARIE + Codex 服务器远程开发具体实施指南

版本：v1.2  
适用环境：Windows 本地电脑 + MobaXterm + Linux 服务器 + MATLAB R2025b + MARIE 3.0  
服务器项目路径：`/home/<user>/marie-tools`  
MATLAB 路径：`/path/to/MATLAB/R2025b/bin/matlab`

## 1. 目标与最终工作方式

本指南将当前的人工循环：

```text
制定任务
-> 人工在 MATLAB 终端输入命令
-> 人工复制输出
-> Agent 分析有限上下文
-> 再次人工执行
```

改造成以下受控闭环：

```text
本地电脑上的 MobaXterm
-> SSH 登录 Linux 服务器
-> tmux 中运行 Codex CLI
-> Codex 直接读取 /home/<user>/marie-tools
-> Codex 调用统一的 MATLAB batch 入口
-> 日志、状态、快照和摘要写入 runs/<CaseTag>
-> Codex 读取运行证据并继续诊断
-> 用户只在高成本或破坏性步骤前确认
```

完成后，Agent 应能直接看到：

- MARIE 当前源码和实际函数路径；
- 输入 JSON、Body、MSH、电路 JSON 和 runner；
- Git 状态及未提交修改；
- MATLAB 完整标准输出和首次异常堆栈；
- 当前任务是否运行、退出码和日志；
- MAT 文件元数据及轻量数值摘要；
- S 参数、B1-、噪声、SNR/UISNR 图和验收结果。

本方案遵循项目根目录 `AGENTS.md` 和 `MARIE_Agent_Harness.md`。当前源码与服务器实际运行输出的优先级高于历史文档。

### 1.1 当前实施基线（2026-08-11）

已完成：服务器 Codex CLI/ChatGPT 登录、MATLAB `-batch`、只读盘点、统一 `runs/`、新会话初始化，以及一次8通道 WSVIE/TMD/场/后处理实际复现。

尚未完成：tmux 断线恢复验收、标准退出码、launch/execute 任务封装、TMD 路径级单写锁、通用 MAT 数值验证器、固定 worker 资源配置和可证明的 Windows/Linux 同步。

从 v1.2 起，不再按“首次安装”顺序机械执行。后续按以下顺序渐进实施：

```text
Phase 1：inspect/status/tail + prepare（只准备，不启动）
Phase 2A：冻结快照、完整性预检、gate digest 和一次性审批记录（已实施；真实提交仍关闭）

Phase 2B：原子状态机 + tmux + case/TMD 路径锁 + exitcode（11 项隔离测试及一次真实 geometry-only tmux 验收已通过）
Phase 3：通用结构化验证器
Phase 4：Stage A/B/C 和 TMD 候选治理
Phase 5：必要时再做远程桥、调度器或 MCP
```

## 2. 实施范围与边界

### 2.1 第一阶段的范围

第一阶段只打通以下能力：

1. 在服务器运行 Codex CLI；
2. Codex 直接读取服务器项目；
3. 使用 MATLAB `-batch` 运行现有 runner；
4. 使用 tmux 保持 Codex 和 MATLAB 会话；
5. 将输出写入 `runs/<CaseTag>`；
6. 保留高成本计算的人工确认。

第一阶段不需要开发 MCP Server，也不需要重写 MARIE 内核。

### 2.2 不自动授权的操作

以下操作仍必须先向用户报告影响并获得明确授权：

- 修改 `src/`、`startup.m`、`installer.m`；
- 修改 MATLAB license、lmgrd、systemd、防火墙或系统包；
- 启动高内存、长时间或大量 worker/GPU 的正式计算；
- 运行会回写活动电路 JSON 的 TMD；
- 覆盖 accepted/final/validated 资产；
- 终止 MATLAB 进程；
- 移动、压缩、清理或删除原始结果。

## 3. 推荐架构

采用“服务器直接运行 Agent，Git 管理代码，runs 管理运行证据”的架构：

```text
                    Git 远端或受控同步
                  /                    \
Windows 工作副本                         Linux 运行副本
代码、文档、审查                         /home/<user>/marie-tools
                                         |
                                         +-- Codex CLI
                                         +-- MATLAB R2025b
                                         +-- data/
                                         +-- runs/<CaseTag>/
```

原则：

- 代码同步通过 Git 或明确的同步脚本完成；
- 大型 MAT、BASIS 和场数据不通过 Git 同步；
- Windows 修改不等于 Linux 已同步；
- Linux 生成结果不等于 Windows 已取回；
- 每次交付明确说明操作发生在 Windows 还是 Linux；
- 同步前检查 Git 状态，必要时比较 SHA-256。

## 4. 服务器前置检查

通过 MobaXterm 登录服务器：

```bash
ssh psh@SERVER_ADDRESS
```

确认当前用户和路径：

```bash
whoami
hostname
pwd
test -d /home/<user>/marie-tools
test -x /path/to/MATLAB/R2025b/bin/matlab
```

检查基础工具：

```bash
command -v curl
command -v git
command -v tmux
command -v sha256sum
```

Ubuntu/Debian 缺少工具时：

```bash
sudo apt update
sudo apt install -y curl git tmux ca-certificates jq
```

RHEL/Rocky/AlmaLinux：

```bash
sudo dnf install -y curl git tmux ca-certificates jq
```

不要以 `root` 身份运行 Codex 或 MARIE。

## 5. 安装并认证 Codex CLI

### 5.1 安装

在 Linux 服务器执行官方安装命令：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

重新加载 shell，或重新登录 SSH，然后验证：

```bash
command -v codex
codex --version
```

更新时再次运行同一安装器。

### 5.2 认证选择

本项目购买的是 ChatGPT/Codex 账号或工作区席位，不是 OpenAI Platform API Key。因此，服务器 Codex CLI 应使用 **Sign in with ChatGPT**，使用订阅或工作区分配的 Codex 权益。API Key 登录属于另一套按量计费方式，不能把 ChatGPT 订阅账号当作 API Key 使用。

先清除以前可能残留的 API Key 登录和当前 shell 变量：

```bash
codex logout 2>/dev/null || true
unset OPENAI_API_KEY
grep -n "OPENAI_API_KEY" ~/.bashrc ~/.profile 2>/dev/null || true
```

如果最后一条命令找到 `export OPENAI_API_KEY=...`，应从对应 shell 配置中删除，再重新登录 SSH。不要在服务器上为本项目创建或购买 API Key。

### 5.3 有浏览器环境的账号登录

Codex CLI 的标准 ChatGPT 登录命令是：

```bash
codex login
```

选择 **Sign in with ChatGPT**，在浏览器中登录持有 Codex 权益的账号，并在出现工作区选择时选择实际购买席位的工作区。登录完成后验证：

```bash
codex login status
```

### 5.4 纯 SSH/无浏览器服务器登录

优先检查当前 CLI 是否提供设备码登录：

```bash
codex login --help | grep -F -- '--device-auth'
```

只有帮助中确实列出该选项时，才执行：

```bash
codex login --device-auth
```

保持服务器终端开启，在 Windows 浏览器打开终端给出的网址，登录正确的 ChatGPT 账号和工作区，并完成一次性验证码授权。然后在服务器验证：

```bash
codex login status
```

如果当前版本不支持 `--device-auth`，先更新 CLI：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
```

更新后仍不支持时，使用 SSH 本地端口转发完成 `codex login` 的浏览器回调。先运行一次 `codex login`，从登录链接的 `redirect_uri=http://localhost:<PORT>/...` 读取实际回调端口，然后退出该次登录。在 Windows PowerShell 或 MobaXterm 本地终端重新连接：

```powershell
ssh -L <PORT>:127.0.0.1:<PORT> psh@SERVER_ADDRESS
```

在这条带端口转发的 SSH 连接内重新执行：

```bash
codex login
```

将显示的完整登录链接复制到 Windows 浏览器，选择 **Sign in with ChatGPT** 并完成授权。不要猜测端口；必须使用登录链接中显示的实际 `<PORT>`。

### 5.5 认证验收与凭据保护

认证验收：

```bash
codex login status
test -d ~/.codex
```

验收条件：

- 登录方式显示为 ChatGPT 账号，而不是 API Key；
- 账号属于实际购买 Codex 权益的个人账号或单位工作区；
- 能从 `/home/<user>/marie-tools` 正常启动 `codex`；
- 不再要求输入 `OPENAI_API_KEY`；
- 退出 SSH 并重新登录后，认证仍可复用。

凭据要求：

- 不以 `sudo codex` 或 root 身份登录；
- 不把 ChatGPT 密码、浏览器 Cookie、登录链接或验证码写进仓库和日志；
- 不在不同 Linux 用户之间共享 `~/.codex/auth.json`；
- 不把本地电脑的 `auth.json` 直接复制到服务器；
- 每个 Linux 用户应使用自己被授权的 ChatGPT/Codex 账号或工作区席位；
- 为账号启用 MFA；
- 第三方共享或转售账号不应用于包含 MARIE 源码与研究数据的服务器。

Codex 可能将凭据缓存在 `~/.codex/auth.json` 或操作系统凭据存储中。文件存在时收紧权限：

```bash
chmod 700 ~/.codex
chmod 600 ~/.codex/auth.json 2>/dev/null || true
```

该文件可能包含访问令牌，应当按密码保护：不得提交 Git、复制到工单、发到聊天中或放入 `runs/`。需要切换账号或工作区时执行：

```bash
codex logout
codex login
codex login status
```

API Key 只保留给明确需要 OpenAI Platform 按量计费的自动化或 CI 场景，不属于本指南当前的人工 MARIE 开发流程。

## 6. 验证 MATLAB 非交互运行

首先只验证启动、路径和关键函数，不运行求解：

```bash
cd /home/<user>/marie-tools

/path/to/MATLAB/R2025b/bin/matlab -batch "\
cd('/home/<user>/marie-tools'); \
startup; \
assert(exist('load_inputs','file')==2); \
assert(exist('geo_assembly','file')==2); \
assert(exist('solver_wsvie','file')==2); \
disp(version); \
which co_simulation -all; \
which np_compute -all; \
which solver_wsvie -all; \
which solve_st -all;"
```

验收条件：

- MATLAB 正常退出且退出码为 0；
- license 可用；
- `startup` 成功；
- 三个关键函数存在；
- 记录 `which -all` 的实际命中路径；
- 没有误用另一套重复的电子学实现。

不要因为普通输入错误、几何错误或 TMD 失败重新运行 `installer.m`。只有首次安装、MATLAB 大版本变化、编译器变化或 MEX ABI 变化时才考虑安装/重编译。

## 7. 使用 tmux 保持会话

创建 Codex 会话：

```bash
tmux new -s marie-codex
cd /home/<user>/marie-tools
codex
```

常用操作：

- `Ctrl-b` 后按 `d`：从 tmux 脱离；
- `tmux ls`：列出会话；
- `tmux attach -t marie-codex`：恢复会话；
- `tmux capture-pane -pt marie-codex -S -200`：读取最近输出。

首次进入 Codex 后运行：

```text
/status
/permissions
```

不要选择无限制的全系统权限。推荐保留命令审批，并把写权限限制在 `/home/<user>/marie-tools`。

## 8. 第一次 Codex 服务器盘点

在项目根目录启动 Codex 后，使用下面的首个任务：

```text
你正在 Linux 服务器的 /home/<user>/marie-tools 中工作。

先完整阅读 AGENTS.md 和 MARIE_Agent_Harness.md。
只做只读盘点，不修改文件，不启动 MATLAB 求解，不终止进程。

请检查：
1. git status 和当前分支；
2. 项目目录、输入、runner、已有 runs 和结果；
3. MATLAB 路径和版本；
4. 磁盘、内存、CPU/GPU；
5. 当前 MATLAB/TMD 进程；
6. load_inputs、geo_assembly、solver_wsvie、co_simulation、np_compute 的实际路径；
7. Windows 与 Linux 同步状态是否能够被证明。

输出环境盘点报告，不要声称未实际执行的检查已经完成。
```

这一步的目的，是确认 Codex 已真正看到服务器源码，而不是继续基于本地副本或人工粘贴文本推断。

## 9. 统一运行证据目录

所有新任务使用唯一 ASCII CaseTag：

```text
<B0>T_<Nucleus>_<Phantom>_<Nch>Ch_<Topology>_<Mode>_<GeometryTag>_vNN
```

例如：

```text
5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01
```

为案例创建目录：

```bash
cd /home/<user>/marie-tools
CASE_TAG='5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01'
mkdir -p "runs/${CASE_TAG}/logs"
mkdir -p "runs/${CASE_TAG}/snapshots"
mkdir -p "runs/${CASE_TAG}/validation"
```

新任务推荐使用案例与执行轮次两级结构：

```text
runs/<CaseTag>/
├── manifest.yaml
├── status.json                 # 案例级科学状态
├── agent-case.json             # 显式 stage/runner/资源映射
└── executions/<RunID>/
    ├── execution.json          # prepared/running/succeeded/failed/interrupted
    ├── gate.md
    ├── command.txt
    ├── exitcode
    ├── logs/
    ├── snapshots/
    │   └── hashes.sha256
    └── validation/
        ├── summary.json
        └── report.md
```

原始 MAT/BASIS 继续放在 `data/solutions` 和 `data/bases`；不要复制多份大型数组到 `runs/`。

既有 `logs/`、`snapshots/`、`validation/` 和 `reproductions/` 不强制移动。迁移历史目录会破坏引用；新执行使用 `executions/<RunID>` 即可。

## 10. Manifest 模板

在 `runs/<CaseTag>/manifest.yaml` 保存：

```yaml
case_tag: 5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01
status: created
created_at: 2026-08-11T14:30:00+08:00
execution_host: server-hostname
execution_root: /home/<user>/marie-tools
code_commit_or_dirty_state: pending
matlab_version: R2025b
compiler: pending
input_json: data/inputs/inp_5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01.json
body_file: pending
coil_or_wire_file: pending
shield_file: ''
basis_file: ''
b0_tesla: 5
nucleus: 1H
target_frequency_hz: pending
vie_basis: pending
tmd_mode: 0
random_seed_or_optimizer_state: pending
command: pending
output_files: []
warnings: []
validation_summary: pending
```

状态只能按证据逐级提升：

```text
created
-> static-validated
-> geometry-validated
-> em-solved
-> tmd-candidate
-> circuit-accepted
-> final-solved
-> postprocessed
-> research-validated
```

“Simulation completed successfully”最多说明数值流程结束，不能自动提升为 `research-validated`。

## 11. 现有 runner 的最小批处理方式

现有 MATLAB runner 必须从仓库根目录运行并先执行 `startup`。

示例：

```bash
cd /home/<user>/marie-tools

RUN_ID="$(date +%Y%m%d_%H%M%S)"
CASE_TAG='5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01'
LOG_FILE="runs/${CASE_TAG}/logs/run_${RUN_ID}.log"

/path/to/MATLAB/R2025b/bin/matlab \
  -batch "cd('/home/<user>/marie-tools'); startup; run('RUN_${CASE_TAG}.m');" \
  > "${LOG_FILE}" 2>&1

MATLAB_EXIT=$?
printf '%s\n' "${MATLAB_EXIT}" > "runs/${CASE_TAG}/logs/run_${RUN_ID}.exitcode"
```

实时观察：

```bash
tail -n 200 -f "${LOG_FILE}"
```

注意：示例只适用于实际存在 `RUN_<CaseTag>.m` 的案例。既有项目中存在非标准历史命名，例如 `FINALIZE_5T_16CH_FROM_CHECKPOINT.m`；不要仅凭模板猜测文件名，应先检查实际源码。

## 12. 推荐新增的任务封装层

v1.2 分阶段新增：

```text
tools/marie-agent/
├── common.sh
├── inspect.sh
├── approve.sh
├── approve.py
├── launch.sh
├── launch.py
├── prepare.sh
├── prepare.py
├── status.sh
└── tail.sh
```

Phase 1 接口：

```bash
tools/marie-agent/inspect.sh [CaseTag]
tools/marie-agent/prepare.sh <CaseTag> <stage>
tools/marie-agent/status.sh <CaseTag>
tools/marie-agent/tail.sh <CaseTag> [RunID]
```

Phase 1 的 `prepare.sh` 只执行：

1. 验证 CaseTag 只含 ASCII 字母、数字、点、下划线和短横线；
2. 确认项目根路径和 MATLAB 二进制；
3. 检查目标 runner 是否存在；
4. 检查同一 CaseTag 是否已有运行任务；
5. 创建唯一 run ID；
6. 保存输入、runner 和活动电路 JSON 快照；
7. 记录 SHA-256；
8. 记录 Git 状态或 dirty 文件哈希；
9. 写入 `execution.json`，状态为 `prepared`；
10. 生成 `gate.md` 和准确命令，但绝不启动 MATLAB。

Phase 2A 增加 `approve.sh` 和 `launch.sh ... --check`。受保护阶段必须先展示 `gate.md` 并获得明确授权；不能把调用 `prepare` 当作运行授权。审批记录绑定 exact RunID 和 gate digest，1 小时过期，不是人类身份的密码学证明。

当前 `launch.sh <CaseTag> <RunID> --check` 只做快照漂移、MATLAB 路径、状态、审批和 tmux 名称预检。不带 `--check` 会以 RC=11 拒绝，直到 Phase 2B 的原子状态机、case 锁、活动 JSON 真实路径锁、标准退出码和 fake-runner 并发测试全部通过。

每个案例使用 `agent-case.json` 显式记录 runner，不能根据文件名猜测。配置必须包含 `schema_version`、`case_tag`、`artifacts`、`resources` 和逐阶段 `runner/cost/writes_active_json/enabled`。

建议的阶段映射：

| 阶段 | 脚本约定 | 权限 |
|---|---|---|
| `geometry` | `CHECK_<CaseTag>_GEOMETRY.m` | 轻量检查 |
| `stageA` | `PRECOMPUTE_<CaseTag>.m` | 高成本，需批准 |
| `em` | `RUN_<CaseTag>.m` | 高成本，需批准 |
| `tmd` | `RUN_<CaseTag>_TMD_ONLY.m` | 会写回 JSON，需批准 |
| `final` | `FINALIZE_<CaseTag>.m` | 高成本，需批准 |
| `post` | `POST_<CaseTag>.m` | 通常中等成本 |

如果既有脚本命名不同，应在 `agent-case.json` 中显式记录实际入口，不应移动或重命名历史资产来迎合模板。

## 13. 长任务的 tmux 提交模式（Phase 2B，尚未启用）

不要把数小时 MATLAB 求解绑定在当前 Codex 前台命令上。建议每个任务使用独立 tmux session：

```bash
SESSION_NAME="marie_${CASE_TAG}_${RUN_ID}"

tmux new-session -d -s "${SESSION_NAME}" \
  "tools/marie-agent/execute.sh '${CASE_TAG}' 'stageA' '${RUN_ID}'"
```

查询：

```bash
tmux has-session -t "${SESSION_NAME}"
tmux capture-pane -pt "${SESSION_NAME}" -S -200
tail -n 200 "runs/${CASE_TAG}/logs/stageA_${RUN_ID}.log"
```

`execute.sh` 应将进程状态写入执行级 `execution.json`：

```json
{
  "case_tag": "...",
  "run_id": "...",
  "stage": "stageA",
  "state": "running",
  "session": "...",
  "started_at": "...",
  "finished_at": null,
  "exit_code": null,
  "log": "runs/.../stageA_....log"
}
```

MATLAB 结束后更新为 `succeeded` 或 `failed`。`succeeded` 只表示进程退出码为 0，不代表科学验收通过。

案例级 `status.json` 只保存科学状态和门禁；不得用 `succeeded` 覆盖 `em-solved`、`network_gate=failed` 等结论。

## 14. MARIE 阶段门禁

### 14.1 只读盘点

检查：

- Git 状态；
- 输入和已有结果；
- MATLAB/GCC/MEX；
- 磁盘、内存、CPU/GPU 和 worker 预算；
- MATLAB/TMD 进程；
- 关键函数实际路径。

### 14.2 静态输入检查

确认输入 JSON 保留十个字段：

```text
B0
Nucleus
Basis_Functions_VIE
BodyFile
CoilFile
WireFile
ShieldFile
SurfaceBasisSupportFile
TMD
BasisFile
```

未使用字段写空字符串，不写 `null`，不删除字段。

继续检查：

- Body MAT 顶层有 `RHBM`；
- `RHBM.r` 最后一维为 3；
- `epsilon_r` 与 `sigma_e` 尺寸一致；
- `idxS` 合法；
- 坐标统一为 m；
- MSH 为 Gmsh 2.2 ASCII；
- MSH 与电路 JSON 同目录、同主名、同版本；
- 端口、元件和 entity 顺序一致。

### 14.3 几何门禁

正式求解前只执行：

```matlab
cd('/home/<user>/marie-tools');
startup;
MREDM = load_inputs('inp_<CaseTag>.json');
MREDM = geo_assembly(MREDM,1);
visualize_geometry(MREDM);
view(3);
axis equal;
```

导出几何 PNG，并检查：

- phantom 尺寸、中心和方向；
- coil-body 与 coil-shield 间隙；
- 穿透或意外接触；
- Loop 重叠、排距和旋转对称性；
- channel layout 和物理端口数；
- 自由度、体素数和内存预算；
- B0/Nucleus 对应的拉莫尔频率。

几何门禁失败必须停止，不能依赖 TMD 修复几何错误。

### 14.4 Stage A/B/C

```text
Stage A：geometry + assembly + solver -> raw YPn
Stage B：复用同一 raw YPn -> TMD-only candidates
Stage C：冻结 accepted components，复用同频点 accepted post-TMD 校准状态 -> final fields/SNR
```

多物理通道且含独立调谐元件时，post-TMD中的`Jcb`仍对应临时端口，而`JcbRx/JcbTx`已经
映射到物理端口。此时不能把物理端口`YP_s`再次送入TMD=0 matching-only路径与原始`Jcb`
相乘；应冻结JSON、验证网络未变，并直接用accepted post-TMD的校准电流和有限Q损耗状态进行
场/噪声计算。单纯设置`TMD=0`不等于可以安全重复校准。

几何、体模、频率、basis、屏蔽、端口拓扑或电磁算子设置变化后，旧 YPn 和 checkpoint 失效。

禁止：

- 把最终 `YPm/YP_s` 当下一轮原始 YPn；
- TMD 后将旧场与新电路拼接成正式结果；
- 双排阵列未经验证就让不同排共享同一 symmetry 变量组。

## 15. TMD 专项保护

TMD 运行前必须：

1. 确认没有其他任务写同一个活动 JSON；
2. 记录活动 JSON 路径和哈希；
3. 创建带时间戳的 before-TMD 备份；
4. 明确 optim bounds、symmetry、seed 和 worker；
5. 明确输出和日志路径；
6. 获得用户批准。

示意命令：

```bash
ACTIVE_JSON='data/coils/Custom_files/example_v01.json'
RUN_ID="$(date +%Y%m%d_%H%M%S)"

sha256sum "${ACTIVE_JSON}" \
  > "runs/${CASE_TAG}/snapshots/${RUN_ID}_before_tmd.sha256"

cp --preserve=timestamps "${ACTIVE_JSON}" \
  "${ACTIVE_JSON}.before_TMD_${RUN_ID}"
```

TMD 后再次计算哈希并保存最终元件值。失败候选不能覆盖 accepted 版本。

## 16. 结果摘要层

Agent 不需要每次加载完整大型 MAT。建议新增 MATLAB 摘要脚本，将结果写为 JSON、CSV 和小型 summary MAT。

最低摘要字段：

```json
{
  "case_tag": "...",
  "source_mat": "...",
  "mat_readable": true,
  "top_level_variables": [],
  "physical_port_count": 16,
  "has_nan_or_inf": false,
  "gmres_converged": true,
  "sp_p_max_db": -16.8,
  "worst_offdiag_sp_s_db": -13.1,
  "reciprocity_error": 0.001,
  "has_b1m": true,
  "has_noise_covariance": true,
  "noise_hermitian_error": 1e-12,
  "noise_min_eigenvalue": 0.0,
  "has_rx_snr": true,
  "has_uisnr": false,
  "has_tx_b1p": false,
  "has_tx_e_field": false,
  "warnings": []
}
```

Rx 验收解释：

- 前放加载匹配看 `SP_p` 和 `SPm_plot_Rx`；
- 互耦看 `SP_s` 非对角；
- 项目起始 gate 为全部 `SP_p < -15 dB`；
- 谐振偏移 `< 0.5 MHz`；
- 对称组离散 `< 3 dB`；
- 最差非对角 `SP_s < -12 dB`。

这些是当前项目的工程门槛，不是普适法规。

正式 Tx/SAR 结论至少要求：

```matlab
isfield(solution.h_field,'Tx')
isfield(solution.h_field.Tx,'b1p')
isfield(solution.e_field,'Tx')
isfield(solution.e_field.Tx,'e_b')
```

Rx-only 互易回退字段只能用于诊断，不能作为正式 Tx/SAR 数据。

## 17. 日常使用流程

### 17.1 开始工作

```bash
ssh psh@SERVER_ADDRESS
tmux attach -t marie-codex || tmux new -s marie-codex
cd /home/<user>/marie-tools
codex login status
codex
```

如果 `codex login status` 显示未登录或工作区不正确，先按照第 5.3～5.5 节重新完成 ChatGPT 账号授权，不要临时改用他人的 API Key。

给 Codex：

```text
请先读 AGENTS.md 和 MARIE_Agent_Harness.md。
检查 git status、服务器资源、当前 MATLAB 任务和目标 CaseTag 的已有资产。
本轮只完成静态检查和 geometry-only 门禁，不启动正式求解。
```

### 17.2 几何通过后申请正式计算

要求 Codex 先报告：

- 精确 CaseTag；
- 实际命令；
- 阶段和是否写回 JSON；
- worker、CPU/GPU、内存；
- 可用磁盘；
- 输出和日志路径；
- 可复用的 YPn/BASIS/checkpoint；
- 覆盖风险；
- 中断方案。

用户确认后再启动。

### 17.3 运行期间

Codex读取：

```bash
tools/marie-agent/status.sh <CaseTag>
tools/marie-agent/tail.sh <CaseTag>
```

Agent 应报告“运行中、最后成功阶段、当前警告”，不应因为日志暂时没有更新就重复启动任务。

### 17.4 运行结束

执行：

- 检查 MATLAB 退出码；
- 保存完整错误栈；
- `whos('-file', result)` 检查 MAT；
- 检查字段、维度和 NaN/Inf；
- 检查 GMRES、端口维度和互易性；
- 按任务类型检查网络、场、噪声、SNR/UISNR；
- 更新 manifest 状态；
- 记录所有未验证项。

## 18. Git 与 Windows/Linux 同步

### 18.1 推荐方式

代码以 Git commit 为同步依据：

```text
Windows 修改 -> commit/push -> Linux pull
Linux Codex 修改 -> commit/push -> Windows pull
```

每次同步前：

```bash
git status --short
git branch --show-current
git log -1 --oneline
```

若工作树 dirty，不要直接 pull、覆盖或清理。先保存 diff 或提交到独立分支。

### 18.2 不进入 Git 的内容

根据现有仓库策略审查 `.gitignore`，通常不提交：

- 大型 solution MAT；
- BASIS 和缓存；
- 临时 MATLAB 文件；
- 大型日志；
- license 文件和密钥；
- TMD 临时文件。

但应保留可复现所需的 manifest、轻量 summary、输入/runner 哈希和关键验收报告。修改 `.gitignore` 前先检查当前项目是否已经跟踪相关资产。

## 19. 服务器无法访问 Codex 时的备选方案

如果服务器不能连接 Codex/OpenAI，使用本地 Codex + SSH 执行桥：

```text
本地 Codex
-> 阅读 Windows Git 工作副本
-> 通过 Git/rsync 同步源码
-> 通过 ssh 调用服务器 tools/marie-agent/*
-> 只取回日志、summary JSON/CSV 和图片
-> 大型 MAT/BASIS 留在服务器
```

本地 SSH 配置示例：

```sshconfig
Host marie-host
  HostName SERVER_ADDRESS
  User <user>
  IdentityFile ~/.ssh/marie_server_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
```

测试：

```bash
ssh <marie-host> "hostname && test -d /home/<user>/marie-tools"
```

本地 Agent 只调用固定入口：

```bash
ssh <marie-host> \
  "cd /home/<user>/marie-tools && tools/marie-agent/status.sh '<CaseTag>'"
```

不要让本地和服务器同时修改同一活动 JSON，也不要仅依赖网络挂载直接编辑大型结果文件。

## 20. 故障处理

### 20.1 SSH 断线

重新登录并恢复：

```bash
tmux ls
tmux attach -t marie-codex
```

### 20.2 MATLAB 失败

保留：

- 首次异常堆栈；
- 最后成功阶段；
- 完整日志；
- 退出码；
- 输入和 runner 快照；
- 活动电路 JSON 的 before/after 哈希。

先分类为：输入、几何、MEX、资源、license、solver、TMD 或后处理错误，再决定是否重跑。

### 20.3 GLIBCXX/MEX

不要用系统 `libstdc++` 覆盖 MATLAB 自带库。先核对 MATLAB 支持的 GCC，再全量重编译相关 MEX。不要先修改仿真参数掩盖 ABI 问题。

### 20.4 中止任务

按以下顺序：

1. 当前 MATLAB/tmux 会话发送一次 Ctrl+C；
2. 等待 MEX/parfor/GPU 到可中断点；
3. 必要时关闭并行池；
4. 新 SSH 会话确认用户、PID 和完整命令；
5. 对明确主 PID 使用 INT；
6. 再使用 TERM；
7. KILL 仅在获得单独授权后作为最后手段。

不得按进程名批量 kill，也不要在 Storing Fields/save 阶段直接强杀。

## 21. 分阶段实施计划

### 里程碑 A：最小闭环

- [x] 服务器安装 Codex CLI；
- [x] 使用正式购买的 ChatGPT/Codex 账号或工作区席位完成认证；
- [x] `codex login status` 确认不是 API Key 登录；
- [ ] 重新登录 SSH 后认证仍可复用；
- [x] 验证 MATLAB `-batch`；
- [ ] 验证 tmux 断线后 Codex/MATLAB 恢复；
- [x] Codex 完成服务器只读盘点；
- [x] 用隔离 runner 完成一次实际8通道复现；
- [x] 日志写入 `runs/<CaseTag>`；
- [ ] 每次执行保存标准 `.exitcode`。

完成标准：无需人工复制源码和完整终端输出，Codex 能直接读取并诊断一次低成本运行。

### 里程碑 B：任务封装

- [x] 新增 `tools/marie-agent/` Phase 1；
- [x] 实现 inspect/prepare/status/tail；
- [x] 实现冻结 runner/config 快照、gate digest 和 launch --check；
- [x] 实现 exact-run 审批记录格式；
- [x] 实现隔离 fake-runner 状态、事件、case 锁和 canonical JSON 锁基础库；
- [x] 通过 exit0/exit42/SIGTERM/禁止 executable/并发锁/tmux detached 自测；
- [x] 实现审批单次消费、startup_unknown 和 orphan/recovery 分类；
- [x] 实现仅限 light/read-only geometry 的生产 worker；
- [x] 完成真实 geometry-only tmux 验收；
- [ ] 实现 launch/execute；
- [x] 实现唯一 RunID；
- [x] 实现输入/runner/活动 JSON 快照和哈希；
- [ ] 实现退出码与运行状态自动更新；
- [ ] 实现 TMD 单写保护；
- [ ] 实现高成本任务确认流程。

完成标准：Codex 不需要手工拼接 MATLAB 命令，可以通过统一入口启动、观察和归档任务。

### 里程碑 C：结构化验证

- [ ] MATLAB 静态输入检查器；
- [ ] geometry-only 检查器；
- [ ] MAT 元数据与 NaN/Inf 检查；
- [ ] SP_p/SP_s/互易性摘要；
- [ ] 噪声矩阵 Hermitian/PSD 摘要；
- [ ] B1-/SNR/UISNR 摘要；
- [ ] PNG/CSV/JSON 自动导出；
- [ ] manifest 状态自动更新。

完成标准：Agent主要读取结构化证据，而不是依赖数万行日志或完整大型 MAT。

### 里程碑 D：本地远程桥或调度器

- [ ] 本地 SSH alias；
- [ ] 受限远程命令入口；
- [ ] Git/rsync 同步检查；
- [ ] Slurm 或用户级任务队列（如果需要）；
- [ ] 可选的 MCP 接口。

只有在 A-C 稳定后才需要 MCP。固定 CLI 是更容易审计和调试的第一版接口。

## 22. 最终验收清单

- [ ] Agent 能直接读取服务器当前源码，而非仅看到本地快照；
- [ ] 每次运行具有唯一 CaseTag 和 run ID；
- [ ] MATLAB 从项目根目录执行且先运行 `startup`；
- [ ] 所有任务有日志、退出码、状态和 manifest；
- [ ] SSH 断线不终止 Codex 或 MATLAB；
- [ ] Windows/Linux 同步状态可证明；
- [ ] TMD 前后 JSON 有备份和哈希；
- [ ] 几何未通过时不能进入求解；
- [ ] 高成本任务必须由用户批准；
- [ ] MAT 数值完成不被误写为 research validation；
- [ ] 大型结果留在服务器，Agent读取摘要和必要图表；
- [ ] 不自动删除、批量 kill 或覆盖已验证资产。

## 23. 推荐的首次实际操作

首次闭环已经完成。下一步按以下顺序实施：

```text
1. 验证 Phase 1 inspect/prepare/status/tail
2. 用 geometry-only 的 prepare 生成首个 executions/<RunID>
3. 审查 gate、快照、哈希和命令，确认 prepare 没有启动 MATLAB
4. 实现 launch/execute、锁、tmux 和 exitcode
5. 用 geometry-only 验证断线恢复
6. 实现通用 MAT/网络/噪声验证器
7. 8通道网络优化改造为 Stage A/B/C
8. 最后才接入新的正式 EM/TMD 任务
```

不要用正式 16 通道高分辨率求解作为第一条远程 Agent 测试任务。第一条任务应是只读盘点、MATLAB 启动检查或 geometry-only 预检。

## 24. 参考

- 项目规则：`AGENTS.md`
- MARIE 执行约束：`MARIE_Agent_Harness.md`
- 现有自动优化总体设计：`docs/architecture/MARIE_WP7优化框架架构与流程_v01.md`
- OpenAI Codex CLI：<https://learn.chatgpt.com/docs/codex/cli>
- OpenAI Codex/ChatGPT 认证：<https://learn.chatgpt.com/docs/auth>
- OpenAI Codex Sandbox：<https://learn.chatgpt.com/docs/sandboxing>
- OpenAI Codex 非交互模式：<https://learn.chatgpt.com/docs/non-interactive-mode>


## 18. Training closed-loop profile（2026-08-11）

隔离训练案例 5T_1H_Sphere200_8Ch_LoopRx_Training_v01 使用生产档 training-closed-loop-v1。该档是显式 allowlist，不改变既有案例的 geometry-only 默认边界。

执行阶段为 geometry -> stage_a -> tmd -> stage_c -> post。prepare.py 会解析并哈希最近一次成功的上游产物；launch.py 在启动前复核快照与依赖漂移；高成本或写活动 JSON 的阶段必须绑定 exact RunID 的一次性审批。TMD worker 对活动 JSON 的 canonical realpath 加独占锁，在执行目录创建 before_TMD 备份并记录前后 SHA-256。

每个 execution 的 resources.workers 通过 marie_agent_configure_pool 在 runner 之前强制建立 Processes pool，日志必须记录 requested/actual 两个值。单任务上限 64 workers，全局生产预算 96 workers；GPU 0 使用全局独占锁。不同 CaseTag 可在总预算内并行，同一 CaseTag 仍由 case lock 串行。

上手入口和完整命令见 onboarding/MARIE_Agent_Quickstart_8Ch_v01/README.md。首次 Training geometry 成功证据为 runs/5T_1H_Sphere200_8Ch_LoopRx_Training_v01/executions/20260811_231346_geometry/。正式 Stage A、TMD 和 Stage C 未在本次架构验证中启动。
