# MARIE 3.0 src 源码模块与算法详解

> 适用范围：当前本地 marie-tools 仓库。本文依据 src 目录的实际源码、runner 调用链和目录统计整理，不把仓库外的预期功能当成已实现功能。
>
> 目标：回答“每个模块负责什么、为什么存在、谁调用它、输入输出是什么、修改时应去哪里”。对于 TT/QTT、Gmsh、NIfTI 等随仓库分发的第三方子树，按功能类别完整说明，不逐项抄录数百个通用函数。

## 1. 总体定位

src 是 MARIE 3.0 的算法实现层。它把 JSON 和 data 中的模型文件转换为统一的 MREDM 数据结构，依次完成：

1. 输入解析和物理常数初始化；
2. 体模、线圈、导线、屏蔽和基函数几何构建；
3. WIE、SIE、VIE 以及各种耦合积分方程算子装配；
4. 端口激励、预条件和迭代求解；
5. 调谐、匹配、去耦和前放去耦联合仿真；
6. 电磁场、网络参数、SNR 和发射效率计算；
7. 结果保存和可视化。

标准完整仿真的主链如下：

~~~mermaid
flowchart TD
    A["MARIE_runner"] --> B["load_inputs / parse_inputs"]
    B --> C["geo_assembly"]
    C --> D["wsvie_assembly"]
    D --> E["solver_wsvie"]
    E --> F["co_simulation"]
    F --> G["em_ehfield_wsvie"]
    G --> H["em_SNR / em_TXE"]
    H --> I["data/solutions/*.mat"]
~~~

## 2. 源码规模与目录地图

本次统计的 src 共有 1,417 个文件。一级目录如下。

| 一级目录 | 文件数 | 主要语言/格式 | 职责 |
|---|---:|---|---|
| src_geometry | 94 | MATLAB、Gmsh .geo | 几何读取、网格预处理、基函数和端口构建 |
| src_integral_equations | 302 | MATLAB、C++、MEX | WIE/SIE/VIE 及耦合算子装配 |
| src_mathematics | 685 | MATLAB、HTML、MEX | ACA、SVD、Tucker、TT/QTT、数值积分 |
| src_physics | 207 | MATLAB | 电磁场、网络参数、联合电路仿真、性能指标 |
| src_runners | 4 | MATLAB | 用户级工作流入口 |
| src_solver | 59 | MATLAB | RHS、预条件、矩阵向量乘和迭代求解 |
| src_utils | 56 | MATLAB、NIfTI 工具 | 输入解析、数据转换、CloudMR/NIfTI 接口 |
| src_visualizer | 9 | MATLAB | 几何、电流、网络参数和理想模式可视化 |

文件类型中约有 814 个 .m、128 个 .cpp、64 个 .mexa64、14 个 .h、36 个 .geo 和 238 个 TT/QTT HTML 文档。文件数量不能直接代表 MARIE 主算法的复杂度：685 个数学文件中有 669 个属于通用 TT/QTT 工具箱，94 个几何文件中有 72 个属于随仓库分发的 Gmsh 程序和文档。

## 3. MREDM：贯穿全流程的数据总线

MARIE 没有让每个阶段独立传递大量参数，而是持续扩充结构体 MREDM。理解它比记住单个函数更重要。

| 字段类别 | 典型内容 | 生成阶段 | 消费阶段 |
|---|---|---|---|
| inputs | JSON 文件路径、coil/body/wire/shield 配置、basis、求解选项 | load_inputs | 全流程 |
| emc | 频率、角频率、波数、介质和 MRI 物理常数 | em_constants 等 | 装配、场、指标 |
| dimensions | 体模网格尺寸、间距、坐标、mask 和索引 | geo_body_domain | VIE、pFFT、场计算 |
| WIE | 导线节点、线段、端口、基函数和电阻信息 | geo_wcoil | WIE、WVIE、求解器 |
| SIE | 表面三角形、RWG 基、端口和集总元件 | geo_scoil / geo_shield | SIE、SVIE、求解器 |
| EP | 体模介电参数、导电率及对比度信息 | body/load + em_assembly | VIE、损耗和 SNR |
| operators | 自作用和互耦算子、低秩分解、pFFT/TT 数据 | 各 assembly | solver、field |
| solver | RHS、电流解、收敛信息、端口响应 | solver_wsvie | 网络参数、场、保存 |
| functions | 按模型和 basis 选择的函数句柄 | parse_inputs | 求解和场计算 |
| fields | 网络参数、E/H/B1、SNR、TXE、损耗矩阵 | 联合仿真和场阶段 | 保存、后处理 |

