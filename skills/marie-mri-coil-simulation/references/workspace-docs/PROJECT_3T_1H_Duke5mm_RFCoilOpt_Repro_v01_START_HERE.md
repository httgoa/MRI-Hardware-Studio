# 3T RF 线圈优化复现项目：当前重入入口

更新时间：2026-08-26（文档更新；未启动 MATLAB）

> 本节替代下方 2026-08-21 WP7 交接作为当前入口。下方旧正文保留为历史上下文，不再代表当前阶段。

## 每次重新进入项目

从仓库根执行；初始化不会启动 MATLAB：

```bash
cd /home/<user>/marie-tools
sed -n '1,260p' START_HERE.md
sed -n '1,260p' AGENTS.md
sed -n '1,760p' MARIE_Agent_Harness.md
bash tools/session_bootstrap.sh 3T_1H_Duke5mm_RFCoilOpt_Repro_v01
sed -n '1,320p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md
sed -n '1,260p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/status.json
sed -n '1,320p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/manifest.yaml
sed -n '1,220p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/report.md
```

根据当次 bootstrap 重新确认 Git、MATLAB/TMD/MRGF 进程、资源、最新证据时间和活动 JSON 写入者。正式 MATLAB 运行还须从仓库根执行 `startup`，记录 `which load_inputs -all`、`which geo_assembly -all`、`which solver_wsvie -all`、`which co_simulation -all`、`which np_compute -all`。

## 当前唯一恢复点

截至 2026-08-25，`status.json` 为 `wp8-r1-selected-branch-repeatability-pass-r2-next`。WP8-R1 只证明 seed88011 固定电路 Stage C 可重复（repeat02 ROI 平均 SNR 相对跨度约 `1.0573e-11%`）；不同 TMD 分支的 ROI 平均 SNR CV 仍为 `23.1573%`，不能宣称所有分支物理等价。

当前 incumbent 是 `width_p2p5mm`。当前结果是 engineering-validated workflow，不是论文 Figure 17 数值复现。UISNR 使用 Hugo 5 mm、18 mm 粗支撑、rank 1740，网格和 mode-rank 敏感性未完成。

下一步是 **WP8-R2：新建版本化、论文同源 bell-shaped former，并完成 geometry-only 验证**。Gradient 2 在 R2–R4 完成前暂缓；几何改变后现有 YPn 和 pre-TMD checkpoint 立即失效。

当前证据优先读取：

1. `provenance/wp8_latest_evidence_audit_20260825.md`；
2. `wp8_experiments/e2_three_coil/optimization/roi01/WP8_R1_selected_branch_repeatability_completion_v20.md`；
3. `status.json`；
4. `manifest.yaml` 的 `wp8` 节；
5. `report.md` 顶部 WP8 handoff。

`report.md` 分隔线后的 WP0、`report_zh_current.md` 和下方旧 WP7 交接只作历史证据。

## WP8-R2 开工门禁

1. 从论文、R2–R4 修复计划和现有 former 资产冻结几何定义、坐标、单位与参数域。
2. former 和派生 coil 使用新 ASCII 版本名，不原地修改已验证 MSH/JSON。
3. 静态验证 Gmsh 2.2 ASCII、映射、端口、m 单位及 MSH/JSON 同主名。
4. 检查 former—头皮距离、ROI 最短距离、曲率、覆盖、映射失真、BVH/CCD 和拓扑稳定性。
5. 只运行 `load_inputs + geo_assembly + visualize_geometry`；geometry-only 未通过不得进入 Stage A。
6. 几何通过后另行冻结 input、runner、manifest 和资源预算；Stage A 及更高成本计算需明确授权。
7. TMD 前锁定活动 JSON、记录哈希并创建时间戳备份；Stage C 使用独立 FixedCircuit MSH/JSON，`TMD=0` 且全部 `optim.boolean=0`。

R2 前精读 `wp8_experiments/plans/WP8_E2_三线圈位置形状联合优化修复计划_v01.md`、`wp8_experiments/repairs/r0_r5_v01/r3/R3快速工程路线完成报告_v01.md`、`r4/R4工程门禁结论_v01.md`、`r5/R5修复入口与当前门禁_v01.md`，以及仓库根 `docs/architecture/MARIE_WP7优化框架架构与流程_v01.md`。

## 目录职责与 init 完成判据

`status.json`/最新哈希证据负责状态，`manifest.yaml` 负责结构化配置，`provenance/` 负责审计，`wp8_experiments/` 是当前开发区，`assets/` 是 case-local 资产，`project_workspace/README_CN.md` 只作链接导航，`handoff_packages/` 只作冻结移交且其源码不得进入正式 MATLAB path。
三线圈历史配置、原始 MAT/日志、指标、图表与报告的非破坏性用户浏览入口为 `wp8_experiments/e2_three_coil/整理视图_v01/README.md`；它只提供索引和相对链接，不是运行资产副本。

