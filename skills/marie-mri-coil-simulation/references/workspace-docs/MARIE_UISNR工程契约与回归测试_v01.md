# MARIE UISNR 工程契约与回归测试 v01

## 目的

本文把 5T 32 通道项目中已经由代码和合成测试验证的 UISNR 工程经验提升为工作区通用接口。它补充既有 UISNR 原理文档，不改变 MARIE 求解器公式，也不把项目专属 ROI、K 值或网络阈值提升为全局标准。

## 结果命名

- `geo_flag=2`：承载面约束最优 SNR；除非另有证明，不称绝对 UISNR。
- `geo_flag=3`：偶极子壳层 UISNR 近似；只有源距离、壳厚、网格、秩和模式数均收敛后才可去掉“近似”限定。

## 空间语义

每次运行分别记录：

- `Omega_support`：BASIS/UISNR 的活动体素集合，通常为 `RHBM.idxS`；
- `Omega_primary`：设计与报告 ROI；
- `Omega_diagnostic`：局部诊断 ROI。

原生 UISNR 对 `Omega_support` 内每个体素逐点独立优化，每个体素有不同权重。它不产生一个“全 ROI 平均最优电流”。把多个体素 ICP 汇总成共享目标属于独立空间聚合模型，必须记录体素权重、归一化和留出验证。

## 数值与复数约定

对信号列向量 `s` 和噪声矩阵 `Phi`：

\[
q=s^H\Phi^+s,\qquad \mathrm{UISNR}=C\sqrt{\max(\operatorname{Re}q,0)}.
\]

科学后处理先 Hermitian 化 `Phi`，正定且条件良好时使用 Cholesky/线性求解，半正定或病态时采用有记录阈值的特征值/SVD 伪逆。显式 `inv(Phi)` 只用于标明的原生兼容性对照。

若 MARIE 信号组合采用 `s^T w`，物理 ICP 系数为：

\[
w=\frac{\operatorname{conj}(\Phi^+s)}
        {\sqrt{\operatorname{Re}(s^H\Phi^+s)}}.
\]

必须区分抽象分析方向 `Phi^+s` 和映射到 `VK/SK` 的物理系数，避免共轭错误。

## 通用模板接口

Skill 源包 `marie-mri-coil-simulation skills/assets/matlab-scripts/uisnr/` 提供：

- 几何/四视图门禁；
- 资源估算；
- 非覆盖流式 UISNR 写入；
- 稳定二次型内核；
- ICP 物理系数提取；
- 兼容性 tuple 审计；
- 分辨率收敛统计；
- 有限阵列与 UISNR 上界比较；
- 复电流幅值、相位、四时相、散度与流线代理图。

这些模板必须复制到新案例版本后适配，不能原地编辑 Skill 资产，也不能把其中的回调式几何入口误认为完整 MARIE BASIS runner。

## 回归门禁

在 MATLAB 中设置 `skillRoot`，执行
`addpath(fullfile(skillRoot,'tests','uisnr'))`，再调用
`RUN_ALL_UISNR_SKILL_TESTS(skillRoot)`。该入口覆盖：

1. 二次型与直接线性求解一致；
2. 一般可逆模式坐标变换不改变 UISNR；
3. 不同分块大小与流式落盘一致且拒绝覆盖；
4. 全局相位旋转产生共轭方向的物理 ICP 系数；
5. `idxS` 三维写回和体素重排保持一致。

真实项目还必须补充噪声 PSD/秩/截断敏感性、Coarse/Medium/Fine、支持面/源壳、空间留出及有限阵列 `SNR/UISNR <= 1+tolerance` 验证。合成测试通过不等于研究级收敛。

## 复电流与 Hodge

至少绘制 `|J|`、明确定义的标量相位、四个瞬时快照、表面散度和流线。流线若由三角形质心邻接生成，必须标为诊断代理而非物理导线。Hodge 分解还应验证切向性、重构残差、散度/旋度残差、质量矩阵正交性、harmonic 维数与拓扑，以及全局复相位协变性。

## 范围边界

12/14 个区域、固定距离阈值、K4/K8、宽松 Stage-B 门槛、Hugo 匿名材料解剖解释和线圈—体素责任矩阵仍是项目专属或待验证假设，不属于本通用契约。
