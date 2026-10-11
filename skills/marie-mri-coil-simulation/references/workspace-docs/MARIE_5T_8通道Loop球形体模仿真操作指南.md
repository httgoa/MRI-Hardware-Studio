# MARIE 3.0：5 T、8 通道 Loop 接收阵列与球形体模仿真操作指南

> 修订日期：2026-08-06。当前版本已纳入首次试算暴露的独立通道优化失配问题，并以四变量旋转对称电路配置替代原来的宽范围独立优化方案。

## 1. 项目目标

建立一个可复现的 MARIE 3.0 仿真项目：

- 5 T 主磁场；
- `1H` 氢核，拉莫尔频率约 212.887 MHz；
- 直径 200 mm 的均匀有耗球形数值 phantom；
- 8 通道单排 Loop 接收阵列；
- Loop 安装在半径 115 mm 的圆柱面上，球体表面到线圈中部约 15 mm；
- 每个 Loop 方位覆盖约 50 度，相邻通道中心间隔 45 度，名义重叠约 5 度；
- 仅接收模式；
- 启用自动调谐、匹配和接收链路优化；
- 输出 S 参数、频率扫描、每通道 B1-、阵列 SNR、UISNR 和理想表面电流模式。

参考图中包含 Tx 模式、B1+ 和 SAR。当前项目明确为纯 Rx，因此不生成 Tx/B1+ 和 SAR；强行绘制这些量在物理定义和数据结构上都不合适。

## 2. 两条计算链

所需结果不能由一次 `MARIE_runner` 全部产生，需要执行两条计算链。

| 计算链 | Runner | 线圈模型 | 主要输出 |
| --- | --- | --- | --- |
| 实际 8 通道阵列 | `MARIE_runner` | 8 个离散 Loop 和集总元件 | S/Z 参数、频扫、B1-、噪声最优阵列 SNR |
| 理论上限 | `BASIS_runner`，`geo_flag=2` | 连续圆柱表面支撑基 | UISNR、理想电流权重、理想表面电流分布 |

UISNR 是给定体模、频率和允许电流支撑表面下的理论上限，不是 8 Loop 线圈自身的另一个输出。`SNR/UISNR` 才是评价实际阵列接近理论上限程度的指标。

## 3. 基线参数及选取理由

| 参数 | 基线值 | 选取理由 |
| --- | --- | --- |
| `B0` | 5 T | 用户指定 |
| `Nucleus` | `1H` | 用户指定；源码使用 42.577478518 MHz/T |
| 频率 | 212.88739259 MHz | `42.577478518 x 5` |
| phantom 半径 | 0.100 m | 直径 200 mm |
| phantom 分辨率 | 4 mm | 首轮 UISNR 计算更可控；与实际阵列使用同一网格 |
| `epsilon_r` | 50 | 均匀有耗数值 phantom 的基线参数 |
| `sigma_e` | 0.6 S/m | 均匀有耗数值 phantom 的基线参数 |
| VIE 基函数 | PWC，即 `0` | 未知量约为 PWL 的四分之一，适合首轮项目 |
| 线圈圆柱半径 | 0.115 m | 球体赤道处约 15 mm 间距 |
| Loop 高度 | 0.140 m | 覆盖球体中心区域，同时控制电感和计算规模 |
| Loop 方位宽度 | 50 度 | 8 通道中心间隔 45 度，形成约 5 度几何重叠 |
| 通道数 | 8 | 用户指定 |
| 工作模式 | `Rx` | 用户指定 |
| `TMD` | `1` | 启用自动优化 |
| UISNR 支撑面 | 半径 115 mm、高 140 mm 的开放圆柱侧面 | 与实际 Loop 所在圆柱面保持一致 |

`epsilon_r=50`、`sigma_e=0.6 S/m` 是用于跑通和比较的参数化数值基线，并非自动对应某种已标定实验液体。若后续要与实测 phantom 对照，必须替换成目标频率下测得或可靠来源给出的介电常数和电导率，并记录温度、配方和测量方法。

不建议直接把仓库的 `Multilayer_Sphere.mat` 改成 5 T 使用：该文件直径约 240 mm，并包含多层介电参数，既不符合本项目的 200 mm 均匀球，也不能通过修改 `B0` 自动变成 5 T 材料参数。

## 4. 文件规划

在 MARIE 根目录 `/home/<user>/marie-tools` 下使用以下文件：

```text
data/bodies/Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat
data/coils/wire_files/Custom/Sphere8Rx_R115_H140_Span50.msh
data/coils/wire_files/Custom/Sphere8Rx_R115_H140_Span50.json
data/coils/basis_files/Custom/Sphere_CylinderSupport_R115_H140.msh
data/inputs/inp_5T_1H_Sphere200_8LoopRx.json
data/inputs/inp_5T_1H_Sphere200_UISNR.json
data/bases/Sphere200_5T_PWC_CylSupport_UISNR.mat
RUN_5T_8CH_SPHERE.m
RUN_5T_SPHERE_UISNR.m
POST_5T_8CH_SPHERE.m
```

建议先备份当前仓库或创建 Git 分支，不要直接覆盖项目自带模型。

## 5. 生成 200 mm 均匀球形 phantom

在 MATLAB 中执行：

```matlab
cd('/home/<user>/marie-tools');
startup;

outDir = fullfile(pwd, 'data', 'bodies', 'Scatterers', '4mm');
if ~exist(outDir, 'dir'), mkdir(outDir); end

res = 0.004;                 % 4 mm
domainHalfWidth = 0.120;     % 240 mm 计算盒边长的一半
radius = 0.100;              % 200 mm diameter
epsr = 50;
sigma = 0.6;                 % S/m

g = -domainHalfWidth:res:domainHalfWidth;
[X,Y,Z] = ndgrid(g,g,g);
mask = (X.^2 + Y.^2 + Z.^2) <= radius^2;

RHBM = struct();
RHBM.name = 'Sphere_D200mm_4mm_eps50_sig0p6_5T';
RHBM.r = cat(4, X, Y, Z);
RHBM.epsilon_r = ones(size(X));
RHBM.sigma_e = zeros(size(X));
RHBM.rho = zeros(size(X));

RHBM.epsilon_r(mask) = epsr;
RHBM.sigma_e(mask) = sigma;
RHBM.rho(mask) = 1;
RHBM.idxS = find(mask);

bodyFile = fullfile(outDir, ...
    'Sphere_D200mm_4mm_eps50_sig0p6_5T.mat');
save(bodyFile, 'RHBM', '-v7.3');

fprintf('Saved: %s\n', bodyFile);
fprintf('Grid: %d x %d x %d\n', size(X));
fprintf('Active voxels: %d\n', numel(RHBM.idxS));
```

检查生成结果：

```matlab
T = load(bodyFile, 'RHBM');
assert(isfield(T.RHBM, 'idxS'));
assert(abs(max(T.RHBM.r(:,:,:,1),[],'all') - 0.12) < 1e-12);

mid = round(size(mask,3)/2);
figure('Color','w');
imagesc(g*1e3, g*1e3, squeeze(mask(:,:,mid))');
axis image xy;
xlabel('x (mm)'); ylabel('y (mm)');
title('200 mm spherical phantom');
```

首轮统一使用 4 mm。后续若资源允许，可把 `res` 改为 0.002，并为实际阵列和 BASIS 两条计算链同时重算；不能把 2 mm SNR 与 4 mm UISNR 直接逐体素相除。

## 6. 生成 8 通道重叠 Loop 导线网格

本方案采用圆柱贴合的矩形 Loop：上下边为圆柱圆弧，两侧边沿 z 方向。每个环离散为 80 条线段，并放置 8 个集总元件位置：1 个接收端口和 7 个分段电容位置。

在 MATLAB 中执行以下生成脚本：