数据生命周期的关键点：

- runner 开始时 MREDM 主要是输入配置；
- geo_assembly 后才具备可求解的离散几何；
- wsvie_assembly 后 operators 往往占用大量内存；
- solver_wsvie 后得到端口对应的电流列；
- co_simulation 会改变端口等效网络和场的线性组合关系；
- em_ehfield_wsvie 后才形成最终保存所需的 solution 字段。

因此，不应把仿真中途的 MREDM 与最终 MAT 文件里的 solution 当作同一种结构。

## 4. src_runners：四种工作流入口

### 4.1 MARIE_runner.m

用途：执行完整线圈、体模和电路联合仿真，是日常最常用入口。

主步骤：

~~~matlab
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);
MREDM = wsvie_assembly(MREDM, 1);
MREDM = solver_wsvie(MREDM);
MREDM = co_simulation(MREDM);
MREDM = em_ehfield_wsvie(MREDM);
save(result_file, 'solution', '-v7.3');
~~~

geo_flag=1 表示完整几何。输出是 data/solutions 下的 solution 结构，一般包含网络参数、电流、接收场、发射场派生量和 SNR。

### 4.2 BASIS_runner.m

用途：生成并保存理想电流/UISNR 所需的基函数响应，而不是完成普通线圈仿真。

- geo_flag=2：表面基函数路线；
- geo_flag=3：偶极子/ultimate basis 路线；
- 调用 VIE basis 求解器，保存到 data/bases；
- 输出 BASIS 通常包含基函数场、压缩矩阵及后续 MRGF/UISNR 使用的数据。

这一步通常比加载一个已存在的 basis 文件昂贵。不要在每个普通线圈方案中重复生成同一体模、频率和离散设置的 basis。

### 4.3 MRGF_runner.m

用途：使用预生成基函数做降阶/快速场求解。MRGF 可理解为以预计算响应空间替代部分全尺寸体电流求解。

前置条件：

- BASIS_runner 已成功产生兼容的 basis 文件；
- 体模、频率、体素网格、basis 类型和阶数必须匹配；
- basis 文件中应存在 Ue、Ub、U_hat_inv 等 runner 读取的数据。

流程仍包含输入、几何、线圈装配、降阶耦合、求解、联合仿真和场恢复，但体模相关计算通过压缩基表示完成。

### 4.4 CO_SIMULATION_runner.m

用途：已有线圈端口网络矩阵时，只做调谐/匹配/去耦等电路联合仿真，不重新构建完整几何和电磁场。

输入重点是频率相关或单频 Y/Z/S 参数和 Coil JSON 中的 TMD 配置。输出包括优化后的网络参数、元件值、频扫曲线以及电路损耗信息。它不能独立产生新的体内 E/H 场。

## 5. src_utils：输入、路由和数据转换

### 5.1 src_loaders

核心函数：

- load_inputs.m：读取 JSON，加载 data 内引用文件，初始化 MREDM；
- parse_inputs.m：根据 PWC/PWL、Wire/Coil/Shield 组合、pFFT 和 MRGF 设置选择求解与场函数句柄；
- interpolate_PWL.m：处理 PWL 体基上的数据插值；
- update_RHBM.m：更新/规范化体模数据结构。

parse_inputs 是“为什么同一个 runner 会进入不同算法文件”的关键。例如：

- 只有表面线圈和体模时选择 SVIE；
- 只有导线线圈和体模时选择 WVIE；
- 导线、表面线圈和体模组合时选择 WSVIE；
- 含 shield 且启用 pFFT 时，常会选择带 TT 的屏蔽耦合变体；
- PWC 与 PWL 会切换 VIE 算子和场计算实现。

### 5.2 CloudMR 与 NIfTI_20140122

CloudMR 子树用于把 MARIE 数据转换为 CloudMR/医学成像生态可读格式。NIfTI_20140122 是随仓库分发的第三方 NIfTI 读写工具，包含 nii 头、数据、坐标和压缩文件处理。

这些文件不是标准 MARIE_runner 的核心求解器。仅在导入/导出 NIfTI 或调用 to_CloudMR 时参与。

### 5.3 src_transformers

- to_GPU.m：按 gpu_flag 把数组转移到 GPU 或保留在 CPU；
- line_to_cartesian_currents.m：把导线基函数系数转换为笛卡尔电流；
- surface_to_cartesian_currents.m：把 RWG 系数转换为表面笛卡尔电流；
- hh_mm_ss.m：把计算时间格式化为时分秒。

