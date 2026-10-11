# MARIE 新会话入口

本文件用于关闭对话、SSH 重连或更换 Agent 后快速恢复项目上下文。它是导航入口，不替代 `AGENTS.md`、`MARIE_Agent_Harness.md`、实际源码或运行证据。

## 每次新会话的最短流程

从 `/home/<user>/marie-tools` 开始：

```bash
cd /home/<user>/marie-tools
bash tools/session_bootstrap.sh
```

然后按顺序完整阅读：

1. `AGENTS.md`：不可绕过的安全与科学硬约束；
2. `MARIE_Agent_Harness.md`：完整开发、求解和验收流程；
3. `/home/<user>/.codex/skills/marie-mri-coil-simulation/SKILL.md`：已部署的 MARIE skill；
4. 初始化输出列出的最新 `status.json`、`manifest.yaml`、`report.md` 和日志；
5. 与当前任务直接相关的 `docs/` 专题文档、输入和 runner。

若只接管某个案例，可运行：

```bash
bash tools/session_bootstrap.sh 5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01
```

## 当前专注项目

先执行：

```bash
bash tools/session_bootstrap.sh 3T_1H_Duke5mm_RFCoilOpt_Repro_v01
sed -n '1,320p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md
```

该项目已从旧 WP7 交接推进至 WP8-R1 选定分支重复性通过；下一步是 WP8-R2 论文同源 bell-shaped former 几何重建和 geometry-only 验证。项目专属 `START_HERE.md` 是重入检查单，状态仍须由实时 bootstrap 和结构化证据复核。

## 当前交接摘要（2026-08-22）

- 3T 论文复现项目的专属 inputs、coils、basis supports 和 BASIS 已复制并切换到 `runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/assets/`；共享 Hugo body 仍由 `data/bodies/` 提供。
- 迁移采用 `AssetRoot`/`assets/inputs` 受控自动发现并保留旧 `data/` 回退。迁移设计、精确映射和验证证据位于该案例的 `assets/migration/`；在获得单独清理授权前不得移除 `data/` 中的旧项目副本。
- 4 通道 v25 与 3 通道 v07 的迁移后几何门禁已通过；这不等于重新完成电磁求解、TMD 或研究级科学验收。

- Linux 权威运行路径：`/home/<user>/marie-tools`；MATLAB：`/path/to/MATLAB/R2025b/bin/matlab`。
- Windows 与 Linux 不能仅凭同名文件认定同步；需要比较来源、时间、大小和必要时的 SHA-256。
- 工作树已有大量用户/历史改动和未跟踪仿真资产；不得清理、回退或覆盖。
- 8通道非 MRGF 初次案例位于 `runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/`。
- 最新实际复现证据位于该案例的 `reproductions/repro_20260811_1828/`。
- 该次复现完成 WSVIE、TMD、场计算和后处理，状态为 `em-solved`；网络门禁失败：最差非对角 `SP_s=-10.544 dB`。
- 复现简报：`runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/reproductions/repro_20260811_1828/report.md`。
- Phase 1 运行证据接口已实施：`tools/marie-agent/{inspect,prepare,status,tail}.sh`；`prepare` 只创建快照和门禁证据，不启动 MATLAB。
- 首个几何预备证据为 `executions/20260811_193535_geometry/`，进程状态为 `prepared`，`launch_available=false`；它不表示几何已重新执行。
- Phase 2A 预检证据为 `executions/20260811_195711_geometry/`；runner 和 `agent-case.json` 已冻结，`launch --check` 通过，真实提交仍以 RC=11 关闭。
- Phase 2B 已完成首次真实 geometry-only tmux 验收：RunID `20260811_204548_geometry`，MATLAB/包装器退出码均为 0，`GEOMETRY_GATE=PASS`；生产入口仍只允许 light、只读 geometry。
- 当前源码路径存在电子学重复实现；正式运行前必须在 MATLAB 中记录 `which co_simulation -all`、`which np_compute -all` 和 `which solver_wsvie -all`。
- Training golden path 已建立：onboarding/MARIE_Agent_Quickstart_8Ch_v01/，对应 CaseTag 5T_1H_Sphere200_8Ch_LoopRx_Training_v01。
- training-closed-loop-v1 生产档允许 geometry、Stage A、TMD、Stage C、post；高成本/写 JSON 阶段仍要求 exact-run 审批。每案例 worker 在 runner 前强制执行，单任务上限 64、全局预算 96，GPU 和活动 JSON 使用独占锁。
- Training geometry RunID 20260811_231346_geometry 已以 requested/actual 16 workers 通过；Stage A/TMD/Stage C/post 尚未运行。

## 继续开发前必须重新确认

- `git status`、当前分支和目标文件是否已有用户修改；
- 当前 MATLAB/TMD/MRGF 进程，尤其是否有任务写同一线圈 JSON；
- CaseTag、输入、MSH/JSON、Body、BASIS、runner 和输出路径的一致性；
- 最近报告中的状态是否仍对应当前文件哈希；
- 任务是否只读、几何预检、正式求解、TMD、后处理或清理；
- 高成本求解是否已按 Harness 第12节完成门禁并获得授权。

初始化脚本不会启动 MATLAB，也不会证明运行时函数解析、Windows/Linux 同步或科学验收已经完成。
