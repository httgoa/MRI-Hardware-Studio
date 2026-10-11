# MARIE 3.0 可视化脚本使用指南

本文档依据当前仓库 `src/src_visualizer/` 中的源码整理，适用于当前这份 MARIE 3.0。重点说明各函数需要什么数据、如何调用、会产生什么图，以及当前源码中已经确认的限制。

## 1. 可视化工具总览

| 函数 | 用途 | 主要输入 | 当前 Rx 算例可用性 |
| --- | --- | --- | --- |
| `visualize_geometry` | 体模、线圈、屏蔽和端口的三维几何 | 完整 `MREDM` | 可直接使用，但需要保留或重建 `MREDM` |
| `visualize_s_parameters` | S 参数矩阵热图 | `solution.netp.SP_s` | 可直接使用 |
| `visualize_z_parameters` | 阻抗矩阵实部、虚部热图 | `solution.netp.ZP_s` | 可直接使用 |
| `visualize_ZPm_SPm_freq_sweep` | 调谐后阻抗和反射系数的频率扫描 | `solution.netp.figure_freq` | `TMD=1` 且字段完整时可用 |
| `visualize_coil_currents` | Rx/Tx 线圈表面或导线电流矢量 | 完整 `MREDM` 和 `port` | 已修复端口索引及几何输入问题 |
| `visualize_ideal_current_patterns` | UISNR 理想表面电流模式 | BASIS 结果、体模和观察参数 | 只适用于 BASIS 工作流，输入要求高 |
| `set_black_theme` | 把现有图窗改成黑底白字 | 图窗句柄 | 可作为绘图后处理使用 |
| `navia`、`lipari` | 提供两套连续色图 | 色级数量 | 可用于场图或其他标量图 |

项目没有为普通 MARIE 结果提供通用的 B1、E 场、SNR 切片函数；这类结果需要用 MATLAB 的 `imagesc`、`slice` 或 `isosurface` 自行绘制。文档第 10 节给出实用示例。

## 2. 使用前初始化

每次启动 MATLAB 后执行：

```matlab
cd('/home/<user>/marie-tools');
startup;
```

确认可视化函数已经加入路径：

```matlab
which visualize_geometry
which visualize_s_parameters
which visualize_z_parameters
```

正常情况下，返回路径应位于：

```text
/home/<user>/marie-tools/src/src_visualizer/
```

## 3. 两类输入数据

### 3.1 保存的 `solution`

`MARIE_runner` 默认只保存：

```matlab
solution = MREDM.fields;
```

当前算例可这样加载：

```matlab
resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat');

R = load(resultFile, 'solution');
solution = R.solution;
```

它包含网络参数和电磁场，但不包含完整的体模与线圈几何。因此可以直接绘制 S/Z 参数和场切片，不能把 `solution` 直接传给 `visualize_geometry`。

### 3.2 完整的 `MREDM`

刚执行完 `MARIE_runner` 时，工作区通常仍保留 `MREDM`。此时可以直接绘制几何。

关闭 MATLAB 后，可以只重建几何而不重新求解完整仿真：

```matlab
cd('/home/<user>/marie-tools');
startup;

input_file = 'inp_MSphere_HeadCoil1z.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);
```

若还需要把已保存的场结果附加回 `MREDM`：

```matlab
R = load(fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat'), 'solution');
MREDM.fields = R.solution;
```

## 4. 三维几何：`visualize_geometry`

### 4.1 调用方法

```matlab
figure('Color','w');
visualize_geometry(MREDM);
title('Current MARIE geometry');
view(3);
axis equal;
rotate3d on;
```

### 4.2 显示内容

- 体模：先从 `MREDM.dimensions.idxS` 提取六邻域外壳体素，再计算三角边界并进行两次拉普拉斯平滑。
- 导线线圈：棕色线段。
- 表面线圈：棕色三角网格。
- 表面屏蔽：半透明棕色三角面。
- 表面支撑基：半透明橙色方形散点。
- 端口：红色。
- 电容：黄色。
- 电感：蓝色。
- 互感：紫色。
- 电阻：黑色。

坐标单位是米。函数自动启用等比例坐标、网格、Gouraud 光照和头灯。

