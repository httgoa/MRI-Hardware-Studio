# MARIE 3.0 JSON 文件配置指南

本文档依据当前仓库的 `load_inputs.m`、`parse_inputs.m`、`geo_assembly.m`、`em_constants.m`、各 Runner 源码，以及 `data/` 中实际存在的模型文件整理。适用于当前这份 MARIE 3.0 源码，不保证与其他分支或未来版本完全一致。

## 1. JSON 文件的作用与位置

MARIE 使用 JSON 文件选择磁场、核素、体积分方程基函数、人体/体模、线圈、屏蔽及电路协同仿真设置。

输入文件放在：

```text
/home/<user>/marie-tools/data/inputs/
```

运行器中的 `input_file` 通常只填写文件名：

```matlab
input_file = 'inp_my_case.json';
```

运行前必须执行：

```matlab
cd('/home/<user>/marie-tools')
startup
```

`startup` 会把仓库子目录加入 MATLAB 路径。Runner 依赖当前目录为仓库根目录，因此不要从任意目录直接运行。

## 2. 完整 JSON 结构

当前 `load_inputs.m` 会直接读取以下十个字段。即使某项不用，也应保留并填写空字符串 `""`；不要删除字段，也不要写成 `null`。

```json
{
  "B0": 3.0063,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 1,
  "BodyFile": "Scatterers/2mm/Multilayer_Sphere.mat",
  "CoilFile": "",
  "WireFile": "Head_Receivers/Head_Receive_Array_1_Coil_z.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": "Duke_head_5mm_PWC_7T.mat"
}
```

JSON 注意事项：

- 字段名区分大小写，必须与示例完全一致。
- JSON 不允许注释、尾随逗号、MATLAB 表达式或 `NaN`。
- 路径建议统一使用 `/`。
- 数值不加引号；文件名、核素和空值使用字符串。

## 3. 字段总览

| 字段 | 类型 | 是否必须存在 | 取值/路径基准 |
| --- | --- | --- | --- |
| `B0` | 数值 | 是 | 主磁场，单位 T。 |
| `Nucleus` | 字符串 | 是 | 源码支持的核素标识。 |
| `Basis_Functions_VIE` | 整数 | 是 | 推荐仅用 `0=PWC`、`1=PWL`。 |
| `BodyFile` | 字符串 | 是 | 相对于 `data/bodies/` 的 `.mat` 文件。 |
| `CoilFile` | 字符串 | 是，可为 `""` | 相对于 `data/coils/coil_files/` 的表面线圈 `.msh`。 |
| `WireFile` | 字符串 | 是，可为 `""` | 相对于 `data/coils/wire_files/` 的导线线圈 `.msh`。 |
| `ShieldFile` | 字符串 | 是，可为 `""` | 相对于 `data/coils/shield_files/` 的屏蔽 `.msh`。 |
| `SurfaceBasisSupportFile` | 字符串 | 是，可为 `""` | 相对于 `data/coils/basis_files/` 的表面支撑网格。 |
| `TMD` | 整数 | 是 | 推荐仅用 `0` 或 `1`。 |
| `BasisFile` | 字符串 | 是，可为 `""` | 相对于 `data/bases/` 的预计算基文件。 |

## 4. `B0`：主磁场强度

`B0` 的单位是 Tesla。MARIE 使用它和 `Nucleus` 计算拉莫尔频率：

```text
frequency = |gamma/(2*pi)| * B0
```

对 `1H`，源码采用 `42.577478518 MHz/T`：

| B0 | 1H 拉莫尔频率（约） |
| --- | --- |
| 1.5 T | 63.87 MHz |
| 3.0 T | 127.73 MHz |
| 3.0063 T | 128.00 MHz |
| 5.0 T | 212.89 MHz |
| 7.0 T | 298.04 MHz |
| 7.0037 T | 298.20 MHz |

重要限制：修改 `B0` 只会更新频率和相关物理常数，不会自动更新 `BodyFile` 中的 `epsilon_r` 和 `sigma_e`。人体组织介电参数与频率有关，因此 3 T 人体模型不能仅通过把 `B0` 改成 5 T 就视为物理一致的 5 T 模型。

## 5. `Nucleus`：核素

源码使用不区分大小写的字符串比较，当前支持：

