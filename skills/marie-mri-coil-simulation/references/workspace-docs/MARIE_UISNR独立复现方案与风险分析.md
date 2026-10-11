# MARIE UISNR 模块独立复现方案与风险分析

## 1. 决策摘要

单独复现 MARIE 的 UISNR 功能是可行的，但需要先明确“复现到哪一层”。UISNR 后处理公式只有很少代码，完整 UISNR 求解器却依赖源空间、人体全波响应、场基压缩和噪声建模，无法从 MARIE 中剪下一个函数就独立运行。

建议采用三级边界：

| 级别 | 复现内容 | 可行性 | 预计风险 | 建议 |
|---|---|---|---|---|
| L1 | 已有 `B1-` 和噪声矩阵 `Phi`，计算 UISNR、权重和诊断 | 很高 | 低 | 立即采用，现有 Python 项目已有可靠基础 |
| L2 | 从每个模式的 E/H 场和材料构造 `Phi`、`B1-`，再算 UISNR | 高 | 中 | 下一阶段重点，直接服务 CST |
| L3 | 自行生成理想源基、求人体全波响应并逼近 UISNR | 中等 | 很高 | 长期目标，待 L1/L2 验证后开发 |

推荐路线不是逐行翻译 MATLAB，而是：

1. 保留当前 Python 项目的稳定线性代数内核。
2. 从 MARIE 借鉴数据流、模式构造和收敛方法。
3. 建立 MARIE HDF5/MAT 导出适配器，用相同场数据交叉验证。
4. 优先接通 CST 场后处理，形成有限阵列 SNR/UISNR 比较闭环。
5. 最后独立实现理想偶极子或表面电流基求解器。

## 2. 为什么不能只复制 `em_ehfield_vie.m`

MARIE 的 UISNR 核心位于 `src/src_physics/src_electromagnetism/em_ehfield_vie.m`，但它假设输入 `BASIS` 已包含：

- `Ue`：所有压缩模式的入射电场；
- `Ub`：所有压缩模式的入射磁场；
- `Jb`：每个模式在人体内激发的极化电流；
- `X` 等降阶映射；
- 与人体体素、VIE 基函数阶次完全一致的索引布局。

这些数据来自：

```text
geo_assembly
  -> vie_assembly
  -> IncidentField_Basis
  -> sSVD_rwgBasis / rSVD_dipoleBasis
  -> ie_solver_vie_basis
  -> em_ehfield_vie
```

如果只复制最后一个函数，将没有物理正确的 `Ue`、`Ub`、`Jb` 和 `Phi`。因此真正可独立抽取的是“模态后处理接口”，而不是 MARIE 的完整实现文件。

## 3. 与当前 UISNR-5T 项目的关系

当前项目 `C:\path\to\UISNR-5T-project` 已经实现：

- 均匀有损球的解析矢量球面波模式；
- 样品噪声下的最优模式组合；
- Lee 球心独立基准；
- `optimal_snr_squared()` 的稳定特征值白化；
- 固定的 5 T 回归结果和自动测试。

现有 `C:/path/to/UISNR-5T-project/src/uisnr5t/core.py` 中的算法比 MARIE 直接 `inv(Phi)` 更适合作为产品内核：

```text
Hermitian 化
  -> 按通道噪声对角元做尺度归一化
  -> eigh
  -> 截断数值零特征值
  -> 在白化空间计算二次型
```

需要借鉴 MARIE 的不是这一小段线性代数，而是：

- 一般人体与任意模式下如何形成完整噪声协方差；
- 如何生成表面约束模式或终极偶极子模式；
- 如何保存模式数量的 UISNR 收敛；
- 如何将最优权重映射回理想表面电流；
- 如何将同一框架用于有限阵列 SNR。

## 4. 推荐的独立模块边界

### 4.1 领域数据结构

建议新增逻辑模块，但在 Harness 批准前不应实际改动 UISNR-5T 代码：