冲突时按“当前源码/运行输出 → 根规则/Harness → status/manifest 及哈希匹配证据 → 本节 → 专题报告 → 历史 handoff”判定；不一致时停止状态升级。

开始开发前必须已读取实时 bootstrap、status/manifest 和最新审计；说明任务阶段；确认目标文件及活动 JSON 无冲突；明确 input、body、MSH/JSON、basis、runner 和输出版本；区分可复用证据与 R2 后失效缓存。正式计算另需 runtime `which -all`、资源、RunID、输出和授权记录。

禁止 reset/checkout/清理非本任务修改；未经授权不修改 `src/` 或已验证资产，不启动高成本计算，不终止用户 MATLAB。Hugo 不等价于 Duke，当前 UISNR 不是绝对 UISNR，流程完成不等于 research-validated。

---

# 历史交接（2026-08-21，WP7；不再作为当前入口）
# MARIE RF线圈优化复现：当前交接与快速启动

更新时间：2026-08-21 CST  
项目根 CaseTag：`3T_1H_Duke5mm_RFCoilOpt_Repro_v01`  
当前工作包：`WP7`  
当前状态：`real-MARIE closed-loop iteration 1 completed；no engineering-significant accepted step`

> 本文件是当前案例的状态入口。项目资产的统一浏览入口现为 `project_workspace/README_CN.md`；原始权威路径保持不变，以免破坏已有 runner。案例根目录旧 `report.md` 只记录 WP0，`status.json` 和 `manifest.yaml` 也未完整反映后续阶段；它们是历史证据，不应作为当前状态结论。

## 0. 统一项目文件入口

从 `project_workspace/` 浏览当前项目文件：

- `01_共享基础/`：WP0–WP5配置、支撑域、BASIS、日志和来源记录；
- `02_四通道历史优化/`：WP6四线圈建模、全部仿真结果、WP7优化器及R0–R5修复证据；
- `03_三通道论文实验E2/`：三线圈建模、Stage A–C、前三步优化、派生图表和支持脚本；
- `04_汇报与交接/`：报告、规划和三线圈交接包；
- `05_资产清单/全部资产索引_v01.csv`：2515个权威文件的路径、大小和类别索引。

该目录使用相对符号链接，不复制大型 MAT，不改变既有脚本的实际输出路径。

## 1. 下次启动：先执行这些命令

```bash
cd /home/<user>/marie-tools
sed -n '1,240p' START_HERE.md
sed -n '1,240p' AGENTS.md
sed -n '1,760p' MARIE_Agent_Harness.md
bash tools/session_bootstrap.sh 3T_1H_Duke5mm_RFCoilOpt_Repro_v01
sed -n '1,320p' runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md
git status --short --branch
ps -eo user,pid,ppid,etime,%cpu,%mem,rss,args --sort=-%cpu | awk 'NR==1 || tolower($0) ~ /matlab|tmd|mrgf/'
```

随后读取：

1. `WP7_优化控制器实施与验证方案_v01.md`；
2. `wp7_optimizer/reports/WP7_L0_L3_优化控制器阶段报告_v01.md`；
3. `wp7_optimizer/reports/WP7_真实Hugo几何扰动验证_v01.md`；
4. `wp7_optimizer/reports/WP7_StageA真实电磁有限差分结果_v01.md`；
5. `wp7_optimizer/reports/WP7_首轮完整优化闭环报告_v01.md`；
6. `wp6_geometry/mesh_sensitivity_shared_endpoints_v06/final_summary.json`；
7. `wp6_geometry/paper_metrics_shared_v25/summary.json`；
8. `项目管理日志.md` 的 LOG-064 至 LOG-075。

不要仅凭本交接文档启动正式求解；必须重新核对 git、进程、资源、输入哈希和授权。

## 2. 项目总览

目标是复现 Serrallés 等 2025 RF线圈优化论文。正式 Duke 路线仍缺与 Duke 线圈坐标匹配的介电体模，当前批准路线是 Hugo 5 mm 替代体模，用于验证算法和工程闭环；所有 Hugo 结论均不等价于 Duke 论文正式复现。

