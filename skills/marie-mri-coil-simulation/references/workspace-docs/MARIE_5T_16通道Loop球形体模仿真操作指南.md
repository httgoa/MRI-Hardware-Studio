# MARIE 3.0：5 T、16 通道双排 Loop 接收阵列仿真操作指南

## 1. 推荐架构

本案例采用三阶段工作流，将昂贵的三维电磁求解与需要反复迭代的 TMD 电路优化分开：

```text
Stage A：几何 + WIE/VIE 组装 + 电磁求解
    -> 保存原始多端口导纳矩阵 YPn
    -> 可选保存完整 pre-TMD MREDM 检查点

Stage B：加载同一个 YPn，反复执行 TMD
    -> 修改种子、边界或 symmetry
    -> 优化调谐/匹配电路
    -> 检查 SP_p、谐振频率和 SP_s
    -> 每轮保存独立结果与 JSON 备份

Stage C：接受最终电路
    -> 使用 TMD=0 固定元件值
    -> 计算 B1-、噪声协方差、SNR 和 SNR/UISNR
```

该思路适合本项目。16 通道 TMD 可能需要多轮搜索，而几何、体模、频率和离散网格在这些轮次中不变。重复求解三维电磁系统既耗时，也会增加结果管理风险。

必须注意：Stage A 不能只运行 `geo_assembly`。用于 TMD 的缓存必须完成 `wsvie_assembly` 和 `solver_wsvie`，得到尚未附加匹配网络的原始 `YPn`。

## 2. 固定设计

| 项目 | 设置 |
|---|---|
| 静磁场与核种 | 5 T，`1H` |
| 目标频率 | 212.887393 MHz |
| 体模 | 直径 200 mm，4 mm 体素，`epsilon_r=50`，`sigma=0.6 S/m` |
| 阵列 | 16 个纯 Rx WIE Loop，上排 1--8，下排 9--16 |
| 支撑半径 | 115 mm |
| Loop 高度 | 90 mm |
| 周向跨角 | 50 度 |
| 上排 | `z=+25 mm`，方位角 `0:45:315` 度 |
| 下排 | `z=-25 mm`，相对上排错位 22.5 度 |
| 轴向范围 | `[-70,+70] mm` |
| TMD 分组 | 上、下排各一套 `Cp1/Ls/Cp2/Cseg`，共 8 个变量 |

主要文件：

```text
CREATE_5T_16CH_DOUBLE_ROW_CASE.m
PRECOMPUTE_5T_16CH_EM_NETWORK.m
RUN_5T_16CH_TMD_ONLY.m
FINALIZE_5T_16CH_FROM_CHECKPOINT.m
RUN_5T_16CH_SPHERE.m
POST_5T_16CH_SPHERE.m
```

## 3. 环境与初始化

Linux 终端：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
cd /home/<user>/marie-tools
~/MATLAB/R2025b/bin/matlab
```

MATLAB：

```matlab
cd('/home/<user>/marie-tools');
startup;
assert(exist('load_inputs','file')==2);
assert(exist('co_simulation_Rx_optim','file')==2);
```

服务器同时只能运行一个写入当前线圈 JSON 的 TMD 任务。

## 4. 创建并检查几何

首次创建该几何版本：

```matlab
CREATE_5T_16CH_DOUBLE_ROW_CASE;
```

生成：

```text
data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.msh
data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json
data/coils/wire_files/Custom/Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5_channel_layout.csv
data/inputs/inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json
```

结构检查：

```matlab
caseName = 'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5';
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    [caseName '.json']);

J = jsondecode(fileread(coilJson));
E = J.coil_configuration.elements;

assert(numel(E)==128);
assert(sum(strcmp({E.type},'port'))==16);
assert(all(arrayfun(@(e) strcmp(e.excitation.TxRx,'Rx'),E)));

for ch = 1:16
    idx = (ch-1)*8 + (1:8);
    assert(strcmp(E(idx(1)).type,'port'));
    assert(all(strcmp({E(idx(2:8)).type},'element')));
    assert(all(arrayfun(@(e) e.excitation.entity,E(idx))==ch));
end
```

几何可视化：

```matlab
input_file = 'inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM,1);

figure('Color','w');
visualize_geometry(MREDM);
view(3); axis equal; rotate3d on;
title('5 T, 16-channel double-row Rx array');

assert(abs(MREDM.emc.freq/1e6-212.88739259)<1e-6);
```

确认导线没有进入体模，上下排位于正确 z 位置，下排错位 22.5 度，端口和 7 个分段电容顺序一致。几何错误不能由 TMD 修复。

`CREATE_5T_16CH_DOUBLE_ROW_CASE` 会重新生成线圈 JSON。进入 TMD 迭代后不要再次运行它，否则已经优化的电路值会被种子覆盖。

## 5. TMD 变量组织

每通道依次包含一个三元 port 网络和 7 个分段电容：

```text
[Cp1, Ls, Cp2] + 7 x Cseg
```

MARIE 的内部计数在一个通道内增加 `3+7=10`。因此，同排共享变量时，JSON symmetry 也必须逐通道递减 10。建模脚本当前采用：

```matlab
for ch = 1:16
    idx = (ch-1)*8 + (1:8);

    if ch <= 8
        E(idx(1)).optim.symmetry = 1000 - 10*(ch-1);
        tuneSym = 5000 - 10*(ch-1);
    else
        E(idx(1)).optim.symmetry = 2000 - 10*(ch-9);
        tuneSym = 6000 - 10*(ch-9);
    end

    for k = idx(2:8)
        E(k).optim.symmetry = tuneSym;
    end
