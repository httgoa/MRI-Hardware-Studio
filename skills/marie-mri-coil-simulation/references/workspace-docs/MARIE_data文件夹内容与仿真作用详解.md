# MARIE 3.0 data 文件夹内容与仿真作用详解

本文档依据当前工作区 2026-08-07 的实际文件、MARIE 3.0 源码加载路径和 runner 保存逻辑整理。它描述的是当前这份仓库，不代表上游仓库未来版本一定保持相同内容。

当前 data 目录共有 67 个文件：

| 格式 | 数量 | 主要用途 |
|---|---:|---|
| .msh | 34 | Gmsh 2.2 ASCII 几何网格 |
| .json | 24 | 仿真输入或线圈集总元件/端口配置 |
| .mat | 5 | 体模、电磁网络矩阵；以后还会保存 BASIS 和 solution |
| .csv | 2 | 自定义阵列的通道布局记录，不由求解器自动读取 |
| .txt | 2 | 目录占位文件，无仿真作用 |

## 1. data 在完整仿真中的位置

~~~mermaid
flowchart LR
    I["data/inputs/*.json<br/>选择 B0、体模、线圈、屏蔽和运行模式"]
    B["data/bodies/*.mat<br/>体素坐标与电磁材料"]
    C["data/coils/coil_files<br/>表面线圈 SIE"]
    W["data/coils/wire_files<br/>细导线线圈 WIE"]
    S["data/coils/shield_files<br/>屏蔽表面 SIE"]
    BS["data/coils/basis_files<br/>理想基底的支撑表面"]
    EB["data/bases/*.mat<br/>预计算 EM basis、UISNR、MRGF 数据"]
    X["data/coils/external_coils<br/>外部 Y 参数与电路配置"]
    G["几何装配与积分方程求解"]
    O["data/solutions/*.mat<br/>网络参数、场、SNR、电流等结果"]

    I --> G
    B --> G
    C --> G
    W --> G
    S --> G
    BS --> G
    EB --> G
    X --> G
    G --> O
~~~

运行时的关键关系：

1. startup.m 执行 addpath(genpath('./'))，把整个项目及 data 子目录加入 MATLAB 搜索路径。
2. MARIE_runner、BASIS_runner 或 MRGF_runner 指定一个输入 JSON。
3. load_inputs 读取 JSON，建立 MREDM.inputs，同时计算拉莫尔频率等电磁常数。
4. geo_body_domain 加载 BodyFile；geo_assembly 再加载 CoilFile、WireFile、ShieldFile 或 BasisFile。
5. 求解完成后，runner 将 solution 或 BASIS 写入 data/solutions 或 data/bases。

重要：所有 runner 都假设当前工作目录是 MARIE 根目录，即 /home/<user>/marie-tools。

## 2. 顶层目录总览

~~~text
data/
├── bases/       预计算电磁基、UISNR、MRGF 压缩数据
├── bodies/      体素体模和介质参数
├── coils/       表面线圈、导线线圈、屏蔽、基底及外部网络
├── inputs/      仿真任务 JSON
└── solutions/   完整仿真和独立联合仿真的输出
~~~

这五个目录的职责不同：

- inputs 是任务清单，负责“选什么”。
- bodies 和 coils 是几何/物理输入，负责“算什么”。
- bases 是可复用的预计算加速与理想基数据。
- solutions 是计算结果，负责“保存了什么”。

## 3. data/inputs：仿真任务入口

### 3.1 文件格式

这里的 JSON 由 load_inputs 读取。当前版本要求以下 10 个字段：

~~~json
{
  "B0": 3.0,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "Scatterers/2mm/Multilayer_Sphere.mat",
  "CoilFile": "",
  "WireFile": "Head_Receivers/example.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": ""
}
~~~

字段到目录的对应关系：

| 字段 | 实际根目录 | 仿真作用 |
|---|---|---|
| BodyFile | data/bodies/ | 体素坐标、介电常数、电导率和活动体素 |
| CoilFile | data/coils/coil_files/ | 表面导体线圈，进入 SIE |
| WireFile | data/coils/wire_files/ | 细导线线圈，进入 WIE |
| ShieldFile | data/coils/shield_files/ | 屏蔽表面，进入 SIE |
| SurfaceBasisSupportFile | data/coils/basis_files/ | BASIS_runner 的表面支撑基 |
| BasisFile | data/bases/ | BASIS 输出或 MRGF/MARIE 外部激励基 |

### 3.2 当前三个输入文件

#### inp_MSphere_HeadCoil1z.json

- 格式：标准输入 JSON，322 B。
- B0：3.0063 T。
- 核素：1H。
- VIE 基函数：1，即 PWL。
- BodyFile：Scatterers/2mm/Multilayer_Sphere.mat。
- WireFile：Head_Receivers/Head_Receive_Array_1_Coil_z.msh。
- TMD：1，启用自动调谐/匹配联合仿真。
- BasisFile：Duke_head_5mm_PWC_7T.mat。

仿真作用：这是当前内置最小工作算例，使用多层球体和单个 z 向接收 Loop。由于 WireFile 非空，普通 MARIE_runner 的 geo_assembly 使用实际导线线圈，不读取 BasisFile；因此当前 data/bases 中没有该 BASIS 文件也不影响这个普通算例。

