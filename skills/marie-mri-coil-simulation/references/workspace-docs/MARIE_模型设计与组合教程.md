# MARIE 3.0 模型设计与组合教程

本教程用于从零创建并组合 MARIE 的 BodyFile、WireFile、CoilFile 和 ShieldFile。推荐的工作方式是：先独立验证每个部件，再逐步组合；不要第一次就同时修改线圈、体模和屏蔽。

## 1. 四类模型与选择原则

| JSON 字段 | 模型 | 适用场景 | 是否需同名 JSON |
|---|---|---|---|
| BodyFile | 体积散射体 | 均匀球、头部或人体体模 | 否 |
| WireFile | 细导线模型，WIE | Loop、Dipole、Birdcage 导线 | 是，通常需要 |
| CoilFile | 导电表面模型，SIE | 铜片、PCB、柔性表面线圈 | 是 |
| ShieldFile | 导电屏蔽表面 | 圆筒屏蔽、RF cage | 仅带端口/元件时需要 |

选择规则：

1. 可近似为细圆导线的线圈，先选 WireFile。它最适合快速验证 Loop 阵列。
2. 导体宽度、开槽、铜带、PCB 走线会影响结果时，选 CoilFile。
3. 连续、无端口的金属圆筒或屏蔽罩，作为无源 ShieldFile。
4. 屏蔽上带缝隙、端口或集总元件时，按表面结构建模并提供同名 JSON。
5. BodyFile 决定体积网格、介电参数和计算量，应最先完成。

建议的组合递进：

1. BodyFile + 单通道 WireFile。
2. BodyFile + 多通道 WireFile。
3. BodyFile + WireFile + 无源 ShieldFile。
4. 需要真实导体宽度时，用 CoilFile 替换或补充 WireFile。

## 2. 目录、文件名与版本

MARIE 从固定目录读取模型：

~~~text
/home/<user>/marie-tools/
  data/coils/wire_files/
  data/coils/coil_files/
  data/coils/shield_files/
  data/bodies/
  data/inputs/
  data/solutions/
~~~

建议为每个案例建立 Custom 子目录：

~~~text
data/
  coils/
    wire_files/Custom/CaseA_8Loop.msh
    wire_files/Custom/CaseA_8Loop.json
    coil_files/Custom/CaseA_CopperArray.msh
    coil_files/Custom/CaseA_CopperArray.json
    shield_files/Custom/CaseA_Shield.msh
  bodies/Custom/CaseA_Sphere200_2mm_5T.mat
  inputs/inp_CaseA_8LoopSphere.json
~~~

规则：

- WireFile/CoilFile 的 MSH 与配套 JSON 必须同名，只扩展名不同。
- JSON 写相对于各模型根目录的路径，例如 Custom/CaseA_8Loop.msh。
- 不覆盖内置示例；显著改动时创建新版本，例如 CaseA_v02。
- 保存 CAD 或 Gmsh 源文件、MSH、元件 JSON、输入 JSON 和参数记录。

## 3. 全部模型共用的坐标与单位规范

MARIE 几何坐标使用 m。常见换算：

| 含义 | 数值 |
|---|---:|
| 200 mm 球直径 | 0.200 m |
| 100 mm 球半径 | 0.100 m |
| 2 mm 体素 | 0.002 m |
| 20 mm 间隙 | 0.020 m |

建议统一坐标系：

- 体模中心设为原点 [0, 0, 0]。
- z 为轴向，x-y 为横断面。
- 环形 Loop 阵列绕 z 轴分布。

定义以下几何边界：

~~~text
R_body   < R_coil < R_shield
~~~

对直径约 200 mm 的球体，一组保守起点是 R_body=0.100 m、R_coil=0.125 m、R_shield=0.160 m。这只是工程起点；最终间距和尺寸应由频率、人体负载、耦合和可制造性确定。

最常见错误是把 mm 当成 m，导致尺寸放大 1000 倍。所有 CAD 导出和 MSH 中的坐标都必须再次确认。