## 6. src_geometry：从模型文件到离散未知量

### 6.1 geo_assembly.m 总调度

geo_assembly 根据 geo_flag 和输入中是否存在 Body、Wire、Coil、Shield 来组织几何。其职责不是画图，而是生成积分方程所需的离散自由度、端口和域索引。

### 6.2 body_geometry

主要功能：

- geo_body_domain.m：读取 RHBM/体素体模，构造 x、y、z 网格、分辨率、mask 和活动体素索引；
- geo_recompute_domain.m：模型变换或裁剪后重算计算域；
- get_ROIs.m：提取感兴趣区域；
- grid3d.m：生成规则三维网格。

体模在 VIE 中不是表面三角网格，而是带复介电参数的体素集合。BodyFile 决定材料分布，JSON 中的 body 设置决定位置、旋转、裁剪和 basis 离散方式。

### 6.3 scoil_geometry

这是线圈、导线和屏蔽几何的主要预处理区。

| 子模块 | 功能 |
|---|---|
| mesh_geo | 解析和整理节点、三角形/线段、区域标签 |
| triangle_geo | 三角面方向、面积、邻接关系等基础量 |
| rwg_geo | 从共享边构造 RWG 表面基函数 |
| ports_geo | 将端口和集总元件映射到网格自由度 |
| geo_scoil.m | 构建表面线圈 SIE 几何 |
| geo_wcoil.m | 构建细导线 WIE 几何 |
| geo_shield.m | 构建屏蔽表面几何 |
| geo_scoil_lumped_elements.m | 解析调谐、匹配、去耦等元件位置 |

表面导体使用三角面和 RWG 基函数，细导线使用线段/节点基函数。两者物理上都表示导体电流，但离散空间和积分核不同，不能只通过改扩展名互换。

### 6.4 basis_geometry

- geo_assembly_surface_basis.m：构造表面理想电流基；
- geo_assembly_ultimate_basis.m：构造 ultimate/偶极子支持；
- geo_spherical_basis.m：球谐/球形相关基；
- geo_ultimate_basis.m：理想源基定义；
- geo_dipole_supports：偶极子位置、方向和支持域。

该目录主要服务 BASIS_runner 和 UISNR/MRGF，不是普通 coilFile 的生成器。

### 6.5 GMSH 子树

scoil_geometry/GMSH 内含 Gmsh 可执行文件、.geo 示例、手册、tutorial 和演示。MARIE 借助它生成或处理表面网格，但其中的大量示例并不属于 MARIE 算法。更换 Gmsh 版本时必须核验 .msh 格式兼容性，尤其是旧解析器对 Gmsh 2.x 文本格式的假设。

## 7. src_integral_equations：电磁离散核心

### 7.1 方程族与命名

| 缩写 | 离散对象 | 主要未知量 | 典型用途 |
|---|---|---|---|
| WIE | 细导线 | 线电流 | wireFile 导线线圈 |
| SIE | 导体表面 | RWG 表面电流 | coilFile、shieldFile |
| VIE | 有损介质体素 | 体极化电流 | BodyFile |
| WVIE | 导线 + 体模 | 线/体耦合电流 | wire coil 加体模 |
| SVIE | 表面 + 体模 | 面/体耦合电流 | surface coil 加体模 |
| WSIE | 导线 + 表面 | 线/面耦合电流 | wire 与 coil/shield 耦合 |
| WSVIE | 导线 + 表面 + 体模 | 全耦合未知量 | 通用完整系统 |

离散后的系统可概念性写成：

~~~text
[ Zss  Zsw  Zsc  Zsb ] [ Is ]   [ Vs ]
[ Zws  Zww  Zwc  Zwb ] [ Iw ] = [ Vw ]
[ Zcs  Zcw  Zcc  Zcb ] [ Ic ]   [ Vc ]
[ Zbs  Zbw  Zbc  Zbb ] [ Jb ]   [  0 ]
~~~

其中 s、w、c、b 分别代表 shield、wire、surface coil 和 body。实际代码会按存在的模型删减区块，并常以 FFT、ACA、Tucker 或 TT 的隐式算子代替显式稠密矩阵。

### 7.2 wsvie_assembly.m 总装配

完整流程按以下顺序调用：

1. wie_assembly：导线自阻抗和损耗；
2. sie_assembly：线圈表面自阻抗；
3. shield_sie_assembly：屏蔽自阻抗；
4. vie_assembly：体模 N/K 卷积算子；
5. wsvie_coupling_assembly：线、面、屏蔽和体之间的互耦。