### 4.3 常用观察命令

```matlab
view(3)       % 三维视角
view(0,0)     % 正视图
view(90,0)    % 侧视图
view(0,90)    % 俯视图
rotate3d on   % 鼠标旋转
zoom on       % 鼠标缩放
```

保存图片：

```matlab
exportgraphics(gcf, ...
    fullfile(pwd, 'data', 'solutions', 'current_geometry_3D.png'), ...
    'Resolution', 300);
```

### 4.4 注意事项

- 当前实现不会再把全部有效体素直接传给 `boundary(P,1)`。它先剔除六邻域均被占据的
  内部体素，以避免Sphere240/2 mm这类约90万点模型触发Qhull进程级终止。该降采样仅用于
  显示体模外表面，不改变求解网格、线圈几何或电磁结果。
- 若体模支持域少于四个外壳体素，函数以
  `MARIE:visualize_geometry:InsufficientBodySurface`明确失败。
- 函数默认将体模设为不透明。若线圈位于体模内部或被遮挡，可在绘图后降低表面透明度：

```matlab
h = findobj(gca, 'Type', 'Surface');
set(h, 'FaceAlpha', 0.35);
```

这条命令会同时改变体模和表面线圈的透明度。

## 5. S 参数：`visualize_s_parameters`

### 5.1 调用方法

```matlab
SP = solution.netp.SP_s;
visualize_s_parameters(SP);
```

也可以直接从结果文件读取：

```matlab
R = load(fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat'), 'solution');
visualize_s_parameters(R.solution.netp.SP_s);
```

### 5.2 绘图效果与解释

函数绘制 `20*log10(abs(SP))` 的端口矩阵热图：

- 对角线是各端口反射系数，例如 S11、S22。
- 非对角线是端口间耦合，例如 S12、S21。
- 默认颜色范围固定为 -40 到 -5 dB。
- 每个单元格会显示一位小数。

当前单端口算例只会显示一个格子，约为 `S11=-57.6 dB`。这表示匹配很好，不是图像缺失。

查看精确数值：

```matlab
SdB = 20*log10(abs(SP));
disp(SdB);
```

注意：低于 -40 dB 的数值仍会打印在格子中，但颜色会被压到色轴下限。

## 6. Z 参数：`visualize_z_parameters`

### 6.1 调用方法

```matlab
ZP = solution.netp.ZP_s;
visualize_z_parameters(ZP);
```

### 6.2 绘图效果与解释

函数生成一个包含两个子图的图窗：

- 左图：`abs(real(ZP))`，默认范围 0 到 70 ohm。
- 右图：`abs(imag(ZP))`，默认范围 0 到 35 ohm。

理想 50 ohm 匹配通常表现为：

```text
real(Z11) 接近 50 ohm
imag(Z11) 接近 0 ohm
```

当前算例约为实部 49.9 ohm、虚部 0.1 ohm，和很低的 S11 一致。

重要限制：源码使用绝对值，因此图中看不出虚部和互阻抗的正负号。需要符号时直接检查：

```matlab
disp(real(ZP));
disp(imag(ZP));
```

## 7. 频率扫描：`visualize_ZPm_SPm_freq_sweep`

### 7.1 调用方法

```matlab
fieldnames(solution.netp.figure_freq)
visualize_ZPm_SPm_freq_sweep(solution.netp.figure_freq);
```

### 7.2 所需字段

`figure_freq` 必须包含：

```text
ZPm_plot_Rx
SPm_plot_Rx
ZPm_plot_Tx
SPm_plot_Tx
freq_range
freq_idx
```

这些数据由 `TMD=1` 的调谐/匹配流程产生。频率范围通常是目标频率的 80% 到 120%，共 5000 个点，`freq_idx` 指向目标频率。

### 7.3 绘图效果

每种存在的工作模式分别生成图窗，包含：

1. `real(Zii)` 随频率变化，并画出 50 ohm 参考线。
2. `imag(Zii)` 随频率变化，并画出 0 ohm 参考线。
3. `20*log10(abs(Sii))` 随频率变化。

竖线表示目标拉莫尔频率。可以用它检查谐振点、阻抗匹配和工作带宽。

