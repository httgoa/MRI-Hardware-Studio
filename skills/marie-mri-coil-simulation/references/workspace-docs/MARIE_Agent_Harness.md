# MARIE 3.0 Agent Harness

> 目的：规范 AI Agent 在本工作区中创建、修改、运行、核查和归档 MARIE 仿真任务的行为。
>
> 适用范围：`C:\path\to\marie-tools` 的当前工程资产，以及与其明确同步的 Linux `/home/<user>/marie-tools` 运行副本。
>
> 本文是详细执行手册；根目录 `AGENTS.md` 是自动生效的精简硬规则。

## 1. Harness 的角色

MARIE 是研究型电磁仿真软件，不是具有完整 schema、测试和事务式输出管理的生产应用。Agent 的职责不只是“让 runner 跑完”，而是建立一条可追溯证据链：

~~~text
需求
-> 独立案例资产
-> 静态与几何验证
-> 数值求解
-> 电路验收
-> 场和噪声验收
-> 后处理与复现包
-> 研究结论
~~~

任何阶段失败时，Agent 应停在该阶段，保存证据并说明下一步，不能跨过失败门禁继续生成貌似完整的图和结论。

## 2. 事实来源与冲突处理

发生冲突时使用以下优先级：

1. 当前实际源码和运行时输出；
2. 根目录 `AGENTS.md`；
3. 本 Harness；
4. 专项现役文档；
5. README、历史日志和旧案例说明。

关键专项文档：

- `docs/architecture/MARIE_src源码模块与算法详解.md`：源码调用链和已知风险；
- `docs/architecture/MARIE_data文件夹内容与仿真作用详解.md`：data 资产和格式；
- `docs/guides/MARIE_JSON文件配置指南.md`：输入字段；
- `docs/guides/MARIE_Runner算法与使用指南.md`：runner 选择；
- `docs/guides/MARIE_TMD模块使用教程.md`：电路优化；
- `docs/guides/MARIE_模型设计与组合教程.md`：自定义模型；
- `docs/guides/MARIE_可视化脚本使用指南.md`：后处理；
- `docs/operations/MARIE_使用指南_Codex经验.md`：环境、恢复和清理；
- `docs/validation/MARIE_UISNR实现与代码分析.md`：UISNR 数学链；
- `docs/case-history/5T_16Ch/MARIE_5T_16通道Loop球形体模仿真日志.md`：特定案例历史，不是通用规则。

已知文档冲突：README 和中文帮助提到 `TMD_runner.m`，当前 `src/src_runners` 实际只有 `MARIE_runner.m`、`BASIS_runner.m`、`MRGF_runner.m` 和 `CO_SIMULATION_runner.m`。Agent 不得凭 README 调用不存在的入口。

## 3. 环境边界

### 3.1 Windows 与 Linux

当前 Windows 路径主要用于代码、文档、案例文件和审查；已知 Linux 服务器运行路径为：

~~~text
/home/<user>/marie-tools
/path/to/MATLAB/R2025b/bin/matlab
~~~

Agent 必须明确每项操作发生在哪里：

- 在 Windows 修改文件，不代表 Linux 副本已经同步；
- Linux 生成的 MAT、日志或 JSON 回写，不代表 Windows 副本已经更新；
- 未获得远程连接和授权时，只提供命令，不宣称已经在服务器执行；
- 同步前比较文件主名、大小、修改时间和必要时的 SHA-256。

### 3.2 MATLAB 会话前置条件

从工具箱根目录执行：

~~~matlab
cd('/home/<user>/marie-tools');
startup;

assert(exist('load_inputs','file')==2);
assert(exist('geo_assembly','file')==2);
assert(exist('solver_wsvie','file')==2);
~~~

首次安装、MATLAB 大版本变化、编译器变化或 MEX ABI 变化时才运行 installer。普通输入错误、几何错误和 TMD 失败不应触发重新安装。

### 3.3 许可证与系统服务

Agent 可以检查许可证环境变量和服务状态，但不能未经授权修改：

- 网络许可证文件；
- lmgrd 配置；
- systemd unit；
- 防火墙；
- 系统主机名；
- MATLAB 安装目录。

不得把许可证密钥、完整 license 文件或敏感服务器配置写入仓库文档和日志。

## 4. 项目命名规范

### 4.1 CaseTag

新案例使用 ASCII、无空格、可排序的 CaseTag：