end
```

这形成 8 个独立变量：上排和下排各自的 `Cp1/Ls/Cp2/Cseg`。不要使用“每通道减 3”或“所有电容固定同一个 symmetry”的旧写法；普通可优化元件同样推进内部计数。

内部编号检查：

```matlab
portInternal = zeros(16,3);
tuneInternal = zeros(16,7);
c1 = 0;

for ch = 1:16
    idx = (ch-1)*8 + (1:8);
    for q = 1:3
        portInternal(ch,q) = E(idx(1)).optim.symmetry + c1;
        c1 = c1 + 1;
    end
    t = c1 - 1;
    for q = 1:7
        tuneInternal(ch,q) = E(idx(q+1)).optim.symmetry + t;
        c1 = c1 + 1;
    end
end

assert(all(all(portInternal(1:8,:)==portInternal(1,:))));
assert(all(all(portInternal(9:16,:)==portInternal(9,:))));
assert(all(all(tuneInternal(1:8,:)==tuneInternal(1,:))));
assert(all(all(tuneInternal(9:16,:)==tuneInternal(9,:))));
assert(isempty(intersect(portInternal(1,:),portInternal(9,:))));
assert(isempty(intersect(tuneInternal(1,:),tuneInternal(9,:))));
```

## 6. Stage A：预计算三维电磁网络

打开脚本：

```text
PRECOMPUTE_5T_16CH_EM_NETWORK.m
```

默认不保存完整检查点。若只需要 `YPn`，直接运行：

```matlab
PRECOMPUTE_5T_16CH_EM_NETWORK;
```

如果磁盘空间足够，并希望最终阶段也不重复电磁求解，请在运行前设置环境变量：

```matlab
setenv('MARIE_SAVE_FULL_CHECKPOINT','1');
PRECOMPUTE_5T_16CH_EM_NETWORK;
```

该阶段执行几何装配、积分算子组装和系统求解，但不运行 TMD，也不计算最终场。必定生成：

```text
data/solutions/YPn_5T_Sphere200_16LoopRx_DoubleRow_H90.mat
```

其中包含：

- `YPn`：TMD 前原始导纳矩阵；
- `network_meta`：输入文件、频率、矩阵大小和生成时间。

启用后还会生成：

```text
data/solutions/MREDM_preTMD_5T_Sphere200_16LoopRx_DoubleRow_H90.mat
```

完整 `MREDM` 可能很大，保存和加载都需要时间。只做多轮 S 参数优化时，保存 `YPn` 即可。

### 6.1 何时可以复用 `YPn`

以下内容必须保持不变：

- `.msh` 几何、导线离散和集总点顺序；
- 体模、电参数和空间位置；
- B0、核种和频率；
- VIE 基函数、网格分辨率和屏蔽结构；
- 端口拓扑、元件数量、`type`、`load`、`optim.boolean` 和实体映射。

可以在不重算 `YPn` 的情况下修改：

- 元件 `value`；
- `optim.minim/maxim`；
- 正确设计的 `optim.symmetry`；
- TMD 粒子群设置；
- 电路元件 Q 值和前放参数，但应重新验证噪声与最终 SNR。

**只要改变 Loop 尺寸、重叠、排距、错位角、体模或端口/元件布局，就必须建立新的 case 名称并重新执行 Stage A。**

## 7. Stage B：反复执行 TMD-only

每轮开始前修改线圈 JSON 中的种子、边界或分组，然后运行：

```matlab
RUN_5T_16CH_TMD_ONLY;
```

脚本会：

1. 加载已保存的原始 `YPn`；
2. 若存在上一轮完成的 TMD MAT，读取其已校准的16端口 `SP_s` 和 `SP_p` 作为轮次对比基线；
3. 按当前线圈 JSON 运行纯 Rx TMD，并实时显示 PSO 最优目标函数收敛曲线；
4. 将优化元件值写回线圈 JSON；
5. 自动创建带时间戳的 JSON 备份；
6. 输出每端口目标匹配、最低点、谐振频率和状态；
7. 生成并保存优化前/后的 S 参数对比图；
8. 保存带时间戳的独立 TMD MAT 文件。

输出示例：

```text
data/solutions/TMD_5T_Sphere200_16LoopRx_DoubleRow_H90_YYYYMMDD_HHMMSS.mat
...Sphere16Rx_...json.before_TMD_YYYYMMDD_HHMMSS
data/solutions/TMD_progress/TMD_Sparameters_YYYYMMDD_HHMMSS.png
data/solutions/TMD_progress/TMD_Sparameters_YYYYMMDD_HHMMSS.fig
```

### 7.1 TMD 进展可视化

`RUN_5T_16CH_TMD_ONLY.m` 提供两层可视化：

1. **优化器实时图**：`particleswarm` 运行时显示当前最优目标函数随迭代次数的变化。曲线持续下降表示搜索仍在改进；长时间平台表示本轮接近收敛，也可能表示边界或变量分组限制了搜索。
2. **每轮物理结果图**：TMD 返回后自动生成四联图，包含上一轮与当前轮的 `SP_s`、前放加载后的 `SP_p` 轮次对比，以及当前轮的接收频率扫描。首轮没有已校准的历史结果，因此基线面板显示 unavailable，只绘制当前轮结果。

实时曲线不是 S 参数，不能用其纵轴直接判断 `-15 dB` 是否合格。MARIE 只有在一轮优化结束并完成网络校准后，才返回可直接解释的 `SP_s`、`SP_p` 和 `SPm_plot_Rx`。在每一个粒子评价处强制重建完整 S 参数图会明显拖慢 PSO，因此本流程采用“实时看目标函数、每轮结束看 S 参数”的方式。

原始 TMD `YPn` 在本案例中包含物理端口及可调元件对应的临时端口，维度可大于16。它不能直接传入 `co_simulation_Rx_no_optim` 生成所谓的“TMD 前16端口基线”，否则 `preamplifier_match` 会把临时端口误当成物理接收端口并发生索引越界。只有完成 TMD 校准并收缩到16个物理端口的结果才能用于该对比。

四联图按以下顺序判读：

| 图 | 主要问题 | 判读方法 |
|---|---|---|
| Previous TMD `SP_s` | 上一轮已校准网络的本征端口状态 | 用作轮次对比；首轮无该数据 |
| Current TMD `SP_s` | 当前轮线圈本征互耦是否改善 | 重点看非对角元素，最差值建议 `< -12 dB` |
| `SP_p` previous/current | 前放加载后的接收匹配是否随轮次改善 | 当前每个通道应低于 `-15 dB`，并检查通道离散 |
| Current Rx frequency sweep | 当前谐振是否位于 212.887 MHz 附近 | 谷值应靠近 Target，频偏建议 `< 0.5 MHz` |

`SP_p` 是前放加载后的逐通道反射指标，不是完整的互耦矩阵。不能因为 `SP_p` 很低就忽略 `SP_s` 非对角互耦；同样，也不能仅因 `SP_s` 对角线较浅就判定纯 Rx 前放加载匹配失败。

每次运行的 PNG 和可再次编辑的 MATLAB FIG 都保存在 `data/solutions/TMD_progress/`。比较不同轮次时，应同时保留对应的 `TMD_*.mat` 和 `.json.before_TMD_*`，避免图像与电路版本失去对应关系。

脚本顶部的开关控制实时收敛图：

```matlab
showOptimizerProgress = true;   % GUI交互运行：显示PSO收敛图
showOptimizerProgress = false;  % 无桌面或批处理运行：关闭实时图
```

无论该开关为何值，每轮结束后的 S 参数四联图都会生成并保存。实时图只用于观察搜索过程，不改变代价函数、搜索边界或最终结果。

### 7.2 首轮工程门槛

| 指标 | 建议门槛 |
|---|:---|
| 前放加载匹配 | 所有 `SP_p < -15 dB` |
| 谐振偏移 | 所有端口 `< 0.5 MHz` |
| 同一物理对称组的匹配离散 | `< 3 dB` |
| 最差非对角互耦 | `SP_s < -12 dB` |

纯 Rx 匹配使用 `SP_p` 和 `figure_freq.SPm_plot_Rx`；`SP_s` 对角线不是该条件下的主要匹配指标。`SP_s` 非对角元素用于互耦检查。

#### 7.2.1 互耦验证模块

互耦验证必须使用目标频率处的常规多端口矩阵 `SP_s` 非对角元素。不要使用 `SP_p` 判断端口间互耦：`SP_p` 是逐通道前放加载后的反射指标，不是完整的 16×16 耦合矩阵。噪声协方差矩阵能够反映接收噪声相关性，但也不能替代电路互耦检查。

本案例端口分组为：

```matlab
upperPorts = 1:8;
lowerPorts = 9:16;
```

建议同时回答四个问题：

1. 全阵列最差的非对角 `Sij` 是哪一对端口？
2. 上排内部、下排内部和跨排耦合分别有多大？
3. 强耦合是否集中在几何相邻 Loop，而不是随机远距离端口？
4. `SP_s` 是否基本满足互易性，排除端口映射或数值异常？

##### A. 全矩阵与分块最差值

加载当前 TMD MAT 后执行：

```matlab
SPs = netp.SP_s;                 % 若加载完整 solution，则改为 solution.netp.SP_s
assert(isequal(size(SPs),[16 16]),'Expected a 16x16 physical-port SP_s');

