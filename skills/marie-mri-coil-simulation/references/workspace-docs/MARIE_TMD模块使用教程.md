# MARIE 3.0 TMD 模块使用教程

## 1. 模块定位

TMD 用于 MARIE 电磁网络与集总电路的协同仿真，包括调谐、匹配以及受支持电路拓扑下的去耦。它以三维电磁求解得到的原始多端口网络为输入，优化线圈 JSON 中声明为可变的电容、电感和匹配网络。

TMD 不重新设计线圈几何。Loop 重叠、轴向排距、错位角或屏蔽结构造成的互耦，仍需通过几何设计解决。

推荐将计算分成三个阶段：

```text
Stage A：固定几何的三维电磁求解，保存原始 YPn
Stage B：复用 YPn，多轮运行 TMD，筛选 S 参数
Stage C：冻结最终电路，以 TMD=0 计算场、噪声和 SNR
```

这样比每轮都运行完整 MARIE runner 更高效，也更容易追踪每次电路修改。

## 2. `YPn`、`YPm` 与最终结果

主流程进入 TMD 时：

```matlab
YPn = MREDM.fields.netp.YP_s;
```

此时 `YPn` 是尚未附加调谐和匹配网络的原始导纳矩阵。TMD 结束后：

```matlab
MREDM.fields.netp.YP_s = YPm;
```

最终 `solution.netp.YP_s` 已经是处理后的 `YPm`。不能把它再次作为原始 `YPn` 输入 TMD，否则会重复附加电路。

因此：

- 仅保存最终 `MARIE_1_*.mat`，通常无法可靠独立重跑 TMD。
- 在 `solver_wsvie` 后、`co_simulation` 前保存原始 `YPn`，即可反复执行电路优化。
- 若还希望最终场计算不重复电磁求解，需要额外保存 pre-TMD 的完整 `MREDM` 检查点。

## 3. 开启与关闭 TMD

输入 JSON：

```json
{
  "B0": 5,
  "Nucleus": "1H",
  "WireFile": "Custom/MyRxArray.msh",
  "TMD": 1
}
```

| 设置 | 行为 | 用途 |
|---:|---|---|
| `TMD=1` | 运行优化并把新元件值写回线圈 JSON | 搜索调谐/匹配方案 |
| `TMD=0` | 使用 JSON 当前值，不运行 PSO | 最终固定电路复算 |

TMD 会覆盖线圈 JSON。每轮运行前必须备份，且禁止多个任务并发写同一个 case。

## 4. 几何与电路文件关系

WIE 线圈通常包含同名文件：

```text
data/coils/wire_files/Custom/MyRxArray.msh
data/coils/wire_files/Custom/MyRxArray.json
```

必须满足：

1. `.msh` 集总点顺序与 JSON `elements` 顺序一致。
2. `excitation.entity` 指向正确通道。
3. `type='port'` 数量等于最终 RF 端口数。
4. `load`、元件数量、`optim.boolean` 与生成原始 `YPn` 时保持一致。

TMD 模式下，可优化元件可能临时成为电磁求解端口，因此原始 `YPn` 的维度可能远大于最终 `16x16` RF 网络。这不是通道数错误。

## 5. 线圈 JSON 的 TMD 字段

### 5.1 三元匹配网络

```json
{
  "number": 1,
  "type": "port",
  "load": "capacitorParallel_inductorSeries_capacitorParallel",
  "value": [2.6453e-11, 2.37565e-8, 2.71397e-11],
  "Q": [500, 200, 500],
  "optim": {
    "boolean": 1,
    "minim": [5e-12, 5e-9, 5e-12],
    "maxim": [80e-12, 60e-9, 80e-12],
    "symmetry": 1000
  },
  "cross_talk": {},
  "excitation": {"entity": 1, "TxRx": "Rx"}
}
```

`value`、`Q`、`minim` 和 `maxim` 顺序对应 `Cp1/Ls/Cp2`，单位为 F/H/F。