#### inp_5T_1H_Sphere200_16LoopRx_DoubleRow.json

- 格式：标准输入 JSON，309 B。
- B0：5 T；核素：1H；PWC。
- BodyFile：Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat。
- WireFile：Custom/Sphere16Rx_2Row_R115_H140_Span50_Z50_Stagger22p5.msh。
- TMD：1。

仿真作用：16 通道双排球形体模接收阵列，排中心 z=±0.05 m，第二排方位错开 22.5 度。

当前状态：所引用的 4 mm BodyFile 不在当前 Windows 工作区中，因此本输入暂时不能独立运行。Linux 服务器上若已生成该 MAT 文件，则可运行。

#### inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json

- 格式：标准输入 JSON，308 B。
- 与前一个案例相同，但使用 H90/Z25 线圈版本。
- WireFile：Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.msh。
- 排中心 z=±0.025 m。

当前状态：同样引用当前工作区中不存在的 4 mm 球体 MAT 文件。

## 4. data/bodies：体模与体积介质

### 4.1 MAT 文件格式和必需变量

当前四个体模都是 MATLAB 5.0 MAT 文件，主变量名均为 RHBM。

当前 geo_body_domain 实际依赖：

| 字段 | 形状 | 作用 |
|---|---|---|
| RHBM.r | [n1,n2,n3,3] | 每个体素中心的 x、y、z 坐标，单位 m |
| RHBM.epsilon_r | [n1,n2,n3] | 相对介电常数 |
| RHBM.sigma_e | [n1,n2,n3] | 电导率，单位 S/m |
| RHBM.idxS | [nActive,1] | 活动散射体素的 MATLAB 线性索引 |
| RHBM.rho | 可选 | 密度/掩膜类数据，部分后处理或导出使用 |
| RHBM.name | 字符串 | 体模名称 |

idxS 不是三维 0/1 掩膜。代码用 mask(RHBM.idxS)=true，并用 length(idxS) 计算活动体素数量，因此它必须是合法的线性索引列向量。

### 4.2 RHBM/2mm/Hugo_Head_3T.mat

- 格式：MATLAB 5.0 MAT，约 13.9 MB。
- RHBM.r：310×178×162×3。
- epsilon_r：范围 1 到 84。
- sigma_e：范围 0 到 2.138 S/m。
- 其他字段：name、rhos。
- 文件名含义：Hugo 人体模型的头部，材料参数标记为 3 T。

仿真作用：提供真实解剖头部体素和组织材料参数。

当前兼容性：该文件没有 idxS，而当前 geo_body_domain 强制读取 RHBM.idxS；因此它不能直接作为当前版本 BodyFile。使用前应生成 idxS，例如 find(RHBM.sigma_e>0)，并验证空气/背景是否应排除。文件中的字段是 rhos 而不是常见的 rho，也应先确认其物理含义。

### 4.3 Scatterers/1mm/Multilayer_Sphere.mat

- 格式：MATLAB 5.0 MAT，约 27.3 MB。
- 网格：241×241×241，坐标范围约 -0.12 到 0.12 m。
- 活动体素：7,236,577。
- epsilon_r：1 到 60。
- sigma_e：0 到 0.45 S/m。
- 包含 name、rho、r、idxS。

仿真作用：高分辨率多层球形体模，适合网格收敛、球体基准和高分辨率场/SNR 计算。

代价：活动体素超过 720 万，PWC 已非常大，PWL 更昂贵。它不适合第一次调试几何和电路。

### 4.4 Scatterers/2mm/Multilayer_Sphere.mat

- 格式：MATLAB 5.0 MAT，约 2.87 MB。
- 网格：121×121×121，坐标范围约 -0.12 到 0.12 m。
- 活动体素：904,089。
- epsilon_r：1 到 60。
- sigma_e：0 到 0.45 S/m。
- 包含 name、rho、r、idxS。

仿真作用：当前最小算例实际使用的多层球体。相比 1 mm 版本，计算量明显较低，适合功能验证和常规开发。

### 4.5 Scatterers/2mm/inhomogeneous_cylinder.mat

- 格式：MATLAB 5.0 MAT，约 0.90 MB。
- 网格：73×73×84。
- 活动体素：316,470。
- 坐标范围约 -0.084 到 0.082 m。
- epsilon_r：1 到约 68.18。
- sigma_e：0 到约 1.935 S/m。
- 包含 name、rho、r、idxS。

仿真作用：非均匀圆柱介质基准，可用于验证空间非均匀介质、耦合和场分布。

## 5. data/coils 的格式基础

### 5.1 MSH

当前 34 个 MSH 全部为 Gmsh 2.2 ASCII：

~~~text
MeshFormat = 2.2 0 8
~~~

当前解析器主要使用：

| Gmsh 类型 | 含义 | 在 MARIE 中的作用 |
|---:|---|---|
| 1 | Line | Wire 导线段；或表面模型的端口/集总元件支撑边 |
| 2 | Triangle | Coil、Shield 或 Basis 支撑表面 |
| 15 | Point | Wire 模型中每个集总元件/端口的位置 |