```text
src/uisnr5t/
├── core.py                 # 已有：稳定二次型和基础领域模型
├── conventions.py          # 物理、相量、噪声和归一化约定
├── modal_fields.py         # 通用模态场数据结构
├── sample_noise.py         # E场 + sigma -> Phi
├── modal_uisnr.py          # B1- + Phi -> UISNR/权重/收敛
├── ideal_currents.py       # 权重 -> 原始源电流系数
└── adapters/
    ├── marie.py            # MARIE MAT/HDF5 导入和约定转换
    └── cst.py              # CST 场和端口归一化导入
```

最小数据契约：

```python
@dataclass(frozen=True)
class ModalFieldSet:
    electric_field: np.ndarray       # [n_voxels, 3, n_modes], complex V/m
    magnetic_flux: np.ndarray        # [n_voxels, 3, n_modes], complex T
    conductivity: np.ndarray         # [n_voxels], S/m
    voxel_volume: np.ndarray         # scalar or [n_voxels], m^3
    coordinates: np.ndarray          # [n_voxels, 3], m
    mode_ids: tuple[str, ...]
    normalization: "ModeNormalization"
    convention: "PhysicsConvention"

@dataclass(frozen=True)
class ModalUISNRResult:
    uisnr_em_factor: np.ndarray      # [n_voxels]
    optimal_weights: np.ndarray      # [n_voxels, n_modes]
    convergence: np.ndarray          # [n_voxels, n_mode_steps]
    effective_rank: int
    eigenvalues: np.ndarray
    diagnostics: dict
    convention: "PhysicsConvention"
```

大型人体模型不能要求一次将全部 `E[n_voxels,3,n_modes]` 装入内存，因此接口还应支持块读取器：

```python
for voxel_block in field_source.iter_blocks():
    accumulate_noise_covariance(voxel_block)
```

## 5. L1：复现模态 UISNR 后处理器

### 5.1 输入与输出

输入：

- `b1_minus[n_voxels, n_modes]`；
- `phi[n_modes, n_modes]`；
- 物理缩放与约定；
- 可选模式顺序和模式数扫描点。

输出：

- 每个体素的 UISNR；
- 最优组合权重；
- `cUISNR` 模式收敛曲线；
- 特征值谱、有效秩、条件数和警告；
- 可复现元数据。

### 5.2 数值实现

不复制 MARIE 的 `inv(Phi)`。延续当前项目的白化策略：

```math
\Phi_h=\frac{\Phi+\Phi^H}{2}
```

先做通道噪声尺度归一化，再对相关矩阵分解：

```math
C=D^{-1/2}\Phi_hD^{-1/2}=Q\Lambda Q^H
```

保留 `lambda_i > rcond * lambda_max` 的模式。对灵敏度 `s`：

```math
q=s^H\Phi^+s
```

```math
UISNR=C_{physics}\sqrt{\max(\operatorname{Re}q,0)}
```

最优权重使用同一个截断伪逆：

```math
w=\Phi^+s
```

权重必须明确其归一化方式，例如：

- `w^H Phi w = 1`：单位噪声；
- `w^H s = 1`：单位信号；
- 仅保存未归一化方向。

推荐默认单位噪声归一化，另存归一化枚举。

### 5.3 与 MARIE 的第一轮对照

从 MARIE 导出：

```text
BASIS.Ub
BASIS.phi
BASIS.UISNR
BASIS.wUISNR
BASIS.cUISNR
BASIS.nmodes
人体 idxS、res、B0、T0、M0
```

第一轮只比较无物理缩放的核：

```math
u(\mathbf r)=\sqrt{s^H\Phi^+s}
```

确认二次型一致后，再处理 `B1-`、`res^3`、温度和 M0。这样可以把数值错误与物理缩放错误分离。

## 6. L2：复现样品噪声构造器

### 6.1 通用形式

对每个模式的复电场，样品噪声 Gram 矩阵可写为：

```math
\Phi_{mn}=\alpha_{loss}
\sum_v \sigma_v
\mathbf E_m(\mathbf r_v)^*\cdot
\mathbf E_n(\mathbf r_v)\Delta V_v
```