### 5.2 分段调谐电容

```json
{
  "number": 2,
  "type": "element",
  "load": "capacitor",
  "value": 2.7894e-12,
  "Q": 500,
  "optim": {
    "boolean": 1,
    "minim": 1.5e-12,
    "maxim": 5e-12,
    "symmetry": 5000
  },
  "cross_talk": {},
  "excitation": {"entity": 1, "TxRx": "Rx"}
}
```

### 5.3 字段说明

| 字段 | 含义 | 注意事项 |
|---|---|---|
| `type` | `port` 或 `element` | 与 `.msh` 点顺序一致 |
| `load` | 电路拓扑/元件类型 | 决定 `value` 的数量与顺序 |
| `value` | 当前值和优化起点 | 使用 SI 单位 |
| `Q` | 品质因数 | 影响损耗、噪声和 SNR |
| `optim.boolean` | 是否作为 TMD 变量 | 改变它会改变原始网络端口结构 |
| `optim.minim/maxim` | 优化边界 | 应符合实际元件范围 |
| `optim.symmetry` | 变量共享标识的输入值 | MARIE 还会添加内部偏移 |
| `excitation.TxRx` | `Rx`、`Tx` 或 `TxRx` | 决定协同仿真分支 |

## 6. `optim.symmetry` 的内部规则

在 `co_simulation_matching_tuning_settings.m` 中，内部编号近似为：

```matlab
internalPortSym = jsonPortSym + c1;
internalTuneSym = jsonTuneSym + t;
```

`c1` 会经过每个展开的 port 变量和每个参与优化的普通元件。相同的最终内部编号才表示共享同一优化变量。

对于本项目固定结构：

```text
每通道 = 1 个三元 port + 7 个分段电容
内部计数步长 = 3 + 7 = 10
```

复现内部编号：

```matlab
nChannels = 16;
portInternal = zeros(nChannels,3);
tuneInternal = zeros(nChannels,7);
c1 = 0;

for ch = 1:nChannels
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
```

该代码只适用于上述固定顺序。其他 port 拓扑、固定元件或不同 JSON 排列必须重新按源码计数，不能套用固定步长或固定 `t`。

### 6.1 何时共享变量

只有几何、负载、端口位置、元件位置、Q 值和前放模型均可通过严格对称变换映射时才共享。人体模型、偏心体模、不对称屏蔽体、不同 Loop 尺寸或局部去耦网络都会破坏共享依据。

变量过少会掩盖真实不对称；变量过多会扩大 PSO 维度并产生离群端口。建议从物理对称分组开始，再根据结果逐步拆分。

## 7. 16 通道双排案例

上排 1--8 和下排 9--16 分别具有 45 度旋转对称性，但两排 z 位置和方位错位不同，因此各使用一套变量：

```matlab
for ch = 1:16
    idx = (ch-1)*8 + (1:8);
    if ch <= 8
        E(idx(1)).optim.symmetry = 1000 - 10*(ch-1);
        tuneGroup = 5000 - 10*(ch-1);
    else
        E(idx(1)).optim.symmetry = 2000 - 10*(ch-9);
        tuneGroup = 6000 - 10*(ch-9);
    end
    for k = idx(2:8)
        E(k).optim.symmetry = tuneGroup;
    end
end
```

最终为 8 个变量：上下排各自的 `Cp1/Ls/Cp2/Cseg`。选择依据是物理对称性、源码内部编号规则，以及 64 个完全独立变量曾产生多个失谐离群端口的实际结果。

完整执行步骤见 `MARIE_5T_16通道Loop球形体模仿真操作指南.md`。

## 8. Stage A：保存可复用原始网络

必须在：

```matlab
MREDM = solver_wsvie(MREDM);
```

之后、`co_simulation` 之前保存：