```matlab
cd('/home/<user>/marie-tools');
startup;

outDir = fullfile(pwd, 'data', 'coils', 'wire_files', 'Custom');
if ~exist(outDir, 'dir'), mkdir(outDir); end

meshFile = fullfile(outDir, 'Sphere8Rx_R115_H140_Span50.msh');

nCh = 8;
Rc = 0.115;                 % cylindrical former radius, m
zHalf = 0.070;              % total height 140 mm
span = deg2rad(50);         % loop angular width
nArc = 24;                  % each top/bottom arc
nSide = 16;                 % each vertical side

nodes = zeros(0,3);
loopNodeIds = cell(nCh,1);

for ch = 1:nCh
    phi0 = 2*pi*(ch-1)/nCh;

    pTop = linspace(-span/2, span/2, nArc+1);
    top = [Rc*cos(phi0+pTop(:)), Rc*sin(phi0+pTop(:)), ...
           zHalf*ones(numel(pTop),1)];

    zr = linspace(zHalf, -zHalf, nSide+1);
    zr = zr(2:end);
    right = [Rc*cos(phi0+span/2)*ones(numel(zr),1), ...
             Rc*sin(phi0+span/2)*ones(numel(zr),1), zr(:)];

    pBottom = linspace(span/2, -span/2, nArc+1);
    pBottom = pBottom(2:end);
    bottom = [Rc*cos(phi0+pBottom(:)), Rc*sin(phi0+pBottom(:)), ...
              -zHalf*ones(numel(pBottom),1)];

    zl = linspace(-zHalf, zHalf, nSide+1);
    zl = zl(2:end-1);        % avoid duplicating both corner nodes
    left = [Rc*cos(phi0-span/2)*ones(numel(zl),1), ...
            Rc*sin(phi0-span/2)*ones(numel(zl),1), zl(:)];

    loop = [top; right; bottom; left];
    firstId = size(nodes,1) + 1;
    ids = firstId:firstId+size(loop,1)-1;
    nodes = [nodes; loop]; %#ok<AGROW>
    loopNodeIds{ch} = ids;
end

assert(all(cellfun(@numel, loopNodeIds) == 80));

% 每个通道 8 个集总元件位置：节点 1,11,...,71
lumpedLocal = 1:10:71;
nPoint = nCh*numel(lumpedLocal);
nLine = sum(cellfun(@numel, loopNodeIds));

fid = fopen(meshFile, 'w');
assert(fid > 0, 'Cannot create mesh file');
cleanup = onCleanup(@() fclose(fid));

fprintf(fid, '$MeshFormat\n2.2 0 8\n$EndMeshFormat\n');
fprintf(fid, '$Nodes\n%d\n', size(nodes,1));
for i = 1:size(nodes,1)
    fprintf(fid, '%d %.16g %.16g %.16g\n', ...
        i, nodes(i,1), nodes(i,2), nodes(i,3));
end
fprintf(fid, '$EndNodes\n');

fprintf(fid, '$Elements\n%d\n', nPoint+nLine);
eid = 0;

% 点元件顺序必须与线圈 JSON 的 64 个 elements 一致
for ch = 1:nCh
    ids = loopNodeIds{ch};
    for k = lumpedLocal
        eid = eid + 1;
        fprintf(fid, '%d 15 2 %d %d %d\n', ...
            eid, ch, ch, ids(k));
    end
end

% 每个 Loop 的线元件必须连续排列
for ch = 1:nCh
    ids = loopNodeIds{ch};
    for k = 1:numel(ids)
        n1 = ids(k);
        n2 = ids(mod(k,numel(ids))+1);
        eid = eid + 1;
        fprintf(fid, '%d 1 2 %d %d %d %d\n', ...
            eid, ch, ch, n1, n2);
    end
end
fprintf(fid, '$EndElements\n');

clear cleanup;
fprintf('Saved: %s\n', meshFile);
```

### 6.1 创建四变量旋转对称 Rx 电路 JSON

项目自带 `Head_Receive_Array_8_Coils.json` 可以作为字段结构模板，但**不能复制后只改名称就直接用于本项目**。该模板为 8 个通道分配了彼此独立的 `optim.symmetry` 组；在本项目的均匀球体和旋转对称 Loop 几何中，这会让粒子群同时搜索大量独立变量，可能产生只有个别通道匹配、其余通道谐振频率严重偏移的非对称解。

本项目把电路约束为四个共享优化变量：

1. 端口并联电容 `Cp1`；
2. 端口串联电感 `Ls`；
3. 端口并联电容 `Cp2`；
4. 每个 Loop 内 7 个相同的分段调谐电容 `Cseg`。

创建或重置当前线圈 JSON：

```matlab
srcJson = fullfile(pwd, 'data', 'coils', 'wire_files', ...
    'Head_Receivers', 'Head_Receive_Array_8_Coils.json');
dstJson = fullfile(pwd, 'data', 'coils', 'wire_files', ...
    'Custom', 'Sphere8Rx_R115_H140_Span50.json');

coilCfg = jsondecode(fileread(srcJson));
E = coilCfg.coil_configuration.elements;

% 5 T、200 mm 球形 phantom 的对称优化初值
refPort = [26.4530e-12, 23.7565e-9, 27.1397e-12];
refSegmentC = 2.7894e-12;

% co_simulation_matching_tuning_settings 会叠加元素位置偏移。
% 以下递减编号使 8 个通道最终映射到相同的 4 个内部变量。
portSym = [100 90 80 70 60 50 40 30];
tuneSym = [101 91 81 71 61 51 41 31];

for ch = 1:8
    idx = (ch-1)*8 + (1:8);

    E(idx(1)).value = refPort;
    E(idx(1)).optim.boolean = 1;
    E(idx(1)).optim.symmetry = portSym(ch);
    E(idx(1)).optim.minim = [5e-12, 5e-9, 5e-12];
    E(idx(1)).optim.maxim = [80e-12, 60e-9, 80e-12];

    for k = 2:8
        E(idx(k)).value = refSegmentC;
        E(idx(k)).optim.boolean = 1;
        E(idx(k)).optim.symmetry = tuneSym(ch);
        E(idx(k)).optim.minim = 1.5e-12;
        E(idx(k)).optim.maxim = 5.0e-12;
    end
end

coilCfg.coil_configuration.name = ...
    'Sphere8Rx_R115_H140_Span50.json';
coilCfg.coil_configuration.elements = E;

fid = fopen(dstJson, 'w');
assert(fid > 0);
fprintf(fid, '%s', jsonencode(coilCfg, PrettyPrint=true));
fclose(fid);
```

核验：

```matlab
J = jsondecode(fileread(dstJson));
E = J.coil_configuration.elements;

assert(numel(E) == 64);
assert(sum(strcmp({E.type}, 'port')) == 8);
assert(all(arrayfun(@(x) strcmp(x.excitation.TxRx,'Rx'), E)));
assert(all(arrayfun(@(x) x.optim.boolean == 1, E)));

expectedPortSym = [100 90 80 70 60 50 40 30];
expectedTuneSym = [101 91 81 71 61 51 41 31];
for ch = 1:8
    idx = (ch-1)*8 + (1:8);
    assert(E(idx(1)).optim.symmetry == expectedPortSym(ch));
    assert(all(arrayfun(@(x) x.optim.symmetry, E(idx(2:8))) == ...
               expectedTuneSym(ch)));
end
```

真正控制自动优化的是输入 JSON 的 `TMD=1`。线圈 JSON 顶层自带的字符串字段 `"tmd"` 在当前解析路径中不是主开关。

这里的初始值来自第一次试算中唯一在目标频率附近匹配成功的通道，只用于给共享优化提供合理起点，不是最终设计值。边界有意收窄，以避免再次出现约 `1 pF` 到 `130 pF`、约 `4 nH` 到 `95 nH` 的非物理通道分叉。若最终值贴住边界，应根据频扫方向逐步扩展对应边界，而不是一次恢复到原模板的十倍宽范围。

重要：MARIE 的 `co_simulation_store_elements` 会把优化后的元件值写回这个线圈 JSON。正式运行前应保存模板副本或将其纳入 Git；不要把一次失败优化后被回写的 JSON 误当成原始初值文件。

## 7. 创建常规 8 通道仿真 JSON

创建：

```text
data/inputs/inp_5T_1H_Sphere200_8LoopRx.json
```

内容：

```json
{
  "B0": 5.0,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat",
  "CoilFile": "",
  "WireFile": "Custom/Sphere8Rx_R115_H140_Span50.msh",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "",
  "TMD": 1,
  "BasisFile": ""
}
```

字段解释：

- `Basis_Functions_VIE=0`：PWC；首轮不要用 PWL。
- `CoilFile=""`：没有 SIE 表面线圈。
- `WireFile`：使用 WIE 导线 Loop。
- `ShieldFile=""`：本项目未加入 RF shield。
- `TMD=1`：执行自动调谐和匹配。
- `BasisFile=""`：常规线圈激励不需要预计算基。

## 8. 几何预检查

在开始昂贵求解之前，仅构建几何：

```matlab
cd('/home/<user>/marie-tools');
startup;

input_file = 'inp_5T_1H_Sphere200_8LoopRx.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);

figure('Color','w');
visualize_geometry(MREDM);
view(3);
axis equal;
rotate3d on;
title('5 T, 8-channel Rx loop array, 200 mm sphere');
```