`alpha_loss` 由时间平均、单/双边噪声谱和场相量定义决定。当前 UISNR-5T Harness 使用时间平均 Joule 损耗并包含 `1/2`；MARIE 的等价极化电流表达不能在没有推导时假定同一个系数。

### 6.2 块式实现

如果 `E_block` 形状为 `[n_block, 3, n_modes]`，可以将其重排为 `[3*n_block, n_modes]`，并执行：

```python
weighted_e = e_flat * np.sqrt(loss_weight_flat[:, None])
phi += weighted_e.conj().T @ weighted_e
```

优点：

- 自动得到 Hermitian 半正定矩阵；
- 可分块，内存与总人体体素数解耦；
- 可使用 NumPy、CuPy 或 BLAS；
- 适用于 MARIE、CST 或其他求解器的场。

### 6.3 CST 接口需要额外处理

CST 导出场必须附带：

- 每个端口的激励定义：1 W accepted power、1 W incident power、1 V 或 1 A；
- 端口相位参考和平面；
- 是否包含匹配网络；
- 复数场的相量约定；
- 插值后的体素坐标与体积；
- 各组织的复介电参数；
- 被动端口的终端条件。

所有通道可各自任意缩放，只要 `B1-` 和 `Phi` 做一致的合同变换，理论二次型不变。但若场和噪声来自不同归一化，结果会完全错误且可能表面上仍然平滑。

## 7. L3：复现理想源空间和人体响应

### 7.1 表面约束路径优先

完整复现时建议先做表面约束基，不先做通用偶极子壳层：

1. 读取三角形支撑面。
2. 构造 RWG 基函数拓扑。
3. 获得每个 RWG 模式对人体的 E/H 场。
4. 对场映射做 SVD 压缩。
5. 计算压缩模式的 `Phi` 和最优权重。
6. 将权重映射回 RWG 系数并画理想电流。

在早期，可以让 CST 或 MARIE 负责第 3 步；Python 负责 4-6 步。这已经能提供“指定线圈筒上的最优可用电流模式”，并且比绝对 UISNR 更接近工程设计。

### 7.2 偶极子壳层路径

后续再实现：

- 人体外部源壳层生成；
- 三方向偶极子源；
- 源到人体场算子；
- 随机 SVD 与伴随算子；
- DEIM 或其他插值选点；
- VIE 人体散射求解；
- 源距离、厚度、分辨率和截断秩收敛。

此时才接近 MARIE 的完整 UISNR 求解器。若没有独立的全波算子，实现 rSVD 本身并不能产生正确 UISNR。

## 8. MARIE 与当前项目的约定冲突

这是最大的科学风险。

| 项目 | 当前 UISNR-5T | MARIE 代码表现 |
|---|---|---|
| 相量 | `exp(-i*omega*t)` | 需从全部算子符号进一步确认 |
| 复介电常数 | `eps + i*sigma/omega` | 由 `ce=i*omega*eps0` 和材料变量间接表达 |
| 接收场 | `conj(Bx-iBy)/2` | `mu0*(Hx-iHy)`，无显式 `1/2` 和共轭 |
| 场量 | `B` | `Ub` 看似为 `H`，乘 `mu0` 后得到 `B` |
| 样品损耗 | 时间平均，含 `1/2` | 等效极化电流二次型，需推导整体系数 |
| 温度 | 案例可配置，常用 300 K | 固定 310 K |
| 磁化强度 | 单位 `M0` | 由纯水核密度与 B0 计算物理 `M0` |
| 体素缩放 | 解析球中无离散 `res^3` | 最终缩放显式包含 `res^3` |

未经约定映射，绝对结果可能差 2、`sqrt(2)`、`mu0`、`res^3` 或 `M0` 等巨大因子。空间分布看起来正确并不能证明绝对 SNR 正确。

必须建立两种明确模式：

- `canonical`：使用 UISNR-5T Harness 冻结约定；
- `marie_compatibility`：严格重现 MARIE 输出，仅用于对照。

适配器把 MARIE 数据转换为 canonical。核心算法内部不能到处使用兼容性条件分支。

## 9. 潜在危险清单