## 4. 创建 BodyFile

### 4.1 必需字段

BodyFile 是 MAT 文件，必须至少包含 RHBM：

~~~matlab
RHBM.r          % [nx, ny, nz, 3]，体素中心坐标，单位 m
RHBM.epsilon_r  % [nx, ny, nz]，相对介电常数
RHBM.sigma_e    % [nx, ny, nz]，电导率，单位 S/m
RHBM.idxS       % [nActive, 1]，活动体素在线性索引中的位置
~~~

网格应为规则笛卡尔网格，且 x、y、z 的间隔一致或至少各自等间距。MARIE 会从 RHBM.r 推断网格分辨率。

### 4.2 生成直径 200 mm 的均匀球

以下脚本在 data/bodies/Custom 下创建半径 100 mm、体素 2 mm 的球体。介电参数仅用于演示，正式 5 T 计算前必须替换为目标频率下可信的材料数据。

~~~matlab
cd('/home/<user>/marie-tools')

outDir = fullfile(pwd, 'data', 'bodies', 'Custom');
if ~exist(outDir, 'dir'), mkdir(outDir); end

dx = 0.002;
Rbody = 0.100;
axis1 = -0.110:dx:0.110;
[X, Y, Z] = ndgrid(axis1, axis1, axis1);
mask = X.^2 + Y.^2 + Z.^2 <= Rbody^2;

RHBM.r = cat(4, X, Y, Z);
RHBM.idxS = find(mask);
RHBM.epsilon_r = ones(size(mask));
RHBM.sigma_e = zeros(size(mask));
RHBM.epsilon_r(mask) = 50;
RHBM.sigma_e(mask) = 0.6;

save(fullfile(outDir, 'CaseA_Sphere200_2mm_5T.mat'), 'RHBM', '-v7.3');
~~~

检查：

~~~matlab
B = load(fullfile(pwd, 'data', 'bodies', 'Custom', ...
    'CaseA_Sphere200_2mm_5T.mat'), 'RHBM');
assert(isfield(B, 'RHBM'));
assert(size(B.RHBM.r, 4) == 3);
assert(isequal(size(B.RHBM.epsilon_r), size(B.RHBM.sigma_e)));
assert(isvector(B.RHBM.idxS) && size(B.RHBM.idxS,2) == 1);
assert(all(B.RHBM.idxS >= 1 & B.RHBM.idxS <= numel(B.RHBM.epsilon_r)));
fprintf('网格: %s; 有效体素: %d\n', ...
    mat2str(size(B.RHBM.epsilon_r)), numel(B.RHBM.idxS));
~~~

首次设计时建议先使用 3 到 5 mm 粗网格完成流程验证，确认无误后再提高分辨率。

## 5. 创建 WireFile：Loop 与细导线线圈

### 5.1 格式要求

WireFile 使用 ASCII Gmsh 2.2 MSH。当前代码读取：

- Gmsh Point 单元，type 15：端口位置。
- Gmsh Line 单元，type 1：导线段。

坐标单位必须为 m。

### 5.2 端口与电路 JSON 的一一映射

当前 Wire 加载过程按 MSH 中 Point 出现的顺序创建端口，并按 JSON 中 elements 的顺序读取元件。因此必须保持：

~~~text
第 1 个 Point <-> 第 1 个 JSON element
第 2 个 Point <-> 第 2 个 JSON element
...
~~~

对 8 通道 Rx 阵列：

- MSH 中应有 8 个端口 Point。
- 同名 JSON 中应有 8 个 elements。
- number 推荐连续为 1 到 8。
- 每个元素的 excitation.entity 对应同一编号。
- 纯接收通道写 excitation.TxRx 为 Rx。

### 5.3 导线拓扑

每个 Loop 必须由连续 Line 构成闭合回路，相邻导线段共享节点。不同 Loop 的 Line 不要在元素列表中交错，推荐导出顺序为：