| JSON 值 | 核素 | 源码中的旋磁比 `gamma/(2*pi)` |
| --- | --- | --- |
| `1H` | 氢-1/质子 | 42.577478518 MHz/T |
| `2H` | 氘 | 6.536 MHz/T |
| `3HE` | 氦-3 | 32.434 MHz/T |
| `13C` | 碳-13 | 10.705 MHz/T |
| `7LI` | 锂-7 | 16.546 MHz/T |
| `15N` | 氮-15 | -4.316 MHz/T |
| `17O` | 氧-17 | -5.772 MHz/T |
| `23NA` | 钠-23 | 11.262 MHz/T |
| `25MG` | 镁-25 | -2.614 MHz/T |
| `31P` | 磷-31 | 17.235 MHz/T |
| `35CL` | 氯-35 | 4.171 MHz/T |
| `39K` | 钾-39 | 1.250 MHz/T |
| `59CO` | 钴-59 | 10.054 MHz/T |
| `79BR` | 溴-79 | 10.666 MHz/T |
| `87RB` | 铷-87 | 13.932 MHz/T |
| `129XE` | 氙-129 | 11.777 MHz/T |

不要填写未列出的核素。当前源码没有清晰的“Unsupported nucleus”错误分支，错误可能在后续访问未初始化常数时才出现。

## 6. `Basis_Functions_VIE`：VIE 基函数

| 值 | 类型 | 含义 | 每个散射体素对应的场未知量规模 |
| --- | --- | --- | --- |
| `0` | PWC | Piecewise Constant，分段常数基函数。 | 约 3 个分量。 |
| `1` | PWL | Piecewise Linear，分段线性基函数。 | 约 12 个分量。 |

选择建议：

- 首次调通、较大人体模型或内存受限时，优先使用 `0`（PWC）。
- 需要更高阶空间表示且资源充足时，再考虑 `1`（PWL）。
- PWL 的未知量规模约为 PWC 的 4 倍，实际内存和时间增长还受组装、压缩和求解器影响。
- 源码仅显式判断 `==1` 为 PWL，其他值会进入 PWC 分支。这是实现细节，不是合法取值扩展；配置时只使用 `0` 或 `1`。

预计算 `BasisFile` 必须和这里的 PWC/PWL 类型一致。文件名中常用 `PWC` 或 `PWL` 标识这种兼容关系。

## 7. `BodyFile`：人体或体模

### 7.1 当前仓库候选

| JSON 中填写的值 | 模型含义 | 网格 | 数组大小 | 材料情况 | 建议用途 |
| --- | --- | --- | --- | --- | --- |
| `Scatterers/2mm/Multilayer_Sphere.mat` | 多层球形介质体模 | 2 mm | `121x121x121` | 5 类（含背景），`epsilon_r` 为 1/20/30/40/60，`sigma_e` 最大 0.45 S/m | 首次测试首选；本次成功算例使用它。 |
| `Scatterers/1mm/Multilayer_Sphere.mat` | 同一多层球体的高分辨率版本 | 1 mm | `241x241x241` | 与 2 mm 版本相同的 5 类材料 | 收敛性比较；内存与时间显著增加。 |
| `Scatterers/2mm/inhomogeneous_cylinder.mat` | 实验型非均匀圆柱体模 | 2 mm | `73x73x84` | 3 类（含背景），非背景介电参数不均匀 | 圆柱体模、算法和实验对照。 |
| `RHBM/2mm/Hugo_Head_3T.mat` | 仓库命名为 Hugo 的解剖头部模型，材料标注为 3 T | 2 mm | `310x178x162` | 18 组介电参数，`epsilon_r` 最高 84、`sigma_e` 最高 2.138 S/m | 真实形态头部研究，但需先完成结构兼容检查。 |

### 7.2 Hugo 文件的当前兼容性问题

当前 `geo_body_domain.m` 要求 `RHBM.idxS`。仓库中的 `Hugo_Head_3T.mat` 当前字段为：

```text
r, epsilon_r, sigma_e, name, rhos
```

它缺少 `idxS`，因此不能保证未经预处理就能被当前 Runner 直接使用。不要覆盖原文件。应先复制为新模型，核对组织掩膜，并生成符合当前结构的 `idxS`。

此外，该文件名和内部名称都标注为 3 T。用于 5 T 研究时，应先准备频率一致的 5 T `epsilon_r`、`sigma_e` 数据，而不是只改 JSON 的 `B0`。

### 7.3 自定义 RHBM 的最低结构

`.mat` 文件必须包含名为 `RHBM` 的结构体，当前几何与电磁组装至少使用：