~~~text
<B0>T_<Nucleus>_<Phantom>_<Nch>Ch_<Topology>_<Mode>_<GeometryTag>_vNN
~~~

示例：

~~~text
5T_1H_Sphere200_16Ch_LoopRx_2Row_H90_R115_v01
~~~

原则：

- `B0/Nucleus` 明确频率来源；
- `Phantom` 包含尺寸或主体标识；
- `Nch` 是物理 RF 通道数，不是 TMD 临时端口数；
- `Topology/Mode` 区分 Loop、Birdcage、Rx、Tx 或 TxRx；
- `GeometryTag` 只写决定几何的关键参数；
- `_vNN` 用于几何、网格、端口拓扑或体模版本；
- PSO/TMD 轮次不递增几何版本，而使用时间戳。

既有文件不强制重命名；新资产遵循本规范。

### 4.2 文件名映射

| 资产 | 命名规则 |
|---|---|
| 输入 JSON | 共享案例：`data/inputs/inp_<CaseTag>.json`；独立项目：`runs/<ProjectCaseTag>/assets/inputs/inp_<CaseTag>.json` |
| Wire/Coil 网格 | `<GeometryStem>_vNN.msh` |
| 电路 JSON | 与对应 MSH 同目录、同主名、同版本 `.json` |
| 通道布局 | `<GeometryStem>_vNN_channel_layout.csv` |
| 完整 runner | `RUN_<CaseTag>.m` |
| 原始网络 | `PRECOMPUTE_<CaseTag>.m` 和 `YPn_<CaseTag>.mat` |
| TMD-only | `RUN_<CaseTag>_TMD_ONLY.m` |
| 最终固定电路 | `FINALIZE_<CaseTag>.m` |
| 后处理 | `POST_<CaseTag>.m` |
| 最终结果 | `MARIE_0_inp_<CaseTag>_FINAL.mat` 或 runner 明确记录的唯一名称 |
| 轮次结果 | `TMD_<CaseTag>_YYYYMMDD_HHMMSS.mat` |
| 日志 | `<CaseTag>_YYYYMMDD_HHMMSS.log` |

### 4.3 版本何时必须增加

下列变化必须创建新 `_vNN` 和新 CaseTag，并重新计算 YPn：

- Loop 尺寸、位置、重叠、排距、错位角；
- MSH 节点、线段、三角形或物理标签；
- 端口数量、元件数量、元素顺序或 entity 映射；
- BodyFile、材料、体素尺寸、位置或裁剪；
- B0、Nucleus、Basis_Functions_VIE；
- ShieldFile 或支撑结构；
- PWC/PWL、pFFT 或会改变原始电磁算子的设置。

仅修改以下项目时，可以复用同一原始 YPn，但必须保留 TMD 轮次记录：

- 元件 seed value；
- optim.minim/maxim；
- 经验证的 optim.symmetry；
- PSO 设置；
- 元件 Q 和前放参数。Q 变化后仍需重新计算最终噪声和 SNR。

## 5. 目录和资产管理

### 5.1 权威位置

| 目录 | 允许内容 |
|---|---|
| `data/inputs` | 输入 JSON，不放日志或结果 |
| `data/bodies` | Body MAT 和必要说明 |
| `data/coils/*_files` | MSH、同名电路 JSON、几何元数据 |
| `data/bases` | BASIS/UISNR/MRGF 预计算结果 |
| `data/solutions` | 原始网络、checkpoint、TMD、最终 solution |
| `data/solutions/<CaseTag>_figures` | PNG、FIG、CSV 和轻量 summary MAT |
| `runs/<CaseTag>` | 输入快照、runner 快照、manifest、日志和验收记录 |
| `data/_trash/<timestamp>` | 待复核的隔离文件，不是永久归档 |

独立项目允许采用 `runs/<ProjectCaseTag>/assets/` 作为案例资产根，其内部保持 `inputs/`、`coils/*_files/`、`bases/` 等与 `data/` 对应的相对结构。`load_inputs` 的解析优先级为：绝对路径、输入 JSON 所在目录相对路径、显式或受控自动发现的 `AssetRoot`、旧版 `data/` 回退。自动发现仅对 `.../assets/inputs/` 生效；`BodyFile` 可以继续回退到共享 `data/bodies/`。历史报告、交接快照和已验证资产不得借迁移原地改写。