当前源码只绘制对角项，因为循环实际采用 `ind2 = ind1`；它不会绘制 S12 等端口耦合的频率曲线。

## 8. 线圈电流：`visualize_coil_currents `？

### 8.1 设计调用方式

函数接口是：

```matlab
visualize_coil_currents(MREDM, port)
```

其中 `port` 是从 1 开始的端口编号。设计目标是分别绘制 `JcbRx` 和 `JcbTx` 的三维电流矢量，箭头位置对应导线段中心或表面三角形中心。

理论调用示例：

```matlab
visualize_coil_currents(MREDM, 1);
```

### 8.2 当前仓库修复说明

原函数错误地把最终外部端口列再次按屏蔽、导线和表面线圈的内部端口数偏移。单端口结果只有一列时，会因此尝试访问第 10 列并报告“位置 2 的索引超出数组边界”。原函数还引用未定义变量 `COIL/WIRE`，并混用了文件路径和已构造的几何结构。

当前本地版本已修复为：

- `port` 直接选择 `JcbRx(:,port)` 或 `JcbTx(:,port)` 的最终外部端口列；
- 屏蔽、导线和表面线圈只按行区间拆分；
- 直接读取 `MREDM.WIE.coil`、`MREDM.SIE.coil/shield`，不重新加载网格文件；
- 对 WIE 和 RWG/SIE 电流统一绘制实部；
- 对端口范围、几何尺寸和电流系数尺寸给出明确错误。
- 先消除复电流的任意全局相位，再绘制相位对齐后的实部；
- 将箭头按最大电流归一化并按线圈几何尺寸缩放，避免箭头改变坐标范围；
- 对平面线圈显式设置三轴显示范围，避免零厚度方向被 MATLAB 自动扩展到 `[-1,1]`；
- 使用普通文本标题，避免 `sprintf` 将 LaTeX 反斜杠误解析为转义字符。

修复后的调用仍然是：

```matlab
visualize_coil_currents(MREDM, 1)
```

彩色点表示采样后的导体位置及相对电流幅值，黑色箭头表示相位对齐后实部电流的方向和相对大小。色条定义为：

```text
100 × |Re(J_phase-aligned)| / max(|Re(J_phase-aligned)|)
```

因此色条范围固定为 `0–100%`：

- `100%` 是当前工作模式、当前端口中的峰值电流位置；
- 接近 `0%` 表示相位对齐后的实部电流接近零；
- 颜色适合比较同一张图内的电流分布均匀性，不能用于比较不同仿真的绝对电流。

采用相对色条是因为函数可同时显示 WIE 导线电流和 SIE/RWG 表面电流，两者的系数或重建矢量不一定具有相同物理量纲；将它们放在同一个绝对安培色条上会产生误导。箭头长度也按当前图的最大值归一化，不能从图中读取绝对安培值。

### 8.3 提取绝对复电流系数

对于纯 WIE 导线线圈，可从结果中直接提取端口 `port` 的导线电流系数：

```matlab
port = 1;
Nshield = 0;
if ~isempty(MREDM.SIE.shield)
    Nshield = MREDM.dimensions.N_shield_sie;
end
Nw = MREDM.dimensions.N_wie;

Jwire = MREDM.fields.JcbRx(Nshield+(1:Nw), port);

fprintf('最大 |J|: %.6g\n', max(abs(Jwire)));
fprintf('最小 |J|: %.6g\n', min(abs(Jwire)));
fprintf('平均 |J|: %.6g\n', mean(abs(Jwire)));
fprintf('幅值变异系数: %.3f%%\n', ...
    100*std(abs(Jwire))/mean(abs(Jwire)));
```

`Jwire` 是复数，应同时保留幅度和相位：

```matlab
Jmag = abs(Jwire);
Jphase_deg = angle(Jwire)*180/pi;
```

其绝对单位和归一化取决于端口激励、电压定义及联合仿真校准。跨案例比较前必须确保激励和功率归一化一致。

### 8.4 色条结果如何解释

单根闭合 Loop 在准静态条件下通常表现为沿环较连续的电流。如果整圈大部分位置颜色接近且箭头方向连续，说明电流提取和几何映射基本合理。

以下现象需要进一步检查：