### 9.1 科学定义风险

**把受限最优值误称为 UISNR。**

表面 RWG 支撑域不完备时，只是该支撑面的最优值；偶极子壳层也必须证明对源距离、厚度、体素和模式数量收敛。

**将场归一化错误隐藏在比值中。**

若 `B1-` 和 `Phi` 不按同一模式系数缩放，二次型失去不变性。有限阵列 SNR 与 UISNR 使用不同约定时，可能出现 `SNR/UISNR > 1`。

**噪声因子与带宽混淆。**

功率耗散、噪声电压谱、单边/双边 PSD、单位带宽 SNR 和图像 SNR 不是同一量。

**用样品噪声上限代表真实线圈。**

UISNR 排除了导体、匹配元件、前放和电缆损耗；实际阵列比较必须单独加入这些项。

### 9.2 数值风险

**噪声矩阵病态。**

高阶模式会产生极小噪声特征值。直接求逆可能产生虚假超高 SNR。截断阈值必须对任意通道缩放保持稳定，并报告有效秩。

**随机 SVD 不可重复。**

必须固定随机种子、记录块大小和误差，并用重复随机试验确认 UISNR 稳定。

**模式数收敛不等于网格收敛。**

还需独立检查体素分辨率、积分阶数、源壳参数和 VIE 迭代容差。

**内存爆炸。**

复数 `E[n_voxel,3,n_mode]` 很快达到数十至数百 GB。必须块式累计 `Phi`，场图只按需要保存。

**复数转置错误。**

MATLAB 的 `'` 是共轭转置，`.'` 才是普通转置。Python 中对应 `.conj().T` 与 `.T`，翻译错误会破坏互易性和噪声矩阵。

### 9.3 工程风险

**MAT/HDF5 数据布局。**

MATLAB 列主序、1 基索引、`-v7.3` HDF5 复数表示和维度顺序都可能导致轴交换或共轭错误。导入器必须用小型标记数组测试。

**MARIE 当前路径遮蔽。**

电子学模块存在重复目录和不同版本文件。虽然基础 UISNR 链路主要不经过电子学模块，但若同时比较实际阵列 SNR，路径污染可能影响结果。

**缺少完整示例资产。**

`BASIS_runner` 硬编码输入未随当前仓库完整提供，不能把一次运行失败简单归因于 Python 移植。

**依赖 MATLAB/GPU/MEX/工具箱。**

MARIE 的形态学壳层使用 Image Processing Toolbox，求解还可能依赖 Parallel/GPU 与已编译 MEX。

### 9.4 许可与发布风险

- 复制 MARIE 实质性代码时必须保留 MIT 声明。
- 捆绑 Gmsh 时需单独处理 GPL；更建议检测用户安装的 Gmsh。
- Dunavant LGPL、NIfTI BSD 和 TT/QTT 许可需进入 third-party notices。
- 人体模型和网格的再分发权不能仅由根 MIT 文件推定。
- “参考论文公式独立实现”和“逐行翻译代码”应在工程记录中区分。

### 9.5 验证风险

**循环验证。**

如果 Python 实现完全照 MARIE 写，再只用 MARIE 输出验证，两者可能共享同一个错误。必须保留独立基准：

- 当前 Lee 球心解析 oracle；
- 均匀球径向/离心收敛；
- 基变换不变性；
- 直接耗散积分与 `Phi` 对角元；
- 至少一个不同求解器或文献数据点。

## 10. 验收测试设计

### 10.1 纯线性代数测试

1. 对随机 Hermitian 正定 `Phi`，与高精度 `solve` 对比。
2. 对随机可逆基变换 `A`：

   ```math
   s'=A^Hs,\quad \Phi'=A^H\Phi A
   ```

   UISNR 应保持不变。
3. 对重复/近重复模式，结果应稳定且有效秩下降。
4. 任意单模式缩放不改变 UISNR。
5. 非 PSD、NaN、负对角和维度错误必须显式失败。

### 10.2 噪声积分测试