### 5.2 不可覆盖资产

Agent 不得原地覆盖：

- 仓库内置示例；
- 已标记 accepted/final/validated 的 MSH、JSON 或 MAT；
- 用户未授权修改的源代码；
- 正在被运行任务读取或写入的文件；
- 唯一一份 BASIS、phantom 或结果文件。

需要修改时先复制为新版本。不得使用 `old`、`new`、`final2` 作为长期版本名；用 `_vNN`、状态和时间戳表达含义。

### 5.3 TMD 写回治理

TMD 会修改活动线圈 JSON。每轮必须：

1. 确认服务器没有另一个任务写同一 JSON；
2. 计算或记录活动 JSON 哈希；
3. 创建 `.before_TMD_YYYYMMDD_HHMMSS` 备份；
4. 运行 TMD；
5. 保存 TMD MAT、进展图和日志；
6. 记录 TMD 后 JSON 哈希和最终元件值；
7. 未通过门槛时把该轮标为 candidate/failed，不覆盖 accepted 版本。

### 5.4 运行清单 manifest

每个正式 case 应记录：

~~~yaml
case_tag:
status:
created_at:
code_commit_or_dirty_state:
matlab_version:
compiler:
input_json:
body_file:
coil_or_wire_file:
shield_file:
basis_file:
b0_tesla:
nucleus:
target_frequency_hz:
vie_basis:
tmd_mode:
random_seed_or_optimizer_state:
command:
output_files:
warnings:
validation_summary:
~~~

若工作树是 dirty，必须记录相关文件的 diff 或哈希，不能只写 commit ID。

### 5.5 SSD/HDD 分层存储规范

工作站存储分为控制面和数据面，遵循服务器指南“系统盘保存代码、数据盘保存大文件和实验输出”的要求。

#### 5.5.1 控制面：系统 SSD

`/home/<user>/marie-tools` 保留：

- 源代码、Git 元数据、工具和测试；
- `projects/<ProjectID>/cases/` 中的输入 JSON、MSH、电路 JSON 和 runner；
- 文档、manifest、状态、指标 JSON/CSV 和必要的轻量图；
- 运行入口和指向数据面的软链接。

系统盘不得作为大型 `YPn`、`MREDM_*`、`*_FINAL.mat`、UISNR BASIS 或批量 checkpoint 的长期权威位置。

#### 5.5.2 数据面：11 TB HDD

默认个人根为：

~~~text
/mnt/data/<user>/marie/
├── shared/                         # 个人项目间复用、哈希冻结的 body/basis
├── projects/<ProjectID>/
│   ├── runs/<CaseTag>/<RunTag>/    # 大型运行证据和结果
│   ├── artifacts/bases/            # UISNR/MRGF/BASIS
│   ├── large_assets/               # 大型 body/support 数据
│   ├── scratch/                    # 可删除的运行临时数据
│   ├── trash/<timestamp>/          # 同一数据面的可恢复隔离区
│   └── archive/                    # 已关闭但需保留的正式结果
└── legacy/                         # 尚未完成治理的旧数据
~~~

`/mnt/data/shared/` 仅在管理员或项目负责人确认共享所有权、权限和哈希后使用，不能把个人可变文件直接写入其中。

#### 5.5.3 逻辑路径和软链接

项目可以让下列逻辑目录整体或按子目录链接到数据面：

~~~text
projects/<ProjectID>/runs
projects/<ProjectID>/artifacts/bases
projects/<ProjectID>/assets/bodies        # 仅大型、稳定 body
~~~

`cases/`、`tools/`、`docs/` 和活动配置保留为系统盘普通目录。不要在一个 RunTag 内建立指向多个未记录位置的临时链接。每个正式 manifest 增加：

~~~yaml
storage:
  logical_path:
  physical_path:
  realpath:
  filesystem_source:
  filesystem_type:
  storage_tier: ssd-control | hdd-data
  size_bytes:
  sha256:
  link_type: regular | symlink | hardlink
~~~

输入使用项目相对路径或受控 `AssetRoot`；不要把 `/mnt/data` 绝对路径写死在可移植 case 定义中。运行前解析 `realpath` 并冻结到 RunTag manifest。

#### 5.5.4 容量与可写门禁

高成本任务在 `load_inputs` 前必须记录 `df -hT`、`df -ihT`、目标 `realpath` 和挂载选项，并满足：