~~~text
Point 1 到 Point 8
Loop 1 的所有 Line
Loop 2 的所有 Line
...
Loop 8 的所有 Line
~~~

只有几何上接近、但节点没有连接的线段，会被识别为断开的导线。

### 5.4 Gmsh 结构示意

以下是一个平面 Loop 的结构示意，实际阵列应使用参数脚本批量生成并绕 z 轴旋转：

~~~geo
lc = 0.010;
Point(1) = {0.125, 0.000, 0.000, lc};  // 端口点
Point(2) = {0.125, 0.030, 0.000, lc};
Point(3) = {0.095, 0.030, 0.000, lc};
Point(4) = {0.095,-0.030, 0.000, lc};
Point(5) = {0.125,-0.030, 0.000, lc};
Line(1) = {2,3};
Line(2) = {3,4};
Line(3) = {4,5};
Line(4) = {5,2};
~~~

### 5.5 配套电路 JSON

创建同目录同名文件 CaseA_8Loop.json。一个端口条目的模板如下：

~~~json
{
  "coil_configuration": {
    "name": "CaseA 8-channel loop receive array",
    "tmd": false,
    "elements": [
      {
        "number": 1,
        "type": "port",
        "load": "capacitorParallel_inductorSeries_capacitorParallel",
        "value": [1.0e-12, 1.0e-9, 1.0e-12],
        "Q": [500, 200, 500],
        "optim": {
          "boolean": 1,
          "minim": [0.1e-12, 0.1e-9, 0.1e-12],
          "maxim": [20e-12, 10e-9, 20e-12],
          "symmetry": 1
        },
        "cross_talk": {},
        "excitation": {"entity": 1, "TxRx": "Rx"}
      }
    ]
  }
}
~~~

将模板扩展为 8 个 elements，并逐项更新 number 和 entity。value、Q、optim 范围必须依据实际元件和目标频率设定，不能把示例数字当作最终 5 T 电路设计。

## 6. 创建 CoilFile：表面铜片、PCB 与宽导体

当导体宽度、开槽、铜带形状、PCB 走线或表面电流分布重要时，应使用 CoilFile。

### 6.1 表面网格要求

CoilFile 使用 ASCII Gmsh 2.2，当前解析器支持：

- Line：端口或集总元件的支撑边。
- Triangle：三角形导电面。
- Quadrangle：四边形导电面。

必须满足：

1. 导电表面连通、无退化面。
2. 每条端口/元件 Line 恰好是两张三角面的公共边。
3. 不要把单纯外轮廓边导出为 Line 元素，否则可能报错 Expected to find exactly two triangles for each line。
4. 端口/元件 Line 使用正的物理标签。
5. 物理标签最好从 1 连续编号，且与 JSON elements 顺序一致。

当前代码使用 Line 的第一个物理标签识别元件。CAD/Gmsh 导出后要确认物理标签没有被自动重排。

### 6.2 表面网格与 JSON 的映射

最保守规则：

~~~text
物理 Line 标签 1 <-> JSON elements 第 1 项
物理 Line 标签 2 <-> JSON elements 第 2 项
...
~~~

一个 Loop 有两个电容缝隙和一个馈电端口时，可将三条内部支撑 Line 分别设为物理组 1、2、3，并在同名 JSON 中提供三个元素。JSON 结构和 WireFile 类似，但对象是表面网格的物理 Line，而不是 MSH Point。

### 6.3 递进验证

不要直接做 8 通道复杂表面网格。按以下顺序验证：

1. 单个铜片，仅三角面。
2. 单 Loop，加入一个端口 Line。
3. 单通道 Loop，加入全部电容 Line 和 JSON。
4. 两通道阵列，检查耦合。
5. 扩展为完整阵列。

每一步先进行第 10 节的几何预检，确认网格拓扑通过后再运行完整仿真。

## 7. 创建 ShieldFile

### 7.1 无源屏蔽

连续、无端口的圆筒屏蔽罩或 RF cage 可只创建：

~~~text
data/coils/shield_files/Custom/CaseA_Shield.msh
~~~