geo_flag 控制是否为普通全模型、basis 或 MRGF 路径。

### 7.3 src_wie

实现细导线积分方程：

- 建立导线段之间的 Green 函数作用；
- 加入导体有限电导损耗；
- 组装端口/集总元件激励；
- 形成后续 WVIE/WSVIE 所需的导线自作用块。

适合几何半径远小于波长和曲率尺度的细线模型。粗带状线圈更适合表面网格 SIE。

### 7.4 src_sie

实现 RWG 表面积分方程：

- C++ Assembly 计算三角形对的积分；
- self、edge、vertex、near 和 far 情况采用不同奇异/近奇异处理；
- src_operators_shield_sie 提供屏蔽表面的专用装配；
- 端口、铜损耗和集总元件形成附加矩阵项。

Cpp_Assembly/bin 中的 .mexa64 是 Linux MATLAB 可加载的 MEX 二进制；include/src 是其 C++ 源码。

### 7.5 src_vie

VIE 是体模电磁响应的核心。

- em_assembly 构造介质对比度；
- assembly_N 和 assembly_K 构造 dyadic Green 算子分量；
- PWC 每个体素通常对应 3 个笛卡尔分量；
- PWL 引入线性空间变化，未知量和耦合分量更多；
- 卷积结构允许使用 FFT，而不存储完整体素对稠密矩阵；
- singular 和 cubatures 处理同体素及近邻体素积分；
- Cpp_Assembly 中 solve_st 等 MEX 加速奇异积分。

PWC 较省内存，适合先建立可运行方案；PWL 精度潜力更高，但装配和求解代价显著增加。

### 7.6 src_wvie、src_svie、src_wsie

这些目录负责不同离散空间之间的互耦：

- WVIE：导线测试/基函数与体素极化电流之间的作用；
- SVIE：RWG 表面电流与体素之间的作用；
- WSIE：线段与三角表面之间的作用。

它们通常既提供直接/低秩装配，也提供 pFFT 或 C++ 加速版本。互易性常用于从一个方向的耦合构造转置/共轭方向，但必须遵循代码中的基函数排序和归一化。

### 7.7 src_wsvie/src_pfft

pFFT 的思想是：

1. 把非规则线/面基函数投影到规则辅助网格；
2. 在规则网格上用 FFT 快速应用 Green 卷积；
3. 插值回原始自由度；
4. 对近场项做直接校正，避免网格近似破坏精度。

子目录职责：

- src_pfft_coil：线圈到辅助网格的投影/插值；
- src_pfft_supporting：网格、核和辅助函数；
- src_svie_pfft：表面-体 pFFT；
- src_wvie_pfft：导线-体 pFFT；
- src_wsvie_pfft：完整系统的 pFFT 组合。

pFFT 主要降低大规模耦合矩阵的内存和矩阵向量乘成本。启用后，operators 内保存的是投影矩阵、FFT 核和近场校正，而不是单个完整 Z 矩阵。

### 7.8 src_wsvie/src_tt

该目录把屏蔽/体模或其他规则高维耦合表示为 TT 张量。K_components 和 N_components 分别组织两类 Green 算子在 x/y/z 及 PWL 分量上的作用。

TT 适合可分离、可压缩的高维规则数据；其精度与秩截断容差相关。内存不足时不能只盲目降低 TT 容差，因为这也会改变场和网络结果。

### 7.9 src_basis

为 BASIS_runner 和降阶求解准备体模基响应，负责将理想源基映射到 VIE 求解及压缩表示。它与普通线圈端口激励不同：前者构造一个可重用的响应空间，后者求有限端口的实际电流。

## 8. src_solver：隐式大系统求解

### 8.1 solver_wsvie.m

顶层求解器完成：

1. rhs_assembly 生成所有端口激励列；
2. prec_wsvie 建立预条件器；
3. 调用 parse_inputs 选定的 IE solver；
4. 按端口求解电流；
5. np_compute 由端口电压、电流得到 Y/Z/S 参数。

代码先尝试较多 GPU 运算，失败后降低 GPU 使用，再失败则转 CPU。该回退能处理部分显存问题，但当前 catch 没有检查异常类型，非显存错误也可能被显示为 Out of GPU memory。诊断时应查看第一次异常栈，而不能只依据警告文字。

### 8.2 src_rhs

rhs_assembly 按统一自由度顺序拼接激励。体模没有外加端口，因此 body 块通常为零；线圈、导线和屏蔽端口则产生相应电压激励列。

端口顺序必须与几何模块、网络参数矩阵和联合仿真中的端口映射一致。端口数不对时，优先检查这里的 RHS 列数和 SIE/WIE port 结构。