| 字段 | 要求 |
| --- | --- |
| `RHBM.r` | 大小为 `[n1,n2,n3,3]` 的坐标网格，单位 m，规则等距。 |
| `RHBM.epsilon_r` | 大小为 `[n1,n2,n3]` 的相对介电常数。 |
| `RHBM.sigma_e` | 同尺寸电导率，单位 S/m。 |
| `RHBM.idxS` | 散射体素的 MATLAB 线性索引列向量。 |
| `RHBM.name` | 建议提供，便于追踪模型。 |

运行前检查：

```matlab
bodyPath = fullfile('data', 'bodies', ...
    'Scatterers/2mm/Multilayer_Sphere.mat');
S = load(bodyPath, 'RHBM');
RHBM = S.RHBM;

required = {'r','epsilon_r','sigma_e','idxS'};
assert(all(isfield(RHBM, required)), 'RHBM 缺少必需字段');
assert(isequal(size(RHBM.r,1), size(RHBM.epsilon_r,1)));
assert(isequal(size(RHBM.r,2), size(RHBM.epsilon_r,2)));
assert(isequal(size(RHBM.r,3), size(RHBM.epsilon_r,3)));
assert(isequal(size(RHBM.epsilon_r), size(RHBM.sigma_e)));
assert(all(isfinite(RHBM.epsilon_r(:))));
assert(all(isfinite(RHBM.sigma_e(:))));
assert(all(RHBM.idxS >= 1 & RHBM.idxS <= numel(RHBM.epsilon_r)));

res = abs(RHBM.r(2,1,1,1) - RHBM.r(1,1,1,1));
fprintf('尺寸: %s, 分辨率: %.3f mm, 散射体素: %d\n', ...
    mat2str(size(RHBM.epsilon_r)), res*1e3, numel(RHBM.idxS));
```

## 8. `CoilFile`：表面线圈（SIE）

值相对于 `data/coils/coil_files/`。当前仓库候选：

| JSON 值 | 说明 | JSON 基础端口/模式 |
| --- | --- | --- |
| `Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.005.msh` | 8 腿高通鸟笼线圈，文件名标识约 5 mm 网格 | 2，`TxRx` |
| `Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.0025.msh` | 同一鸟笼线圈，约 2.5 mm 网格 | 2，`TxRx` |
| `Head_Birdcage/Type_high_rad_12.3cm_legs_8_len_2cm_mesh_0.00125.msh` | 同一鸟笼线圈，约 1.25 mm 网格，成本最高 | 2，`TxRx` |
| `Head_Overlap/OverlapCoil_2_stacks.msh` | 双层重叠式头部接收阵列 | 16，`Rx` |
| `Head_StadiumTriangular/Stadium_Triangular.msh` | Stadium/Triangular 头部线圈 | 8，`TxRx` |
| `Head_StadiumTriangular/Stadium_Triangular_refined.msh` | 上述线圈的细化网格 | 8，`TxRx` |
| `SKYRA_Coil/SKYRA_Coil.msh` | SKYRA 线圈模型 | 2，`TxRx` |

每个 `CoilFile` 必须有同目录、同基本名称的 `.json` 集总元件文件。例如：

```text
SKYRA_Coil/SKYRA_Coil.msh
SKYRA_Coil/SKYRA_Coil.json
```

`CoilFile` 使用表面三角网格和 SIE；不要把 `wire_files` 中的文件填入此字段。

## 9. `WireFile`：导线线圈（WIE）

值相对于 `data/coils/wire_files/`。当前仓库候选：

| JSON 值 | 说明 | 基础端口/模式 |
| --- | --- | --- |
| `Head_Receivers/Head_Receive_Array_1_Coil.msh` | 单通道头部接收线圈 | 1，`Rx` |
| `Head_Receivers/Head_Receive_Array_1_Coil_z.msh` | 单通道、z 方向版本；成功示例使用 | 1，`Rx` |
| `Head_Receivers/Head_Receive_Array_1_Coil_4ports.msh` | 文件名标识 4 个内部加载/求解位置 | JSON 基础物理端口 1，`Rx` |
| `Head_Receivers/Head_Receive_Array_1_Coil_8ports.msh` | 文件名标识 8 个内部加载/求解位置 | JSON 基础物理端口 1，`Rx` |
| `Head_Receivers/Head_Receive_Array_8_Coils.msh` | 8 通道头部接收阵列 | 8，`Rx` |
| `Head_Receivers/Head_Receive_Array_16_Coils.msh` | 16 通道头部接收阵列 | 16，`Rx` |
| `Head_Receivers/Head_Receive_Array_31_Coils.msh` | 31 通道头部接收阵列 | 31，`Rx` |
| `Prostate_Receivers/Prostate_Array_8_Middle.msh` | 前列腺 8 通道中部阵列 | 8，JSON 含 `Rx`/`TxRx` 定义 |
| `Prostate_Receivers/Prostate_Array_8_Lateral.msh` | 前列腺 8 通道侧向阵列 | 8，JSON 含 `Rx`/`TxRx` 定义 |
| `Prostate_Receivers/Prostate_Array_16.msh` | 前列腺 16 通道阵列 | 16，JSON 含 `Rx`/`TxRx` 定义 |