Wire MSH 中 type 15 的数量应等于同名 JSON 的 elements 总数，不等于物理端口数。JSON 中 type=port 的条目数量才是物理 RF 端口数。

### 5.2 线圈 JSON

线圈、导线和带集总元件的屏蔽使用另一类 JSON：

~~~json
{
  "coil_configuration": {
    "name": "example",
    "tmd": false,
    "elements": [
      {
        "number": 1,
        "type": "port",
        "load": "capacitorParallel_inductorSeries_capacitorParallel",
        "value": [1e-12, 1e-9, 1e-12],
        "Q": [500, 200, 500],
        "optim": {
          "boolean": 1,
          "minim": [1e-13, 1e-10, 1e-13],
          "maxim": [1e-10, 1e-8, 1e-10],
          "symmetry": 1
        },
        "cross_talk": {},
        "excitation": {
          "entity": 1,
          "TxRx": "Rx"
        }
      }
    ]
  }
}
~~~

仿真作用：

- type=port 定义物理 RF 端口。
- type=element 定义分布电容、电感或互感等集总元件。
- load/value/Q 构成电路模型。
- optim 决定 TMD=1 时哪些参数参与自动调谐、匹配或去耦。
- excitation.entity 将元件归属到某个线圈通道。
- excitation.TxRx 决定 Rx、Tx 或 TxRx 工作类型。

文件顶层 coil_configuration.tmd 目前主要是描述性字段；真正是否自动调谐由输入 JSON 的 TMD 控制。

## 6. data/coils/wire_files：细导线线圈

这些模型进入 WIE。每个 MSH 由 type 1 导线段和 type 15 集总元件位置组成，同名 JSON 定义端口、电容、电感和优化范围。

### 6.1 Custom

#### Sphere16Rx_2Row_R115_H140_Span50_Z50_Stagger22p5.msh

- 1,280 个节点。
- 1,280 条 Line；128 个 Point 元件。
- 作用：16 通道双排球形 Loop 接收阵列，阵列半径名称标记为 115 mm，两排中心 z=±50 mm，排间方位错开 22.5 度。

#### 同名 .json

- 128 个电路条目。
- 16 个物理端口。
- 每通道平均 1 个 port 加 7 个分布元件。
- 全部按 Rx 配置；支持输入 TMD=1 时自动优化。

#### 同名 _channel_layout.csv

- CSV 文本，16 行通道布局。
- 字段：Channel、RowCenterZ_m、Azimuth_deg。
- 作用：记录通道编号、所在排和方位角，供人工复核、绘图和后处理。
- 求解器不会自动读取该 CSV。

#### Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.msh

- 1,280 个节点。
- 1,280 条 Line；128 个 Point 元件。
- 作用：较短的双排 16 通道版本，两排中心 z=±25 mm。

#### 同名 .json

- 128 个条目，16 个物理端口，Rx 配置。

#### 同名 _channel_layout.csv

- 记录 z=±0.025 m 以及两排的 0/22.5 度错列方位。
- 仅作为设计元数据，不参与求解。

### 6.2 Head_Receivers

#### Head_Receive_Array_1_Coil.msh / .json

- MSH：1,499 条 Line，4 个 Point。
- JSON：4 个条目，其中 1 个物理 Rx 端口。
- 作用：单个头部接收 Loop 的基本模板。

#### Head_Receive_Array_1_Coil_z.msh / .json

- MSH：1,500 条 Line，4 个 Point。
- JSON：4 个条目，其中 1 个 Rx 端口。
- 作用：单 Loop 的 z 向版本；当前 inp_MSphere_HeadCoil1z.json 使用它。

#### Head_Receive_Array_1_Coil_4ports.msh / .json

- MSH：1,520 条 Line，4 个 Point。
- JSON：4 个电路条目，但只有 1 个条目 type=port。
- 作用：具有 4 个集总元件位置的单线圈变体。

注意：文件名中的 4ports 不等于 JSON 中存在 4 个 RF 端口。当前 JSON 统计只有 1 个物理端口。

#### Head_Receive_Array_1_Coil_8ports.msh / .json

- MSH：1,520 条 Line，8 个 Point。
- JSON：8 个电路条目，但只有 1 个物理 Rx 端口。
- 作用：具有 8 个集总元件位置的单线圈变体。

#### Head_Receive_Array_8_Coils.msh / .json

- MSH：11,992 条 Line，64 个 Point。
- JSON：64 个条目，8 个物理 Rx 端口。
- 作用：8 通道头部接收阵列。

#### Head_Receive_Array_16_Coils.msh / .json

- MSH：23,984 条 Line，128 个 Point。
- JSON 设计目标显然是约 128 个条目和 16 个物理通道。
- 作用：16 通道头部接收阵列模板。

当前状态：JSON 第 578 行在 number=29 的条目中出现孤立字符 v，并缺少正常的 value/Q 字段，因此不是合法 JSON。jsondecode 会直接失败。修复并逐项核对前，不应将它作为可运行模板。

#### Head_Receive_Array_31_Coils.msh / .json