### 8.3 src_preconditioners

- prec_wsvie.m：按当前模型组合拼接预条件结构；
- prec_LU.m：对导体/端口相关块做 LU 型预条件；
- prec_vie.m：对 VIE 体块做近似逆或对角型预条件。

预条件器不改变理论方程，但显著影响 GMRES 迭代次数。端口迭代长期达到上限时，应检查预条件、材料对比、网格和调谐网络，而非只提高最大迭代次数。

### 8.4 src_ie_solver

按模型分为：

- ie_solver_svie：表面线圈/体模；
- ie_solver_wvie：导线/体模；
- ie_solver_wsvie：导线、表面、屏蔽、体模的通用组合；
- ie_solver_vie：纯体模或 basis 响应。

每组中又有普通、shield、pFFT、pFFT+TT、MRGF 等变体。它们的差别主要在矩阵向量乘函数和 operators 表示，不是不同的用户输入格式。

### 8.5 src_mvp

MVP 即 matrix-vector product。GMRES 不需要显式得到整个大矩阵，只需要反复计算 y=A*x。

- mvp_vie/mvp_G、mvp_N、mvp_K：FFT 形式体积分算子；
- mvp_svie：表面-体耦合；
- mvp_coupling：ACA/Tucker/TT 低秩耦合；
- mvp_wsvie：按块组合所有自作用和互耦。

这是排查“迭代中维度不匹配、GPU 类型不一致、TT rank 异常”的主要目录。

### 8.6 src_iterative_solvers

包含定制 GMRES 和 MATLAB 迭代接口辅助函数。标准端口求解常见设置为相对容差约 1e-5、restart 约 50、最大迭代约 200，具体以实际 solver 文件为准。

保存的 Iterations 和残差应作为收敛质量证据。仿真打印 completed 并不自动证明离散误差和物理模型已经收敛。

## 9. src_physics：场、网络、电路和 MRI 指标

### 9.1 src_electromagnetism

核心职责：

- em_constants.m：由静磁场 B0、核种等计算拉莫尔频率、波数和基础常数；
- em_assembly.m：形成体模介质对比和材料算子；
- em_ehfield_wsvie.m：顶层 E/H 场恢复，随后调用性能指标；
- em_efield：SVIE、WVIE、WSVIE、VIE 的 E 场实现；
- em_hfield：对应的 H 场和 B1 场实现；
- pFFT、TT、shield、MRGF 后缀表示不同算子表示路线。

场恢复本质上是把已求得的导体/体电流重新作用到观察体素。它仍可能是高成本步骤，并非“求解完成后免费得到”。

### 9.2 src_electronics/src_network_parameters

np_compute 从端口激励和电流推导 Y 参数，再通过变换函数得到 Z、S 或 ABCD 参数。src_network_parameter_transforms 包含：

- Y 与 Z 互换；
- Z/Y 与 S 互换；
- S 与 ABCD 互换；
- 参考阻抗归一化。

网络参数反映端口级行为。S11 很好并不能单独证明接收场均匀、SNR 高或体模模型正确。

### 9.3 src_electronics/co_simulation

该模块把全波求得的裸线圈端口网络与集总元件、电缆/前放条件结合。

| 子目录 | 功能 |
|---|---|
| co_sim_settings | 解析 Tx/Rx 标签、优化变量、Q 值、对称和共享元件映射 |
| co_sim_options | 粒子群等优化器参数 |
| co_sim_cost_functions | 调谐、匹配、去耦、前放去耦和损耗感知目标函数 |
| co_sim_calibration | 优化后校准元件值和端口响应 |
| co_sim_runners | M、T、D、PD、DT 等阶段组合 |
| co_sim_master_files | Rx、Tx、TxRx 及混合模式总流程 |
| co_sim_freq_sweep | 扫频计算 ZPm/SPm 和谐振曲线 |

缩写含义：

- T：tuning，调谐到目标频率；
- M：matching，匹配到参考阻抗；
- D：decoupling，端口/通道去耦；
- PD：preamplifier decoupling，前置放大器去耦；
- DT：detuning，非工作状态失谐。

co_simulation 最终输出调谐匹配后的网络矩阵、元件值、损耗矩阵和把裸端口场组合成实际 Tx/Rx 通道场的变换关系。

### 9.4 src_performance_metrics

#### em_SNR.m

使用接收 B1-、体损耗噪声、导体损耗和集总元件损耗形成噪声协方差，并计算最优通道合并的 SNR。它依赖正确的 Rx 场和噪声矩阵，不能用单通道 abs(B1-) 直接替代。