必须目视确认：

1. 8 个 Loop 均匀分布在球体周围。
2. Loop 不穿入球体。
3. 相邻 Loop 的覆盖区域有小幅重叠，但导线不发生意外交叉。
4. z 方向中心和球体中心一致。
5. 端口数量为 8。

数值检查：

```matlab
fprintf('Larmor frequency: %.6f MHz\n', MREDM.emc.freq/1e6);
fprintf('Temporary WIE solve ports: %d\n', MREDM.dimensions.M_ports);
fprintf('Active voxels: %d\n', MREDM.dimensions.N_scat);

assert(abs(MREDM.emc.freq/1e6 - 212.88739259) < 1e-6);

coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere8Rx_R115_H140_Span50.json');
C = jsondecode(fileread(coilJson));
E = C.coil_configuration.elements;
assert(sum(strcmp({E.type},'port')) == 8);
```

`TMD=1` 时，MARIE 会把待优化的普通元件临时提升为数值求解端口。因此这里的 `MREDM.dimensions.M_ports` 可能是 64，而不是 8；这是优化装配机制。最终 co-simulation 收缩回 8 个物理接收端口，保存结果中的 `solution.netp.SP_s` 才应当是 `8 x 8`。

注意：`load_inputs` 会启动并行池。几何预检查也可能出现并行池启动信息，但不会进入完整电磁求解。

## 9. 创建并运行常规 Runner

不要反复修改项目自带 `MARIE_runner.m`。在根目录复制一份：

```matlab
copyfile(fullfile('src','src_runners','MARIE_runner.m'), ...
         'RUN_5T_8CH_SPHERE.m');
edit RUN_5T_8CH_SPHERE.m
```

把其中的：

```matlab
input_file = 'inp_MSphere_HeadCoil1z.json';
```

改成：

```matlab
input_file = 'inp_5T_1H_Sphere200_8LoopRx.json';
```

运行：

```matlab
cd('/home/<user>/marie-tools');
startup;
RUN_5T_8CH_SPHERE;
```

SSH 批处理方式：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
cd /home/<user>/marie-tools
~/MATLAB/R2025b/bin/matlab -batch "startup; RUN_5T_8CH_SPHERE"
```

预期输出文件：

```text
data/solutions/MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat
```

成功日志应依次出现 Geometry、WIE/VIE assembly、network parameters、co-simulation、electromagnetic fields 和 `[Saved]`。`TMD=1` 时日志可能显示 64 个临时求解端口：8 个物理端口加 56 个分段元件被临时提升为数值端口；最终保存的 `SP_s` 仍必须是 `8 x 8`。

重新运行同一个 `RUN_5T_8CH_SPHERE` 时，MATLAB 的 `save` 会直接覆盖：

```text
data/solutions/MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat
```

不需要提前删除失败 MAT 文件。需要保留失败案例时，应在重新运行前另行改名或复制；不需要保留时直接重新运行即可。

## 10. 常规结果完整性检查

```matlab
resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');

whos('-file', resultFile)
R = load(resultFile, 'solution');
solution = R.solution;

fieldnames(solution)
fieldnames(solution.netp)
fieldnames(solution.h_field)
fieldnames(solution.h_field.Rx)
fieldnames(solution.snr_field)

assert(isequal(size(solution.netp.SP_s), [8 8]));
assert(size(solution.h_field.Rx.b1m,4) == 8);
assert(isfield(solution.snr_field, 'SNR'));
```

### 10.1 区分 `SP_s`、`SP_p` 和频扫

纯 Rx 阵列不能只用 `solution.netp.SP_s` 的对角线判断匹配：

| 结果 | 物理/算法含义 | 本项目用途 |
| --- | --- | --- |
| `SP_s` | 常规多端口网络条件下的完整 S 矩阵 | 非对角线用于评估通道间互耦；对角线作为普通 50 Ω 条件参考 |
| `SP_p` | 其他接收通道按 `Preamp_res` 加载时，各通道的 Rx 反射 | 纯 Rx 工作条件下的主要匹配指标 |
| `figure_freq.SPm_plot_Rx` | 前置放大器加载条件下的 Rx 频率扫描 | 判断主谐振位置、匹配带宽和附加模态 |

MARIE 的纯 Rx 最终优化调用 `matching_and_tuning_and_preamplifierdecoupling`，因此应以 `SP_p` 和 Rx 频扫作为调谐匹配门控，同时保留 `SP_s` 非对角线作为几何/网络互耦指标。`SP_s` 对角线不低于 -15 dB，并不自动否定一个在前放加载条件下匹配良好的纯 Rx 设计。

### 10.2 一次性调谐、匹配和去耦检查

```matlab
SPsDB = 20*log10(abs(solution.netp.SP_s));
SPpDB = 20*log10(abs(solution.netp.SP_p(:)));
F = solution.netp.figure_freq;
nPorts = size(solution.netp.SP_s,1);

targetMHz = F.freq_range(F.freq_idx)/1e6;
targetDB = zeros(nPorts,1);
minimumDB = zeros(nPorts,1);
resonanceMHz = zeros(nPorts,1);

for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    [minimumDB(p),k] = min(curve);
    targetDB(p) = curve(F.freq_idx);
    resonanceMHz(p) = F.freq_range(k)/1e6;
end

couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;
[worstCouplingDB,linearIndex] = max(couplingDB,[],'all');
[worstRow,worstCol] = ind2sub(size(couplingDB),linearIndex);

fprintf('Port | SP_p target | sweep target | sweep min | f_min MHz\n');
for p = 1:nPorts
    fprintf('%4d | %11.3f | %12.3f | %9.3f | %9.6f\n', ...
        p,SPpDB(p),targetDB(p),minimumDB(p),resonanceMHz(p));
end
fprintf('Worst coupling: S%d%d = %.2f dB\n', ...
    worstRow,worstCol,worstCouplingDB);

assert(all(SPpDB < -15), ...
    'Rx matching failed under preamplifier loading');
assert(max(abs(resonanceMHz-targetMHz)) < 0.5, ...
    'At least one Rx resonance is more than 0.5 MHz from target');
assert(max(SPpDB)-min(SPpDB) < 3, ...
    'Unexpected matching asymmetry between channels');
assert(worstCouplingDB < -12, ...
    'Geometric/network decoupling failed: worst Sij is above -12 dB');
```

#### 10.2.1 分别检查调谐、匹配和去耦

下面三段代码互不依赖 `assert`，某项失败不会中断后续检查。运行前应已将结果加载到 `solution`：

```matlab
resultFile = fullfile(pwd,'data','solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');
R = load(resultFile,'solution');
solution = R.solution;
```

**A. 单独检查调谐：主谐振是否位于目标频率附近**

```matlab
F = solution.netp.figure_freq;
nPorts = size(solution.netp.SP_s,1);
targetMHz = F.freq_range(F.freq_idx)/1e6;
resonanceMHz = zeros(nPorts,1);
minimumDB = zeros(nPorts,1);

fprintf('\n[TUNING] target = %.6f MHz\n',targetMHz);
fprintf('Port | f_res (MHz) | offset (MHz) | minimum (dB)\n');
for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    [minimumDB(p),k] = min(curve);
    resonanceMHz(p) = F.freq_range(k)/1e6;
    fprintf('%4d | %11.6f | %+12.6f | %12.3f\n', ...
        p,resonanceMHz(p),resonanceMHz(p)-targetMHz,minimumDB(p));
end

tuningLimitMHz = 0.5;
if all(abs(resonanceMHz-targetMHz) < tuningLimitMHz)
    fprintf('PASS: all resonances are within %.2f MHz of target.\n', ...
        tuningLimitMHz);
else
    fprintf('FAIL: maximum resonance offset = %.3f MHz.\n', ...
        max(abs(resonanceMHz-targetMHz)));
end
```

**B. 单独检查匹配：目标频率处前放加载反射是否达标**

```matlab
SPpDB = 20*log10(abs(solution.netp.SP_p(:)));
matchLimitDB = -15;

fprintf('\n[MATCHING] preamplifier-loaded SP_p at target\n');
fprintf('Port | SP_p (dB) | result\n');
for p = 1:numel(SPpDB)
    if SPpDB(p) < matchLimitDB
        state = 'PASS';
    else
        state = 'FAIL';
    end
    fprintf('%4d | %9.3f | %s\n',p,SPpDB(p),state);
end

if all(SPpDB < matchLimitDB)
    fprintf('PASS: all Rx channels are below %.1f dB.\n',matchLimitDB);