| 图像表现 | 可能原因 |
| --- | --- |
| 集总元件或馈电点附近颜色变化 | 馈电、调谐元件和离散节点造成的局部变化，可能合理 |
| 非馈电位置突然降到接近 0% | 网格断裂、段顺序错误或电流索引不匹配 |
| 相邻箭头频繁反向 | 几何段方向不一致、全局相位之外存在强烈局部相位变化 |
| 整图接近单一颜色 | 电流非常均匀，或色标归一化掩盖了很小的差异；应检查数值统计 |
| 只有少数点为 100%，其余接近 0% | 强局部热点、端口定义异常，或最大值离群 |

若要比较多个端口，应分别运行：

```matlab
for port = 1:size(MREDM.fields.JcbRx,2)
    visualize_coil_currents(MREDM, port);
end
```

每张图都会独立归一化到 `100%`。因此端口间只能比较空间形态；绝对峰值比较必须另外提取 `JcbRx/JcbTx` 数值并采用共同归一化。

如果 MATLAB 已经加载过旧函数，先刷新函数缓存：

```matlab
clear visualize_coil_currents
rehash path
which visualize_coil_currents -all
visualize_coil_currents(MREDM, 1)
```

`which` 应指向当前项目的 `src/src_visualizer/visualize_coil_currents.m`。Linux 服务器上的源码也必须同步为修复版本，本地 Windows 文件的修改不会自动传到服务器。

结果 MAT 只保存 `solution`，不保存完整几何。关闭 MATLAB 后回看电流时，需先用原 JSON 重建 `MREDM`，再挂载结果：

```matlab
cd('/home/<user>/marie-tools');
startup;
MREDM = load_inputs('inp_MSphere_HeadCoil1z.json');
MREDM = geo_assembly(MREDM, 1);
R = load('data/solutions/MARIE_1_inp_MSphere_HeadCoil1z.mat', 'solution');
MREDM.fields = R.solution;
visualize_coil_currents(MREDM, 1);
```

## 9. 理想电流模式：`visualize_ideal_current_patterns` ？

### 9.1 适用范围

该函数不是普通 `MARIE_runner` 的结果浏览器，而是用于 `BASIS_runner` 生成的 UISNR 理想电流模式。它要求使用 `geo_flag=2` 的表面支撑基，因为输入中必须存在 `BASIS.Substrate`。

### 9.2 输入含义

```matlab
visualize_ideal_current_patterns( ...
    target_point, az, el, ...
    BASIS.SK, BASIS.VK, BASIS.wUISNR, BASIS.cUISNR, ...
    BASIS.Substrate, RHBM)
```

| 参数 | 含义 |
| --- | --- |
| `target_point` | `3 x N` 目标坐标，单位米 |
| `az`、`el` | 每个目标的观察方位角和仰角，单位度 |
| `SK`、`VK` | BASIS 模态分解结果 |
| `wUISNR` | 每个目标体素的理想接收权重 |
| `cUISNR` | UISNR 随模态数量的收敛数据 |
| `Substrate` | 表面支撑网格 |
| `RHBM` | 含 `r` 和 `idxS` 的体模结构 |

### 9.3 单目标调用示例

```matlab
S = load('/path/to/generated_basis.mat', 'BASIS');
BASIS = S.BASIS;

B = load(fullfile(pwd, 'data', 'bodies', ...
    'Scatterers', '2mm', 'Multilayer_Sphere.mat'), 'RHBM');
RHBM = B.RHBM;

target_point = [0; 0; 0];
az = 35;
el = 25;

visualize_ideal_current_patterns( ...
    target_point, az, el, ...
    BASIS.SK, BASIS.VK, BASIS.wUISNR, BASIS.cUISNR, ...
    BASIS.Substrate, RHBM);
```

函数为每个目标绘制两幅图：`omega*t=0` 和 `omega*t=pi/2`，同时显示半透明体模、目标点、表面支撑网格和理想电流箭头。

当前源码在多个目标时会重复使用最后一个目标点的标记索引，因此建议一次只传入一个目标，或者修复目标索引的保存逻辑后再批量绘图。

## 10. 普通场结果的实用绘图命令