SPsDB = 20*log10(max(abs(SPs),realmin));
upperPorts = 1:8;
lowerPorts = 9:16;

% 全阵列最差非对角互耦：数值越接近 0，互耦越严重
couplingDB = SPsDB;
couplingDB(1:17:end) = -Inf;
[worstAllDB,idx] = max(couplingDB,[],'all');
[worstAllRow,worstAllCol] = ind2sub(size(couplingDB),idx);

% 上排、下排内部需要排除各自对角线
upperBlock = SPsDB(upperPorts,upperPorts);
upperBlock(1:9:end) = -Inf;
[worstUpperDB,idx] = max(upperBlock,[],'all');
[r,c] = ind2sub([8 8],idx);
worstUpperPair = [upperPorts(r),upperPorts(c)];

lowerBlock = SPsDB(lowerPorts,lowerPorts);
lowerBlock(1:9:end) = -Inf;
[worstLowerDB,idx] = max(lowerBlock,[],'all');
[r,c] = ind2sub([8 8],idx);
worstLowerPair = [lowerPorts(r),lowerPorts(c)];

% 跨排块没有物理对角线，不要删除同一局部索引的元素
crossBlock = SPsDB(upperPorts,lowerPorts);
[worstCrossDB,idx] = max(crossBlock,[],'all');
[r,c] = ind2sub([8 8],idx);
worstCrossPair = [upperPorts(r),lowerPorts(c)];

fprintf('Worst all:   S%d%d = %.2f dB\n', ...
    worstAllRow,worstAllCol,worstAllDB);
fprintf('Worst upper: S%d%d = %.2f dB\n', ...
    worstUpperPair(1),worstUpperPair(2),worstUpperDB);
fprintf('Worst lower: S%d%d = %.2f dB\n', ...
    worstLowerPair(1),worstLowerPair(2),worstLowerDB);
fprintf('Worst cross: S%d%d = %.2f dB\n', ...
    worstCrossPair(1),worstCrossPair(2),worstCrossDB);
```

首轮工程门槛：

```matlab
assert(worstAllDB < -12, ...
    'Coupling failed: at least one off-diagonal Sij is above -12 dB');
