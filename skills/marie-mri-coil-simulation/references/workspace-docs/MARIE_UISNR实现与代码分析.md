# MARIE Tools：UISNR 实现与代码分析

## 1. 开源许可判断

### 1.1 MARIE 主体代码

仓库根目录 [LICENSE](https://github.com/cloudmrhub/marie-tools/blob/main/LICENSE) 是 MIT License，版权人为 Ilias I. Giannakopoulos，年份为 2025。MIT 许可证允许：

- 使用、复制和修改代码；
- 合并到自己的软件；
- 发布、再许可和销售；
- 用于学术或商业项目。

约束是：复制或发布该软件的全部或实质性部分时，必须保留原版权声明和 MIT 许可文本。软件按“原样”提供，作者不承担适用性或损失责任。

因此，MARIE 自身的 UISNR MATLAB 实现原则上可以用于本项目，也可以翻译成 Python。但若直接复制、改写或形成实质性派生代码，应在源码、第三方声明或发行包中保留 MARIE 的版权与 MIT 许可证，并清楚标注修改内容。

### 1.2 仓库并非所有内容都采用同一个许可证

“仓库根目录是 MIT”不等于每个捆绑组件都变成 MIT。当前检出版本至少包含以下独立许可：

| 组件 | 许可 | 对本项目的影响 |
|---|---|---|
| MARIE 主体 | MIT | 可自由修改和商业使用，保留版权与许可声明 |
| TT/QTT 数学库 | MIT 类宽松许可 | 可复用，保留其作者与许可声明 |
| NIfTI MATLAB 工具 | BSD 类许可 | 可复用，源/二进制发布需保留相应声明 |
| Gmsh 可执行程序 | GPL v2 or later + exception | 若随软件重新分发，需单独遵守 GPL；仅调用用户自行安装的 Gmsh 边界更清晰 |
| Dunavant 积分代码 | 文件头声明 GNU LGPL | 复制或发布时需遵守 LGPL 条款 |
| MATLAB/工具箱 | 商业软件依赖，不属于开源代码 | 不能把 MATLAB 自身或受限组件当作 MARIE 许可证的一部分 |

人体模型、网格和预计算数据是否可再分发，还应检查其来源和单独授权。仓库内能读取到数据，不自动意味着这些数据可在商业产品中不加审查地重新发布。

> 本节是工程许可分析，不构成法律意见。最稳妥的产品方案是用论文公式和 MARIE 的数据流作参考，独立实现 Python 核心，并仅复制确有必要、许可明确的代码。

## 2. UISNR 在项目中的位置

MARIE 的 UISNR 不是对某个现成线圈求 SNR。它先构造一个尽可能完备的候选电流/激励空间，求出这些模式在有损人体中的总电磁场与相关噪声，再对任意目标体素寻找最优线性组合。

完整入口在 `src/src_runners/BASIS_runner.m`：

```text
load_inputs
  -> geo_assembly
  -> vie_assembly
  -> IncidentField_Basis
  -> ie_solver_vie_basis
  -> em_ehfield_vie
  -> 保存 BASIS
```

对应的数学链路为：

```text
候选源系数 a
  -> 入射电场基 Ue_inc、磁场基 Ub_inc
  -> VIE 求人体极化电流 Jb
  -> 散射场叠加，得到总场 Ue、Ub
  -> 由人体耗散得到样品噪声协方差 Phi
  -> B1- 灵敏度向量 s(r)
  -> s(r)^H Phi^-1 s(r)
  -> UISNR、最优权重和理想电流模式
```

## 3. 关键文件索引

| 层次 | 文件 | 作用 |
|---|---|---|
| 工作流 | `src/src_runners/BASIS_runner.m` | 串联几何、VIE、场基、UISNR 与保存 |
| 源空间选择 | `src/src_integral_equations/src_basis/IncidentField_Basis.m` | 在表面 RWG 基和偶极子壳层基之间路由 |
| 表面场基 | `src/src_integral_equations/src_basis/sSVD_rwgBasis.m` | 从指定支撑面的 RWG 电流生成并压缩 E/H 场基 |
| 终极场基 | `src/src_integral_equations/src_basis/rSVD_dipoleBasis.m` | 从包围人体的体素偶极子源生成随机 SVD 场基 |
| 理想源壳层 | `src/src_geometry/basis_geometry/geo_dipole_supports/geo_ultimate_basis.m` | 按距离和厚度生成包围人体的源支撑域 |
| 人体响应 | `src/src_solver/src_ie_solver/ie_solver_vie/ie_solver_vie_basis.m` | 对每个入射模式用 GMRES 求人体极化电流 |
| UISNR 核心 | `src/src_physics/src_electromagnetism/em_ehfield_vie.m` | 总场、噪声协方差、UISNR、收敛曲线与权重 |
| 真实阵列 SNR | `src/src_physics/src_performance_metrics/em_SNR.m` | 以同一二次型计算有限阵列 SNR |
| 物理常数 | `src/src_physics/em_constants.m` | 核种、频率、温度、M0 和缩放常数 |
| 电流回投 | `src/src_visualizer/visualize_ideal_current_patterns.m` | 将最优权重还原为表面理想电流并绘图 |

## 4. 第一步：定义“终极”候选源空间

### 4.1 两种基空间

`src/src_integral_equations/src_basis/IncidentField_Basis.m` 只有一个简单分派：

```matlab
if geo_flag == 2
    BASIS = sSVD_rwgBasis(MREDM);
elseif geo_flag == 3
    BASIS = rSVD_dipoleBasis(MREDM);
end
```

- `geo_flag = 2`：表面支撑的 RWG 电流模式。性能上限受指定线圈筒/曲面约束，适合研究“给定几何外壳上能够达到的最优性能”。
- `geo_flag = 3`：包围人体的偶极子源壳层。源自由度更大，目标是逼近 ultimate intrinsic SNR。

这两个上限应在软件中明确区分。表面约束结果可以称为 `support-constrained optimal SNR`，偶极子壳层在完备性和收敛性得到验证后才称为 UISNR。

### 4.2 偶极子支撑域

`src/src_geometry/basis_geometry/geo_dipole_supports/geo_ultimate_basis.m` 的实现步骤是：

1. 读取人体体素掩膜。
2. 对每个横截面做 `bwconvhull`，得到较平滑的包络。
3. 用形态学膨胀产生离人体一定距离的外层体素。
4. 以两个不同半径膨胀结果相减，得到有限厚度壳层。
5. 壳层体素作为候选偶极子源位置，人体体素作为场求解位置。

当前硬编码默认值位于 `src/src_utils/src_loaders/load_inputs.m`：

```matlab
inputs.Basis_distance  = 0.02;  % 2 cm offset
inputs.Basis_thickness = 3;     % 3 voxel layers
inputs.rSVD_blocksize  = 1000;
```

因此 MARIE 所计算的“终极”结果仍依赖源壳层距离、厚度、体素分辨率、基函数阶次和 SVD 截断。它是数值近似的上限，需要用这些参数的收敛性来证明。

## 5. 第二步：生成并压缩入射场基

### 5.1 表面 RWG 路径

`src/src_integral_equations/src_basis/sSVD_rwgBasis.m` 从支撑面的 RWG 基函数出发，装配表面到人体体素的耦合矩阵：

- `K` 型耦合产生磁场基 `Hinc`；
- `N` 型耦合产生电场基；
- 积分矩阵乘以 `res^3`，体现体素测试/积分的离散缩放；
- 对磁场耦合矩阵做经济型 SVD；
- 按阈值压缩奇异值；
- 用 DEIM 选代表性采样位置；
- 将电场基变换到与压缩磁场基一致的模式坐标。

核心数据关系是：

```text
原始 RWG 电流系数 j
Hinc = K_surface_to_body j
Hinc ≈ Ub SK VK^H
```

代码保存：

- `Ub`：压缩磁场基；
- `Ue`：与其对齐的电场基；
- `SK`、`VK`：奇异值和原始 RWG 电流方向；
- `P`：DEIM 选择矩阵；
- `X`：用于 MRGF 降阶映射的矩阵。

### 5.2 偶极子随机 SVD 路径

`src/src_integral_equations/src_basis/rSVD_dipoleBasis.m` 不显式构造完整的大型源到场矩阵，而是通过算子矩阵向量乘形成随机 SVD：

1. `rSVD_Q` 估计磁场耦合算子的列空间。
2. `rSVD_Q_adjoint` 估计伴随算子的列空间。
3. 在两个低维子空间之间形成小矩阵 `T`。
4. 对 `T` 做 SVD，恢复主要磁场模式 `Ub`。
5. 根据奇异值相对阈值截断模式。
6. 由对应源方向通过 `N` 算子生成电场基 `Ue`。
7. 用 DEIM 和 `X` 构造后续 MRGF 所需映射。

这使软件不必存储“所有候选偶极子 × 所有人体体素”的稠密矩阵，是现实人体 UISNR 能够计算的关键之一。

### 5.3 当前截断设置

`src/src_utils/src_loaders/load_inputs.m` 以 GMRES 容差 `1e-5` 派生：

```matlab
tol_rSVD = 1e-3;
tol_sSVD = 1e-3;
tol_DEIM = 1e-4;
```

这些值目前没有暴露到 JSON。移植时应改为显式配置，并保存每次计算的奇异值谱、保留秩和误差估计。

## 6. 第三步：求每个模式在人体中的散射响应

`src/src_solver/src_ie_solver/ie_solver_vie/ie_solver_vie_basis.m` 将每个压缩场模式视为一个“虚拟端口”。设模式数为 `N_ports`，对每个模式执行：

```matlab
rhs = ce * material_contrast .* BASIS.Ue(:,i);
Jb(:,i) = GMRES(VIE_operator, rhs);
```

这里：

- `Ue(:,i)` 是第 `i` 个候选源在人体中的入射电场；
- `material_contrast` 由复介电参数构造；
- `Jb(:,i)` 是有损人体中感生的等效极化电流；
- VIE 算子通过 FFT/压缩卷积完成矩阵向量乘；
- 每个模式单独调用 GMRES，可以并行化或分批计算。

代码还构造：

```matlab
Zbb_hat_inv = X.' * ((Ue.' * Jb) * X);
[U_hat_inv,S_hat_inv,V_hat_inv] = svd(Zbb_hat_inv,'econ');
```

这部分主要服务于 MRGF 的快速在线求解，不是计算一次 UISNR 的必需输出。但它很适合作为未来 CST 前置优化中的“人体响应缓存”。

## 7. 第四步：形成总场与样品噪声协方差

### 7.1 总场

`src/src_physics/src_electromagnetism/em_ehfield_vie.m` 对每个模式从 `Jb` 计算散射 E/H 场，然后叠加入射场：

```matlab
BASIS.Ue(:,port) = BASIS.Ue(:,port) + E_scattered;
BASIS.Ub(:,port) = BASIS.Ub(:,port) + H_scattered;
```

叠加之后，`Ue`、`Ub` 表示人体存在时的总场基。UISNR 必须使用总接收磁场，而噪声由人体内电场耗散或等价极化电流二次型决定。

### 7.2 样品噪声 Gram 矩阵

代码第 42-52 行构造：

```matlab
Mpow = repmat(Mc_inv(idxS),[ql 1]) / ce;
Gx(:,port) = G(Jb_port);
phi = Jb' * (real(Mpow) .* Gx);
BASIS.phi = conj(phi);
```

从结构上看，`phi` 是所有模式在人体耗散内积下的 Gram 矩阵：

```math
\Phi_{mn} \sim \int_V \sigma(\mathbf r)
E_m(\mathbf r)^* \cdot E_n(\mathbf r)\,dV
```

其非对角元描述不同接收模式的相关样品噪声。UISNR 不能用每个模式的独立噪声标量代替这个完整矩阵。

移植验证时应检查：

- `Phi ≈ Phi^H`；
- 所有特征值非负，允许数值误差范围内的小负值；
- 对角元与直接积分 `∫sigma|E|^2 dV` 一致；
- 任意基变换 `A` 下，`Phi_new = A^H Phi A`，最终 UISNR 不变；
- 体素尺寸变化时积分收敛。

## 8. 第五步：计算 UISNR、权重和模式收敛

### 8.1 接收灵敏度

对于第 `j` 个散射体体素，代码形成：

```matlab
b1m = mu0 * (Ub_x - 1i*Ub_y);
s = transpose(b1m);
```

即 `s` 是该体素对全部候选模式的复接收灵敏度向量。

注意：这里没有显式的 `1/2`。很多 MRI 文献定义：

```math
B_1^- = (B_x^* - iB_y^*)/2
```

不同相量与互易性约定也会改变是否取共轭。MARIE 的绝对 UISNR 与其他软件对比前，必须先核对其 `Ub` 的含义、圆极化因子和共轭约定。

### 8.2 最优 SNR

代码实际计算：

```matlab
SphiS  = s' * inv(Phi) * s;
snr_map = sqrt(SphiS);
UISNR = scaling * snr_map;
```

等价数学式为：

```math
UISNR(\mathbf r)
= C\sqrt{s(\mathbf r)^H\Phi^{-1}s(\mathbf r)}
```

其中 MARIE 使用：

```math
C = \frac{\Delta V\,\omega M_0}{\sqrt{4k_BT_0}}
```

代码中的 `Delta V = res^3`，`T0 = 310 K`。`M0` 由 `src/src_physics/em_constants.m` 根据核密度、旋磁比、自旋、B0 和温度计算，而不是简单取 1。

### 8.3 最优接收权重

代码保存的权重为：

```matlab
wUISNR = transpose((s' Phi^-1 s)^-1 * s' Phi^-1);
```

其方向本质上等价于噪声白化匹配滤波：

```math
w_{opt} \propto \Phi^{-1}s
```

前面的标量归一化不改变 SNR，只改变组合输出的幅度。对线圈设计而言，`wUISNR` 比单张 UISNR 图更有价值，因为它可以映射回候选电流基，显示达到该目标点最优接收所需的电流幅相组合。

### 8.4 模式收敛曲线

代码从 `1...N_ports` 取约 50 个对数分布的模式数量 `nmodes`，重复计算：

```text
cUISNR(r, k) = 使用前 k 个奇异模式时的 UISNR
```

这可以回答：

- 当前场基是否足以逼近上限；
- 目标 ROI 达到 90%/95% UISNR 需要多少有效模式；
- 某些深部区域是否比表层需要更多独立模式；
- 实际阵列通道数是否已经进入收益递减区间。

## 9. 第六步：将最优场组合还原成理想电流

`src/src_visualizer/visualize_ideal_current_patterns.m` 只支持表面支撑基。它先找到达到最终 UISNR 95% 的最小模式数，再执行：

```matlab
Jc = VK(:,1:k) / SK(1:k,1:k) * wUISNR(1:k,target_voxel);
```

这一步将压缩场模式权重映射回原始 RWG 电流系数。随后在每个三角形中心计算笛卡尔电流向量，并分别绘制 `omega*t = 0` 与 `pi/2` 两个相位。

它能够给出电流方向、热点和相位旋转，但还不是可直接制造的线圈拓扑。要从理想电流走向设计，需要追加：

- 流函数或等值线离散；
- 闭合导体路径约束；
- 最小线宽/间距；
- 通道分割与馈电位置；
- 互耦、匹配、导体和元件损耗；
- CST 全波验证。

## 10. 与有限阵列 SNR 的比较

`src/src_physics/src_performance_metrics/em_SNR.m` 对实际线圈阵列使用相同的最优合并二次型，但噪声矩阵为：

```matlab
Phi_total = phi_sample + phi_coil + phi_lump;
```

还可以加入联合仿真网络中的集总元件噪声。于是可构造：

```math
\eta(\mathbf r)=\frac{SNR_{array}(\mathbf r)}{UISNR(\mathbf r)}
```

为了让比值有意义，两边必须使用相同的：

- 人体模型、分辨率和材料；
- B0、核种、频率、温度和 M0；
- `B1-`、相量和互易性约定；
- 体素积分与噪声谱定义；
- ROI 掩膜和空间插值方法。

## 11. 原实现需要改进的地方

### 11.1 不应显式求逆

代码多次使用 `inv(Phi)`。对近线性相关模式，`Phi` 很容易病态。Python 实现应优先采用：

```text
Hermitian 化 Phi
  -> 特征值/Cholesky 分解
  -> 截断不可辨识噪声模态
  -> solve(Phi, s)
  -> real(s^H solve(Phi,s))
```

同时输出条件数、有效秩、最小特征值和正则化阈值。

### 11.2 模式顺序与“前 k 个模式”假设

`cUISNR` 直接取 `Phi(1:k,1:k)` 和前 `k` 列 `Ub`。这依赖基模式已经按磁场耦合奇异值排序。该顺序不一定等于对特定 ROI 最有效的 SNR 顺序。建议额外实现：

- 原始奇异值顺序收敛；
- 噪声白化后的主接收模式排序；
- 针对 ROI 的贪心/特征模态排序。

### 11.3 异常捕获过宽

`ie_solver_vie_basis` 的整个 GPU 分支使用无条件 `catch`，任何错误都可能被解释为 GPU 内存不足。重构时应只捕获明确的资源异常，其他错误保留完整堆栈。

### 11.4 绝对标度约定没有集中管理

`res^3`、`M0`、`T0`、`B1-` 和噪声因子分散在多个函数。建议把它们放入版本化 `PhysicsConvention`，并随结果保存。

### 11.5 缺少开箱即用的 UISNR 示例

当前 `BASIS_runner` 硬编码的输入文件未随 `data/inputs` 提供，`data/bases` 也基本为空。因此应把 MARIE 当作参考实现，不能在未补齐输入、修复路径并编译 MEX 前假设结果可直接复现。

## 12. Python 软件的推荐实现边界

### 12.1 最小可复用 UISNR 内核

如果电磁场已经由 MARIE、CST 或其他求解器给出，Python 第一版只需实现：

```python
class UISNRInput:
    b1_minus: complex_array        # [n_voxels, n_modes]
    noise_covariance: complex_array # [n_modes, n_modes]
    voxel_mask: bool_array
    scale: float
    conventions: PhysicsConvention

class UISNRResult:
    uisnr: float_array
    optimal_weights: complex_array
    condition_number: float
    effective_rank: int
    diagnostics: dict
```

数值核心建议写成：

```python
phi_h = 0.5 * (phi + phi.conj().T)
eigval, eigvec = np.linalg.eigh(phi_h)
keep = eigval > rcond * eigval.max()
whitener = eigvec[:, keep] / np.sqrt(eigval[keep])
z = b1_minus @ whitener
uisnr_kernel = np.linalg.norm(z, axis=1)
uisnr = scale * uisnr_kernel
```

这种白化写法避免显式求逆，并自然处理有效秩。权重可通过截断伪逆或线性求解恢复。

### 12.2 三层开发路线

**层 A：后处理器**

输入 `B1-` 和 `Phi`，输出 UISNR、权重、收敛和诊断。先用合成正定矩阵、基变换不变性和 MARIE 导出数据测试。

**层 B：样品噪声构造器**

输入每个模式的复电场、组织电导率和体素体积，计算：

```math
\Phi_{mn}=\sum_v \sigma_v E_m(v)^*\cdot E_n(v)\Delta V
```

该层可以直接接收 CST 多端口场，不必先复刻 MARIE 的 VIE。

**层 C：终极场基求解器**

实现偶极子/表面电流源、人体全波响应、rSVD/DEIM 和模式收敛。这是最困难、耗时最长的一层，适合在 A、B 两层验证稳定后逐步开发。

### 12.3 最适合当前项目的借用方式

短期不建议把 800 多个 MATLAB 文件整体嵌入软件。建议：

1. 将 MARIE 作为 UISNR 参考后端和交叉验证器。
2. 用 MATLAB 将 `Ub`、`Ue`、`phi`、`UISNR`、`wUISNR`、`nmodes` 导出为 HDF5。
3. Python 独立复算 UISNR，先达到数值一致。
4. 接入 CST 的多端口 E/H 场，计算有限阵列 SNR。
5. 在同一约定下生成 `SNR_array/UISNR` 图。
6. 最后再决定是否用 Python 重写偶极子基和 VIE 求解器。

## 13. 必做验证清单

- `Phi` 的 Hermitian 相对误差；
- `Phi` 的特征值谱、条件数和有效秩；
- 任意可逆模式变换下 UISNR 不变；
- 模式增加时 `cUISNR` 理论上不下降；
- 均匀球结果与解析/文献基准一致；
- 表面位置、中心位置和不同场强下的收敛；
- 体素分辨率、源壳距离、壳厚和 SVD 阈值收敛；
- MATLAB 与 Python 对相同 `B1-`、`Phi` 的逐体素一致性；
- CST 与 MARIE 的端口功率、场相位和 `B1-` 归一化一致性；
- 有限阵列样品噪声 SNR 不应系统性超过同约定 UISNR。

## 14. 结论

MARIE 的 UISNR 实现主体采用 MIT 许可证，可以作为本软件的重要参考。其核心不是第 65-91 行的矩阵公式，而是如何构造足够完备又可计算的源场子空间：用表面 RWG 或偶极子壳层定义候选源，用 SVD/rSVD 压缩场空间，用 VIE 求每个模式的人体散射和耗散，再以完整噪声协方差进行最优合并。

对当前软件最合适的策略是先独立实现稳定的 Python `B1- + Phi -> UISNR` 内核和 CST 场后处理器，将 MARIE 用作数据生成与验证参考；等归一化、噪声和有限阵列比较全部验证后，再开发 Python 版理想场基和人体降阶求解。这条路线能较快产生可用结果，也保留了未来逼近完整 UISNR 求解器的技术路径。