#### em_TXE.m

计算在损耗约束下的最大或组合发射效率。若没有正式 Tx 通道，当前代码可能依据互易性使用 Rx 场形成一个发射式派生量。这可用于数学诊断，但 Rx-only 项目的该结果不应被表述为经过 Tx 驱动、功率归一化和 SAR 验证的正式发射结论。

#### em_g_factor.m

利用多通道灵敏度和噪声协方差评估并行成像几何因子。需要正确的通道维、加速方向和采样别名关系。

## 10. src_mathematics：数值基础设施

### 10.1 ACA

src_ACA/aca.m 实现 Adaptive Cross Approximation。它通过少量矩阵行列抽样构造 U*V' 低秩近似，避免显式形成大互耦矩阵。常用于线-面、线-屏蔽和面-屏蔽远程耦合。

### 10.2 SVD、逆和 Tucker

- src_SVD/compress_SVD.m：奇异值截断和低秩压缩；
- src_inverse/fast_pinv.m：快速/截断伪逆；
- src_tucker/hosvd.m：高阶 SVD；
- hosvd_to_full.m：从 Tucker 因子恢复张量；
- nmp.m：张量模乘等辅助运算。

Tucker 适合压缩具有三维网格结构的耦合核。压缩容差决定速度、内存和精度的平衡。

### 10.3 TT_QTT

该子树约 669 个文件，是通用 Tensor Train / Quantized Tensor Train 工具箱，而不是 669 个 MARIE 专用物理模块。

主要类别：

- @tt_tensor、@tt_matrix、@qtt_tucker：MATLAB 类和运算符重载；
- core：TT core 操作、正交化、舍入、秩处理；
- cross：TT-cross/交叉逼近；
- solve：AMEn、DMRG、TT-GMRES 等张量求解；
- fmex：平台相关加速 MEX；
- examples、tests、exp：第三方示例和测试；
- doc/tt2：自动生成的 HTML 帮助文档；
- misc、tt_regression：辅助算法和回归工具。

MARIE 主要把它作为大规模规则耦合算子的压缩和应用引擎。删除 examples 看似不影响标准仿真，但不建议随意裁剪第三方子树，因为类方法、动态路径和 fmex 依赖不容易由文件名判断。

### 10.4 src_quads

包含：

- 一维 Gauss 积分；
- 三角形 Dunavant 积分；
- SIE 面积分节点；
- 球面积分的 Lebedev 节点等。

它们服务于 Green 函数积分、奇异项校正和球形基函数。提高积分阶数能降低积分误差，但不能修复错误网格、错误单位或错误材料参数。

## 11. src_visualizer：内置结果显示

| 函数 | 输入 | 效果 |
|---|---|---|
| visualize_geometry | MREDM | 显示线圈、导线、屏蔽和体模几何；体模先提取六邻域外壳，再调用三维boundary，避免高分辨率全体素Qhull崩溃 |
| visualize_coil_currents | MREDM、端口 | 在线圈网格上显示复电流派生量 |
| visualize_ideal_current_patterns | BASIS/相关结构 | 显示理想电流模式 |
| visualize_s_parameters | S 矩阵 | dB(S) 热图 |
| visualize_z_parameters | Z 矩阵 | 实部/虚部热图 |
| visualize_ZPm_SPm_freq_sweep | 扫频结果 | 阻抗和 S 参数随频率曲线 |
| lipari、navia | 数值数组 | 专用 colormap |
| set_black_theme | 图窗/坐标轴 | 黑色主题样式 |

visualizer 只负责已有数据的呈现，不会替代场计算。具体调用和已知限制见 MARIE_可视化脚本使用指南.md。

## 12. 加速机制如何组合

| 技术 | 压缩/加速对象 | 优点 | 主要风险 |
|---|---|---|---|
| MEX/C++ | 奇异积分、三角/体素耦合 | 大幅降低装配时间 | MATLAB/GCC/libstdc++ ABI 不兼容 |
| FFT | 规则体素卷积 | O(N log N) 形式应用 | 需要规则域和正确 padding |
| pFFT | 非规则导体与规则网格耦合 | 不形成完整稠密矩阵 | 近场校正和网格设置影响精度 |
| ACA | 远程互耦低秩矩阵 | 内存低、实现直接 | 几何近距离时 rank 可能升高 |
| Tucker/HOSVD | 三维耦合张量 | 利用多维可分结构 | 截断容差影响结果 |
| TT/QTT | 高维规则算子 | 极强压缩潜力 | rank、容差和第三方接口较复杂 |
| GPU | MVP、FFT、向量运算 | 缩短迭代和场恢复时间 | 显存、数据转移、异常误分类 |
| MRGF | 体模响应空间 | 多方案复用、降阶求解 | basis 兼容性要求严格 |