同样必须存在同名 `.json` 文件。`WireFile` 使用导线离散和 WIE。

文件名中的 `4ports`/`8ports` 不一定等于最终 `SP_s` 的网络端口数。`TMD=1` 时，可优化的普通元件会临时转换为求解端口，因此日志可能显示多个 `Port:`，最终物理网络端口数应以 `size(solution.netp.SP_s)` 为准。

## 10. `ShieldFile`：屏蔽体

值相对于 `data/coils/shield_files/`。当前候选：

| JSON 值 | 说明 | 配套 JSON |
| --- | --- | --- |
| `SKYRA_Shields/SKYRA_shield_150cm_coarse.msh` | SKYRA 150 cm 粗网格被动屏蔽 | 无，按被动屏蔽读取 |
| `SKYRA_Shields/SKYRA_shield_150cm_fine.msh` | SKYRA 150 cm 细网格被动屏蔽 | 无，按被动屏蔽读取 |
| `Head_Shields/Stadium_Coil_Head_Shield.msh` | Stadium 头部线圈屏蔽 | 无，按被动屏蔽读取 |
| `SKYRA_Coil/SKYRA_Coil_Shielded.msh` | 带集总元件定义的 SKYRA 屏蔽/线圈组合 | 有同名 JSON，2 个 `TxRx` 基础端口 |

源码会检查同名 `.json`：存在时按带集总元件的表面结构读取；不存在时按被动屏蔽读取。

## 11. `CoilFile`、`WireFile`、`ShieldFile` 的组合

| Coil | Wire | Shield | 计算含义 |
| --- | --- | --- | --- |
| 有 | 空 | 空 | 表面线圈 + 人体，SVIE。 |
| 空 | 有 | 空 | 导线线圈 + 人体，WVIE。 |
| 有 | 有 | 空 | 表面线圈 + 导线线圈 + 人体，WSVIE。 |
| 任意 | 任意 | 有 | 在上述系统上加入屏蔽耦合。 |
| 空 | 空 | 空 | 不建立线圈；`MARIE_runner` 会尝试从 `BasisFile` 读取外部电磁基激励。 |

不要把同一个物理线圈同时作为 `CoilFile` 和 `WireFile` 重复加入。两者同时非空仅适用于确实包含两类离散结构的系统。

## 12. `SurfaceBasisSupportFile`：表面支撑基

该字段相对于 `data/coils/basis_files/`。

- `MARIE_runner`（`geo_flag=1`）：忽略。
- `MRGF_runner`（`geo_flag=4`）：忽略。
- `BASIS_runner` 且 `geo_flag=2`：必填，用它生成表面支撑电磁基。
- `BASIS_runner` 且 `geo_flag=3`：忽略，源码根据人体掩膜自动生成体外偶极子支撑层。

当前表面网格候选：

```text
Ultimate_basis/Ella_Head.msh
Ultimate_basis/Duke_Head.msh
Ultimate_basis/Duke_HeadCervicalSpine.msh
Ultimate_basis/Billie_Head.msh
Elliptic_Cylinder_basis/Duke_Body.msh
Stadium_basis/Duke_Head.msh
Stadium_basis/Billie_Head.msh
Cylinder_basis/Duke_Head.msh
Helmet_basis/Duke_Head.msh
Bell_basis/Duke_Head.msh
Bell_basis/Duke_Head_refined.msh
```

支撑网格必须与所选人体模型在坐标、尺度和覆盖区域上匹配。仅因文件名同为 `Head` 并不能保证几何兼容。

## 13. `TMD`：调谐、匹配与去耦模式

| 值 | 实际行为 |
| --- | --- |
| `0` | 不优化标记为可调的普通元件，使用线圈 JSON 中已有元件值进入无优化协同仿真/校准分支。 |
| `1` | 启用调谐、匹配、去耦相关优化；`optim.boolean=true/1` 的普通元件会在几何阶段转换为求解端口。 |