- MSH：46,199 条 Line，171 个 Point。
- JSON：171 个条目，31 个物理 Rx 端口。
- 作用：31 通道头部接收阵列；也是 external_coils 中 CST 网络配置的几何对应参考。

### 6.3 Prostate_Receivers

#### Prostate_Array_16.msh / .json

- MSH：23,984 条 Line，128 个 Point。
- JSON：128 个条目，16 个物理端口。
- 标签统计：112 个条目为 Rx，16 个为 TxRx。
- 作用：16 通道前列腺阵列，包含混合 TxRx/Rx 元件标记。

#### Prostate_Array_8_Lateral.msh / .json

- MSH：11,992 条 Line，64 个 Point。
- JSON：64 个条目，8 个物理端口。
- 标签统计：56 个 Rx，8 个 TxRx。
- 作用：8 通道前列腺阵列的 lateral 位置版本。

#### Prostate_Array_8_Middle.msh / .json

- MSH：11,992 条 Line，64 个 Point。
- JSON：64 个条目，8 个物理端口。
- 标签统计：56 个 Rx，8 个 TxRx。
- 作用：8 通道前列腺阵列的 middle 位置版本。

混合标签不应仅凭文件名解释。运行时 co_simulation 会读取每个条目的 TxRx 并判断属于纯 Rx、纯 Tx、TxRx 或混合优化路径。

## 7. data/coils/coil_files：表面导体线圈

这些模型进入 SIE。MSH 中 type 2 是导电三角面，type 1 是端口/集总元件的支撑边；同名 JSON 将这些边映射为电容、互感和 RF 端口。

### 7.1 Head_Birdcage

以下三个文件描述相同命名参数的高通鸟笼线圈：半径 12.3 cm、8 根腿、长度名称标记为 2 cm，不同后缀表示表面网格尺寸。

#### mesh_0.005.msh / .json

- MSH：2,095 节点；2,958 三角形；32 条元件 Line。
- JSON：16 个条目，2 个物理 TxRx 端口。
- 作用：最粗网格，适合快速调试。

#### mesh_0.0025.msh / .json

- MSH：7,156 节点；11,832 三角形；64 条元件 Line。
- JSON：16 个条目，2 个 TxRx 端口。
- 作用：中等分辨率。

#### mesh_0.00125.msh / .json

- MSH：26,152 节点；47,328 三角形；128 条元件 Line。
- JSON：16 个条目，2 个 TxRx 端口。
- 作用：精细表面网格，计算和内存代价最高。

三个 JSON 使用 capacitor 和 capacitorParallel_capacitorSeries 负载。不同网格版本不应混用 MSH 与另一版本的 JSON，物理边映射可能不同。

### 7.2 Head_Overlap/OverlapCoil_2_stacks.msh / .json

- MSH：6,896 节点；6,896 三角形；144 条元件 Line。
- JSON：144 个条目，16 个物理 Rx 端口。
- 作用：两层重叠式头部接收阵列，用重叠几何降低相邻线圈耦合。

### 7.3 Head_StadiumTriangular

#### Stadium_Triangular.msh / .json

- MSH：1,724 节点；2,064 三角形；76 条 Line。
- JSON：64 个条目，8 个物理 TxRx 端口。
- 负载包含 capacitor、端口匹配网络和 mutual_inductor。
- 作用：stadium 形 8 通道三角面线圈，包含互感/去耦电路描述。

#### Stadium_Triangular_refined.msh / .json

- MSH：5,520 节点；8,256 三角形；152 条 Line。
- JSON：同样 64 个条目、8 个 TxRx 端口。
- 作用：上述模型的精细网格版本，用于网格收敛或正式计算。

### 7.4 SKYRA_Coil/SKYRA_Coil.msh / .json

- MSH：11,721 节点；18,130 三角形；320 条 Line。
- JSON：64 个条目，2 个物理 TxRx 端口。
- 作用：SKYRA 命名的表面线圈模型，包含电容和并联电容网络。

## 8. data/coils/shield_files：屏蔽模型

ShieldFile 的加载方式取决于是否存在同名 JSON：

- 没有同名 JSON：geo_shield 将其作为无源导电屏蔽表面。
- 有同名 JSON：按带端口/集总元件的 SIE 结构加载。

### 8.1 Head_Shields/Stadium_Coil_Head_Shield.msh

- 1,389 节点，2,650 个三角形。
- 无同名 JSON。
- 作用：Stadium 头部线圈的无源屏蔽表面。

### 8.2 SKYRA_Shields/SKYRA_shield_150cm_coarse.msh

- 1,755 节点，3,414 个三角形。
- 无同名 JSON。
- 作用：长度名称标记为 150 cm 的粗网格 SKYRA 屏蔽。

### 8.3 SKYRA_Shields/SKYRA_shield_150cm_fine.msh

- 12,183 节点，24,130 个三角形。
- 无同名 JSON。
- 作用：同一屏蔽的精细网格版本，用于更高精度表面电流和耦合计算。

### 8.4 SKYRA_Coil/SKYRA_Coil_Shielded.msh / .json