| WP | 当前结果 | 状态边界 |
|---|---|---|
| WP0 | 仓库、论文、环境和资产盘点 | 完成 |
| WP1 | Duke/Ella与论文ROI依赖核查 | 缺正式Duke介电体模，阻塞 |
| WP2 | Figure 14/SIE直接源与有限差分层A | 几何与SIE kernel通过；完整论文Eq.38依赖不足 |
| WP3 | Hugo R2 ROI、支撑面和BASIS准备/实验 | 已有结果，但现有v02 BASIS不能作为严格UISNR上界 |
| WP4 | 直接源重建、Huygens BASIS/MRGF复验 | 用户暂时验收；G4严格完备性仍不足 |
| WP5 | 调谐与理想去耦单端口验证 | 单端口范围PASS，多端口正式范围依赖WP4 |
| WP6 | Hugo SLIM四通道、Stage A–C、共享电路三网格 | Hugo替代路线PASS；Duke路线阻塞 |
| WP7 | 四优化方法、真实几何Stage A与首轮Stage A-C闭环 | 首轮真实闭环完成；最大改善0.389%，未达到2%接受筛选 |

## 3. WP6权威基线

用于继续WP7的线圈基线是细网格 v25：

- 输入：`data/inputs/inp_3T_1H_Hugo5mm_4Ch_SurfaceLoopRx_WP6SlimArray_SIEMesh3mm_SharedEndpointsFixed_v25.json`
- MSH：`data/coils/coil_files/Custom/WP6HugoSlimArray4ChSepFineSharedEndpointsFixed_v25/WP6_HugoAnteriorOffset20_SlimEnergy_4ChLoop_W8_Sep560x500_SIEMesh3mm_SharedEndpointsFixed_v25.msh`
- 电路JSON：同目录同主名 `.json`
- 体模：`data/bodies/RHBM/5mm/Hugo_Head_3T_R2Crop_5mm_v01.mat`
- 频率：127.732435554 MHz；4物理端口；1572个SIE三角形。

三网格共享电路结果：

- 网格：6 / 4.5 / 3 mm，对应796 / 1180 / 1572三角形；
- SNR相邻差：2.775% / 1.689%；
- B1−相邻最大差：0.938% / 1.435%；
- 三层网络均通过；最细网格 `SP_p=[-15.259,-15.287,-18.277,-15.452] dB`；
- 最差互耦：−12.282 dB；
- 权威汇总：`wp6_geometry/mesh_sensitivity_shared_endpoints_v06/final_summary.json`。

SNR/UISNR后处理：

- ROI半径40 mm，2092体素；
- ROI SNR均值7393.685，UISNR均值16347.511；
- Eq.38 proxy：0.529356；
- 19体素超过100%，最大110.724%；
- 这是支撑域约束UISNR且仍有上界有效性警报，不得当作绝对UISNR或正式论文结论；
- 权威汇总：`wp6_geometry/paper_metrics_shared_v25/summary.json`。

## 4. WP7已完成开发

代码位于 `wp7_optimizer/`，没有修改公共优化算法 `src/`。

已实现：

- 多ROI `1-SNR/UISNR` 目标与输入门禁；
- 边界barrier和解析梯度；
- 三步长中心有限差分；
- 最多30次Armijo回溯；
- L-BFGS、曲率拒绝和负梯度回退；
- 1A affine grid、1B affine FD-L-BFGS；
- 2A控制点grid、2B控制点FD-L-BFGS；
- 候选SHA-256、原子checkpoint、异常传播；
- WP6 BVH/CCD fail-closed接入。

验证结果：

- 自动化测试：12/12 PASS；
- 1A/1B/2A/2B解析cost均严格下降；
- L2/L3冻结Hugo代理均从0.529356降至0.499356；
- 代理结果只证明控制器集成，不是MARIE电磁改善。

常用命令：

```bash
python -m pytest -q runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/tests/test_wp7_controller.py
python runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/RUN_WP7_L0_L1_v01.py
python runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/RUN_WP7_L2_L3_PROXY_v01.py
```

后二者拒绝/避免覆盖策略应在重跑前检查；不要直接覆盖已有checkpoint或结果。

## 5. 真实Hugo几何验证

有效 CaseTag：`3T_1H_Hugo5mm_4Ch_WP7AffineGeomFD_v02`。

- 候选根：`data/coils/coil_files/Custom/3T_1H_Hugo5mm_4Ch_WP7AffineGeomFD_v02/`；
- 19个候选：baseline，加scale/u/v在`3e-6、1e-5、3e-5`的正负扰动；
- 输入：`data/inputs/inp_3T_1H_Hugo5mm_4Ch_WP7AffineGeomFD_v02_*.json`；
- Python汇总：`wp7_optimizer/results/wp7_real_hugo_affine_geometry_fd_v02.json`；
- MATLAB汇总：`wp7_optimizer/results/matlab_geometry_fd_v01/wp7_hugo_affine_geometry_fd_v01.mat`。