```

建议解释尺度：

| 最差非对角 `Sij` | 解释 | 处理 |
|---:|---|---|
| `< -15 dB` | 较好 | 可继续检查场和 SNR |
| `-15` 至 `-12 dB` | 首轮可接受，但裕量有限 | 保留结果并检查几何相邻端口 |
| `> -12 dB` | 不通过 | 优先优化重叠、排距或错位角，不要只扩展 TMD 元件范围 |

上述阈值是本项目的工程筛选值，不是适用于所有线圈和前放架构的统一标准。正式报告必须给出完整矩阵和最差端口对，不能只写“互耦通过”。

##### B. 互耦矩阵可视化

```matlab
figure('Color','w','Position',[100 100 1150 900]);
tiledlayout(2,2,'TileSpacing','compact','Padding','compact');

blocks = {upperPorts,upperPorts,'Upper to upper'; ...
          lowerPorts,lowerPorts,'Lower to lower'; ...
          upperPorts,lowerPorts,'Upper to lower'; ...
          lowerPorts,upperPorts,'Lower to upper'};

for k = 1:4
    nexttile;
    B = SPsDB(blocks{k,1},blocks{k,2});
    imagesc(B,[-40 0]);
    axis image;
    set(gca,'YDir','normal');
    xlabel('Excited port');
    ylabel('Observed port');
    title(blocks{k,3});
    colorbar;
end

sgtitle('16-channel SP_s coupling blocks at 212.887 MHz');
```

读取热图时重点观察非对角元素。`Upper to upper` 和 `Lower to lower` 中的主对角线是各端口自身反射，不属于互耦；跨排两个块中的所有元素均为互耦。若强耦合呈现符合环形相邻关系的带状或周期结构，通常与几何相邻有关；若远距离端口随机出现强耦合，应重新核对端口编号、实体映射和 symmetry。

##### C. 输出最强的若干无序端口对

互易网络的 `Sij` 与 `Sji` 表示同一对端口，因此列表只保留上三角：

```matlab
pairMask = triu(true(16),1);
pairValues = SPsDB;
pairValues(~pairMask) = -Inf;

[sortedDB,linearIdx] = sort(pairValues(:),'descend');
keep = isfinite(sortedDB);
sortedDB = sortedDB(keep);
linearIdx = linearIdx(keep);

nReport = min(12,numel(sortedDB));
[observedPort,excitedPort] = ind2sub([16 16],linearIdx(1:nReport));

couplingTable = table(observedPort,excitedPort,sortedDB(1:nReport), ...
    'VariableNames',{'PortI','PortJ','Coupling_dB'});
disp(couplingTable);
```

应把最强端口对映射回三维几何。对于双排错位阵列，必须分别判断它属于同排相邻、跨排近邻还是非近邻异常耦合。仅看端口编号差不能可靠判断空间距离。

##### D. 互易性数值检查

无源线性线圈网络原则上应近似互易。使用非共轭转置 `.'` 检查：

```matlab
reciprocityAbs = max(abs(SPs-SPs.'),[],'all');
reciprocityRel = reciprocityAbs/max(max(abs(SPs),[],'all'),realmin);

fprintf('SP_s reciprocity absolute error: %.3e\n',reciprocityAbs);
fprintf('SP_s reciprocity relative error: %.3e\n',reciprocityRel);

assert(reciprocityRel < 1e-6, ...
    'Unexpected SP_s asymmetry: check port mapping and numerical setup');
```

`1e-6` 是用于发现明显映射或计算异常的初始数值阈值。如果项目的求解容差导致稳定但略大的误差，应记录实际基线后再调整，不能为了通过检查随意放宽。

##### E. 最差端口对的频率扫描

目标频率处通过并不保证频带内始终满足要求。若 `figure_freq.SPm_plot_Rx` 保存了完整的端口对频扫，可绘制最差端口对：

```matlab
F = netp.figure_freq;             % 完整 solution 时使用 solution.netp.figure_freq
assert(ndims(F.SPm_plot_Rx)==3 && ...
    size(F.SPm_plot_Rx,1)==16 && size(F.SPm_plot_Rx,2)==16, ...
    'SPm_plot_Rx does not contain a full 16-port frequency sweep');

couplingCurve = 20*log10(max(abs(squeeze( ...
    F.SPm_plot_Rx(worstAllRow,worstAllCol,:))),realmin));

figure('Color','w');
plot(F.freq_range/1e6,couplingCurve,'LineWidth',1.5);
xline(F.freq_range(F.freq_idx)/1e6,'k--','Target');
yline(-12,'r:','-12 dB');
grid on;
xlabel('Frequency (MHz)');
ylabel(sprintf('|S_{%d%d}| (dB)',worstAllRow,worstAllCol));
title('Worst coupling-pair frequency sweep');
```

如果该数组只保存了对角频扫，则不能从中推断宽带互耦，需要修改频扫模块或在多个频点重新计算完整 `SP_s`。不要把对角 `Sii` 曲线误标为耦合曲线。

##### F. 互耦验收结论

互耦模块通过至少要求：

```matlab
couplingPass = worstAllDB < -12;
reciprocityPass = reciprocityRel < 1e-6;

assert(couplingPass,'Worst off-diagonal coupling failed');
assert(reciprocityPass,'SP_s reciprocity check failed');
```

通过后仍需保留：完整 `SP_s` 热图、最强端口对表、三类分块最差值和互易性误差。TMD 可以改变端口网络状态，但若最差互耦持续不合格，应返回几何外层优化，而不是无限增加 PSO 迭代次数。

### 7.3 迭代策略

按以下顺序调整，不要同时改变所有设置：