这些技术不是互斥的。例如含屏蔽的 WSVIE 可以同时使用 pFFT 处理线圈-体模耦合、TT 处理屏蔽-体模耦合、ACA 处理导体之间的远程耦合，并在 GPU 上执行 MVP。

## 13. 从文件类型判断用途

| 类型 | 含义 | 是否可直接编辑 |
|---|---|---|
| .m | MATLAB 算法、runner、类方法 | 可以，但应保留备份和测试 |
| .cpp/.h/.c | MEX 或第三方加速源码 | 修改后必须重新编译 |
| .mexa64 | Linux 64 位 MATLAB MEX | 不可文本编辑；与 ABI/版本相关 |
| .geo | Gmsh 几何脚本/示例 | 可编辑，但需重新网格化 |
| .html/.pdf | TT/Gmsh 文档 | 不参与求解 |
| .png/.pos | 第三方示例资产/后处理示例 | 通常不参与 MARIE runner |

installer.m 会编译 src 中需要的 C++。出现 GLIBCXX_x.y.z not found 时，根因通常是编译所用 libstdc++ 新于 MATLAB 自带运行库，应使用 MATLAB 支持的 GCC 重新编译，而不是仅复制 MEX 文件。

## 14. 按研究任务定位修改位置

| 目标 | 首先查看 | 通常不应先改 |
|---|---|---|
| 新增 coil/wire/shield 几何 | data 模型、src_geometry | GMRES 内核 |
| 新增 BodyFile/材料 | data/bodies、body loaders、em_assembly | co_sim cost function |
| 修改端口和元件 | ports_geo、Coil JSON、co_sim_settings | VIE Green 核 |
| 改调谐/匹配目标 | co_sim_cost_functions、co_sim_options | geometry |
| 新增求解算法 | src_ie_solver、src_mvp、preconditioners | visualizer |
| 改 SNR 噪声模型 | em_SNR、损耗矩阵生成 | S 参数变换 |
| 改 UISNR/basis | BASIS_runner、src_basis、basis_geometry | 普通 MARIE_runner |
| 改场可视化 | src_visualizer 或独立后处理脚本 | em_efield/em_hfield |
| 修复 MEX 兼容 | installer、Cpp_Assembly、mex -setup | JSON 输入 |

建议遵循“模型文件 → 几何检查 → 装配检查 → 小规模求解 → 场与指标”的修改顺序。不要同时改变网格、材料、端口、求解器和后处理，否则无法定位结果变化来源。

## 15. 已知源码风险与维护注意事项

以下结论来自当前本地源码检查，不代表所有上游版本均相同。

### 15.1 电子学模块存在重复目录

src_physics/src_electronics 下同时存在：

~~~text
src_electronics/co_simulation
src_electronics/src_electronics/co_simulation
~~~

网络参数目录也重复。两棵树中大部分文件相同，但部分 co_simulation、cost function、runner 和设置文件内容不同。startup.m 使用 addpath(genpath('./')) 时，MATLAB 路径顺序可能决定实际调用哪一份。

每次修改电子学代码前运行：

~~~matlab
which co_simulation -all
which np_compute -all
which runner_M_T_PD -all
~~~

不要在未比较差异前删除其中一棵目录。

### 15.2 GPU 回退可能掩盖原始错误

solver_wsvie.m 和 em_ehfield_wsvie.m 使用宽泛 catch 后直接报告显存不足。维度错误、未定义字段、MEX 崩溃或其他运行时异常也可能进入同一分支。

调试时可先强制 CPU，或临时改为 catch ME 后执行：

~~~matlab
disp(getReport(ME, 'extended'))
~~~

保留原始堆栈后再判断是否真是 GPU OOM。

### 15.3 特定 Wire/Shield 耦合分支需验证

当前 wsvie_coupling_assembly.m 的部分 Wire+Shield 及 Wire+Coil+Shield 分支给 Zsw.U/Zsw.V 赋值时引用 U、V，但附近未见对应局部装配返回值。若启用这些组合，可能出现未定义变量或错误沿用的问题。

这不影响已经成功运行的纯 surface coil + body 算例，但在筹划 wireFile 与 shieldFile 组合前应做最小模型单元测试，并检查 Zsw 的尺寸和互易关系。

