# MARIE Agent Rules

> **Portable snapshot notice:** This file is a historical workspace-governance snapshot bundled for consultation. It does not override the active repository's root instructions or grant permission to run, modify, or delete anything.

本仓库是 MARIE 3.0 MRI 线圈仿真工作区。详细规则见 `MARIE_Agent_Harness.md`；它是本文件的解释性依据，但本文件的硬约束优先。

## 范围与环境

- 当前 Windows 工作区是代码、文档和案例资产工作区；Linux `/home/<user>/marie-tools` 是已知 MATLAB 运行路径。除非用户明确提供远程执行能力，不得假设两边已同步。
- 所有 MATLAB runner 都从仓库根目录运行，并先执行 `startup`。不要在 Bash 中直接执行 `.m` 文件名。
- 先读取 `git status`，保留用户已有修改；不得回退、覆盖或清理非本任务改动。

## 案例与文件

- 每个新设计使用唯一 ASCII `CaseTag`；共享/内置案例输入可位于 `data/inputs/inp_<CaseTag>.json`，独立项目输入可位于 `runs/<ProjectCaseTag>/assets/inputs/inp_<CaseTag>.json` 并由 `AssetRoot` 或受控自动发现解析；脚本为 `RUN_`、`PRECOMPUTE_`、`FINALIZE_`、`POST_` 加同一 CaseTag。
- Wire/Coil 的 `.msh` 与电路 `.json` 必须同目录、同主名、同版本；显著几何或端口变化创建 `_vNN`，不得原地改写已验证参考模型。
- TMD 会回写线圈 JSON。运行前创建带时间戳备份；同一活动 JSON 同时只允许一个写入任务。
- 几何、体模、频率、basis、屏蔽或端口拓扑改变后，旧 `YPn` 和 pre-TMD checkpoint 立即失效。仅电路值/边界变化才可复用原始 YPn。
- 原始输入、结果 MAT、BASIS、日志和对应 JSON 不得混放或只保留最后一个副本；派生图进入 case 专属目录。
- 存储采用 SSD 控制面与 HDD 数据面分层：代码、case 定义、runner、文档和轻量证据留在工作区；大型 MAT/BASIS、checkpoint、运行输出和大型共享体模优先放在 `/mnt/data/<user>/marie/`。允许用项目内软链接保持逻辑路径，但 manifest 必须同时记录逻辑路径、`realpath`、文件系统、大小和哈希。不得因迁移直接删除源文件；复制、校验、切换和删除必须分阶段授权。

## 强制工作流

新会话开始时，先阅读根目录 `START_HERE.md`，并从仓库根目录执行 `bash tools/session_bootstrap.sh`。该脚本只做只读盘点；其输出是现场线索，不替代本文件、Harness、实际源码和运行证据。

每次目录职责、运行证据结构、runner 约定、初始化、验证门禁、部署方式或公共调用接口发生架构更新时，必须同步更新仓库内 `marie-mri-coil-simulation skills/`，在 `references/architecture-interfaces.md` 登记变更和接口，刷新 bundle manifest，验证后再部署到 Codex skill 目录。

1. 盘点输入、依赖、实际函数路径和已有结果。
2. 静态检查 JSON、Body、MSH、电路映射、单位、端口和文件存在性。
3. 只运行 `load_inputs + geo_assembly + visualize_geometry`；几何未通过不得进入求解。
4. 先用 PWC/粗网格/少通道基线，再运行正式分辨率。
5. 多轮电路设计使用 Stage A 原始 YPn、Stage B TMD-only、Stage C `TMD=0` 固定电路场计算。
6. 最终结果必须完成数值、网络、场、噪声和可复现性核查后才可标记 research-validated。

## 权限与安全

- 默认允许只读分析、文档更新、新增隔离案例文件和非破坏性检查。
- 高成本任务启动前必须验证输出目标可写、不是只读挂载，且满足 Harness 的系统盘保底空间、目标盘余量和临时副本预算；未知输出规模时先运行小规模资源探针。
- 修改 `src/`、`installer.m`、`startup.m`、许可证/systemd、共享模型、已验证 JSON，或启动高成本服务器计算前，先说明影响并取得明确授权。
- 不得自动删除。失败结果先移入带时间戳的 `data/_trash/`；永久删除、批量移动、进程终止和清场必须单独确认。
- 不得使用宽泛删除或按进程名批量 kill；中止顺序是 Ctrl+C、确认 PID 后 INT、TERM，KILL 仅最后手段。
- 不通过改输入、放宽阈值、吞掉异常或替换系统库来掩盖 MEX、维度、收敛或物理错误。

## 科学与数值门禁

- 坐标统一为 m；Body 必须含 `RHBM.r/epsilon_r/sigma_e/idxS`；MSH 使用当前解析器兼容的 Gmsh 2.2 ASCII。
- 纯 Rx 匹配看 `SP_p` 和 `SPm_plot_Rx`，互耦看 `SP_s` 非对角；TMD 临时端口数不等于最终物理端口数。
- 当前 Rx 阵列起始工程门槛：全部 `SP_p < -15 dB`、谐振偏移 `< 0.5 MHz`、对称组离散 `< 3 dB`、最差非对角 `SP_s < -12 dB`。这些不是普适标准，变更必须记录依据。
- 检查全部数组有限、S 矩阵互易性、噪声矩阵 Hermitian/半正定、GMRES 收敛、通道对称性及网格敏感性。
- Rx-only 的互易回退 TXE 不能作为正式 Tx/SAR 结论；正式 Tx 必须存在 `h_field.Tx.b1p` 和 `e_field.Tx.e_b`。
- SNR/UISNR 只在相同 B0、核种、体模、网格、ROI、带宽、场/噪声归一化和支撑域下比较；超过 100% 先视为约定或实现问题。

## 已知风险与报告

- `startup` 递归加路径，电子学目录有重复实现；正式运行前记录 `which co_simulation -all` 和 `which np_compute -all`。
- GPU 回退的宽泛 `catch` 可能把其他错误误报为显存不足；保留首次异常堆栈。
- README 中的 `TMD_runner` 与当前源码不一致；实际独立入口是 `CO_SIMULATION_runner` 或项目的 TMD-only 脚本。
- 报告必须列出 CaseTag、输入快照、代码状态、环境、命令、输出、检查指标、警告和未验证项；“Simulation completed successfully”只表示数值流程结束。