1. 输出目标存在、属于预期用户、可写且挂载选项不含 `ro`；
2. 目标盘可用空间至少为预计持久输出的 2.5 倍，以覆盖 checkpoint、MAT v7.3 保存临时副本和失败证据；
3. 任务结束后系统盘预计仍保留 `max(15% 文件系统容量, 200 GiB)`；
4. 数据盘任务结束后预计仍保留 `max(10% 文件系统容量, 500 GiB)`；
5. 输出规模未知时先用较低 rank、较少端口或 ROI-only 路径做资源探针；
6. 容量不足时停止在 prepared 状态，不能自动清理其他案例来腾空间。

上述是默认运维门禁；项目可记录更严格阈值，不得无记录放宽。系统盘只可短时缓存确定尺寸的热点文件，任务结束后按已批准清单清理。

#### 5.5.5 I/O 与 checkpoint

- 大型 MAT、BASIS 和最终输出直接写入数据面，避免先落系统盘再复制；
- MATLAB JobStorage、锁和小型状态可留在本地 SSD，但必须有独立路径且不得成为唯一科学证据；
- HDD 随机 I/O 较慢，优先阶段性顺序 checkpoint，避免高频保存整个 MREDM；
- 每一阶段只保留一个明确的可恢复 checkpoint；最终结果验证后，将重复 checkpoint 列入清理候选；
- 不跨文件系统依赖硬链接；跨 SSD/HDD 迁移按普通文件复制并重新计算哈希；
- 保存失败时保留原输出，写新临时名并仅在完整校验后原子改名。

#### 5.5.6 迁移协议

迁移大型现有结果必须分阶段：

1. 只读盘点引用、大小、inode/硬链接和正在运行的进程；
2. 生成精确源/目标 manifest，确认数据盘目录与权限；
3. 停止相关写任务，复制到数据面，不移动唯一源；
4. 对普通文件逐项校验大小和 SHA-256，对目录校验清单；
5. 将项目逻辑路径切换为软链接，并验证 `realpath`；
6. 执行 `load_inputs`、geometry-only 和结果只读打开回归；
7. 观察至少一个独立会话重入，确认 bootstrap、runner 和后处理均可解析；
8. 源副本进入单独清理清单，获得明确永久删除授权后才删除；
9. 在架构注册表记录路径、兼容性和证据。

移动到同一文件系统的 `trash/` 只改变目录，不释放空间；清理目标若是释放容量，报告必须区分“已隔离”和“已永久释放”。

#### 5.5.7 保留等级

| 等级 | 内容 | 默认策略 |
|---|---|---|
| A 权威 | accepted/final MAT、验证 BASIS、输入/runner/电路快照、最终指标与报告 | 永久保留并校验哈希 |
| B 恢复 | 最后一个可续算 checkpoint、已采用 Stage A 原始 YPn | 保留到案例关闭或重算成本复核 |
| C 可重建 | 重复 MREDM、派生全分辨率图、被后续阶段完整包含的 checkpoint | 验证后列入清理候选 |
| D 失败/临时 | 损坏输出、失败保存、scratch、拒绝候选的大型副本 | 先隔离，按精确清单永久删除 |

同一 UISNR compatibility tuple 的验证 BASIS 是共享权威资产，有限阵列不得各复制一份；manifest 通过哈希引用它。改变 body、材料、网格、频率、source support、模式截断或归一化时必须生成新的版本。

## 6. Agent 工作流

### 6.1 第 0 阶段：任务分类

开始前明确任务属于哪一类：

- 文档/源码审查；
- 新模型创建；
- 几何预检；
- 全波 EM 求解；
- TMD 电路优化；
- fixed-circuit 场计算；
- BASIS/UISNR；
- 后处理和报告；
- 故障诊断；
- 数据清理。

不把多个高风险阶段隐式捆绑。例如“优化线圈”不自动授权删除旧结果、修改源码、重启许可证服务或启动数小时正式任务。

### 6.2 第 1 阶段：只读盘点

Agent 必须先检查：

- `git status` 和现有用户修改；
- 输入、模型、配套 JSON 和结果是否存在；
- MATLAB、GCC、MEX 和工具箱版本；
- 磁盘、内存、CPU/GPU 和并行 worker 预算；
- 当前是否已有相关 MATLAB/TMD 进程；
- 关键函数实际路径。