以下不是独立的项目函数，但直接使用 MARIE 保存的数据，是查看普通仿真结果最实用的方法。

### 10.1 B1- 接收场中间切片

```matlab
B1m = solution.h_field.Rx.b1m;
z = round(size(B1m,3)/2);
port = 1;

figure('Color','w');
imagesc(squeeze(abs(B1m(:,:,z,port)))');
axis image off;
set(gca, 'YDir', 'normal');
colormap(navia(256));
colorbar;
title(sprintf('|B1-|, z slice %d, port %d', z, port));
```

绘图前先检查实际字段：

```matlab
fieldnames(solution.h_field)
fieldnames(solution.h_field.Rx)
```

纯 Rx 算例没有 `Tx` 字段，访问 `solution.h_field.Tx` 报错属于预期行为。

### 10.2 SNR 中间切片

```matlab
fieldnames(solution.snr_field)
```

**运行输出：**

    ans =  2×1 cell 数组
    {'SNR_avg'}
    {'SNR'    }

根据返回的实际字段名选择数组。例如假设字段名为 `snr`：（应该是SNR，已经修改：SNR = solution.snr_field.**SNR**; ）

```matlab
SNR = solution.snr_field.SNR; 
z = round(size(SNR,3)/2);

figure('Color','w');
imagesc(squeeze(abs(SNR(:,:,z)))');
axis image off;
set(gca, 'YDir', 'normal');
colormap(lipari(256));
colorbar;
title(sprintf('SNR, z slice %d', z));
```

不要在未检查字段名时直接假设数据一定叫 `snr`。（比如我们检查后发现应该是SNR）



### 10.3 三个正交切片

```matlab
V = abs(B1m(:,:,:,1));
ix = round(size(V,1)/2);
iy = round(size(V,2)/2);
iz = round(size(V,3)/2);

figure('Color','w');
tiledlayout(1,3, 'Padding','compact', 'TileSpacing','compact');

nexttile;
imagesc(squeeze(V(ix,:,:))'); axis image off; title('Sagittal');

nexttile;
imagesc(squeeze(V(:,iy,:))'); axis image off; title('Coronal');

nexttile;
imagesc(squeeze(V(:,:,iz))'); axis image off; title('Axial');

colormap(navia(256));
colorbar;
```

```matlab
V = abs(SNR(:,:,:,1));
ix = round(size(V,1)/2);
iy = round(size(V,2)/2);
iz = round(size(V,3)/2);

figure('Color','w');
tiledlayout(1,3, 'Padding','compact', 'TileSpacing','compact');

nexttile;
imagesc(squeeze(V(ix,:,:))'); axis image off; title('Sagittal');

nexttile;
imagesc(squeeze(V(:,iy,:))'); axis image off; title('Coronal');

nexttile;
imagesc(squeeze(V(:,:,iz))'); axis image off; title('Axial');

colormap(navia(256));
colorbar;
```



### 10.4 发射效率（TXE）可视化

#### 10.4.1 先确认字段和数据有效性

`MARIE_runner` 和 `MRGF_runner` 把发射效率保存到：

```text
solution.txe_field.TXE
solution.txe_field.TXE_avg
```

先检查实际结果：

```matlab
assert(isfield(solution, 'txe_field'), '结果中没有 txe_field');
fieldnames(solution.txe_field)

TXE2 = real(solution.txe_field.TXE);
fprintf('TXE 尺寸: %s\n', mat2str(size(TXE2)));
fprintf('NaN: %d, Inf: %d, 负值: %d\n', ...
    nnz(isnan(TXE2)), nnz(isinf(TXE2)), nnz(TXE2 < 0));
```

源码 `em_TXE.m` 对矩阵

```text
conj(Phi^(-1)) * b1p^H * b1p
```

取最大特征值，因此 `TXE` 是平方型指标。在 `B1+` 以 tesla、损耗矩阵以 watt 归一化的前提下，可把

```matlab
TXE_uT_sqrtW = 1e6 * sqrt(max(TXE2, 0));
```

解释为常用的 `B1+` 发射效率，单位 `µT/sqrt(W)`。`max(...,0)` 只用于消除浮点误差产生的极小负值；如果存在明显负值，应先检查损耗矩阵和数值稳定性，不能直接截断后忽略。