```matlab
YPn = MREDM.fields.netp.YP_s;
save(rawNetworkFile,'YPn','network_meta','-v7.3');
```

本项目提供：

```matlab
PRECOMPUTE_5T_16CH_EM_NETWORK;
```

`YPn` 只在几何、体模、网格、频率、屏蔽结构和原始端口/元件拓扑不变时有效。改变元件数、类型、顺序或 `optim.boolean` 后也必须重算。

可选保存完整 pre-TMD `MREDM` 检查点，用于最终场计算，但文件可能很大。仅迭代 S 参数时无需保存完整检查点。

## 9. Stage B：独立反复运行 TMD

本项目当前函数签名要求 `Q_val`，纯 Rx 调用为：

```matlab
RLC_org = geo_scoil_lumped_elements(coilJson,0);
RLC_tmd = geo_scoil_lumped_elements(coilJson,1);
Q_val = co_simulation_get_Q_values(RLC_tmd);
[options_PSO_1,options_PSO_2] = co_simulation_optimization_settings();

[return_elements,phi_lumped_elements,M_cal,YPm,ZPm,SPm,SPp,figure_freq] = ...
    co_simulation_Rx_optim(YPn,emc,RLC_org,RLC_tmd,Q_val, ...
    options_PSO_1,options_PSO_2);
```

随后使用 `geo_scoil_print_lumped_elements` 将结果写回 JSON，并单独保存 `SPm/SPp/figure_freq/M_cal`。本项目已封装：

```matlab
RUN_5T_16CH_TMD_ONLY;
```

该脚本自动创建带时间戳的 JSON 备份和 TMD MAT 文件。每轮调整顺序建议为：

1. 检查元件映射与内部 symmetry。
2. 调整种子和实际可实现边界。
3. 检查是否出现边界饱和。
4. 必要时拆分物理上不再等价的分组。
5. 匹配合格但互耦不合格时返回几何设计，不要无限扩大电路范围。

仓库自带的 `CO_SIMULATION_runner.m` 体现了相同思路，但当前版本缺少 `Q_val`，输出参数顺序也与现有函数不一致，且保存阶段使用未初始化的 `MREDM`。不要原样用于正式结果。

## 10. TMD 结果验收

纯 Rx 阵列主要检查：

- `SP_p`：前放加载条件下的接收匹配；
- `figure_freq.SPm_plot_Rx`：频扫和谐振位置；
- `SP_s` 非对角元素：端口互耦；
- 对称通道离散：检查映射或 symmetry 是否异常。

建议首轮门槛：

```text
所有 SP_p < -15 dB
所有谐振偏移 < 0.5 MHz
对称组匹配离散 < 3 dB
最差非对角 SP_s < -12 dB
```

核心检查：

```matlab
SPsDB = 20*log10(abs(netp.SP_s));
SPpDB = 20*log10(abs(netp.SP_p(:)));
F = netp.figure_freq;
targetMHz = F.freq_range(F.freq_idx)/1e6;
nPorts = numel(SPpDB);
resonanceMHz = NaN(nPorts,1);

for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    [minimumDB,k] = min(curve);
    resonanceMHz(p) = F.freq_range(k)/1e6;
    fprintf('%2d: target=%7.2f dB, min=%7.2f dB at %.4f MHz\n', ...
        p,SPpDB(p),minimumDB,resonanceMHz(p));
end

couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;
worstCouplingDB = max(couplingDB,[],'all');

assert(all(SPpDB < -15),'Rx matching failed');
assert(max(abs(resonanceMHz-targetMHz)) < 0.5,'Rx detuning failed');
assert(worstCouplingDB < -12,'Rx coupling failed');
```

`Simulation completed successfully` 只代表程序完成，不代表电路合格。

## 11. Stage C：冻结电路并计算最终性能

TMD-only 改变电路后，旧结果中的 B1-、电场、噪声协方差和 SNR 仍对应旧校准，不能直接复用。

接受最终元件值后：