结论：

- 19/19通过结构、体模SAT、跨线圈BVH和CCD；
- 固定拓扑：1572节点、1572三角形、12条元件线；
- 最小体模保守间隙5.705 mm；最小跨线圈间隙33.727 mm；
- CCD unresolved=0；
- scale/u/v三步长灵敏度散布为`8.60e-5 / 5.62e-6 / 3.80e-7`；
- baseline和`±1e-5`六例的MATLAB geometry-only为7/7 PASS。

`...AffineGeomFD_v01/` 是失败过程资产：首次自适应重采样改变拓扑，只写出baseline，保留用于问题追踪；后续不得使用。

## 6. WP7首轮真实电磁闭环与下一步

首轮`1A`真实MARIE坐标搜索已经完成：

- 六个`±3e-5`候选全部完成独立Stage A；
- 共享固定电路Stage B为5/6 PASS，`scale_m3em05`因通道1匹配−14.961 dB拒绝；
- 五个候选完成`TMD=0` Stage C，网络、场、噪声与哈希门禁全部PASS；
- baseline Eq.38为`0.529356353877`，最优`v_p3em05`为`0.527297366344`；
- 相对改善`0.388961%`，严格下降PASS，但2%工程显著性筛选FAIL；
- checkpoint保留baseline为正式接受点，终止原因`no_engineering_significant_step`。

下一步不能直接线性放大`+v`步长。若继续WP7，应新建版本并：

1. 为`+v`线搜索定义明确上界和回溯序列；
2. 对新增步长重新执行former chart、体模间隙、BVH、CCD与MATLAB geometry-only门禁；
3. 对通过候选重跑Stage A-C；
4. 仅当真实Eq.38改善达到预先冻结门槛时更新接受checkpoint；
5. 当前UISNR仍是支撑域约束参考值，不能标记绝对UISNR或research-validated。

## 7. 关键风险与禁止事项

- 工作树高度dirty，包含既有`src/`、MEX、模型和结果改动；不得reset、checkout或清理。
- 电子学存在重复实现；正式运行记录`which co_simulation -all`、`which np_compute -all`、`which solver_wsvie -all`。
- 几何变化使旧YPn失效；不得用v25 YPn评价WP7新候选。
- 当前v02 UISNR BASIS不是已证明完备的严格上界；L4不得标记research-validated。
- 不得把Hugo路线报告为Duke等价。
- 不得删除失败的v01候选、TMD备份、MAT或原始证据；需要清理时另行列清单并授权。
- 用户MATLAB桌面长期存在，不能终止；截至本次交接，无batch、TMD、MRGF或worker进程。
- geometry-only首次曾自动开启64 workers，已经退出释放；现役runner已改为显式4 workers并自动关闭。

## 8. 证据索引

- 项目计划：`MARIE_RF线圈优化论文复现项目规划.md`
- 全过程日志：`项目管理日志.md`
- WP6当前状态：`wp6_geometry/status.json`
- WP6三网格：`wp6_geometry/mesh_sensitivity_shared_endpoints_v06/final_summary.json`
- WP6论文指标：`wp6_geometry/paper_metrics_shared_v25/summary.json`
- WP7方案：`WP7_优化控制器实施与验证方案_v01.md`
- WP7控制器报告：`wp7_optimizer/reports/WP7_L0_L3_优化控制器阶段报告_v01.md`
- WP7真实几何报告：`wp7_optimizer/reports/WP7_真实Hugo几何扰动验证_v01.md`
- WP7 Stage A报告：`wp7_optimizer/reports/WP7_StageA真实电磁有限差分结果_v01.md`
- WP7首轮闭环报告：`wp7_optimizer/reports/WP7_首轮完整优化闭环报告_v01.md`
- WP7首轮checkpoint：`wp7_optimizer/results/closed_loop_iter001_v01/checkpoint.json`
- WP7控制器源码：`wp7_optimizer/controller/wp7_controller.py`
- WP7测试：`wp7_optimizer/tests/test_wp7_controller.py`

## 9. 当前结论标签

可以使用：

- `WP6 Hugo surrogate shared-circuit three-grid validated`
- `WP7 optimizer controller validated at L0/L1`
- `WP7 frozen-proxy closure passed`
- `WP7 real-Hugo affine geometry validated`
- `WP7 real-MARIE closed-loop iteration 1 completed`
- `WP7 no engineering-significant accepted step`

不能使用：

- `WP7 formal EM optimization validated`
- `absolute UISNR validated`
- `Duke paper reproduction completed`
- `research-validated`
