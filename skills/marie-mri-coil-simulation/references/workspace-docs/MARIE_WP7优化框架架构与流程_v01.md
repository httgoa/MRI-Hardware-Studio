# MARIE WP7 优化框架架构与流程 v01

日期：2026-08-18  
适用案例：`3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer`  
实验 CaseTag：`3T_1H_Hugo5mm_4Ch_WP7FourStage_v01`  
状态：基础闭环已形成；当前科学状态为 `postprocessed`，不是 `research-validated`

> **Portable snapshot note:** WP7 优化 pipeline is maintained in the active MARIE workspace and is not bundled with this public skill snapshot.

## 1. 架构结论

当前 WP7 已形成一个可审计的基础 MRI 接收线圈优化框架。它不是“优化器直接调用一次 MARIE”的单脚本，而是由控制与治理、几何与资产、MARIE 计算、证据与决策四层组成的分阶段闭环。每个候选必须经过几何门禁、原始网络求解、候选专属电路优化、固定电路场重算和统一后处理；任一阶段失败都会返回控制器并保留证据。

本框架解决了本轮最重要的系统性问题：几何优劣不能在共享固定电路下公平排序。正式目标评估必须让每个几何候选使用自己的 Stage A 原始 `YPn` 和独立 TMD，再以 `TMD=0` 重算最终场。该规则已经由独立 TMD 因果复验和几何重排序实验证实。

## 2. 范围与非目标

框架当前覆盖纯 Rx 四通道表面线圈的局部几何优化：

- 仿射参数和周期 B-spline 控制点参数化；
- 坐标网格搜索、有限差分梯度、回溯和 L-BFGS；
- SLIM 支撑面映射、冻结拓扑、体模间隙、BVH/CCD 门禁；
- MARIE Stage A / Stage B / Stage C；
- 匹配、互耦、谐振、互易性、噪声、SNR 和支撑域 UISNR 检查；
- 接受/拒绝、checkpoint、哈希、日志和报告。

当前不覆盖正式 Tx/SAR、制造容差闭环、全局最优证明、完备绝对 UISNR 或论文 Duke/Ella 数值等价复现。

## 3. 四层架构

| 层 | 核心职责 | 当前实现 | 主要输出 |
|---|---|---|---|
| 控制与治理层 | 定义变量、边界、目标、候选、预算和接受规则 | `controller/wp7_controller.py`、config、checkpoint | candidate ID、参数、seed、接受状态 |
| 几何与资产层 | 将参数映射为 MSH/JSON/input，并执行 fail-closed 门禁 | `BUILD_WP7_*`、WP6 SLIM/BVH/CCD | 版本化 MSH、JSON、geometry manifest |
| MARIE 计算层 | raw YPn、候选专属 TMD、固定电路场重算 | `PRECOMPUTE_*`、TMD runner、`FINALIZE_*` | Stage A、TMD、Stage C MAT |
| 证据与决策层 | 统一目标、网络/噪声门禁和归档 | `POST_*`、comparison、reports | Eq.38、SNR、结论、图表、报告 |

层间只通过版本化资产和明确数据契约衔接，不依赖工作区中的隐式 MATLAB 状态。

## 4. 核心数据契约

### 4.1 候选身份

每个候选至少由 CaseTag、阶段、候选名、参数向量、步长、MSH/JSON/input 哈希、TMD seed、硬边界、Body、B0、核种、basis、ROI 和各阶段输出共同确定。候选名不能替代哈希；dirty 工作树必须记录相关文件哈希。

### 4.2 Stage A：几何到原始网络

输入为通过 geometry-only 门禁、`TMD=1` 且所有可调元件展开的候选。输出至少包括 `YPn`、`Jcb`、`omega`、维度、互易误差和时间。

`YPn` 缓存键由几何、体模、B0/核种、VIE basis、屏蔽和端口拓扑共同决定。上述任一项变化时旧 Stage A 立即失效；只有电路值或搜索边界变化时才允许复用兼容 raw `YPn`。

### 4.3 Stage B：候选专属 TMD

Stage B 只读取当前候选的 raw `YPn`。活动 JSON 在运行前必须备份并加 canonical 路径独占锁；所有局部搜索区间必须与 JSON `optim.minim/maxim` 硬边界相交，越界或非有限结果在写回前失败。

当前工程门槛：全部 `SP_p < -15 dB`、最差非对角 `SP_s < -12 dB`、谐振偏移 `<0.5 MHz`，且网络近似互易。

### 4.4 Stage C：固定电路场

Stage B 通过后复制为新版本冻结 JSON，将全部 `optim.boolean=0`，输入设置 `TMD=0`。Stage C 重新执行网络、场和噪声计算；禁止把旧场与新 TMD 网络拼接。