MATLAB 路径检查：

~~~matlab
which co_simulation -all
which np_compute -all
which solver_wsvie -all
which solve_st -all
~~~

电子学目录存在重复实现。Agent 必须记录实际命中的路径，不得假设 genpath 顺序稳定。

### 6.3 第 2 阶段：静态输入检查

输入 JSON 保留当前 loader 需要的十个字段，即使未使用也写空字符串，不能写 null 或删除字段：

~~~text
B0, Nucleus, Basis_Functions_VIE, BodyFile, CoilFile,
WireFile, ShieldFile, SurfaceBasisSupportFile, TMD, BasisFile
~~~

检查：

- B0 单位 Tesla，Nucleus 是源码支持值；
- Basis_Functions_VIE 为当前实现支持的 PWC/PWL 编码；
- 相对路径从对应 data 根目录解析；
- Body MAT 顶层存在 RHBM；
- RHBM.r 最后一维为 3；
- epsilon_r、sigma_e 尺寸一致；
- idxS 是合法线性索引列向量；
- Wire/Coil MSH 与电路 JSON 同主名；
- 纯 Rx 的物理 port 标记为 Rx；
- CoilFile 和 WireFile 不重复表示同一实体；
- BasisFile 与 B0、体模、网格、basis 和支撑面兼容。

### 6.4 第 3 阶段：网格与映射检查

统一使用 m。常见 1000 倍错误必须显式检查。

WireFile：

- 使用当前解析器兼容的 Gmsh 2.2 ASCII；
- type 15 Point 顺序与 JSON elements 顺序一致；
- type 1 Line 连续且每个 Loop 闭合；
- 不同 Loop 不应意外共享节点；
- 物理通道数、端口数和 entity 映射一致。

CoilFile/带元件 ShieldFile：

- 导电面无退化、重复或错误法向；
- 元件 Line 是两张三角形的公共边；
- 不把普通外边界导出为元件 Line；
- 物理 Line 标签与 JSON elements 一一对应。

### 6.5 第 4 阶段：几何门禁

在任何矩阵装配前执行：

~~~matlab
MREDM = load_inputs('inp_<CaseTag>.json');
MREDM = geo_assembly(MREDM,1);
visualize_geometry(MREDM);
view(3); axis equal; rotate3d on;
~~~

必须人工或程序确认：

- phantom 尺寸、中心和方向；
- coil-body clearance；
- coil-shield clearance；
- 不存在穿透或意外接触；
- Loop 重叠和阵列旋转对称性；
- 通道编号与 channel_layout；
- 物理端口数；
- 自由度和体素数符合资源预算；
- 拉莫尔频率符合 B0/Nucleus。

几何错误不能由 TMD 修复。该门禁失败时停止。

### 6.6 第 5 阶段：粗基线

新拓扑按以下顺序扩大：

1. 粗体素、PWC；
2. 单通道；
3. 2 到 4 通道；
4. 完整通道粗网格；
5. 正式网格；
6. 最后加入屏蔽、高阶 basis 或更复杂去耦。

不得在最复杂设置上第一次验证端口、单位和拓扑。

### 6.7 第 6 阶段：完整网络与 TMD

对于需要多轮电路优化的阵列，使用：

~~~text
Stage A: geometry + assembly + solver -> raw YPn
Stage B: same raw YPn -> repeated TMD-only candidates
Stage C: accepted components + TMD=0 -> final fields/SNR
~~~

Stage A 缓存有效性由几何、体模、频率、basis、屏蔽和端口拓扑共同决定。禁止把最终 YPm/YP_s 当作下一轮原始 YPn。

optim.symmetry 必须按源码实际内部变量计数验证。只有几何、负载和预期元件值确实对称时才共享变量。双排阵列不得默认让不同排共享同一变量组。

### 6.8 第 7 阶段：最终固定电路

接受 TMD 后：

1. 冻结线圈 JSON 和哈希；
2. 输入设置 TMD=0；
3. 从兼容的 pre-TMD MREDM checkpoint 继续，或完整重算；
4. 重新运行 co_simulation 和场计算；
5. 只把该固定电路结果用于 B1-、噪声、SNR 和 SNR/UISNR。

TMD-only 结果不包含与最终电路一致的完整场；旧场不得与新电路网络拼接成正式结果。

### 6.9 第 8 阶段：后处理和归档

