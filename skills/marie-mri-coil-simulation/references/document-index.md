# MARIE Documentation Index

All paths below are relative to `references/workspace-docs/`. Search with `python scripts/query_marie_docs.py "<query>"` when the question spans documents.

| Question | Primary document | Useful search terms |
|---|---|---|
| Agent rules, permissions, naming, safety | `AGENTS.md`, `MARIE_Agent_Harness.md` | CaseTag, permission, research-validated, cleanup |
| New-session initialization and handoff | `START_HERE.md`, `MARIE_新会话初始化机制.md` | session_bootstrap, onboarding, handoff, latest evidence |
| 3T Duke/Hugo RF-coil optimization project re-entry | `PROJECT_3T_1H_Duke5mm_RFCoilOpt_Repro_v01_START_HERE.md` | WP8-R2, bell-shaped former, seed88011, Gradient 2 |
| Remote execution evidence architecture | `MARIE_Codex远程开发具体实施指南.md` | agent-case, executions, prepare, launch, validator |
| WP7 optimization architecture, Stage A/B/C, candidate-specific TMD | `MARIE_WP7优化框架架构与流程_v01.md` | WP7, optimizer, YPn cache, independent TMD, checkpoint |
| Agent training loop and concurrent resource governance | MARIE_Agent训练闭环与并发资源治理.md | training-closed-loop-v1, workers, dependency, JSON lock |
| Phase 2B fake-runner evidence | `MARIE_Phase2B_fake_selftest_20260811.md` | state, events, flock, tmux, exitcode |
| Installation, startup, license, recovery | `MARIE_使用指南_Codex经验.md`, `MARIE_帮助文档_中文.md` | license, startup, systemd, GLIBCXX, interrupt |
| JSON fields and valid values | `MARIE_JSON文件配置指南.md` | Basis_Functions_VIE, BodyFile, WireFile, TMD |
| Data files and available models | `MARIE_data文件夹内容与仿真作用详解.md` | bodies, wire_files, coil_files, bases, solutions |
| Source modules and algorithms | `MARIE_src源码模块与算法详解.md`, `MARIE_tools_项目架构剖析报告.md` | WIE, SIE, VIE, pFFT, TT, solver, shadowing |
| Runner selection and I/O | `MARIE_Runner算法与使用指南.md` | MARIE_runner, BASIS_runner, MRGF_runner, CO_SIMULATION_runner |
| Tuning/matching/decoupling | `MARIE_TMD模块使用教程.md`, `MARIE_5T_16通道联合TMD解决方案.md` | YPn, SP_p, SP_s, symmetry, Stage A |
| 5 T fixed-32-channel graded Stage-B gate | `MARIE_5T_32CH_STAGE_B分级网络门禁_v01.md` | Grade A, Grade B, exploratory Stage C, adjacency exceptions |
| Custom body/coil/wire/shield models | `MARIE_模型设计与组合教程.md` | Gmsh 2.2, Point, Line, Triangle, RHBM |
| Visualization and result inspection | `MARIE_可视化脚本使用指南.md` | geometry, B1-, SNR, current, colorbar |
| 5 T 8-channel case | `MARIE_5T_8通道Loop球形体模仿真操作指南.md` | Sphere200, 8LoopRx, UISNR, postprocessing |
| 5 T 16-channel case | `MARIE_5T_16通道Loop球形体模仿真操作指南.md`, `MARIE_5T_16通道Loop球形体模仿真日志.md` | DoubleRow, H90, TMD-only, checkpoint |
| UISNR algorithms and scientific conventions | `MARIE_UISNR实现与代码分析.md`, `MARIE_UISNR独立复现方案与风险分析.md`, `MARIE_UISNR工程契约与回归测试_v01.md`, `../uisnr-workflow-and-contracts.md`, `../uisnr-icp-complex-conventions.md`, `../uisnr-convergence-validation.md` | Phi, whitening, ideal current, pointwise ROI, physical coefficient, convergence |
| Absolute SNR and comparison with measurement | `../snr-measurement-normalization.md` (skill-root reference) | bandwidth, voxel volume, M0, sequence factor, calibration, NRMSE |
| Data cleanup | `MARIE_16通道仿真数据清理模板.md`, `MARIE_使用指南_Codex经验.md` | data/_trash, isolate, delete, BASIS |
| SSD/HDD placement, capacity gates, migration and retention | `../storage-layout.md` (skill-root reference), `MARIE_Agent_Harness.md` section 5.5 | /mnt/data, realpath, symlink, headroom, checkpoint, retention |
| Upstream overview and disclaimer | `README.md` | structure, requirements, license |

For architecture ownership, public command interfaces, deployment synchronization, and the append-only update registry, read `references/architecture-interfaces.md` directly from the skill root.

## Retrieval Rules

1. Search headings first, then read the complete matching section.
2. For behavior claims, verify against current source when available.
3. Treat simulation logs as case history, not universal instructions.
4. Treat thresholds such as `SP_p < -15 dB` and worst `SP_s < -12 dB` as project engineering gates unless the active study defines stricter criteria.
5. Note the known README mismatch: the current source uses `CO_SIMULATION_runner.m`; do not assume `TMD_runner.m` exists.