else
    fprintf('FAIL: worst SP_p = %.2f dB; required < %.1f dB.\n', ...
        max(SPpDB),matchLimitDB);
end
```

**C. 单独检查去耦：定位最差非对角 `SP_s`**

```matlab
SPsDB = 20*log10(abs(solution.netp.SP_s));
nPorts = size(SPsDB,1);
couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;

[worstCouplingDB,idx] = max(couplingDB,[],'all');
[rowPort,colPort] = ind2sub(size(couplingDB),idx);
decouplingLimitDB = -12;

fprintf('\n[DECOUPLING] full SP_s matrix (dB)\n');
disp(round(SPsDB,2));
fprintf('Worst pair: S%d%d = %.2f dB\n', ...
    rowPort,colPort,worstCouplingDB);

if worstCouplingDB < decouplingLimitDB
    fprintf('PASS: all off-diagonal Sij are below %.1f dB.\n', ...
        decouplingLimitDB);
else
    fprintf('FAIL: worst Sij = %.2f dB; required < %.1f dB.\n', ...
        worstCouplingDB,decouplingLimitDB);
end
```

这里的 `-15 dB` 匹配门槛和 `-12 dB` 去耦门槛是本项目当前的最低筛查标准，可根据实验室设计规范修改。不要用 `SP_s` 对角线替代纯 Rx 的 `SP_p` 匹配检查。

#### 10.2.2 S 参数可视化与图片保存

运行前应已将结果加载到 `solution`。以下脚本分别显示常规多端口 `SP_s`、非对角互耦、目标频率处前放加载 `SP_p`，以及前放加载频率扫描。

```matlab
SPsDB = 20*log10(abs(solution.netp.SP_s));
SPpDB = 20*log10(abs(solution.netp.SP_p(:)));
F = solution.netp.figure_freq;
nPorts = size(SPsDB,1);
targetMHz = F.freq_range(F.freq_idx)/1e6;

outDir = fullfile(pwd,'data','solutions','figures_5T_8ch');
if ~exist(outDir,'dir'), mkdir(outDir); end

%% Figure 1: SP_s、互耦和 SP_p
f1 = figure('Color','w','Position',[100 100 1550 480]);
tiledlayout(1,3,'Padding','compact','TileSpacing','compact');