后处理脚本必须显式指定：

- solution 文件；
- BodyFile；
- BASIS 文件；
- ROI；
- 单位和归一化；
- 切片索引或空间坐标；
- 色条范围；
- Tx 数据来源。

导出至少包括 S 参数、频扫、逐通道 B1-、噪声相关矩阵、SNR、UISNR、SNR/UISNR、中心线和 summary MAT。原始 MAT 保持只读。

## 7. Runner 选择边界

| 任务 | 入口 | 不能得到 |
|---|---|---|
| 完整有限阵列 | MARIE_runner 或 case-specific RUN | 不自动得到独立 UISNR basis |
| UISNR/理想电流/MRGF basis | BASIS_runner | 不代表实际线圈 S 参数 |
| 复用 basis 的降阶线圈仿真 | MRGF_runner | 不是无需验证的精确替代 |
| 已有 YPn 的电路优化 | CO_SIMULATION_runner 或 TMD-only 脚本 | 不产生新的三维 E/H 场 |

BASIS_runner 和 MRGF_runner 的仓库默认输入未必随数据完整提供。Agent 必须先核对资产，不得把缺文件误诊为算法故障。

## 8. 权限规则

### 8.1 默认允许

- 只读文件、源码、日志和 MAT 元数据；
- 生成检查报告和文档；
- 在 Custom/新 CaseTag 下新增隔离输入、网格和脚本；
- 运行静态、几何和轻量非破坏性检查；
- 保存新名称的派生图和 summary；
- 提供服务器命令供用户执行。

### 8.2 需要明确授权

- 修改任何 `src/` 算法；
- 修改 installer、startup、编译选项或第三方库；
- 修改许可证、systemd、主机名、网络和系统包；
- 覆盖现役线圈 JSON、内置模型或 accepted 结果；
- 启动高内存、长时间或占用大量 worker/GPU 的正式计算；
- 改变科学定义、验收阈值、噪声模型或归一化；
- 恢复或覆盖 TMD 回写后的 JSON；
- 移动、删除、压缩或清理原始数据；
- 终止进程或重启服务器。

### 8.3 禁止动作

- `# Public snapshot: destructive cleanup command removed; use an exact reviewed manifest.`、`# Public snapshot: destructive cleanup command removed; use an exact reviewed manifest.`、`find data -delete`；
- 按进程名批量 kill；
- 为了通过测试降低门槛或删除失败证据；
- 用系统 libstdc++ 覆盖 MATLAB 自带库来规避 GLIBCXX；
- 把 Rx-only TXE 报告为 Tx/SAR；
- 把不同网格、频率或归一化的 SNR 与 UISNR 直接相除；
- 在同一活动 JSON 上并发运行 TMD；
- 在未确认同步状态时宣称 Windows 和 Linux 结果一致。

## 9. 操作安全与故障处理

### 9.1 中止顺序

1. MATLAB Command Window 或 batch 终端按一次 Ctrl+C；
2. 等待当前 MEX/parfor/GPU 调用到可中断点；
3. 必要时关闭当前 MATLAB 的并行池；
4. 新 SSH 终端确认用户、PID 和完整命令；
5. 对明确主 PID 依次使用 INT、TERM；
6. KILL 仅在前述步骤无效且获得授权后使用。

不得在 Storing Fields/save 阶段直接强杀，除非系统安全要求立即停止。

### 9.2 失败结果

- 先保留完整错误栈、最后成功阶段和 diary；
- 使用 `whos('-file',file)` 检查 MAT；
- 顶层缺少预期变量或文件不可读时标为 invalid；
- 移入 `data/_trash/<timestamp>` 隔离，不立即删除；
- TMD 失败时比较 active JSON 和 before_TMD 备份；
- 重新运行前确定错误属于输入、几何、MEX、资源、许可证、求解或后处理。

### 9.3 MEX 与 GPU

GLIBCXX 报错先核对 MATLAB 自带和系统 libstdc++ 版本，再用 MATLAB 支持的 GCC 全量重编译相关 MEX。不要先改仿真参数。

solver 和场计算存在宽泛 catch，可能把维度、字段或 MEX 错误误报为 GPU OOM。调试时保留第一次异常：

~~~matlab
dbstop if error
dbstop if caught error
~~~

完成后清除 caught error 断点。

## 10. 准确性核查

### 10.1 状态等级