> 注意：已有旧示例若写成 `solution.snr_field.TXE` 是错误路径，正确路径是 `solution.txe_field.TXE`。

#### 10.4.2 中间轴位切片

```matlab
TXE2 = real(solution.txe_field.TXE);
TXEeff = 1e6 * sqrt(max(TXE2, 0));  % µT/sqrt(W)

z = round(size(TXEeff,3)/2);
slice = squeeze(TXEeff(:,:,z))';

figure('Color','w');
imagesc(slice);
axis image off;
set(gca, 'YDir', 'normal');
colormap(lipari(256));
cb = colorbar;
cb.Label.String = '\muT/\surdW';
title(sprintf('Transmit efficiency, z slice %d', z));
```

体模外部通常为零。为了避免背景零值影响统计和色轴，可只对非零体素处理：

```matlab
mask = TXEeff > 0 & isfinite(TXEeff);
vals = TXEeff(mask);

fprintf('非零体素数: %d\n', numel(vals));
fprintf('平均值: %.4g µT/sqrt(W)\n', mean(vals));
fprintf('中位数: %.4g µT/sqrt(W)\n', median(vals));
fprintf('最大值: %.4g µT/sqrt(W)\n', max(vals));
```

如果少量热点使主体区域对比度过低，可用非零值的第 99 百分位设置显示上限。该操作只改变显示，不改变原始数据：

```matlab
clim([0 prctile(vals, 99)]);
```

#### 10.4.3 三个正交切片

```matlab
V = TXEeff;
ix = round(size(V,1)/2);
iy = round(size(V,2)/2);
iz = round(size(V,3)/2);

figure('Color','w');
tiledlayout(1,3, 'Padding','compact', 'TileSpacing','compact');

nexttile;
imagesc(squeeze(V(ix,:,:))');
axis image off; set(gca,'YDir','normal'); title('Sagittal');

nexttile;
imagesc(squeeze(V(:,iy,:))');
axis image off; set(gca,'YDir','normal'); title('Coronal');

nexttile;
imagesc(squeeze(V(:,:,iz))');
axis image off; set(gca,'YDir','normal'); title('Axial');

colormap(lipari(256));
cb = colorbar;
cb.Label.String = '\muT/\surdW';
sgtitle('Transmit efficiency');
```

若需要三幅图严格使用同一色轴：

```matlab
axs = findall(gcf, 'Type', 'axes');
cmax = prctile(vals, 99);
set(axs, 'CLim', [0 cmax]);
```

#### 10.4.4 原始平方型 TXE 与平均值

如果研究需要严格复现 MARIE 保存值，应直接显示 `TXE2`，并在标题中明确它是平方型量，而不是 `µT/sqrt(W)`：

```matlab
figure('Color','w');
imagesc(squeeze(TXE2(:,:,z))');
axis image off; set(gca,'YDir','normal');
colorbar;
title('Stored TXE metric (squared form)');
```

源码中的 `TXE_avg` 是所有非零 `TXE2` 的算术平均值：

```matlab
storedAvg = real(solution.txe_field.TXE_avg);
fprintf('保存的 TXE_avg: %.6g\n', storedAvg);
fprintf('sqrt(TXE_avg): %.6g µT/sqrt(W)\n', 1e6*sqrt(max(storedAvg,0)));
```

注意以下两者一般不相等：

```text
sqrt(mean(TXE2))  !=  mean(sqrt(TXE2))
```

前者对应 `sqrt(TXE_avg)`，后者才是发射效率图非零体素的平均值。论文和表格必须说明使用哪一种。

#### 10.4.5 UITXE 可视化

`BASIS_runner` 的极限发射效率不保存在 `solution.txe_field`，而是在 BASIS 文件中：

```matlab
B = load('data/bases/my_basis.mat', 'BASIS');
fieldnames(B.BASIS)

UITXE2 = real(B.BASIS.UITXE);
UITXEeff = 1e6 * sqrt(max(UITXE2, 0));
z = round(size(UITXEeff,3)/2);

figure('Color','w');
imagesc(squeeze(UITXEeff(:,:,z))');
axis image off;
set(gca,'YDir','normal');
colormap(lipari(256));
cb = colorbar;
cb.Label.String = '\muT/\surdW';
title('Ultimate intrinsic transmit efficiency');
```