- MSH：13,476 节点；21,544 三角形；320 条 Line。
- JSON：64 个条目，2 个 TxRx 端口。
- 作用：带线圈电路元件定义的 shielded SKYRA 组合表面。

因为同名 JSON 存在，当前代码不会把它当作单纯无源金属罩，而会加载其端口和集总元件。

## 9. data/coils/basis_files：理想场和 UISNR 的支撑表面

这些文件全部是纯三角面 Gmsh 2.2 MSH，没有端口 Line 和同名 JSON。它们主要由 BASIS_runner 在 geo_flag=2 时通过 SurfaceBasisSupportFile 使用，定义理想表面电流基所在的支撑几何。

它们不是普通真实线圈，也不定义调谐电容。输出的 BASIS 可用于：

- UISNR。
- ideal current patterns。
- 理想发射效率。
- MRGF 压缩基和后续快速求解。

### 9.1 Bell_basis

- Duke_Head.msh：4,488 节点，8,870 三角形；Duke 头部的 bell 形基底。
- Duke_Head_refined.msh：71,169 节点，141,920 三角形；精细版本，计算量非常大。

### 9.2 Cylinder_basis

- Duke_Head.msh：4,516 节点，8,824 三角形；围绕 Duke 头部的圆柱形支撑表面。

### 9.3 Elliptic_Cylinder_basis

- Duke_Body.msh：11,371 节点，22,526 三角形；面向 Duke 身体区域的椭圆柱支撑表面。

### 9.4 Helmet_basis

- Duke_Head.msh：2,668 节点，5,212 三角形；贴近头部的 helmet 形支撑。

### 9.5 Stadium_basis

- Duke_Head.msh：4,674 节点，9,205 三角形。
- Billie_Head.msh：4,674 节点，9,205 三角形。
- 作用：分别用于 Duke 和 Billie 头模位置/尺度配置的 stadium 支撑面。

尽管节点和面数相同，也不能仅凭计数认为两者坐标完全相同；使用时必须与对应体模可视化核对。

### 9.6 Ultimate_basis

- Duke_Head.msh：5,811 节点，11,618 三角形。
- Billie_Head.msh：5,866 节点，11,728 三角形。
- Ella_Head.msh：5,983 节点，11,962 三角形。
- Duke_HeadCervicalSpine.msh：5,560 节点，11,116 三角形。

作用：面向不同 Virtual Population 体模/解剖区域的 ultimate basis 支撑面，用于理想电流、UISNR 和 MRGF 基生成。

## 10. data/coils/external_coils：外部电磁网络联合仿真

该目录不参与普通 geo_assembly。CO_SIMULATION_runner 直接从这里读取预计算网络和电路配置，跳过 MARIE 几何与积分方程装配。

### 10.1 YPn_mat.mat

- 格式：MATLAB 5.0 MAT，约 453 kB。
- 变量：YPn，171×171 complex/double 网络导纳矩阵。
- 作用：外部全波求解器预计算的未加载线圈网络参数，供独立调谐、匹配、去耦优化。

### 10.2 Head_Receive_Array_31_Coils_CST.json

- 格式：线圈电路 JSON，约 85 kB。
- 171 个条目，31 个物理 Rx 端口。
- 作用：与 171×171 YPn 的端口/集总元件顺序对应，描述 CST 外部模型的电路元件和优化边界。

CO_SIMULATION_runner 当前硬编码读取：

~~~matlab
YPn_mat       = 'YPn_mat.mat';
coil_file_inp = 'Head_Receive_Array_31_Coils_CST.json';
~~~

两者维度和条目顺序必须完全一致。该 runner 最终把网络参数、M_cal 和频率扫描信息保存到 data/solutions/CoSimulation_*.mat。

## 11. data/bases：预计算 BASIS 与 MRGF 数据

### 11.1 当前文件

- test.txt：13 B，占位内容 _Test_file_。
- 格式：纯文本。
- 仿真作用：无，仅用于让空目录进入版本控制。

### 11.2 正常运行后应出现什么

BASIS_runner 将输入 JSON 的 BasisFile 解析为：

~~~text
data/bases/<BasisFile>
~~~

并以 MATLAB -v7.3 格式保存变量 BASIS。根据 runner 和 MRGF 读取代码，文件可能包含：

- Ue：总电场基。
- Ub：总磁场基。
- U_hat_inv、S_hat_inv、V_hat_inv、X：MRGF 压缩/逆算子。
- xds、yds、zds 等降阶耦合辅助数据。
- UISNR、UITXE。
- surface-supported basis 下的 Substrate 和 ideal current patterns。

MRGF_runner 会通过 h5read 直接读取这些 HDF5 数据集。因此正式 BASIS 文件必须是 -v7.3 MAT，且数据集名称和复数存储结构与当前代码一致。

## 12. data/solutions：仿真结果

### 12.1 当前文件

- test.txt：13 B，占位内容 _Test_file_。
- 当前 Windows 工作区没有正式 solution MAT；Linux 服务器上已生成的结果尚未同步到这里。

### 12.2 MARIE_runner 输出

命名：

~~~text
MARIE_<TMD>_<input_json_basename>.mat
~~~

例如：