1. 先确认 symmetry、元件顺序和端口映射。
2. 检查优化值是否压在上下界。
3. 谐振整体偏高时，针对性提高等效调谐电容范围；偏低时反向调整。
4. 只有少数端口离群时，先检查其几何和实体映射，再考虑拆分对称组。
5. 匹配合格但互耦不合格时，先比较固定 `YPn` 下不同电路轮次；若互耦随电路显著变化，使用联合 minimax，若长期稳定不合格再进入几何外层扫描。

每轮记录 JSON 备份名、TMD MAT 文件、S 参数进展图、种子、边界、最终元件值和四项门槛。不要只保留最后一次被覆盖的线圈 JSON。

### 7.4 损耗感知的最差通道优化

本案例默认启用独立的损耗感知最终优化阶段：

```matlab
useLossAwareTMD = true;
targetReturnDB = -15;
useCouplingConstraint = true;
targetCouplingDB = -12;
useFullHardBounds = true;
```

原版 MARIE 最终 TMD 目标主要最小化端口阻抗整体误差，而且代价函数没有传入元件 `Q`。对于 16 通道及多个优化变量族，整体范数可能通过改善多数通道来补偿少数失败通道，因此会出现部分通道已经达到 `-20 dB`，另一个变量族仍停留在 `-10 dB` 左右的情况。最终校准再计入有限 `Q` 后，优化阶段预测的匹配质量也可能与输出的 `SP_p` 不一致。

损耗感知版本只替换最终的联合调谐、匹配和前放加载优化，不修改 MARIE 原始函数。它在每次粒子评估中使用与最终校准一致的有限 `Q` 元件模型，同时计算前放加载后的逐通道 `SP_p` 和常规多端口 `SP_s`。启用互耦约束时使用：

```text
matchRatio    = max_p(|SP_p(p)|)       / 10^(targetReturnDB/20)
couplingRatio = max_i!=j(|SP_s(i,j)|) / 10^(targetCouplingDB/20)
cf            = max(matchRatio, couplingRatio)
```

因此：

- `cf < 1` 表示所有物理接收端口匹配和所有非对角互耦均达到目标；
- 匹配与互耦不能互相补偿，也不能再通过牺牲一个通道族改善平均值；
- JSON 中的 `optim.minim` 和 `optim.maxim` 是最终阶段的硬边界；
- `useFullHardBounds=true` 时搜索完整 JSON 硬边界；改为 `false` 时才使用当前值附近的 `0.5-1.5` 倍窗口；
- 最终仍以校准后的 `SP_p`、频率扫描和 `SP_s` 非对角互耦验收，而不是只看 PSO 目标值。

涉及的新增文件为：

```text
src/src_physics/src_electronics/co_simulation/
  co_sim_cost_functions/
    matching_and_tuning_and_preamplifierdecoupling_loss_aware.m
  co_sim_runners/
    runner_M_T_PD_loss_aware.m
  co_sim_master_files/
    co_simulation_Rx_optim_loss_aware.m
```

修改本地工程后，必须将以上三个文件和 `RUN_5T_16CH_TMD_ONLY.m` 同步到 Linux 服务器的相同相对路径。重新进入 MATLAB 后执行：

```matlab
cd('/home/<user>/marie-tools');
startup;
clear functions;
rehash path;

which co_simulation_Rx_optim_loss_aware -all
which runner_M_T_PD_loss_aware -all
which matching_and_tuning_and_preamplifierdecoupling_loss_aware -all

RUN_5T_16CH_TMD_ONLY;
```

三个 `which` 结果都必须指向 `/home/<user>/marie-tools/src/...` 下的新文件。该改动只依赖已有 `YPn`，不需要重新执行 Stage A。若要与原版目标做对照，将 `useLossAwareTMD` 改为 `false`；不要覆盖或改名 MARIE 原版 `co_simulation_Rx_optim.m`、`runner_M_T_PD.m` 和原始代价函数。

每轮输出新增以下记录：

```matlab
metrics.loss_aware_tmd
metrics.coupling_constrained_tmd
metrics.target_return_dB
metrics.target_coupling_dB
metrics.full_hard_bounds
metrics.worst_loaded_return_dB
metrics.worst_loaded_margin_dB
```

其中 `worst_loaded_margin_dB > 0` 才表示最差端口低于目标线。若损耗感知优化仍长期停滞，应先检查失败通道族的元件是否压在硬边界，再决定扩大对应元件范围；不要只增加迭代次数。

#### 7.4.1 本案例的实际优化经验

本案例经历了以下阶段：

1. 初始独立 symmetry 设置发生 MARIE 内部 ID 碰撞，表现为奇偶通道交替失配和 B1- 能量差异。
2. 修复内部 ID 后，原版 TMD 的代表性结果为四个通道族约 `-14.212/-19.699/-12.595/-15.542 dB`，谐振和互耦通过，但匹配未全部通过。
3. 扩大 Cp1、Ls、Cp2 和 Cseg 范围后，原版目标仍把一个通道族留在约 `-10 dB`，重复运行改善很小。
4. 切换到只约束匹配的损耗感知 minimax 后，所有通道跨过 `-15 dB`，但最差互耦从早期约 `-15 dB` 恶化为 `S10,9=-9.732 dB`。
5. 固定几何和固定 `YPn` 的六轮结果证明 `S10,9` 随电路状态变化超过 5 dB，因此下一轮必须使用匹配与互耦联合 minimax，而不是立即修改几何。
6. 联合匹配/互耦轮次 `20260807_070421` 已取得最差 `SP_p=-16.081 dB`、最差互耦 `S4,3=-12.257 dB`，证明两项可以同时满足；但端口 10/12/14/16 的谷底位于 `213.866870 MHz`，最大频偏 `0.979478 MHz`。原因是该轮代价只评估目标频点幅值，没有约束谷底位置。