1. 冻结当前线圈 JSON。
2. 使用 `TMD=0`，禁止再次运行 PSO。
3. 从保存的 pre-TMD `MREDM` 检查点计算最终场；或执行一次常规 `TMD=0` 完整复算。

16 通道案例提供：

```matlab
FINALIZE_5T_16CH_FROM_CHECKPOINT;
```

只有最终固定电路结果才用于 B1-、噪声协方差、SNR 和 SNR/UISNR 报告。

## 12. 去耦能力边界

`cross_talk` 和 `mutual_inductor` 用于明确存在的互感去耦电路，例如：

```json
"load": "mutual_inductor",
"cross_talk": {
  "coupled_port": 50,
  "coupled_value": -2.29e-8
}
```

`coupled_port` 指向配对元件，互感符号取决于参考方向。元件必须成对并与几何集总点一致。

如果模型没有实际去耦电路，TMD 不能把任意 `SP_s` 互耦自动消除。匹配通过但耦合失败时，应扫描 Loop 重叠、排距、错位角或建立真实去耦拓扑。

## 13. 优化器与边界建议

当前 `co_simulation_optimization_settings.m` 使用 `particleswarm`，项目版本的主要设置包括：

```text
SwarmSize = 300
MaxIterations = 500 / 400
UseParallel = false
MaxStallIterations = 50
```

调整优先级：

1. 先修复几何、映射、symmetry、种子和边界。
2. 减少不必要的独立变量。
3. 只有问题定义正确但仍未收敛时，才增加粒子或迭代数。

谐振整体偏高通常提示等效调谐电容不足，偏低通常相反；强耦合和匹配网络会改变简单 LC 直觉，最终以频扫和边界饱和情况为准。

## 14. 常见问题

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 多端口离群或奇偶交替 | symmetry、点顺序、端口位置或 entity 错误 | 复现内部编号并检查 B1- 通道规律 |
| 最优值压在边界 | 范围不足或拓扑不可实现 | 只扩大有证据的变量，必要时改拓扑 |
| `SP_s` 对角差但 `SP_p` 好 | 加载定义不同 | 纯 Rx 匹配以 `SP_p` 为主 |
| `SP_p` 好但 `Sij` 差 | 几何互耦或去耦不足 | 返回几何外层循环 |
| 使用最终 `YP_s` 重跑后异常 | 把 `YPm` 错当 `YPn` | 重新加载 Stage A 原始网络 |
| 改了几何仍沿用旧 `YPn` | 缓存失效 | 新 case 重新执行 Stage A |
| TMD 后旧 SNR 未变化 | 使用了旧场结果 | 用最终电路执行 Stage C |
| 多任务结果互相覆盖 | 并发写同一 JSON | case 隔离并保留时间戳备份 |

## 15. 结果与版本管理

每轮至少保存：

- 几何版本和原始 `YPn` 文件；
- TMD 前 JSON 备份；
- 种子、边界和 symmetry；
- TMD MAT 结果及 `SP_p/SP_s` 门槛；
- TMD 后最终 JSON；
- 是否进入固定电路 Stage C。

只有 MAT 而没有对应 JSON，无法可靠恢复实际电路。只有最后一个被覆盖的 JSON 而没有每轮记录，也无法比较优化策略。

## 16. 核心原则

1. 三维电磁网络是外层固定问题，TMD 是可反复运行的内层电路问题。
2. 独立 TMD 必须使用原始 `YPn`，不能使用最终 `YPm`。
3. `optim.symmetry` 必须根据实际源码计数验证。
4. TMD 会写回 JSON，每轮必须备份并禁止并发写入。
5. 匹配看 `SP_p`，互耦看 `SP_s` 非对角元素。
6. TMD 通过后才冻结电路，以 `TMD=0` 生成最终场和 SNR。
7. 改变几何或原始端口拓扑后，旧 `YPn` 立即失效。