Agent 使用以下状态，不得跳级：

| 状态 | 含义 |
|---|---|
| created | 文件已创建，未验证 |
| static-validated | 路径、schema、数量和映射通过 |
| geometry-validated | 三维几何、单位、间隙和端口通过 |
| em-solved | 数值求解结束，尚未证明网络合格 |
| tmd-candidate | 一轮电路优化完成，待验收 |
| circuit-accepted | 网络门槛通过，元件被冻结 |
| final-solved | 固定电路场与噪声已重算 |
| postprocessed | 图表和 summary 已生成 |
| research-validated | 独立核查、收敛和约定一致性通过 |

`Simulation completed successfully` 最多支持 em-solved 或 final-solved，不自动支持 research-validated。

### 10.2 数值完整性

检查：

- 所有输出数组无 NaN/Inf；
- 结果 MAT 可读且顶层变量正确；
- 物理端口维度符合设计；
- GMRES 每端口迭代和残差未异常；
- SP_s 互易性误差处于已验证容差；
- 噪声矩阵 Hermitian，特征值在数值容差内非负；
- CPU/GPU 或直接/pFFT 在小模型上有一致性证据；
- 网格、basis、积分或压缩容差有敏感性检查。

不得使用显式 `inv(Phi)` 作为默认科学后处理；优先 Cholesky、线性求解和有记录的特征值截断，并报告条件数、有效秩和阈值。

### 10.3 网络参数

纯 Rx 起始工程门槛：

- 全部 `SP_p < -15 dB`；
- `SPm_plot_Rx` 谐振偏移小于 0.5 MHz；
- 对称通道匹配离散小于 3 dB；
- 最差非对角 `SP_s < -12 dB`；
- 无源线性网络 `SP_s` 近似互易。

解释规则：

- `SP_p` 是前放加载后的 Rx 匹配；
- `SP_s` 对角不是纯 Rx 匹配的唯一判据；
- `SP_s` 非对角用于互耦；
- 双排阵列分别检查上排、下排、跨排对齐和跨排错位耦合；
- 阈值是本项目起始 gate，不是法规或通用硬件标准。

### 10.4 场、SNR 和噪声

检查：

- B1- 通道维等于物理 Rx 通道数；
- 场图与线圈空间位置和对称性相符；
- 单位从 T 到 microT 等转换有明确标注；
- Rx 噪声矩阵包含样品、导体和集总元件损耗；
- 噪声相关矩阵对角为 1 且无明显非物理值；
- ROI 在 phantom mask 内，未把背景零值纳入均值；
- 色条固定策略与跨方案比较一致。

### 10.5 UISNR 边界

实际阵列 SNR 和 UISNR 比较必须统一：

- B0、Nucleus 和频率；
- BodyFile、材料和空间位置；
- 体素网格、mask 和 ROI；
- PWC/PWL；
- 场相量、B1- 定义和复共轭约定；
- 时间平均、噪声 PSD、带宽和温度；
- 磁化强度和绝对缩放；
- source support、模式数和截断；
- 体素体积因子。

若 SNR/UISNR 大于 100%、UISNR 随模式数异常下降、噪声矩阵显著非 PSD，或结果对任意通道缩放敏感，停止发布并审查约定和数值白化。

表面支撑域得到的是该支撑面约束下的最优值；未证明源空间完备和收敛时，不应无条件称为绝对 UISNR。

### 10.6 Tx 与 SAR

正式 Tx 评估至少要求：

~~~matlab
isfield(solution.h_field,'Tx')
isfield(solution.h_field.Tx,'b1p')
isfield(solution.e_field,'Tx')
isfield(solution.e_field.Tx,'e_b')
~~~

还需说明驱动权重、接受/前向功率归一化、质量密度和 SAR 平均定义。Rx-only 互易回退 TXE 只能标为诊断性派生量。

## 11. 易错点清单