### 15.4 Rx-only 下的 TXE 需要谨慎命名

em_TXE.m 在没有 Tx 场时可使用 Rx 场的互易性回退，并选择另一标签的 lumped loss 矩阵。该输出可用于数学比较，但不等于正式 Tx 模式下经过驱动、功率和 SAR 定义验证的发射效率。

### 15.5 预编译 MEX 是平台相关产物

.mexa64 只面向 Linux 64 位 MATLAB，且依赖编译器 ABI。MATLAB 升级、GCC 升级、Linux 升级或复制到新服务器后，应重新执行兼容编译和最小测试。


### 15.6 TMD 局部搜索不得越过声明硬边界

自 2026-08-14 起，`optim.minim/maxim` 是 TMD 元件值的持久硬边界。单通道调谐、匹配以及阵列去耦生成的 0.8–1.2 或 0.95–1.05 局部搜索区间，必须与声明硬边界取交集；交集为空时以 `MARIE:TMD:EmptyHardBoundIntersection` 失败，不能回退到越界区间。

`geo_scoil_print_lumped_elements` 在打开输出 JSON 前检查所有待回写值的有限性和硬边界。越界时以 `MARIE:TMD:HardBoundViolation` fail closed，活动 JSON 保持不变。需要扩展参数域时应派生新的版本化 JSON、记录物理依据并重新运行 TMD，不得静默裁剪或修改已验证资产。

## 16. 调试与源码追踪命令

### 16.1 查看真实调用文件

~~~matlab
which MARIE_runner -all
which co_simulation -all
which solver_wsvie -all
which solve_st -all
~~~

### 16.2 查看当前函数调用关系

~~~matlab
dbstop if error
dbstop if caught error
MARIE_runner
dbstack
~~~

注意：dbstop if caught error 会在 GPU 回退捕获点停下，适合识别被误报的原始异常；完成后用 dbclear if caught error 取消。

### 16.3 检查 MREDM 阶段状态

~~~matlab
fieldnames(MREDM)
whos MREDM
fieldnames(MREDM.operators)
fieldnames(MREDM.fields)
~~~

大型 MREDM 不建议反复 save 为默认 MAT 格式；确需保存调试快照时用 -v7.3，并确认磁盘空间。

### 16.4 检查求解收敛

~~~matlab
% 字段名以当前 solver 输出为准
fieldnames(MREDM.solver)
size(MREDM.solver.Jcb)
any(~isfinite(MREDM.solver.Jcb(:)))
~~~

同时记录每端口迭代数、残差、耗时和是否发生 GPU/CPU 回退。

## 17. 推荐阅读顺序

第一次读源码建议按以下顺序，而不是从 TT_QTT 开始：

1. src_runners/MARIE_runner.m；
2. src_utils/src_loaders/load_inputs.m 和 parse_inputs.m；
3. src_geometry/geo_assembly.m；
4. src_integral_equations/wsvie_assembly.m；
5. src_solver/src_ie_solver/solver_wsvie.m；
6. 当前模型对应的 ie_solver 和 mvp 文件；
7. src_physics/src_electronics/co_simulation/co_simulation.m；
8. src_physics/src_electromagnetism/em_ehfield_wsvie.m；
9. em_SNR.m、em_TXE.m 和 visualizer；
10. 最后再追 pFFT、TT、ACA 和 C++ 实现细节。

## 18. 与其他文档的关系

- MARIE_使用指南_Codex经验.md：安装、启动、运行、结果回看和应急处理；
- MARIE_Runner算法与使用指南.md：四种 runner 的专项讲解；
- MARIE_data文件夹内容与仿真作用详解.md：模型和输入数据资产；
- MARIE_JSON文件配置指南.md：JSON 参数和可选项；
- MARIE_模型设计与组合教程.md：coil/wire/shield/body 自定义；
- MARIE_可视化脚本使用指南.md：内置绘图函数和后处理；
- MARIE_UISNR实现与代码分析.md：basis、理想电流和 UISNR 专项分析。

## 19. 最终判断

src 的主算法不是单一“电磁求解器”，而是由几何离散、混合积分方程、结构化压缩、隐式迭代求解、端口网络、电路优化和 MRI 指标组成的完整研究链。标准算例只会激活其中一部分路径；目录中存在某个函数不表示当前 JSON 一定会调用它。

研究结果可用性的最低要求是：确认实际函数路径、几何与单位正确、MEX 兼容、迭代收敛、网络参数合理、场中无 NaN/Inf，并对网格、basis、压缩容差和端口定义进行独立敏感性验证。