这说明“继续增加原版 PSO 迭代次数”不是本案例的主要解决办法。对于多通道、多变量族接收阵列，应同时满足：

- symmetry 的真实内部 ID 无碰撞；
- 搜索边界覆盖合理元件值；
- 代价函数使用与最终校准一致的有限 Q 模型；
- 代价函数约束最差通道，而不是只最小化整体误差。

轮次 `20260807_063923` 的最差匹配为 `-16.101 dB`、最大频偏 `0.451412 MHz`，但 `S10,9=-9.732 dB`，不能进入正式 Stage C。联合目标应先使用 `SP_p<-15 dB` 和非对角 `SP_s<-12 dB` 验证同时可行；通过后再考虑提高鲁棒性目标。

#### 7.4.4 当前冻结候选：20260807_070421

本项目决定停止继续优化，以轮次 `20260807_070421` 的当前线圈 JSON 进入 Stage C。该选择是人工放宽流程门槛，不表示自动验收四项全部通过。

| 指标 | 当前结果 | 原门槛 | 判断 |
|---|---:|---:|---|
| 最差前放加载匹配 | -16.081 dB | < -15 dB | 通过 |
| 最差匹配裕量 | 1.081 dB | > 0 dB | 通过 |
| 最差非对角互耦 `S4,3` | -12.257 dB | < -12 dB | 通过，裕量 0.257 dB |
| 最大谐振偏移 | 0.979478 MHz | < 0.5 MHz | 未通过，人工接受 |
| `SP_s` 互易性相对误差 | 1.419e-15 | < 1e-6 | 通过 |

四类通道结果：

| 通道族 | SP_p target (dB) | f_min (MHz) | 状态 |
|---|---:|---:|---|
| 1/3/5/7 | -16.085 | 213.389907 | 原规则下 DETUNED |
| 2/4/6/8 | -28.137 | 213.015151 | PASS |
| 9/11/13/15 | -16.081 | 212.725566 | PASS |
| 10/12/14/16 | -17.133 | 213.866870 | 原规则下 DETUNED |

进入 Stage C 前必须冻结并保留：

```text
当前 Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json
TMD_5T_Sphere200_16LoopRx_DoubleRow_H90_20260807_070421.mat
TMD_Sparameters_20260807_070421.png/.fig
Sphere16Rx_...json.before_TMD_20260807_070421
```

Stage C 必须使用该轮结束后写回的 JSON，并以 `TMD=0` 重新执行最终场与 SNR 求解，禁止再次运行 Stage B 后继续沿用 `070421` 标签。论文或报告中应披露：所有端口在目标频点满足前放加载匹配，互耦满足当前门槛，但部分端口的扫频谷底相对目标频率最大偏移约 `0.98 MHz`。

#### 7.4.2 联合优化前的种子与备份

不要覆盖当前匹配合格的 `063923` 电路。Linux MATLAB 中先执行：

```matlab
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json');

copyfile(coilJson,[coilJson '.accepted_match_only_20260807_063923']);

seedJson = [coilJson '.before_TMD_20260807_053238'];
assert(exist(seedJson,'file')==2,'Historical coupling-friendly seed is missing');
copyfile(seedJson,coilJson);
```

选择该种子的依据是：它接近早期互耦通过的电路状态，同时保留后续扩大后的元件边界。恢复后重新运行 symmetry 内部 ID 检查，并确认 JSON 的 `optim.minim/maxim` 仍为当前批准范围。

若不希望恢复历史种子，也可从当前 JSON 使用完整硬边界重新搜索，但不得删除上述 `accepted_match_only` 备份。联合优化仍复用同一个 `YPn`，不需要重跑 Stage A。

#### 7.4.3 自动仿真日志

`RUN_5T_16CH_TMD_ONLY.m` 每次成功保存 TMD MAT 后，会自动追加：

```text
MARIE_5T_16通道Loop球形体模仿真日志.md
```

每一轮自动记录：

- `runTag`、case、优化模式与目标；
- 使用的 `YPn`、线圈 JSON、运行前备份和上一轮基线；
- TMD MAT 与 S 参数图片路径；
- 最差 `SP_p`、匹配裕量和最大谐振偏移；
- 全阵列、上排、下排及跨排最差互耦，以及 `SP_s` 互易性误差；
- 逐端口 `SP_p`、扫描最小值、谐振频率与状态；
- 匹配、谐振、互耦和互易性四项门槛是否通过以及本轮建议。

只有成功完成并保存结果的轮次才会写入日志。优化中断、函数缺失或 MATLAB 报错不会产生一条“成功轮次”，这类故障应人工写在日志的过程记录中。日志是运行索引，不替代对应的 MAT、JSON 备份和图像文件。

### 7.5 TMD 阶段发现电磁求解设置错误时的回退流程

TMD 是固定原始电磁网络 `YPn` 上的电路优化。若 TMD 过程中发现几何、材料、频率、离散或端口映射有误，当前 `YPn` 与由它产生的全部 TMD 验收结果立即失效。TMD 无法通过调整电容、电感修复错误的三维电磁模型。

此时应执行：

```text
停止当前 TMD
  -> 标记并隔离旧 YPn、TMD MAT、S 参数图和被更新的线圈 JSON
  -> 修正输入 JSON、几何或电磁求解设置
  -> 使用新 caseTag/caseName 重新执行 Stage A
  -> 验证新 YPn 的频率、维度、有限性和版本对应关系
  -> 修改 TMD-only runner 指向新 YPn 与新线圈 JSON
  -> 从新 YPn 重新开始 Stage B
```

仅重新运行 `geo_assembly` 不够。新的 TMD 缓存必须重新完成：