| 易错点 | 后果 | Agent 动作 |
|---|---|---|
| mm 当 m | 模型放大 1000 倍 | 几何边界和 axis equal 检查 |
| MSH/JSON 不同名或顺序错 | 端口错位、索引越界 | 一一核对 Point/Line 和 elements |
| 把 Point 数当物理端口数 | TMD 维度误判 | 数 type=port 和最终 SP_s |
| 所有对称通道共用变量 | 双排失配被强行约束 | 按物理对称和内部计数验证 |
| 改几何后复用旧 YPn | 电路优化基于错误网络 | 新版本重跑 Stage A |
| 把 YPm/YP_s 当原始 YPn | TMD 索引和物理错误 | 只加载 Stage A raw YPn |
| TMD 后复用旧场 | 网络与场不一致 | TMD=0 执行 Stage C |
| 只看 SP_s 对角判断 Rx | 错判匹配 | Rx 看 SP_p/频扫 |
| 只看 SP_p 判断去耦 | 漏掉互耦 | 看 SP_s 非对角和分块 |
| B0 改了、材料未更新 | phantom 不对应目标频率 | 核对 epsilon_r/sigma_e 来源 |
| PWL/细网格直接开跑 | 内存和时间失控 | PWC/粗网格分阶段 |
| broad catch 当 GPU OOM | 掩盖真实异常 | 保存首次错误堆栈 |
| addpath 路径遮蔽 | 混用两套电子学代码 | 记录 which -all |
| 只有图片没有输入快照 | 无法复现 | 归档 manifest、JSON、runner、MAT |
| 随机 PSO/rSVD 不记录 seed | 结果不可复现 | 固定或记录随机状态 |
| `'` 与 `.'` 混用 | 破坏互易/噪声矩阵 | 明确共轭转置语义 |

## 12. 高成本任务门禁

Agent 在启动正式服务器计算前必须向用户报告：

- 精确 CaseTag 和命令；
- 预计阶段及是否会写回 JSON；
- worker、CPU/GPU 和内存设置；
- 预计输出路径和覆盖风险；
- 是否已有可复用 YPn/BASIS/checkpoint；
- 当前磁盘可用空间；
- 中断和日志方案。

未获得授权时，可以完成脚本和预检查，但不启动高成本任务。

并行池 worker 数不能只按 CPU 核数设置，应按每 worker 内存和共享系统负载决定。禁止在共享服务器上默认占满全部资源。

## 13. Agent 交付格式

每次仿真相关交付至少包含：

1. **范围**：本次做了哪些阶段，哪些未做；
2. **资产**：创建/修改的文件及版本；
3. **环境**：Windows/Linux、MATLAB、编译器、关键函数路径；
4. **命令**：实际执行命令，而不是计划命令；
5. **状态**：使用第 10.1 节状态；
6. **指标**：端口数、频率、SP_p、最差 Sij、互易性、收敛和场完整性；
7. **警告**：路径遮蔽、fallback、随机性、材料和模型限制；
8. **复现**：输入、JSON 哈希、runner、日志和输出路径；
9. **遗留**：pending、out-of-scope 和需要用户决定的动作。

不得使用“已经验证”“安全”“最终”这类词，除非对应门禁确实通过并有证据。

## 14. 清理与收尾

默认只做只读清理预览。分类：

- 原始输入：保留；
- 原始 MAT/BASIS：正式 case 保留；
- 派生图片：确认可重建后可列为候选；
- 失败/损坏文件：先隔离；
- TMD before/after JSON：保留至案例关闭；
- checkpoint：确认最终结果和重算成本后再决定。

永久删除必须在用户看过候选清单后再次明确确认。清理后重新检查引用、结果完整性和工作区状态。

## 15. 最小 Agent 检查表

### 修改前

- [ ] 已读 AGENTS.md 和相关专项文档。
- [ ] 已检查 git status，未覆盖用户改动。
- [ ] 已明确 Windows/Linux 边界和同步状态。
- [ ] 已建立唯一 CaseTag 和输出路径。

### 求解前

- [ ] JSON 十字段、模型路径和 RHBM 结构通过。
- [ ] MSH/电路 JSON 同名、顺序和端口一致。
- [ ] 单位、几何间隙、端口数和频率通过。
- [ ] 已完成 geometry-only 门禁。
- [ ] 已评估资源、日志、TMD 写回和覆盖风险。

### 结果后

- [ ] MAT 可读、字段和维度正确、无 NaN/Inf。
- [ ] GMRES、互易性、噪声矩阵和网络门槛已检查。
- [ ] 最终场对应 fixed circuit，而不是旧 TMD 场。
- [ ] SNR/UISNR 和 Tx 指标满足约定边界。
- [ ] 已归档输入快照、JSON、runner、manifest、日志和图。
- [ ] 未验证项已明确标注，没有把 numerical completion 当作 research validation。