### 4.5 后处理与目标

核心目标为中心 40 mm ROI（2092 体素）的 Eq.38 代理量：

`J = 1 - ||SNR_ROI||₂ / ||UISNR_ROI||₂`

越小越好。比较必须保持 B0、核种、Body、网格、ROI、带宽、场/噪声归一化和 UISNR 支撑域一致。当前 BASIS 是 Hugo 表面支撑域约束参考，不是已证明完备的绝对 UISNR；局部 `SNR/UISNR > 100%` 必须保留并报告。

## 5. 优化控制器

| 阶段 | 搜索空间 | 方法 | 作用 |
|---|---|---|---|
| 1A | 低维仿射参数 | 坐标网格搜索 | 确定可辨识方向 |
| 1B | 低维仿射参数 | 中心有限差分 + 回溯/L-BFGS | 连续下降细化 |
| 2A | B-spline 控制点模式 | 局部网格搜索 | 引入 width/height/diamond/skew |
| 2B | 控制点组合方向 | 有限差分梯度 | 组合已识别方向 |
| 扩展线搜索 | 接受方向附近 | 离散夹逼 + 独立 TMD | 处理真实目标非单调性 |

`wp7_controller.py` 提供多 ROI 目标、barrier、中心有限差分、坐标搜索、L-BFGS、Armijo 回溯、严格下降、确定性候选 ID 和原子 checkpoint。单元测试证明控制逻辑可执行；真实 MARIE 优化仍由 case-local Python/MATLAB runner 编排，尚无单命令通用生产 orchestrator。

候选只有在几何、Stage A、独立 TMD、TMD=0 Stage C、统一 UISNR/ROI 和严格下降全部通过后才可接受。当前 2% 相对改善只是工程显著性筛选，不是普适科学阈值。

## 6. 状态机与失败处理

状态按 `created → static-validated → geometry-validated → em-solved → tmd-candidate → circuit-accepted → final-solved → postprocessed` 推进。完成重复 seed、网格/步长敏感性、约定一致性和独立复核后才可升级为 `research-validated`。

任一门禁失败时不吞异常、不放宽阈值、不覆盖 accepted 资产；保留首次错误栈和失败日志。TMD 失败时核对 before/after JSON 哈希；控制器记录 reject reason 后生成下一候选或终止。

## 7. 目录与证据布局

当前实现位于父案例：

~~~text
runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/
  wp7_optimizer/
    controller/        # 通用控制算法
    config/            # 变量、预算和计划
    checkpoints/       # 接受点和内容哈希
    results/           # Stage A/B/C、比较、图和 manifest
    reports/           # 中文阶段报告
    tests/             # 控制器单元测试
~~~

实验资产位于 `data/coils/coil_files/Custom/<CaseTag>/` 和 `data/inputs/`。当前实验 CaseTag 没有独立 `runs/<CaseTag>/` 根目录，这是历史兼容布局。下一代 orchestrator 应把 status、manifest、executions 和报告收敛到独立案例根，父论文复现案例只保留引用。

## 8. 当前调用入口

~~~bash
python -m pytest -q runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/tests/test_wp7_controller.py
python runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/BUILD_WP7_FOUR_STAGE_CANDIDATES_v01.py
~~~

MATLAB runner 从仓库根目录执行 `startup` 后调用：

- `PRECOMPUTE_WP7_FOUR_STAGE_A_v01` 的环境变量候选白名单接口；
- `RUN_WP6_TMD_TRUST25_v02(rawFile, coilJson, out, seed)`；
- `FINALIZE_WP7_*` 的候选白名单接口；
- `POST_WP7_*` 的统一后处理。

这些入口证明分阶段可执行性，但还不是稳定公共 API。下一阶段应注册到 `agent-case.json`/`tools/marie-agent`，由 prepare/approve/launch/status 管理。

## 9. 当前成果与技术债

已经形成：可测试控制器、参数化表面几何与 CCD、真实 Stage A–C、每候选独立 TMD、公平目标比较、固定电路场、checkpoint、哈希、备份、锁、日志、图和中文报告。

仍需：`-3H` 多 seed、`-2.5H/-3.5H` 夹逼、网格/步长/元件容差敏感性、更完备 UISNR/G4、通用 orchestrator、独立 CaseTag 证据根，以及论文优化器等预算比较。

## 10. 图资产

- Mermaid：`docs/architecture/assets/MARIE_WP7_Optimization_Pipeline_v02.mmd`
- SVG：`docs/architecture/assets/MARIE_WP7_Optimization_Pipeline_v02.svg`
- PNG：`docs/architecture/assets/MARIE_WP7_Optimization_Pipeline_v02.png`