```text
geo_assembly -> wsvie_assembly -> solver_wsvie -> 保存新的 YPn
```

#### 7.5.1 是否必须重跑 Stage A

| 修改内容 | 旧 `YPn` 是否有效 | 处理方式 |
|---|---|---|
| Loop 尺寸、位置、重叠、排距、错位角 | 否 | 新建几何版本并重跑 Stage A |
| 导线网格、端口位置、分段元件物理位置 | 否 | 重跑 Stage A，并重新验证实体映射 |
| 体模文件、尺寸、材料参数、体素分辨率 | 否 | 重跑 Stage A |
| 场强、核素、拉莫尔频率 | 否 | 重跑 Stage A，UISNR basis 也需重新判断 |
| VIE 基函数、积分阶数及影响系统矩阵的求解参数 | 否 | 重跑 Stage A |
| 屏蔽体、支撑面或其他导体结构 | 否 | 重跑 Stage A |
| 端口数量、端口实体编号或端口/通道映射 | 否 | 重跑 Stage A |
| 电容/电感初值与上下界 | 是 | 复用正确的 `YPn`，重新运行 Stage B |
| `optim.symmetry` 分组 | 是 | 验证内部 ID 后重新运行 Stage B |
| PSO 粒子数、迭代次数、容差和随机种子 | 是 | 直接重新运行 Stage B |
| 集总元件 Q 值或前放模型参数 | 通常是 | 可复用 `YPn`，但必须重新校准网络并重算最终噪声/SNR |

判断原则是：只要修改会改变线圈、体模和环境之间的电磁耦合，旧 `YPn` 就失效；只修改固定电磁网络上的集总电路或优化器设置，才可以复用 `YPn`。

#### 7.5.2 旧文件与新版本命名

不要直接删除或覆盖错误案例。先将其标记为无效，保留问题原因和时间：

```text
YPn_5T_Sphere200_16LoopRx_DoubleRow_H90_INVALID_<reason>.mat
TMD_5T_Sphere200_16LoopRx_DoubleRow_H90_INVALID_<timestamp>.mat
Sphere16Rx_...json.invalid_backup
TMD_progress/TMD_Sparameters_<timestamp>_INVALID.png
```

修正后的案例使用新版本标识，例如：

```matlab
caseTag  = '5T_Sphere200_16LoopRx_DoubleRow_H90_v2';
caseName = 'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5_v2';
```

Stage A、Stage B、输入 JSON、线圈 JSON、`YPn`、TMD MAT 和图像必须使用同一版本标识。禁止让新 runner 继续读取旧文件名。

旧 TMD 得到的元件值最多只能作为新案例的初始猜测。只有在元件拓扑、数量、顺序和物理位置均未改变时才可移植这些数值；移植后仍必须从新 `YPn` 完整重跑 TMD，旧 S 参数和通过状态不得沿用。

#### 7.5.3 新 `YPn` 的最低验收

在重新进入 Stage B 前运行：

```matlab
rawFile = fullfile(pwd,'data','solutions', ...
    'YPn_5T_Sphere200_16LoopRx_DoubleRow_H90_v2.mat');

S = load(rawFile,'YPn','network_meta');

assert(~isempty(S.YPn),'New YPn is empty');
assert(all(isfinite(S.YPn),'all'),'New YPn contains NaN or Inf');
assert(abs(S.network_meta.frequency_Hz/1e6-212.88739259) < 1e-6, ...
    'New YPn frequency does not match the 5 T proton case');

disp(size(S.YPn));
disp(S.network_meta);
```

同时重新检查三维几何、16 个物理端口、元件顺序、端口实体映射和线圈到体模的间距。`YPn` 数值检查通过不代表几何一定正确。

恢复运行前，还要修改 `RUN_5T_16CH_TMD_ONLY.m` 顶部的 `caseTag` 与 `caseName`，确认 `rawNetworkFile` 和 `coilJson` 指向新版本。第一轮新 TMD 生成的四联 S 参数图应被视为新的基线，不再与错误 `YPn` 的门槛结论混合。

## 8. 几何外层循环

TMD 是固定几何上的内层电路优化，不能取代几何去耦。推荐外层循环：

```text
几何候选 A -> Stage A 一次 -> Stage B 多轮 -> 记录最优门槛
几何候选 B -> Stage A 一次 -> Stage B 多轮 -> 记录最优门槛
几何候选 C -> Stage A 一次 -> Stage B 多轮 -> 记录最优门槛
```

同排耦合优先扫描 `span`；跨排耦合优先扫描 `zRow` 或 `rowStagger`。每个候选必须使用新的 `caseName`、`.msh`、线圈 JSON、输入 JSON、`YPn` 和输出前缀，禁止覆盖其他几何的缓存。

一次只改变一个几何因素，否则无法判断性能变化来源。

## 9. Stage C：固定最终电路并计算场/SNR

通常只有 Stage B 门槛通过后才进入该阶段。本案例人工接受 `070421` 轮次的
`0.979478 MHz` 最大频偏，因此 Stage C 结果必须保留这一限制说明。

### 9.1 统一最终化脚本

确认当前线圈 JSON 是接受的最终版本，然后运行：

```matlab
FINALIZE_5T_16CH_FROM_CHECKPOINT;
```

脚本首先把当前线圈 JSON 保存为：

```text
Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json.accepted_20260807_070421
```

随后自动选择路径：

- 若存在 `MREDM_preTMD_5T_Sphere200_16LoopRx_DoubleRow_H90.mat`，从完整检查点继续，不重复三维电磁求解；
- 若检查点不存在，自动执行一次常规完整求解，并在 `geo_assembly` 之前设置 `MREDM.inputs.tmd=0`；该路径耗时较长，但不会运行 PSO，也不会修改当前元件值。