只有当实际 TXE 与 UITXE 使用相同的 `B0`、核素、体模、体素网格、离散方式和功率归一化时，才可以逐体素比较。平方型指标的相对比值可写为：

```matlab
valid = UITXE2 > 0 & isfinite(UITXE2) & isfinite(TXE2);
ratio2 = zeros(size(TXE2));
ratio2(valid) = max(TXE2(valid),0) ./ UITXE2(valid);

% 幅度效率相对极限值，单位 %
ratioAmpPct = 100 * sqrt(max(ratio2,0));
```

不要把 `TXE2/UITXE2` 和 `sqrt(TXE2/UITXE2)` 混用：前者是平方型性能比，后者是 `B1+ / sqrt(W)` 幅度效率比。

#### 10.4.6 纯 Rx 算例的解释限制

`em_TXE.m` 在不存在 `h_field.Tx` 时会回退到 `h_field.Rx.b1p` 和 Rx 损耗矩阵，因此纯接收线圈结果中也可能存在 `txe_field`。这说明代码能够计算数学上的互易发射效率指标，但不代表线圈已建立真实 Tx 驱动、匹配、功率归一化和 SAR 工作状态。

对于仅标记为 `Rx` 的模型：

- 可以把 TXE 图作为互易性和场形态诊断；
- 不应直接把它作为真实发射性能或安全结论；
- 正式 Tx 分析应使用 `Tx` 或 `TxRx` 端口配置，并同步检查 `B1+`、输入功率、体模损耗和 SAR。



## 11. 辅助显示工具

### 11.1 黑色主题

先完成绘图，再调用：

```matlab
set_black_theme(gcf);
```

它会把图窗和坐标轴设为黑色，并把坐标、标题、图例、色条和黑色线条改为白色。对 S 参数热图使用时，函数还会把热图上的文字统一变白，可能降低某些色块上的对比度。

### 11.2 `navia` 与 `lipari` 色图

```matlab
colormap(navia(256));
colormap(lipari(256));
```

不传参数时返回内置原始色图：

```matlab
cm = navia;
cm = lipari;
```

传入整数时，会插值得到指定数量的颜色。适合 B1、E 场、SNR 等连续标量图。

## 12. 当前算例一键检查

在 MATLAB 中运行以下代码，可重建几何并查看当前结果的几何、S 参数、Z 参数和频扫：

```matlab
cd('/home/<user>/marie-tools');
startup;

input_file = 'inp_MSphere_HeadCoil1z.json';
resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat');

% 读取结果
R = load(resultFile, 'solution');
solution = R.solution;

% 重建几何，不重新求解完整仿真
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);
MREDM.fields = solution;

% 1. 体模与线圈三维几何
figure('Color','w');
visualize_geometry(MREDM);
title('Multilayer Sphere + Head Receive Coil 1z');
view(3);
rotate3d on;

% 2. S 参数
visualize_s_parameters(solution.netp.SP_s);

% 3. Z 参数
visualize_z_parameters(solution.netp.ZP_s);

% 4. 频率扫描（字段存在时）
if isfield(solution.netp, 'figure_freq') && ...
        ~isempty(solution.netp.figure_freq)
    visualize_ZPm_SPm_freq_sweep(solution.netp.figure_freq);
end
```

线圈电流图需要结果中的 `JcbRx/JcbTx`。确认这些字段存在后，可在上述一键检查代码末尾调用 `visualize_coil_currents(MREDM,1)`。

## 13. 推荐检查顺序

1. 先用 `visualize_geometry` 检查线圈、端口和体模的相对位置。
2. 用 `visualize_s_parameters` 检查匹配和通道耦合。
3. 用 `visualize_z_parameters` 检查目标频率处是否接近 50+j0 ohm。
4. 用频率扫描确认谐振点和工作带宽，而不是只看单频结果。
5. 用 B1、E 场或 SNR 切片检查空间分布、对称性、空值和异常热点。
6. 最后再进行线圈电流或 UISNR 理想电流模式分析。