此类屏蔽不需要虚构端口或电路元件。加入屏蔽后应重新检查调谐、匹配和 S 参数。

### 7.2 带缝隙或端口的屏蔽

屏蔽带有缝隙、电容、端口或需要显式求解电流时，创建：

~~~text
CaseA_Shield.msh
CaseA_Shield.json
~~~

网格 Line 的物理标签和同名 JSON 的映射规则与 CoilFile 相同。

## 8. 组合为输入 JSON

“均匀球 + 8 通道 Wire Loop + 无源屏蔽”的输入骨架：

~~~json
{
  "B0": 5.0,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "Custom/CaseA_Sphere200_2mm_5T.mat",
  "CoilFile": "",
  "WireFile": "Custom/CaseA_8Loop.msh",
  "ShieldFile": "Custom/CaseA_Shield.msh",
  "SurfaceBasisSupportFile": "",
  "TMD": 0,
  "BasisFile": ""
}
~~~

首次验证建议 Basis_Functions_VIE 为 0，即 PWC。CoilFile、WireFile、ShieldFile 可留空字符串，但至少要提供一个线圈文件。TMD、BasisFile 和各字段的完整取值规则见 MARIE_JSON文件配置指南.md。

Rx 阵列的元素应写 TxRx=Rx。工具箱仍可基于电磁互易性构造等效发射相关量；这不表示该实际硬件已经成为发射线圈。

## 9. 仿真前的文件检查

在 data/inputs 下创建 check_CaseA.m：

~~~matlab
function check_CaseA()
root = '/home/<user>/marie-tools';
inputFile = fullfile(root, 'data', 'inputs', 'inp_CaseA_8LoopSphere.json');
cfg = jsondecode(fileread(inputFile));

bodyPath = fullfile(root, 'data', 'bodies', cfg.BodyFile);
assert(isfile(bodyPath), '找不到 BodyFile: %s', bodyPath);
B = load(bodyPath, 'RHBM');
assert(isfield(B, 'RHBM'), 'BodyFile 缺少 RHBM');

checkMesh(root, 'wire_files', cfg.WireFile, true);
checkMesh(root, 'coil_files', cfg.CoilFile, true);
checkMesh(root, 'shield_files', cfg.ShieldFile, false);
fprintf('基础文件检查通过。\n');
end

function checkMesh(root, typeDir, relPath, needJson)
if isempty(relPath), return; end
meshPath = fullfile(root, 'data', 'coils', typeDir, relPath);
assert(isfile(meshPath), '找不到网格: %s', meshPath);
fprintf('找到网格: %s\n', meshPath);
if needJson
    [folder, base, ~] = fileparts(meshPath);
    jsonPath = fullfile(folder, [base, '.json']);
    assert(isfile(jsonPath), '缺少同名 JSON: %s', jsonPath);
    C = jsondecode(fileread(jsonPath));
    assert(isfield(C, 'coil_configuration'), 'JSON 缺少 coil_configuration');
    assert(isfield(C.coil_configuration, 'elements'), 'JSON 缺少 elements');
    fprintf('匹配电路元件数: %d\n', numel(C.coil_configuration.elements));
end
end
~~~

执行：

~~~matlab
cd('/home/<user>/marie-tools')
startup
check_CaseA
~~~

它只验证文件、目录和基础结构，不能替代电磁求解，但能提前发现路径拼写、BodyFile 缺字段、MSH 缺失和同名 JSON 缺失。

## 10. 只装配几何，不进行完整求解

通过文件检查后，先装配并查看几何：

~~~matlab
cd('/home/<user>/marie-tools')
startup

MREDM = load_inputs('inp_CaseA_8LoopSphere.json');
MREDM = geo_assembly(MREDM, 1);
visualize_geometry(MREDM)
disp(MREDM.dimensions)
~~~

逐项检查：