缺少完整检查点时出现以下警告是预期行为，不是失败：

```text
Full pre-TMD checkpoint is missing. Running one conventional TMD=0 full EM solve ...
```

输出：

```text
data/solutions/MARIE_0_inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90_FINAL.mat
```

### 9.2 检查点缺失时的注意事项

不需要重新运行 `PRECOMPUTE_5T_16CH_EM_NETWORK`，也不需要手工修改原输入 JSON 的 `TMD` 字段。新版 `FINALIZE_5T_16CH_FROM_CHECKPOINT.m` 会在内存中强制设置 `TMD=0` 并完成常规全求解。

该路径会重新执行：

```text
load_inputs -> geo_assembly -> wsvie_assembly -> solver_wsvie
            -> co_simulation(TMD=0) -> em_ehfield_wsvie -> save
```

运行期间不要再启动 Stage B，不要替换当前线圈 JSON。结束时应看到：

```text
[Stage C completed] ...MARIE_0_..._FINAL.mat
[Finalization mode] conventional TMD=0 full run
[Accepted TMD run] 20260807_070421
```

不要直接把 Stage B 的旧 B1-/SNR 结果解释为新电路结果。TMD 改变了场校准矩阵，最终场和噪声指标必须使用接受的固定电路重新计算。

## 10. 最终结果检查与后处理

加载最终结果：

```matlab
resultFile = fullfile(pwd,'data','solutions', ...
    'MARIE_0_inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90_FINAL.mat');
R = load(resultFile,'solution');
solution = R.solution;

assert(isequal(size(solution.netp.SP_s),[16 16]));
assert(size(solution.h_field.Rx.b1m,4)==16);
assert(isfield(solution.snr_field,'SNR'));
```

运行专用后处理：

```matlab
POST_5T_16CH_SPHERE;
```

MARIE 的 `TMD=0` 接收协同仿真不会生成 `solution.netp.figure_freq`，这是
`co_simulation_Rx_no_optim` 与优化路径的结构差异，不代表最终仿真失败。后处理脚本按以下顺序获取扫频：

1. 优先读取最终结果自身的 `figure_freq`；
2. 若缺失，只从接受轮次 `TMD_..._20260807_070421.mat` 读取扫频缓存；
3. 若接受轮次也不存在，跳过 Figure 01 的扫频子图，继续生成最终 S 参数矩阵、B1-、噪声和 SNR/UISNR 图。

该回退只复用相同冻结电路的扫频曲线。目标频点 `SP_s/SP_p`、场、噪声与 SNR 始终来自最终 `MARIE_0_*_FINAL.mat`。

后处理脚本默认优先读取上述最终 `MARIE_0_*_FINAL.mat`。若最终文件不存在，它会明确警告并回退旧的 `MARIE_1_*.mat`；正式报告不应使用该回退结果。

主要输出：

```text
01_Sparameters_and_Rx_sweep.png
02_B1minus_16channels.png
03_Rx_noise_covariance.png
04_SNR_UISNR_efficiency.png
05_SNR_UISNR_centerline_profiles.png
05_SNR_UISNR_centerline_profiles.csv
summary_metrics.mat
```

## 11. UISNR 与发射指标边界

现有 UISNR basis 对应相同 5 T、200 mm 球体和 `R115/H140` 连续圆柱支撑面。当前导线位于 `z=[-70,+70] mm`，在体模、频率、VIE 基函数和支撑半径一致时可以复用该 UISNR 上限。

改变支撑半径、轴向覆盖、体模、体素大小、频率或 VIE 离散后必须重新生成 UISNR basis。

本案例为纯 Rx 阵列，不提供正式 Tx B1+、SAR 或 SAR 效率。`txe_field` 的互易性辅助数据不能替代真实 Tx/TxRx 仿真。

## 12. 文件管理与运行记录

建议目录角色：

| 文件 | 角色 | 是否可覆盖 |
|---|---|---|
| `.msh` | 固定几何 | 否 |
| 线圈 `.json` | 当前活动电路 | 会被 TMD 更新 |
| `.json.before_TMD_*` | 每轮电路快照 | 否 |
| `YPn_*.mat` | 固定几何原始网络 | 否 |
| `MREDM_preTMD_*.mat` | 可选完整检查点 | 否 |
| `TMD_*_时间戳.mat` | 每轮网络优化结果 | 否 |
| `MARIE_5T_16通道Loop球形体模仿真日志.md` | 自动追加的轮次索引与数值验收 | 仅追加，不覆盖历史 |
| `MARIE_0_*_FINAL.mat` | 最终场和 SNR | 否 |

运行记录至少包含：

| 几何版本 | TMD 轮次 | 种子/边界 | 最差 SP_p | 最大频偏 | 最差同排 Sij | 最差跨排 Sij | 是否接受 |
|---|---|---|---:|---:|---:|---:|---|
| H90/Z25/Span50/Stagger22.5 |  |  |  |  |  |  |  |

## 13. 完成检查表

- [ ] 几何、体模和端口映射检查通过。
- [ ] symmetry 按真实内部计数验证通过。
- [ ] Stage A 保存了带唯一几何标识的原始 `YPn`。
- [ ] 每轮 Stage B 都保存了 TMD MAT 和对应 JSON 备份。
- [ ] 每轮成功的 Stage B 已同步写入仿真日志，并能对应 MAT、JSON 与 S 参数图。
- [ ] 所有端口匹配与谐振门槛通过。
- [ ] 同排和跨排互耦门槛通过。
- [ ] 最终 JSON 已冻结，不再运行 TMD 覆盖。
- [ ] Stage C 使用 `TMD=0` 计算了最终场、噪声和 SNR。
- [ ] 后处理使用的是最终结果，而不是某轮旧电路结果。