~~~text
MARIE_1_inp_MSphere_HeadCoil1z.mat
~~~

格式：MATLAB -v7.3，主变量 solution。

根据实际算例，solution 可包含：

- Jcb：线圈/体模组合电流。
- JcbRx、JcbTx：接收或发射电流。
- netp：YP_s、ZP_s、SP_s、SP_p、figure_freq 等网络参数。
- e_field：电场结果。
- h_field：磁场、B1- 或 B1+。
- snr_field：SNR 相关场。
- txe_field：发射效率相关结果。

具体字段取决于 Tx/Rx 模式、runner 和求解是否完成，不能假设每个结果都同时含 Tx 与 Rx 字段。

### 12.3 MRGF_runner 输出

命名：

~~~text
MRGF_<input_json_basename>.mat
~~~

作用：保存使用预计算 BASIS 和 MRGF 压缩算子得到的快速 WSVIE 结果。

### 12.4 CO_SIMULATION_runner 输出

命名：

~~~text
CoSimulation_<coil_json_basename>.mat
~~~

作用：只保存独立电路联合仿真的网络与变换结果，不包含重新求解得到的完整三维体场。

### 12.5 solutions 不应存放什么

- 不要把输入 JSON、源 MSH 或唯一的线圈电路 JSON 只放在 solutions。
- 不要把失败运行产生的同名 MAT 当成已验证结果。
- 后处理图建议放入与案例同名的子目录，并保留原始 solution MAT。

## 13. 文件在不同 runner 中的使用矩阵