1. 单体素、单方向 E 场的手算结果。
2. 对角元等于各模式的 Joule 损耗。
3. `Phi` Hermitian 半正定。
4. 分块累计与一次性计算一致。
5. 体素拆分但总体积和场不变时结果一致。

### 10.3 物理测试

1. 保持当前 5 T 球心冻结回归。
2. 球心只有预期低阶模式贡献。
3. `lmax`、积分阶数和离心点严格收敛。
4. MARIE 相同 `Ub/Phi` 的无量纲核一致。
5. 完成约定转换后，绝对缩放在规定容差内一致。

### 10.4 CST 接口测试

1. 对所有端口施加随机复数缩放，阵列最优 SNR 不变。
2. Touchstone 与场文件端口顺序一致。
3. 接受功率归一化可从端口功率闭合关系验证。
4. CST 体损耗与 Python `E/sigma` 积分一致。
5. 坐标、单位和组织掩膜通过可视化叠加检查。

## 11. 分阶段实施建议

### Phase A：约定与数据契约

不改变求解器，先完成：

- `PhysicsConvention` 设计；
- MARIE 与 UISNR-5T 约定对照表；
- HDF5 交换 schema；
- 手工小数组导入测试；
- 明确 `uisnr_em_factor` 与绝对物理 SNR 的命名边界。

### Phase B：通用模态后处理

- 扩展现有白化内核以批量处理体素；
- 返回规范化最优权重；
- 生成模式收敛曲线；
- 完成基变换不变性测试；
- 保持球模型回归不变。

### Phase C：MARIE 交叉验证适配器

- MATLAB 端导出最小 `Ub/Phi/UISNR` fixture；
- Python 只复算无量纲二次型；
- 再实现 `marie_compatibility -> canonical` 转换；
- 输出逐项缩放审计表。

### Phase D：CST 样品噪声与有限阵列

- 导入多端口 E/H 场；
- 块式计算样品噪声矩阵；
- 计算最优阵列 SNR；
- 与解析球 UISNR 或 MARIE UISNR 比较；
- 输出效率 `eta` 与改进空间图。

### Phase E：理想表面电流

- 从表面模式场做 SVD；
- 求表面约束最优权重；
- 回投到 RWG/源电流；
- 输出目标 ROI 的理想电流幅相图；
- 将其转为线圈参数设计先验。

### Phase F：完整一般人体 UISNR

- 独立 VIE 或经过验证的外部全波后端；
- 偶极子壳层和 rSVD；
- MRGF 离线/在线降阶；
- 全部源空间、网格和模式收敛；
- 与 MARIE、解析球和 CST 三方验证。

## 12. 建议的停止条件

出现以下任一情况时，不应进入下一阶段：

- 无法解释 MARIE 与 Python 的每一个固定缩放因子；
- `Phi` 有显著负特征值或 Hermitian 误差；
- 结果对无物理意义的通道缩放敏感；
- UISNR 随模式增加明显下降且无法由截断解释；
- 源壳距离或网格变化导致结果不收敛；
- CST 体损耗与 Python 噪声积分不闭合；
- 实际阵列在同约定下稳定超过 UISNR；
- 验证数据与实现来自同一代码路径，没有独立 oracle；
- 依赖数据或第三方组件的再分发许可不明确。

## 13. 最终建议

当前最可行的方案是“借鉴 MARIE 的上游物理链路，不复制其下游数值写法”：

- 继续使用 UISNR-5T 已验证的白化内核；
- 新增通用模态场与样品噪声数据契约；
- 用 MARIE 导出的 `Ub/Phi` 做交叉验证；
- 优先完成 CST 多端口场到有限阵列 SNR 的路径；
- 把表面约束最优电流作为第一个设计指导功能；
- 最后再复现偶极子壳层、VIE 和 MRGF。

这样能够在较短时间内得到可验证、可用于线圈设计的模块，又不会把 MARIE 的 MATLAB 路径、MEX、GPU、工具箱和历史工程问题带入 Python 主程序。完整一般人体 UISNR 仍然可作为长期目标，但必须以独立基准、数值诊断和严格收敛为前提。