因此 `TMD=0` 不应简单理解为“完全跳过 co-simulation”；`MARIE_runner` 仍会调用 `co_simulation`，只是进入不优化分支。

`TMD=1` 的前提是对应线圈 `.json` 中正确提供：

```text
type, load, value, Q, optim.boolean, optim.minim,
optim.maxim, optim.symmetry, excitation.entity, excitation.TxRx
```

优化范围、对称约束、元件 Q 和 Tx/Rx 类型不合理都会导致“数值优化成功但物理结果错误”。

## 14. `BasisFile`：预计算电磁基/MRGF 文件

值相对于 `data/bases/`，但它在不同 Runner 中的角色不同：

| Runner/场景 | `BasisFile` 的角色 |
| --- | --- |
| `MARIE_runner` 且存在 Coil/Wire/Shield | Runner 注释说明该字段被忽略，不决定当前线圈激励。 |
| `MARIE_runner` 且 Coil/Wire/Shield 全空 | 作为外部电磁基激励，代码读取 `/BASIS/Ue` 和 `/BASIS/Ub`。 |
| `BASIS_runner` | 输出文件名；生成的 `BASIS` 结构保存到此文件。 |
| `MRGF_runner` | 必需输入；读取 `Ue`、`Ub`、`U_hat_inv`、`S_hat_inv`、`V_hat_inv` 和 `X`。 |

当前仓库的 `data/bases/` 只有占位文件 `test.txt`，没有可直接使用的 `.mat` 电磁基。示例 JSON 中的 `Duke_head_5mm_PWC_7T.mat` 在当前仓库并不存在；成功示例之所以仍能运行，是因为 `WireFile` 非空，`BasisFile` 未作为激励读取。

Basis 文件必须与以下条件一致：

- `BodyFile` 和体素分辨率；
- `B0`、`Nucleus` 和频率相关介电参数；
- `Basis_Functions_VIE`（PWC/PWL）；
- 表面支撑或偶极子支撑类型；
- 生成它的 MARIE 数据结构版本。

## 15. 推荐配置模板

### 15.1 已验证的最小 Rx 测试

```json
{
  "B0": 3.0063,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 1,
  "BodyFile": "Scatterers/2mm/Multilayer_Sphere.mat",
  "CoilFile": "",
  "WireFile": "Head_Receivers/Head_Receive_Array_1_Coil_z.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": "Duke_head_5mm_PWC_7T.mat"
}
```

这是当前已跑通的流程测试。其 `BasisFile` 不存在但被忽略；为减少误解，也可以将其改为空字符串：

```json
"BasisFile": ""
```

### 15.2 3 T、31 通道头部接收阵列模板

```json
{
  "B0": 3.0063,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "RHBM/2mm/Hugo_Head_3T_compatible.mat",
  "CoilFile": "",
  "WireFile": "Head_Receivers/Head_Receive_Array_31_Coils.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": ""
}
```

其中 `Hugo_Head_3T_compatible.mat` 是建议的新文件名，不是仓库现有文件；使用前必须从原始 Hugo 模型生成符合当前 `RHBM.idxS` 要求的兼容副本。31 通道和解剖模型计算量很大，建议先用 PWC。

### 15.3 5 T 自定义头部研究模板

```json
{
  "B0": 5.0,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "RHBM/2mm/Custom_Head_5T.mat",
  "CoilFile": "",
  "WireFile": "Head_Receivers/Head_Receive_Array_31_Coils.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": ""
}
```

`Custom_Head_5T.mat` 必须由用户提供，并使用约 212.89 MHz 下适当的组织介电参数。此模板不能直接引用 `Hugo_Head_3T.mat` 后声称得到物理一致的 5 T 结果。

## 16. 配置文件预检查脚本

在正式组装前执行以下 MATLAB 代码，可以提前发现大多数路径和字段错误：