| data 内容 | MARIE_runner | BASIS_runner | MRGF_runner | CO_SIMULATION_runner |
|---|---:|---:|---:|---:|
| inputs/*.json | 必需 | 必需 | 必需 | 不使用 |
| bodies/*.mat | 必需 | 必需 | 必需 | 不使用 |
| coil_files | 可选 | 输入中忽略 | 可选 | 不使用 |
| wire_files | 可选 | 输入中忽略 | 可选 | 不使用 |
| shield_files | 可选 | 输入中忽略 | 可选 | 不使用 |
| basis_files | 通常不使用 | geo_flag=2 必需 | 忽略 | 不使用 |
| bases/*.mat | 无实体线圈时可作外部激励 | 输出目标 | 必需 | 不使用 |
| external_coils | 不使用 | 不使用 | 不使用 | 必需 |
| solutions | 输出 | 不输出到此处 | 输出 | 输出 |

注意：BASIS_runner 的结果写入 data/bases，而不是 data/solutions。

## 14. 当前仓库的可用性审计

### 14.1 可直接作为当前最小算例输入

- data/inputs/inp_MSphere_HeadCoil1z.json。
- data/bodies/Scatterers/2mm/Multilayer_Sphere.mat。
- data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_z.msh。
- 对应同名 JSON。

### 14.2 需要补充文件

- 两个 5 T 双排输入需要 data/bodies/Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat。
- inp_MSphere 中列出的 Duke_head_5mm_PWC_7T.mat 当前不存在；普通 Wire MARIE 运行不需要它，但 MRGF/BASIS 链不能据此运行。

### 14.3 需要修复格式

- Head_Receive_Array_16_Coils.json 第 578 行含孤立字符 v，jsondecode 会失败。

### 14.4 需要转换体模

- Hugo_Head_3T.mat 缺少 idxS，当前 geo_body_domain 不能直接加载。

### 14.5 仅作辅助记录

- 两个 channel_layout.csv 不由 MARIE 自动加载。
- bases/test.txt 和 solutions/test.txt 仅为占位文件。

## 15. 推荐的数据管理方式

为每个新案例使用唯一前缀：

~~~text
data/bodies/Custom/CaseA_body_v01.mat
data/coils/wire_files/Custom/CaseA_coil_v01.msh
data/coils/wire_files/Custom/CaseA_coil_v01.json
data/inputs/inp_CaseA_v01.json
data/solutions/MARIE_1_inp_CaseA_v01.mat
~~~

推荐规则：

1. 不覆盖已经验证的内置文件。
2. MSH 和电路 JSON 同名、同版本。
3. JSON 修改前保留种子版本，因为 TMD 可能回写优化后的元件值。
4. 每个 solution 保留对应输入 JSON、线圈版本和 BodyFile 名称。
5. 高分辨率体模、BASIS 和 solution 体积很大，应单独规划服务器磁盘和备份。
6. CSV 适合记录通道编号、行列位置和角度，但真正的求解几何仍以 MSH 为准。

## 16. 快速检查命令

在 MATLAB 中检查输入引用：

~~~matlab
cd('/home/<user>/marie-tools')
startup

cfg = jsondecode(fileread('data/inputs/inp_MSphere_HeadCoil1z.json'));

assert(isfile(fullfile('data','bodies',cfg.BodyFile)));

if ~isempty(cfg.WireFile)
    p = fullfile('data','coils','wire_files',cfg.WireFile);
    assert(isfile(p));
    [folder,base] = fileparts(p);
    assert(isfile(fullfile(folder,[base,'.json'])));
end

if ~isempty(cfg.CoilFile)
    p = fullfile('data','coils','coil_files',cfg.CoilFile);
    assert(isfile(p));
end

if ~isempty(cfg.ShieldFile)
    p = fullfile('data','coils','shield_files',cfg.ShieldFile);
    assert(isfile(p));
end

disp('输入引用检查完成')
~~~

检查体模结构：

~~~matlab
B = load(fullfile('data','bodies',cfg.BodyFile),'RHBM');
required = {'r','epsilon_r','sigma_e','idxS'};
assert(all(isfield(B.RHBM,required)));
assert(size(B.RHBM.r,4)==3);
assert(isequal(size(B.RHBM.epsilon_r),size(B.RHBM.sigma_e)));
assert(isvector(B.RHBM.idxS) && size(B.RHBM.idxS,2)==1);
assert(all(B.RHBM.idxS>=1 & B.RHBM.idxS<=numel(B.RHBM.epsilon_r)));
~~~

只做几何装配：

~~~matlab
MREDM = load_inputs('inp_MSphere_HeadCoil1z.json');
MREDM = geo_assembly(MREDM,1);
visualize_geometry(MREDM)
~~~

## 17. 相关文档

- MARIE_JSON文件配置指南.md：输入 JSON 字段及候选取值。
- MARIE_模型设计与组合教程.md：自行创建 Body、Wire、Coil 和 Shield。
- MARIE_Runner算法与使用指南.md：不同 runner 的算法、输入和输出。
- MARIE_使用指南_Codex经验.md：运行、结果回看、清理和异常处理。
- MARIE_可视化脚本使用指南.md：几何、网络、场、SNR 和电流绘图。

## 18. 当前 67 个文件的完整路径索引

以下索引用于按原始文件名检索。详细格式、字段和仿真作用见前述对应章节。

### 18.1 bases、bodies、inputs、solutions

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/bases/test.txt | TXT | 空目录占位 |
| data/bodies/RHBM/2mm/Hugo_Head_3T.mat | MAT v5 | Hugo 3 T 头部体模；当前缺 idxS |
| data/bodies/Scatterers/1mm/Multilayer_Sphere.mat | MAT v5 | 1 mm 多层球体 |
| data/bodies/Scatterers/2mm/inhomogeneous_cylinder.mat | MAT v5 | 2 mm 非均匀圆柱 |
| data/bodies/Scatterers/2mm/Multilayer_Sphere.mat | MAT v5 | 2 mm 多层球体 |
| data/inputs/inp_5T_1H_Sphere200_16LoopRx_DoubleRow.json | 输入 JSON | 5 T、16 通道 H140 双排案例 |
| data/inputs/inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json | 输入 JSON | 5 T、16 通道 H90 双排案例 |
| data/inputs/inp_MSphere_HeadCoil1z.json | 输入 JSON | 内置多层球体单 Loop 算例 |
| data/solutions/test.txt | TXT | 空目录占位 |

### 18.2 basis_files

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/basis_files/Bell_basis/Duke_Head.msh | Gmsh 2.2 | Duke 头部 bell 支撑基 |
| data/coils/basis_files/Bell_basis/Duke_Head_refined.msh | Gmsh 2.2 | Duke 头部精细 bell 支撑基 |
| data/coils/basis_files/Cylinder_basis/Duke_Head.msh | Gmsh 2.2 | Duke 头部圆柱支撑基 |
| data/coils/basis_files/Elliptic_Cylinder_basis/Duke_Body.msh | Gmsh 2.2 | Duke 身体椭圆柱支撑基 |
| data/coils/basis_files/Helmet_basis/Duke_Head.msh | Gmsh 2.2 | Duke 头部 helmet 支撑基 |
| data/coils/basis_files/Stadium_basis/Billie_Head.msh | Gmsh 2.2 | Billie 头部 stadium 支撑基 |
| data/coils/basis_files/Stadium_basis/Duke_Head.msh | Gmsh 2.2 | Duke 头部 stadium 支撑基 |
| data/coils/basis_files/Ultimate_basis/Billie_Head.msh | Gmsh 2.2 | Billie 头部 ultimate 支撑基 |
| data/coils/basis_files/Ultimate_basis/Duke_Head.msh | Gmsh 2.2 | Duke 头部 ultimate 支撑基 |
| data/coils/basis_files/Ultimate_basis/Duke_HeadCervicalSpine.msh | Gmsh 2.2 | Duke 头颈部 ultimate 支撑基 |
| data/coils/basis_files/Ultimate_basis/Ella_Head.msh | Gmsh 2.2 | Ella 头部 ultimate 支撑基 |

### 18.3 coil_files

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.00125.msh | Gmsh 2.2 | 精细高通鸟笼表面网格 |
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.00125.json | 电路 JSON | 上述精细鸟笼的 16 个元件配置 |
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.0025.msh | Gmsh 2.2 | 中等高通鸟笼表面网格 |
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.0025.json | 电路 JSON | 上述中等鸟笼的元件配置 |
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.005.msh | Gmsh 2.2 | 粗高通鸟笼表面网格 |
| data/coils/coil_files/Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.005.json | 电路 JSON | 上述粗鸟笼的元件配置 |
| data/coils/coil_files/Head_Overlap/OverlapCoil_2_stacks.msh | Gmsh 2.2 | 双层重叠 16 通道表面阵列 |
| data/coils/coil_files/Head_Overlap/OverlapCoil_2_stacks.json | 电路 JSON | 双层重叠阵列的 144 个元件 |
| data/coils/coil_files/Head_StadiumTriangular/Stadium_Triangular.msh | Gmsh 2.2 | Stadium 三角面阵列 |
| data/coils/coil_files/Head_StadiumTriangular/Stadium_Triangular.json | 电路 JSON | Stadium 阵列端口、元件和互感 |
| data/coils/coil_files/Head_StadiumTriangular/Stadium_Triangular_refined.msh | Gmsh 2.2 | 精细 Stadium 三角面阵列 |
| data/coils/coil_files/Head_StadiumTriangular/Stadium_Triangular_refined.json | 电路 JSON | 精细 Stadium 的电路配置 |
| data/coils/coil_files/SKYRA_Coil/SKYRA_Coil.msh | Gmsh 2.2 | SKYRA 表面线圈 |
| data/coils/coil_files/SKYRA_Coil/SKYRA_Coil.json | 电路 JSON | SKYRA 线圈的 64 个元件配置 |

### 18.4 external_coils 和 shield_files

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/external_coils/Head_Receive_Array_31_Coils_CST.json | 电路 JSON | CST 31 通道外部网络配置 |
| data/coils/external_coils/YPn_mat.mat | MAT v5 | 171×171 外部 Y 参数矩阵 |
| data/coils/shield_files/Head_Shields/Stadium_Coil_Head_Shield.msh | Gmsh 2.2 | Stadium 线圈无源头部屏蔽 |
| data/coils/shield_files/SKYRA_Coil/SKYRA_Coil_Shielded.msh | Gmsh 2.2 | 带线圈元件的 SKYRA shielded 表面 |
| data/coils/shield_files/SKYRA_Coil/SKYRA_Coil_Shielded.json | 电路 JSON | 上述 shielded 表面的 64 个元件 |
| data/coils/shield_files/SKYRA_Shields/SKYRA_shield_150cm_coarse.msh | Gmsh 2.2 | 150 cm SKYRA 粗屏蔽 |
| data/coils/shield_files/SKYRA_Shields/SKYRA_shield_150cm_fine.msh | Gmsh 2.2 | 150 cm SKYRA 精细屏蔽 |

### 18.5 wire_files/Custom

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H140_Span50_Z50_Stagger22p5.msh | Gmsh 2.2 | H140/Z50 双排 16 通道导线阵列 |
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H140_Span50_Z50_Stagger22p5.json | 电路 JSON | 上述阵列的 128 个电路条目 |
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H140_Span50_Z50_Stagger22p5_channel_layout.csv | CSV | 上述阵列的通道方位记录 |
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.msh | Gmsh 2.2 | H90/Z25 双排 16 通道导线阵列 |
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json | 电路 JSON | 上述阵列的 128 个电路条目 |
| data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5_channel_layout.csv | CSV | 上述阵列的通道方位记录 |

### 18.6 wire_files/Head_Receivers

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil.msh | Gmsh 2.2 | 单头部 Loop 几何 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil.json | 电路 JSON | 单 Loop 的 4 个元件 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_4ports.msh | Gmsh 2.2 | 单 Loop、4 个元件位置 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_4ports.json | 电路 JSON | 4 个条目、1 个物理端口 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_8ports.msh | Gmsh 2.2 | 单 Loop、8 个元件位置 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_8ports.json | 电路 JSON | 8 个条目、1 个物理端口 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_z.msh | Gmsh 2.2 | z 向单 Loop 几何 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_1_Coil_z.json | 电路 JSON | z 向单 Loop 电路 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_16_Coils.msh | Gmsh 2.2 | 16 通道头部导线阵列 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_16_Coils.json | 损坏的电路 JSON | 第 578 行语法损坏，当前不可加载 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_31_Coils.msh | Gmsh 2.2 | 31 通道头部导线阵列 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_31_Coils.json | 电路 JSON | 31 端口、171 条目 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_8_Coils.msh | Gmsh 2.2 | 8 通道头部导线阵列 |
| data/coils/wire_files/Head_Receivers/Head_Receive_Array_8_Coils.json | 电路 JSON | 8 端口、64 条目 |

### 18.7 wire_files/Prostate_Receivers

| 完整相对路径 | 格式 | 作用 |
|---|---|---|
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_16.msh | Gmsh 2.2 | 16 通道前列腺导线阵列 |
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_16.json | 电路 JSON | 16 端口混合 Rx/TxRx 配置 |
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_8_Lateral.msh | Gmsh 2.2 | 8 通道 lateral 阵列 |
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_8_Lateral.json | 电路 JSON | lateral 阵列混合 Rx/TxRx 配置 |
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_8_Middle.msh | Gmsh 2.2 | 8 通道 middle 阵列 |
| data/coils/wire_files/Prostate_Receivers/Prostate_Array_8_Middle.json | 电路 JSON | middle 阵列混合 Rx/TxRx 配置 |