1. 体模是否居中、尺寸正确。
2. Loop 是否在体模外，且没有与屏蔽相交。
3. 端口数量是否等于通道数。
4. Loop 的位置、旋转、法向和重叠是否符合设计。
5. 是否存在 1000 倍单位错误。

必要时查看体模边界：

~~~matlab
r = MREDM.r;
fprintf('x: [%g, %g] m\n', min(r(:,:,:,1), [], 'all'), max(r(:,:,:,1), [], 'all'));
fprintf('y: [%g, %g] m\n', min(r(:,:,:,2), [], 'all'), max(r(:,:,:,2), [], 'all'));
fprintf('z: [%g, %g] m\n', min(r(:,:,:,3), [], 'all'), max(r(:,:,:,3), [], 'all'));
clear MREDM
~~~

## 11. 推荐的端到端开发流程

### 阶段 A：体模

1. 创建并检查 BodyFile。
2. 用粗网格确认体积、中心和材料掩膜正确。

### 阶段 B：单通道线圈

1. 创建单 Loop WireFile 或 CoilFile。
2. 创建配套 JSON。
3. 运行文件检查、几何装配和完整 MARIE_runner。
4. 检查 S11、调谐状态和接收场。

### 阶段 C：少通道阵列

1. 扩展到 2 或 4 通道。
2. 检查端口顺序、重叠和耦合。
3. 先解决异常 S 参数和调谐失败。

### 阶段 D：完整阵列

1. 扩展到目标通道数。
2. 在粗体素网格完成一次端到端仿真。
3. 通过后使用正式 BodyFile 分辨率。

### 阶段 E：屏蔽

1. 先加入无源 ShieldFile。
2. 重复几何预检。
3. 重跑调谐/匹配与网络参数。
4. 比较有无屏蔽时的耦合、接收场和 SNR。

## 12. 常见错误与优先排查

| 现象 | 常见原因 | 优先处理 |
|---|---|---|
| 找不到 MSH/MAT | JSON 相对路径写错 | 检查对应数据根目录 |
| 找不到同名 JSON | WireFile/CoilFile 未配套电路文件 | 同目录、同文件主名 |
| 端口索引越界 | MSH 端口数与 elements 数不同 | Point/物理 Line 与 JSON 顺序 |
| two triangles 报错 | 端口 Line 不是两张三角面的公共边 | 修改表面网格拓扑 |
| 模型极大或极小 | mm 与 m 混用 | 检查 CAD 和 MSH 坐标 |
| 自动调谐不收敛 | 元件范围不合理、耦合过强、结构相交 | optim 范围和几何间隙 |
| S 参数异常 | 端口顺序错位、端口定义错误 | MSH 与 JSON 映射 |
| 计算量异常大 | 网格太细、体模包围盒太大 | BodyFile 分辨率和外部空白 |

## 13. 提交正式仿真前的清单

- [ ] BodyFile 含 RHBM.r、RHBM.epsilon_r、RHBM.sigma_e、RHBM.idxS。
- [ ] 所有坐标以 m 为单位，所有组件采用同一坐标系。
- [ ] 体模、线圈、屏蔽不穿透或重叠。
- [ ] WireFile 的 Point 数与 JSON elements 数一致。
- [ ] CoilFile 的物理 Line 标签与 JSON elements 顺序一致。
- [ ] 表面端口 Line 均为两张三角面的公共边。
- [ ] MSH 和配套 JSON 同名并在同一目录。
- [ ] 已运行 check_CaseA、geo_assembly 和 visualize_geometry。
- [ ] 已先在粗网格、少通道模型完成一次端到端仿真。
- [ ] 已保存 CAD/Gmsh 源文件、输入 JSON 和版本参数。

## 14. 相关文档

- JSON 字段、候选模型和取值规则：MARIE_JSON文件配置指南.md。
- 仿真、结果保存、回看与异常处理：MARIE_使用指南_Codex经验.md。
- runner 的用途与输入输出：MARIE_Runner算法与使用指南.md。
- 几何、场、网络参数和电流的绘图：MARIE_可视化脚本使用指南.md。