```matlab
cd('/home/<user>/marie-tools')
startup

inputFile = fullfile('data', 'inputs', 'inp_my_case.json');
assert(isfile(inputFile), '输入 JSON 不存在');

cfg = jsondecode(fileread(inputFile));
required = {'B0','Nucleus','Basis_Functions_VIE','BodyFile', ...
    'CoilFile','WireFile','ShieldFile','SurfaceBasisSupportFile', ...
    'TMD','BasisFile'};
assert(all(isfield(cfg, required)), 'JSON 缺少必需字段');

assert(isnumeric(cfg.B0) && isscalar(cfg.B0) && ...
    isfinite(cfg.B0) && cfg.B0 > 0, 'B0 必须是正数');
assert(ismember(double(cfg.Basis_Functions_VIE), [0 1]), ...
    'Basis_Functions_VIE 只能是 0 或 1');
assert(ismember(double(cfg.TMD), [0 1]), 'TMD 只能是 0 或 1');

nuclei = ["1H","2H","3HE","13C","7LI","15N","17O", ...
    "23NA","25MG","31P","35CL","39K","59CO","79BR", ...
    "87RB","129XE"];
assert(any(strcmpi(string(cfg.Nucleus), nuclei)), '不支持的 Nucleus');

bodyPath = fullfile('data', 'bodies', cfg.BodyFile);
assert(isfile(bodyPath), 'BodyFile 不存在：%s', bodyPath);

if ~isempty(cfg.CoilFile)
    p = fullfile('data','coils','coil_files',cfg.CoilFile);
    assert(isfile(p), 'CoilFile 不存在：%s', p);
    [folder,name] = fileparts(p);
    assert(isfile(fullfile(folder,[name '.json'])), ...
        'CoilFile 缺少同名 JSON');
end

if ~isempty(cfg.WireFile)
    p = fullfile('data','coils','wire_files',cfg.WireFile);
    assert(isfile(p), 'WireFile 不存在：%s', p);
    [folder,name] = fileparts(p);
    assert(isfile(fullfile(folder,[name '.json'])), ...
        'WireFile 缺少同名 JSON');
end

if ~isempty(cfg.ShieldFile)
    p = fullfile('data','coils','shield_files',cfg.ShieldFile);
    assert(isfile(p), 'ShieldFile 不存在：%s', p);
end

if ~isempty(cfg.SurfaceBasisSupportFile)
    p = fullfile('data','coils','basis_files', ...
        cfg.SurfaceBasisSupportFile);
    assert(isfile(p), 'SurfaceBasisSupportFile 不存在：%s', p);
end

if ~isempty(cfg.BasisFile)
    p = fullfile('data','bases',cfg.BasisFile);
    if ~isfile(p)
        warning('BasisFile 当前不存在；确认它是待生成输出或本次会被忽略');
    end
end

S = load(bodyPath, 'RHBM');
assert(isfield(S, 'RHBM'), 'BodyFile 中没有 RHBM 结构');
assert(all(isfield(S.RHBM, {'r','epsilon_r','sigma_e','idxS'})), ...
    'RHBM 缺少 r/epsilon_r/sigma_e/idxS');

fprintf('JSON 和基础文件结构检查通过。\n');
```

## 17. 常见配置错误

| 现象 | 常见原因 |
| --- | --- |
| `Reference to non-existent field` | JSON 删除了必需字段，或 RHBM 缺少 `idxS`。 |
| `fopen/fread` 报错 | `.msh` 对应的同名线圈 JSON 缺失，或路径写错。 |
| 找不到 Body/Coil/Wire 文件 | 没有从仓库根目录运行，未执行 `startup`，或字段路径多写了顶层目录。 |
| 结果只有 `Rx`、访问 `Tx` 报错 | 线圈 JSON 的 `excitation.TxRx` 定义为纯 `Rx`，属于预期行为。 |
| 日志端口数多于最终 S 参数端口数 | `TMD=1` 将可优化元件临时转换成求解端口；最终端口以 `SP_s` 为准。 |
| 只改 B0 后结果看似能跑 | 数值流程可能成功，但 BodyFile 介电参数可能仍属于原频率，物理上不一致。 |
| MRGF 找不到 HDF5 数据集 | `BasisFile` 不存在、不是 BASIS 输出，或缺少 MRGF 压缩算子。 |
| 内存快速耗尽 | 使用 1 mm 模型、PWL、多通道线圈或细表面网格导致未知量过大。 |

## 18. 研究任务的推荐配置顺序

1. 用 2 mm 多层球体、单通道线圈和 PWC/PWL 跑通流程。
2. 固定线圈，只替换 BodyFile，验证人体模型结构和位置。
3. 固定人体模型，只替换线圈，检查几何覆盖、端口和匹配。
4. 再启用多通道、细网格或 PWL。
5. 最后生成匹配条件下的 `BasisFile`，进入 MRGF/UISNR 工作流。
6. 每个结果保留对应 JSON、线圈 JSON/MESH、人体模型版本和代码提交号。