% 完整 SP_s，包括对角线参考值
nexttile;
imagesc(SPsDB,[-35 0]);
axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Excited port'); ylabel('Observed port');
title('Full SP_s (dB)');
colormap(gca,turbo(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        text(col,row,sprintf('%.1f',SPsDB(row,col)), ...
            'HorizontalAlignment','center','Color','w','FontSize',8);
    end
end

% 只显示非对角互耦，避免把 SP_s 对角线误认为 Rx 匹配指标
nexttile;
couplingPlot = SPsDB;
couplingPlot(1:nPorts+1:end) = NaN;
imagesc(couplingPlot,[-35 0]);
axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Excited port'); ylabel('Coupled port');
title('Off-diagonal coupling S_{ij} (dB)');
colormap(gca,turbo(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        if row ~= col
            text(col,row,sprintf('%.1f',SPsDB(row,col)), ...
                'HorizontalAlignment','center','Color','w','FontSize',8);
        end
    end
end

% 目标频率处前放加载匹配
nexttile;
bar(1:nPorts,SPpDB,0.65,'FaceColor',[0.20 0.50 0.80]);
hold on; yline(-15,'r--','-15 dB','LineWidth',1.3);
grid on; xlim([0.4 nPorts+0.6]); ylim([min(-30,min(SPpDB)-3) 0]);
xticks(1:nPorts);
xlabel('Rx port'); ylabel('SP_p (dB)');
title(sprintf('Preamplifier-loaded matching at %.3f MHz',targetMHz));
for p = 1:nPorts
    text(p,SPpDB(p)-0.8,sprintf('%.1f',SPpDB(p)), ...
        'HorizontalAlignment','center','VerticalAlignment','top');
end

exportgraphics(f1,fullfile(outDir,'01A_Sparams_matching_coupling.png'), ...
    'Resolution',300);

%% Figure 2: 8 通道前放加载回波损耗频扫
f2 = figure('Color','w','Position',[100 100 1250 650]);
hold on;
for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    plot(F.freq_range/1e6,curve,'LineWidth',1.5, ...
        'DisplayName',sprintf('S_{%d%d}',p,p));
end
xline(targetMHz,'k--',sprintf('Target %.3f MHz',targetMHz), ...
    'LabelVerticalAlignment','bottom');
yline(-15,'r:','-15 dB','LineWidth',1.3);
xlabel('Frequency (MHz)'); ylabel('Return loss (dB)');
title('8-channel preamplifier-loaded Rx frequency sweep');
grid on; ylim([-40 0]);
legend('Location','eastoutside');

exportgraphics(f2,fullfile(outDir,'01B_SPp_frequency_sweep.png'), ...
    'Resolution',300);

fprintf('S-parameter figures saved to: %s\n',outDir);
```

读图规则：

- `SP_p` 柱全部低于红色 `-15 dB` 线，表示目标频率处前放加载匹配通过；
- 频扫谷值的横坐标用于判断调谐，谷值深度用于判断匹配，两者不能混为一项；
- 非对角互耦热图中颜色最接近 0 dB 的格子是最差耦合通道对；
- 对称 8 通道阵列应呈循环重复矩阵。若只有一个通道对异常，应优先检查端口映射、元件编号和网格连续性；
- 当前设计标准下，非对角 `Sij<-12 dB` 为最低筛查要求，`<-15 dB` 更理想。

建议工程目标：

- `SP_p < -15 dB` 为最低 Rx 匹配目标，`<-20 dB` 更理想；
- 主谐振距离 212.887 MHz 小于 0.5 MHz；正式对比时建议进一步控制在 0.2 MHz 内；
- 8 通道 `SP_p` 极差小于约 3 dB，主谐振频率应近似重合；
- 最差非对角 `SP_s` 低于 -12 dB 为最低互耦筛查目标，低于 -15 dB 更理想；
- B1- 图应呈约 45 度旋转关系，没有单独异常通道。

### 10.3 频扫与调谐优化

调谐先解决“谐振谷在哪里”，匹配再解决“目标频率处谷值有多深”。不要在主谐振远离目标频率时盲目优化端口匹配网络。

对于以分段电容主导的初步修正，可用：

```text
C_new ≈ C_old × (f_res / f_target)^2
```

- `f_res > f_target`：需要增大调谐电容；
- `f_res < f_target`：需要减小调谐电容；
- 该公式只用于生成下一轮初值，最终值仍由完整耦合模型优化。

本项目的一次实际迭代中，共享分段电容为约 3.105 pF 时，主谐振位于约 231.5–232.0 MHz。按上式将初值提高到约 3.68 pF 后，最终前放加载反射达到约 -25.5 至 -26.0 dB，主谐振移动到约 213.03–213.08 MHz。

修改当前共享分段电容及边界的通用代码：

```matlab
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere8Rx_R115_H140_Span50.json');
J = jsondecode(fileread(coilJson));
E = J.coil_configuration.elements;

currentC = mean(arrayfun(@(q) q.value,E(2:8)));
newC = currentC*(mean(resonanceMHz)/targetMHz)^2;

for ch = 1:8
    idx = (ch-1)*8 + (1:8);
    for k = 2:8
        E(idx(k)).value = newC;
        E(idx(k)).optim.minim = 0.90*newC;
        E(idx(k)).optim.maxim = 1.10*newC;
    end
end

J.coil_configuration.elements = E;
fid = fopen(coilJson,'w'); assert(fid>0);
fprintf(fid,'%s',jsonencode(J,PrettyPrint=true));
fclose(fid);
```

若新值贴住边界，再沿所需方向扩展；不要一次恢复到项目模板的十倍宽范围。每次只改变一类参数，并记录“旧值、边界、谐振频率、新值”。

### 10.4 匹配网络优化

当主谐振已位于目标频率附近，但 `SP_p` 仍高于 -15 dB 时，保持 `Cseg` 基本不变，调整共享端口网络 `Cp1-Ls-Cp2`。可先以上一轮结果作为初值，并把边界设置为当前值的约 0.5–1.5 倍：

```matlab
refPort = E(1).value;
for ch = 1:8
    idx = (ch-1)*8 + 1;
    E(idx).value = refPort;
    E(idx).optim.minim = 0.5*refPort;
    E(idx).optim.maxim = 1.5*refPort;
end
```

如果日志显示 `not tuned`、`not Tuned and Matched` 或最终 PSO 达到 `MaxIterations`，不能仅凭文字判失败或成功。必须检查最终 `SP_p` 和频扫。源码内部以目标函数 `<1` 作为成功打印阈值；某次实际结果以 `Best=1.037` 达到迭代上限，但最终 `SP_p` 已约为 -26 dB，工程性能仍然通过。

### 10.5 去耦定位与几何优化

完整打印 `SP_s`，并定位最差非对角元素：

```matlab
disp('Full SP_s matrix, dB:');
disp(round(SPsDB,2));

couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;
[worstValue,idx] = max(couplingDB,[],'all');
[rowPort,colPort] = ind2sub(size(couplingDB),idx);
fprintf('Worst coupling: S%d%d = %.2f dB\n', ...
    rowPort,colPort,worstValue);
```

根据矩阵模式选择优化手段：

| 最差耦合位置 | 优先排查/优化 |
| --- | --- |
| 相邻端口，如 S12、S23、S76、S81 | Loop 重叠量、相邻边距离、前置放大器解耦 |
| 次相邻端口 | Loop 高度、端部回流路径、整体圆柱半径 |
| 对向端口 | 体模加载、屏蔽结构和共模路径 |
| 单独一个异常端口 | 端口顺序、网格连续性、元件映射、Loop 方向 |

本项目 50 度 Loop 跨度对应 5 度名义重叠，实算相邻耦合约 -10.30 至 -10.45 dB，而次相邻和对向耦合分别约 -13 dB 和 -18.6 dB。这种规则循环矩阵说明端口映射正确，但相邻几何去耦不足。首个修正点为把跨度提高到约 55 度，使名义重叠增加到 10 度。

重叠并非越大越好。建议对 `span=53°、55°、57°` 做小范围扫描，每次重新生成 `.msh`、重新调谐匹配并记录最差相邻耦合。几何文件应使用包含跨度的版本化文件名，例如 `Sphere8Rx_R115_H140_Span55.msh`，同时复制同名电路 JSON 并更新输入 JSON 的 `WireFile`，避免文件名与实际几何不一致。

### 10.6 日志、回写和失败结果管理

- 日志中的 `Coil n is tuned`、`not tuned` 或 `Tuned and Matched` 是中间算法状态，不能替代最终指标验收；
- `solution.netp.phi_lumped_elements.Rx` 是端口/场校准矩阵，不是最终电容、电感表；
- `co_simulation_store_elements` 会把最终元件值回写到线圈 JSON；重跑前必须确认 JSON 是计划使用的初值；
- 几何变化后应重新调谐，不要直接沿用上一几何的最终结果作为“已完成匹配”；
- 失败 MAT 文件即使包含 SNR，也不能进入 UISNR 效率比较；同名 Runner 重跑会覆盖同名 MAT，需要保留时应提前备份。

读取优化后元件值：

```matlab
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere8Rx_R115_H140_Span50.json');
J = jsondecode(fileread(coilJson));
E = J.coil_configuration.elements;

fprintf(['Channel | Cp1(pF) | Ls(nH) | Cp2(pF)', ...
         ' | Segment C range(pF)\n']);
for ch = 1:8
    idx = (ch-1)*8 + (1:8);
    pv = E(idx(1)).value;
    cv = arrayfun(@(q) q.value,E(idx(2:end)));
    fprintf('%7d | %7.3f | %6.3f | %7.3f | %.3f ... %.3f\n', ...
        ch,pv(1)*1e12,pv(2)*1e9,pv(3)*1e12, ...
        min(cv)*1e12,max(cv)*1e12);
end
```

只有 `SP_p`、频扫位置、互耦矩阵和 B1- 旋转对称性全部通过检查后，当前常规阵列结果才可进入后续 UISNR 与 `SNR/UISNR` 比较。失败结果即使包含完整的 `solution.snr_field.SNR`，也不应作为阵列性能结论。

## 11. 生成 UISNR 圆柱表面支撑网格

UISNR 支撑面与实际 Loop 圆柱面一致：半径 115 mm、高 140 mm。首轮使用 32 个方位节点和 13 个 z 层，形成 768 个三角形。

```matlab
cd('/home/<user>/marie-tools');
startup;

outDir = fullfile(pwd, 'data', 'coils', 'basis_files', 'Custom');
if ~exist(outDir, 'dir'), mkdir(outDir); end

meshFile = fullfile(outDir, ...
    'Sphere_CylinderSupport_R115_H140.msh');

Rc = 0.115;
nPhi = 32;
zv = linspace(-0.070, 0.070, 13);
phi = (0:nPhi-1)*2*pi/nPhi;

nodes = zeros(nPhi*numel(zv),3);
for iz = 1:numel(zv)
    ids = (iz-1)*nPhi + (1:nPhi);
    nodes(ids,:) = [Rc*cos(phi(:)), Rc*sin(phi(:)), ...
                    zv(iz)*ones(nPhi,1)];
end

tri = zeros(2*nPhi*(numel(zv)-1),3);
t = 0;
for iz = 1:numel(zv)-1
    for ip = 1:nPhi
        jp = mod(ip,nPhi)+1;
        n1 = (iz-1)*nPhi + ip;
        n2 = (iz-1)*nPhi + jp;
        n3 = iz*nPhi + ip;
        n4 = iz*nPhi + jp;
        t = t+1; tri(t,:) = [n1 n2 n4];
        t = t+1; tri(t,:) = [n1 n4 n3];
    end
end

fid = fopen(meshFile, 'w');
assert(fid > 0);
cleanup = onCleanup(@() fclose(fid));

fprintf(fid, '$MeshFormat\n2.2 0 8\n$EndMeshFormat\n');
fprintf(fid, '$Nodes\n%d\n', size(nodes,1));
for i = 1:size(nodes,1)
    fprintf(fid, '%d %.16g %.16g %.16g\n', ...
        i, nodes(i,1), nodes(i,2), nodes(i,3));
end
fprintf(fid, '$EndNodes\n');

fprintf(fid, '$Elements\n%d\n', size(tri,1));
for i = 1:size(tri,1)
    fprintf(fid, '%d 2 2 1 1 %d %d %d\n', ...
        i, tri(i,1), tri(i,2), tri(i,3));
end
fprintf(fid, '$EndElements\n');

clear cleanup;
fprintf('Saved: %s\n', meshFile);
```

该支撑面是开放圆柱侧面，不包含端盖。这与单排圆柱 Loop 阵列的可用导体区域更一致。改变支撑面会改变 UISNR 理论上限，因此必须把支撑网格视为研究参数并随结果保存。

## 12. 创建 UISNR/BASIS 输入 JSON

创建：

```text
data/inputs/inp_5T_1H_Sphere200_UISNR.json
```

内容：

```json
{
  "B0": 5.0,
  "Nucleus": "1H",
  "Basis_Functions_VIE": 0,
  "BodyFile": "Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat",
  "CoilFile": "",
  "WireFile": "",
  "ShieldFile": "",
  "SurfaceBasisSupportFile": "Custom/Sphere_CylinderSupport_R115_H140.msh",
  "TMD": 0,
  "BasisFile": "Sphere200_5T_PWC_CylSupport_UISNR.mat"
}
```

这里 `WireFile` 必须为空，因为 BASIS 求的是连续支撑表面的理想电流，而不是 8 Loop 电流。`BasisFile` 是输出文件名，最终写入 `data/bases/`。

## 13. 创建并运行 UISNR Runner

复制 BASIS runner：

```matlab
copyfile(fullfile('src','src_runners','BASIS_runner.m'), ...
         'RUN_5T_SPHERE_UISNR.m');
edit RUN_5T_SPHERE_UISNR.m
```

设置：

```matlab
input_file = 'inp_5T_1H_Sphere200_UISNR.json';
geo_flag   = 2;
```

必须保持 `geo_flag=2`。它表示 surface-supported basis，并使输出中包含 `BASIS.Substrate`，后续理想电流可视化依赖该字段。

### 13.1 修复 `Quad_order_vie_tt` 字段错误

当前源码的 `sSVD_rwgBasis.m` 可能错误读取不存在的 `Quad_order_vie_tt` 和 `Quad_order_sie_tt`。`load_inputs.m` 实际创建的字段是 `Quad_order_vie` 和 `Quad_order_sie`。典型报错为：

```text
无法识别的字段名称 "Quad_order_vie_tt"。
出错 sSVD_rwgBasis
```

这属于源码字段名不一致，不是 JSON 缺少参数。首次运行 UISNR 前，在 Linux 终端执行一次：

```bash
cd /home/<user>/marie-tools
cp src/src_integral_equations/src_basis/sSVD_rwgBasis.m \
   src/src_integral_equations/src_basis/sSVD_rwgBasis.m.before_quad_fix

sed -i \
  -e 's/Quad_order_vie_tt/Quad_order_vie/g' \
  -e 's/Quad_order_sie_tt/Quad_order_sie/g' \
  src/src_integral_equations/src_basis/sSVD_rwgBasis.m

grep -n 'Quad_order_.*tt\|Quad_order_vie\|Quad_order_sie' \
  src/src_integral_equations/src_basis/sSVD_rwgBasis.m | head
```

正确输出中第 19、20 行应分别读取：

```matlab
MREDM.inputs.Quad_order_vie
MREDM.inputs.Quad_order_sie
```

该 `.m` 文件不需要重新运行 `installer` 或重新编译 MEX。修复后建议重新执行完整的 `RUN_5T_SPHERE_UISNR`。如果只想在当前 MATLAB 会话临时绕过错误，可在报错后执行：

```matlab
MREDM.inputs.Quad_order_vie_tt = MREDM.inputs.Quad_order_vie;
MREDM.inputs.Quad_order_sie_tt = MREDM.inputs.Quad_order_sie;

BASIS = IncidentField_Basis(MREDM,geo_flag);
BASIS.Substrate = MREDM.SIE.coil;
BASIS = ie_solver_vie_basis(MREDM,BASIS);
BASIS = em_ehfield_vie(MREDM,BASIS);
save(MREDM.inputs.basis_file,'BASIS','-v7.3');
```

临时兼容字段只对当前工作区有效，关闭 MATLAB 后失效；正式方案仍应修复 `sSVD_rwgBasis.m`。

运行：

```matlab
cd('/home/<user>/marie-tools');
startup;
RUN_5T_SPHERE_UISNR;
```

批处理：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
cd /home/<user>/marie-tools
~/MATLAB/R2025b/bin/matlab -batch "startup; RUN_5T_SPHERE_UISNR"
```

预期输出：

```text
data/bases/Sphere200_5T_PWC_CylSupport_UISNR.mat
```

核验：

```matlab
basisFile = fullfile(pwd, 'data', 'bases', ...
    'Sphere200_5T_PWC_CylSupport_UISNR.mat');

whos('-file', basisFile)
Q = load(basisFile, 'BASIS');
BASIS = Q.BASIS;
fieldnames(BASIS)

assert(isfield(BASIS,'UISNR'));
assert(isfield(BASIS,'wUISNR'));
assert(isfield(BASIS,'cUISNR'));
assert(isfield(BASIS,'SK'));
assert(isfield(BASIS,'VK'));
assert(isfield(BASIS,'Substrate'));
```

BASIS 计算通常比 8 Loop 常规仿真更昂贵。建议先保持 4 mm/PWC/768 三角形；若内存不足，先把 `nPhi` 降到 24、z 层降到 9 做流程验证。改变支撑网格密度后必须重新生成 BASIS。

## 14. 理想电流分布

使用项目自带函数，在球心观察 UISNR 理想电流：

```matlab
bodyPath = fullfile(pwd, 'data', 'bodies', 'Scatterers', ...
    '4mm', 'Sphere_D200mm_4mm_eps50_sig0p6_5T.mat');
basisPath = fullfile(pwd, 'data', 'bases', ...
    'Sphere200_5T_PWC_CylSupport_UISNR.mat');

B = load(bodyPath, 'RHBM');
Q = load(basisPath, 'BASIS');

target_point = [0;0;0];  % m
az = 35;
el = 20;

visualize_ideal_current_patterns( ...
    target_point, az, el, ...
    Q.BASIS.SK, Q.BASIS.VK, ...
    Q.BASIS.wUISNR, Q.BASIS.cUISNR, ...
    Q.BASIS.Substrate, B.RHBM);

exportgraphics(gcf, fullfile(pwd, 'data', 'solutions', ...
    'IdealCurrent_SphereCenter.png'), 'Resolution', 300);
```

该图显示连续支撑面上达到球心 UISNR 的理论最优电流模式，包含 `omega*t=0` 和 `omega*t=pi/2` 两个相位。它不是 8 个实际 Loop 的电流。

当前项目自带函数在一次输入多个目标点时会重复使用最后一个目标的标记索引，因此建议一次只画一个目标点。

## 15. 后处理总脚本

这一节必须在以下条件全部满足后执行：

1. 第 10 节常规阵列质量门控已通过；
2. 第 13 节已生成 `data/bases/Sphere200_5T_PWC_CylSupport_UISNR.mat`；
3. 根目录已经实际创建并保存 `POST_5T_8CH_SPHERE.m`。手册中的代码块不会自动变成 MATLAB 脚本。

若直接运行代码但 BASIS 文件尚未生成，会出现“找不到 `Sphere200_5T_PWC_CylSupport_UISNR.mat`”；若只输入 `POST_5T_8CH_SPHERE` 而没有创建脚本，会出现“函数或变量无法识别”。这两类报错都不是常规阵列 MAT 文件损坏。

创建根目录脚本 `POST_5T_8CH_SPHERE.m`。本项目根目录已提供带集中配置区和逐段中文注释的正式版本；修改文件名、ROI大小、色标或导出分辨率时，优先修改该脚本开头的“用户配置区”。下面代码展示总处理流程。

```matlab
close all;
clearvars;
clc;

cd('/home/<user>/marie-tools');
startup;

resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');
bodyFile = fullfile(pwd, 'data', 'bodies', 'Scatterers', ...
    '4mm', 'Sphere_D200mm_4mm_eps50_sig0p6_5T.mat');
basisFile = fullfile(pwd, 'data', 'bases', ...
    'Sphere200_5T_PWC_CylSupport_UISNR.mat');
outDir = fullfile(pwd, 'data', 'solutions', 'figures_5T_8ch');
if ~exist(outDir,'dir'), mkdir(outDir); end

assert(isfile(resultFile), ...
    'Regular-array result is missing: %s', resultFile);
assert(isfile(bodyFile), ...
    'Body model is missing: %s', bodyFile);
assert(isfile(basisFile), ...
    ['UISNR/BASIS result is missing. Run ', ...
     'RUN_5T_SPHERE_UISNR before this postprocessor: %s'], basisFile);

R = load(resultFile, 'solution');
B = load(bodyFile, 'RHBM');
Q = load(basisFile, 'BASIS');

solution = R.solution;
RHBM = B.RHBM;
BASIS = Q.BASIS;

mask = false(size(RHBM.epsilon_r));
mask(RHBM.idxS) = true;

x = squeeze(RHBM.r(:,1,1,1))*1e3;
y = squeeze(RHBM.r(1,:,1,2))*1e3;
z = squeeze(RHBM.r(1,1,:,3))*1e3;
[~,ix] = min(abs(x));
[~,iy] = min(abs(y));
[~,iz] = min(abs(z));

assert(isequal(size(solution.snr_field.SNR), size(BASIS.UISNR)), ...
    'SNR and UISNR grids differ; do not interpolate silently');

%% Figure 1: S matrix and frequency sweep
SP = solution.netp.SP_s;
SdB = 20*log10(abs(SP));
nPorts = size(SP,1);

f1 = figure('Color','w','Position',[100 100 1250 470]);
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

nexttile;
imagesc(SdB,[-40 -5]);
axis image;
set(gca,'XTick',1:nPorts,'YTick',1:nPorts);
xlabel('Port'); ylabel('Port'); title('dB(S) at 212.887 MHz');
colormap(gca, hot(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        text(col,row,sprintf('%.1f',SdB(row,col)), ...
            'HorizontalAlignment','center','Color','c','FontSize',9);
    end
end

nexttile; hold on;
F = solution.netp.figure_freq;
if ~isempty(F.SPm_plot_Rx)
    for p = 1:nPorts
        plot(F.freq_range/1e6, ...
            20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:)))), ...
            'LineWidth',1.5,'DisplayName',sprintf('S_{%d%d}',p,p));
    end
    xline(F.freq_range(F.freq_idx)/1e6,'k--','Target');
    yline(-15,'r:','-15 dB');
    ylim([-80 0]); grid on;
    xlabel('Frequency (MHz)'); ylabel('dB');
    title('Rx return-loss frequency sweep');
    legend('Location','eastoutside');
else
    text(0.5,0.5,'No Rx frequency sweep','HorizontalAlignment','center');
    axis off;
end

exportgraphics(f1, fullfile(outDir,'01_Sparams_and_sweep.png'), ...
    'Resolution',300);

%% Figure 2: per-channel B1- maps
B1m = solution.h_field.Rx.b1m;
assert(size(B1m,4)==8);

f2 = figure('Color','w','Position',[100 100 1450 650]);
tiledlayout(2,4,'Padding','compact','TileSpacing','compact');
for p = 1:8
    map = abs(B1m(:,:,iz,p))*1e6;  % tesla -> microtesla
    map(~mask(:,:,iz)) = NaN;
    nexttile;
    imagesc(x,y,map'); axis image xy;
    xlabel('x (mm)'); ylabel('y (mm)');
    title(sprintf('|B1-|, Rx %d (microT)',p));
    colormap(gca, hot(256)); colorbar;
end
exportgraphics(f2, fullfile(outDir,'02_B1minus_8channels.png'), ...
    'Resolution',300);

%% Figure 3: phantom, SNR, UISNR, efficiency
SNR = real(solution.snr_field.SNR);
UISNR = real(BASIS.UISNR);

ratio = NaN(size(SNR));
valid = mask & isfinite(SNR) & isfinite(UISNR) & UISNR>0;
ratio(valid) = 100*SNR(valid)./UISNR(valid);

% 中央直径 80 mm 的球形 ROI
X = RHBM.r(:,:,:,1);
Y = RHBM.r(:,:,:,2);
Z = RHBM.r(:,:,:,3);
roi = mask & (X.^2+Y.^2+Z.^2 <= 0.040^2) & valid;
roiValues = ratio(roi);
ratioMean = mean(roiValues,'omitnan');
ratioMax = max(roiValues,[],'omitnan');

f3 = figure('Color','w','Position',[100 50 520 1350]);
tiledlayout(4,1,'Padding','compact','TileSpacing','compact');

nexttile;
anatomy = RHBM.epsilon_r(:,:,iz);
anatomy(~mask(:,:,iz)) = NaN;
imagesc(x,y,anatomy'); axis image xy;
title('Phantom epsilon_r'); xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,gray(256)); colorbar;

nexttile;
snrMap = SNR(:,:,iz); snrMap(~mask(:,:,iz)) = NaN;
imagesc(x,y,snrMap'); axis image xy;
title('8-channel optimal-combination SNR');
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar;

nexttile;
uisnrMap = UISNR(:,:,iz); uisnrMap(~mask(:,:,iz)) = NaN;
imagesc(x,y,uisnrMap'); axis image xy;
title('UISNR'); xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar;

nexttile;
ratioMap = ratio(:,:,iz);
imagesc(x,y,ratioMap'); axis image xy;
clim([0 100]);
title(sprintf('SNR/UISNR (%%), ROI mean %.1f%%, max %.1f%%', ...
    ratioMean,ratioMax));
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar; hold on;
theta = linspace(0,2*pi,300);
plot(40*cos(theta),40*sin(theta),'c:','LineWidth',1.5);

exportgraphics(f3, fullfile(outDir,'03_SNR_UISNR_efficiency.png'), ...
    'Resolution',300);

%% Figure 4: three orthogonal centerline SNR/UISNR profiles
% x-line: y=0,z=0; y-line: x=0,z=0; z-line: x=0,y=0.
% The horizontal axis is physical position in mm; the vertical axis is
% the pointwise efficiency 100*SNR/UISNR in percent.
profileX = squeeze(ratio(:,iy,iz));
profileY = squeeze(ratio(ix,:,iz));
profileZ = squeeze(ratio(ix,iy,:));

roiRadiusMM = 40;
xRoi = profileX(abs(x)<=roiRadiusMM & isfinite(profileX));
yRoi = profileY(abs(y)<=roiRadiusMM & isfinite(profileY));
zRoi = profileZ(abs(z)<=roiRadiusMM & isfinite(profileZ));
profileMean = [mean(xRoi,'omitnan'),mean(yRoi,'omitnan'), ...
               mean(zRoi,'omitnan')];
profileMax = [max(xRoi,[],'omitnan'),max(yRoi,[],'omitnan'), ...
              max(zRoi,[],'omitnan')];

f4 = figure('Color','w','Position',[100 100 1450 430]);
tiledlayout(1,3,'Padding','compact','TileSpacing','compact');

nexttile;
plot(x,profileX,'b-','LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
grid on; ylim([0 100]);
xlabel('x (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('x centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(1),profileMax(1)));

nexttile;
plot(y,profileY,'r-','LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
grid on; ylim([0 100]);
xlabel('y (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('y centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(2),profileMax(2)));

nexttile;
plot(z,profileZ,'Color',[0.15 0.60 0.25],'LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
grid on; ylim([0 100]);
xlabel('z (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('z centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(3),profileMax(3)));

sgtitle(sprintf('Orthogonal centerlines through [%.1f %.1f %.1f] mm', ...
    x(ix),y(iy),z(iz)));
exportgraphics(f4,fullfile(outDir, ...
    '04_SNR_UISNR_centerline_profiles.png'),'Resolution',300);

% Export a long-format table for Excel, Origin, Python or R.
profileAxis = [repmat("x",numel(x),1);repmat("y",numel(y),1); ...
               repmat("z",numel(z),1)];
coordinateMM = [x(:);y(:);z(:)];
efficiencyPercent = [profileX(:);profileY(:);profileZ(:)];
insidePhantom = isfinite(efficiencyPercent);
profileTable = table(profileAxis,coordinateMM,efficiencyPercent, ...
    insidePhantom,'VariableNames', ...
    {'Axis','Coordinate_mm','SNR_UISNR_percent','InsidePhantom'});
writetable(profileTable,fullfile(outDir, ...
    '04_SNR_UISNR_centerline_profiles.csv'));

%% Save numerical summary
summary = struct();
summary.frequency_MHz = 212.88739259;
summary.SdB = SdB;
summary.SNR_avg = solution.snr_field.SNR_avg;
summary.SNR_UISNR_ROI_mean_percent = ratioMean;
summary.SNR_UISNR_ROI_max_percent = ratioMax;
summary.center_voxel_mm = [x(ix) y(iy) z(iz)];
summary.centerline.axis = {'x','y','z'};
summary.centerline.coordinate_mm = {x,y,z};
summary.centerline.SNR_UISNR_percent = {profileX,profileY,profileZ};
summary.centerline.ROI_mean_percent = profileMean;
summary.centerline.ROI_max_percent = profileMax;
save(fullfile(outDir,'summary_metrics.mat'),'summary');

fprintf('Figures saved to: %s\n',outDir);
fprintf('ROI SNR/UISNR mean = %.2f %%\n',ratioMean);
fprintf('ROI SNR/UISNR max  = %.2f %%\n',ratioMax);
fprintf('Centerline ROI means [x y z] = [%.2f %.2f %.2f] %%\n', ...
    profileMean);
```

运行：

```matlab
POST_5T_8CH_SPHERE;
```

### 15.1 收发综合评估扩展

根目录正式版 `POST_5T_8CH_SPHERE.m` 已在上述接收后处理基础上增加以下功能：

1. 从 `e_field.Rx.phi + phi_coil + phi_lump` 及 co-simulation 元件损耗构造总接收噪声协方差；
2. 绘制噪声协方差幅值和归一化噪声相关系数矩阵；
3. 在存在真实 `h_field.Tx.b1p` 与 `e_field.Tx.e_b` 时进行发射评估；
4. 默认使用总损耗约束下最大化球心 B1+ 的复数幅相 shim，并将 `w'*PhiTx*w` 归一化为 1 W 总耗散功率；也可通过 `txWeightsUser` 指定自定义权重；
5. 在轴位 `z=0`、冠状位 `y=0`、矢状位 `x=0` 三个中心剖面显示体素 SAR、B1+ 效率和局部 SAR 效率。

若收发仿真使用同一个结果文件，保持脚本配置：

```matlab
txResultName = '';
```

若发射和接收分开仿真，则填写含有真实 Tx 场的结果文件名：

```matlab
txResultName = 'MARIE_1_inp_5T_1H_Sphere200_8LoopTx.mat';
```

默认球心最优权重由 `PhiTx\conj(B1p_center)` 求得。若要评估CP模式、实验测得shim或其他pTx脉冲的静态权重，可在脚本配置区填写复数列向量，例如：

```matlab
txWeightsUser = exp(-1i*2*pi*(0:7)'/8);  % 示例：8通道等幅递进相位
```

该示例的相位正负号必须结合端口顺序和线圈法向验证，不能未经检查直接当作正确CP模式。脚本会保留相对幅相并自动执行1 W总耗散归一化。

发射模块严格要求：

```text
solution.h_field.Tx.b1p
solution.e_field.Tx.e_b
solution.e_field.Tx.phi
solution.e_field.Tx.phi_coil
solution.e_field.Tx.phi_lump
```

当前仅接收配置没有真实 `Tx` 字段。虽然 MARIE 的 `em_TXE.m` 会在纯 Rx 情况下回退到 Rx 场并生成数学上的互易发射效率，但该结果不代表已经建立真实发射驱动、匹配和 SAR 工作状态。因此综合脚本在纯 Rx 结果上会保留全部接收输出，并明确跳过发射部分，而不会把 `txe_field` 误报为正式 Tx 安全结果。

发射图中的定义为：

```text
B1+效率 = |B1+|，驱动已归一化到1 W总耗散，单位 microT/sqrt(W)
体素SAR = sigma*|E|^2/(2*rho)，单位 W/kg
局部SAR效率 = B1+效率/sqrt(体素SAR)，单位 microT/sqrt(W/kg)
```

这里的 SAR 是未进行质量平均的点式体素 SAR，不能替代 IEC/IEEE 规定的 1 g 或 10 g SAR。局部 SAR 效率用于场形态和设计诊断，也不等同于以峰值 10 g SAR 归一化的正式 pTx SAR 效率。当前均匀水样球缺少质量密度时可使用 `1000 kg/m^3` 回退值；人体模型必须使用逐体素 `RHBM.mass_rho`。

## 16. 建议输出图组

最终至少保留以下图像：

1. `00_geometry.png`：球体、8 Loop 和端口的三维几何。
2. `01_Sparams_and_sweep.png`：8x8 `SP_s` 互耦矩阵和 8 条前放加载 `SP_p` 回波损耗频扫曲线。
3. `02_B1minus_8channels.png`：2x4 排列的 8 个接收通道 B1- 切片。
4. `03_SNR_UISNR_efficiency.png`：phantom、阵列 SNR、UISNR 和 SNR/UISNR。
5. `04_SNR_UISNR_centerline_profiles.png`：穿过球心的 x、y、z 三条正交效率剖线，横轴为坐标，纵轴为 `100*SNR/UISNR`。
6. `04_SNR_UISNR_centerline_profiles.csv`：中心剖线长表数据，可在 Excel、Origin、Python 或 R 中重新绘图和统计。
7. `02B_Rx_noise_covariance.png`：接收总噪声协方差幅值和归一化噪声相关矩阵。
8. `05_Tx_SAR_B1p_SAReff_orthogonal_planes.png`：真实 Tx 结果的体素 SAR、B1+ 效率和局部 SAR 效率三个正交中心剖面；纯 Rx 结果不生成该图。
9. `IdealCurrent_SphereCenter.png`：球心目标的理想表面电流模式。

几何图另存：

```matlab
input_file = 'inp_5T_1H_Sphere200_8LoopRx.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM,1);
figure('Color','w');
visualize_geometry(MREDM);
view(35,20); axis equal;
exportgraphics(gcf, fullfile(pwd,'data','solutions', ...
    'figures_5T_8ch','00_geometry.png'),'Resolution',300);
```

## 17. 结果解释

### 17.1 S 参数

- `SP_p` 及 `SPm_plot_Rx`：前置放大器加载条件下的各通道回波损耗，是纯 Rx 匹配与调谐的主要依据。
- `SP_s` 对角线：常规多端口、参考阻抗条件下的回波损耗，仅作辅助参考，不应单独作为纯 Rx 设计的否决条件。
- `SP_s` 非对角线：端口间互耦，用于定位最差耦合通道对和评价几何去耦。
- 频扫谷值应靠近 212.887 MHz。
- 若谷值偏离目标频率，说明调谐未收敛或优化边界不合适。
- 若 `SP_p` 很好但 `SP_s` 的非对角 `Sij` 较差，说明前放加载匹配成功，但几何或网络去耦仍不足。

### 17.2 B1- 接收场

- 每个通道应在靠近该 Loop 的球体边缘具有较高灵敏度。
- 8 个通道图应近似呈 45 度旋转对称。
- 个别通道幅值或形状明显异常时，优先检查端口顺序、Loop 方向、调谐结果和网格连续性。
- 不应把 8 通道 B1- 简单 RSS 当作最终阵列 SNR；MARIE 的 `snr_field.SNR` 已包含噪声协方差和最优合并。

### 17.3 SNR、UISNR 和 SNR/UISNR

- `SNR`：实际 8 Loop 阵列在当前损耗模型下的噪声最优组合结果。
- `UISNR`：同一体模和连续圆柱支撑面下的理论上限。
- `SNR/UISNR`：实际阵列效率，建议以预先定义的中央 ROI 报告均值和最小值/最大值。
- 比值显著超过 100% 通常表示两条计算链的网格、材料、频率、归一化或支撑定义不一致，应先排查，不能直接解释为超越理论上限。

### 17.4 理想电流模式

- 用于观察达到某个目标点 UISNR 所需的连续表面电流方向和相位。
- 改变目标点会改变理想电流模式。
- 它可指导 Loop 位置和尺寸优化，但不能直接转换成 8 个离散 Loop 的实际电流。

## 18. 分阶段执行建议

### 阶段 A：几何与格式验证

- 4 mm、PWC。
- 只执行 `load_inputs`、`geo_assembly` 和 `visualize_geometry`。
- 检查 8 端口和 64 个集总元件位置。

### 阶段 B：常规 8 通道仿真

- 运行 `RUN_5T_8CH_SPHERE`。
- 先检查全部 `SP_p<-15 dB`、前放加载频扫谷值位于 212.887 MHz 附近、最差非对角 `SP_s` 达到预定互耦指标，以及 B1- 的 45 度旋转对称性。
- 若调谐失败，先调整电容/匹配网络初值和边界，不要立即提高分辨率。
- 阶段 B 未通过时停止，不运行 UISNR，也不报告当前 SNR。

### 阶段 C：UISNR 流程验证

- 可先把支撑面降到 `nPhi=24`、z 层 9。
- 确认 BASIS 文件包含 UISNR、wUISNR、cUISNR、SK、VK 和 Substrate。
- BASIS 文件生成并核验后，再创建和运行 `POST_5T_8CH_SPHERE.m`。

### 阶段 D：统一配置正式结果

- 实际阵列和 UISNR 都使用 4 mm/PWC 基线。
- 固定支撑面后生成最终图和 ROI 指标。
- 资源允许时，再统一升级到 2 mm；两条链必须一起升级。

## 19. 已知限制与风险

1. 当前 MARIE 保存的常规结果只有 `solution=MREDM.fields`，没有完整几何；几何图需要重新执行 `load_inputs + geo_assembly`。
2. 本地 `visualize_coil_currents` 已修复端口列偏移、未定义变量和几何参数类型问题；同步修复后的文件到 Linux 服务器后，可用于绘制实际 8 Loop 的 Rx/Tx 电流实部。
3. 自动调谐依赖粒子群优化，结果可能受初值、边界和随机过程影响；建议记录最终元件值并重复运行验证稳定性。
4. MARIE 会把优化后的元件值回写到线圈 JSON；重复运行前必须确认当前 JSON 是计划使用的初值，而不是上一次失败优化留下的状态。
5. 对称模型必须保留第 6.1 节的四变量共享约束。直接恢复项目自带 JSON 的独立通道 `symmetry` 编号可能再次产生严重非对称失配。
6. 5 T 下实际 phantom 的介电参数必须单独确认。只修改 `B0` 不会自动更新材料参数。
7. 本项目未包含 RF shield、馈线、前置放大器实物布局和制造公差；结果应视为数值设计基线，而不是直接等同于实验系统。
8. 圆柱支撑面的范围决定 UISNR 上限。扩大或封闭支撑面通常会改变理论上限，因此跨研究比较时必须保持一致。

## 20. 最终归档清单

每次正式结果至少归档：

- 两个输入 JSON；
- phantom MAT 文件及介电参数来源；
- 8 Loop `.msh` 和同名电路 `.json`；
- UISNR 支撑面 `.msh`；
- 两个 Runner 副本；
- MARIE `solution` 文件；
- BASIS/UISNR 文件；
- 后处理脚本和所有 PNG；
- MATLAB、MARIE 代码版本、编译器版本和 Git commit；
- 运行日志、耗时、并行 worker 数量和峰值内存；
- 目标频率处 `SP_p`、频扫谷值及频率、完整 `SP_s` 矩阵与最差 `Sij`、ROI SNR/UISNR 统计和最终优化元件值。
