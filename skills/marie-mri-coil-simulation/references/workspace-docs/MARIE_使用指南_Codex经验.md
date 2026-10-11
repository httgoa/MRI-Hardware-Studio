# MARIE 3.0 工具箱使用指南

> Agent 在本仓库创建、运行或核查仿真前，应遵循 [AGENTS.md](AGENTS.md) 和 [MARIE_Agent_Harness.md](MARIE_Agent_Harness.md)。

> 适用仓库：`cloudmrhub/marie-tools` 当前本地版本（MARIE 3.0，源码标注年份 2025）  
> Linux 安装目录：`/home/<user>/marie-tools`  
> MATLAB 安装目录示例：`/home/<user>/MATLAB/R2025b`；也可通过 `MATLAB_BIN` 指向可执行文件。  
> 本指南依据仓库中的 `README.md`、各 runner 的 help 注释、`load_inputs.m` 和内置示例配置整理。

## 1. MARIE 是什么

MARIE（Magnetic Resonance Integral Equation Suite）是用于 MRI 系统频域电磁分析的 MATLAB 工具箱。当前版本包含：

- WIE、SIE、VIE、WVIE、SVIE 和 WSVIE 积分方程；
- 基于 GMRES 的迭代求解器；
- pFFT、SVD、Tucker、Tensor Train 和 ACA 等加速/压缩方法；
- 线圈、导线、屏蔽体和体素人体模型的几何处理；
- 电场、磁场、B1、SNR 和发射效率等后处理；
- 调谐、匹配、去耦和失谐的电路联合仿真。

该工具箱不是“打开即显示结果”的 GUI 软件。标准工作方式是：准备 JSON 输入文件，运行相应的 runner 脚本，然后从 `data/solutions/` 读取 `.mat` 结果。

## 2. 目录结构

data 子目录中每个现有文件的格式、用途、runner 依赖关系和当前可用性，见 [MARIE_data文件夹内容与仿真作用详解.md](MARIE_data文件夹内容与仿真作用详解.md)。

src 子目录的算法模块、调用链、加速机制、输入输出和已知源码风险，见 [MARIE_src源码模块与算法详解.md](MARIE_src源码模块与算法详解.md)。

```text
marie-tools/
├── data/
│   ├── bases/          # 预计算电磁基、UISNR 和 MRGF 数据
│   ├── bodies/         # MAT 格式体素人体/仿体模型
│   ├── coils/
│   │   ├── basis_files/
│   │   ├── coil_files/
│   │   ├── external_coils/
│   │   ├── shield_files/
│   │   └── wire_files/
│   ├── inputs/         # JSON 仿真输入
│   └── solutions/      # MAT 仿真输出
├── src/
│   ├── src_geometry/
│   ├── src_integral_equations/
│   ├── src_mathematics/
│   ├── src_physics/
│   ├── src_runners/    # 用户主要入口
│   ├── src_solver/
│   ├── src_utils/
│   └── src_visualizer/
├── installer.m         # 一次性编译 MEX/C++ 例程
└── startup.m           # 每个新 MATLAB 会话加载路径
```

仓库 README 中的 `doc/` 仍标注为 “Coming Soon”，因此当前最可靠的说明来自 runner 文件头部的 help 注释和源码。

## 3. 使用前检查

### 3.1 检查许可证服务

服务器当前使用网络许可证。首次配置或新的 SSH 终端中，可临时设置：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
```

测试 MATLAB：

```bash
/path/to/MATLAB/R2025b/bin/matlab -batch "disp(version)"
```

能输出 `R2025b` 并正常退出，说明客户端能获取许可证。

临时 `export` 只对当前 SSH 终端有效。推荐只执行一次，将变量写入 `~/.bashrc`：

```bash
grep -qxF 'export MLM_LICENSE_FILE=27000@<license-server>' ~/.bashrc || \
echo 'export MLM_LICENSE_FILE=27000@<license-server>' >> ~/.bashrc
source ~/.bashrc

echo "$MLM_LICENSE_FILE"
```

预期输出为 `27000@<license-server>`。若主机名无法解析，可将上述值改为已验证的 `27000@<license-server>`。两种写法二选一即可。

### 3.2 每次如何打开 MATLAB

完成上述 `.bashrc` 配置后，每次新建 MobaXterm/SSH 终端，直接执行：

```bash
matlab
```

若 `matlab` 命令未在 `PATH` 中，则使用绝对路径：

```bash
/path/to/MATLAB/R2025b/bin/matlab
```

MobaXterm 必须启用 X11 forwarding，才能显示 MATLAB 图形界面。打开 MATLAB 后，在 MATLAB 命令窗口执行：

```matlab
cd('/home/<user>/marie-tools')
startup
```

这两行是每次新 MATLAB 会话都需要执行的工具箱初始化。日常完整流程为：

```text
SSH 登录服务器 -> matlab -> cd('/home/<user>/marie-tools') -> startup -> 运行/分析任务
```

只运行仿真、不需要 GUI 时，可在 Linux 终端使用批处理模式：

```bash
cd /home/<user>/marie-tools
matlab -batch "startup; MARIE_runner"
```

若重新登录后 MATLAB 报 License Error 5，先检查：

```bash
echo "$MLM_LICENSE_FILE"
systemctl is-active matlab-licensing.service
```

预期分别为许可证地址和 `active`。环境变量为空时执行 `source ~/.bashrc` 后再启动 MATLAB；许可证服务未运行时，由管理员或具备 sudo 权限的用户执行：

```bash
sudo systemctl start matlab-licensing.service
```

### 3.3 一次性安装

首次下载代码、更新源码、切换 MATLAB 大版本或更换编译器后，应重新执行安装器。正常日常使用不需要重复运行。

在 MATLAB 中：

```matlab
cd('/home/<user>/marie-tools')
mex -setup C++
installer
```

成功标志：

```text
WVIE assembly routines are compiled successfully
SVIE assembly routines are compiled successfully
SIE assembly routines are compiled successfully
VIE assembly routines are compiled successfully
MARIE 3.0 successfully installed
```

### 3.4 每次启动 MATLAB 后加载工具箱

```matlab
cd('/home/<user>/marie-tools')
startup
```

`startup.m` 只执行 `addpath(genpath('./'))`，正常情况下不会打印信息。没有报错即表示加载完成。

验证：

```matlab
which MARIE_runner
contains(path, '/home/<user>/marie-tools/src')
```

预期结果：`which` 返回 `MARIE_runner.m` 的完整路径，`contains` 返回逻辑值 `1`。

> 注意：`startup`、`installer`、`MARIE_runner` 和 `mex` 都是 MATLAB 命令，不要直接输入 Linux shell。

## 4. 首次运行：内置最小算例

当前仓库自带一个可直接运行的输入：

```text
data/inputs/inp_MSphere_HeadCoil1z.json
```

它描述的是：

- `B0 = 3.0063 T`；
- 核种为 `1H`；
- 2 mm 多层球形仿体 `Multilayer_Sphere.mat`；
- 单通道 Rx 导线线圈 `Head_Receive_Array_1_Coil_z.msh`；
- 开启 TMD/联合仿真；
- 使用 WSVIE 完整求解流程。

### 4.1 在 MATLAB GUI 中运行

```matlab
cd('/home/<user>/marie-tools')
startup
MARIE_runner
```

必须从仓库根目录运行。源码大量使用 `./data/...` 相对路径，如果当前目录不正确，会出现输入、模型或输出文件找不到的问题。

### 4.2 在 SSH 终端批处理运行

```bash
export MLM_LICENSE_FILE=27000@<license-server>
cd /home/<user>/marie-tools
/path/to/MATLAB/R2025b/bin/matlab -batch "startup; MARIE_runner"
```

### 4.5 仿真结果检查方法与经验

#### 4.5.1 确认结果已经写入磁盘

只有命令窗口同时出现以下两行，才表示计算和保存都已完成：

```text
[MARIE 3.0] Simulation completed successfully.
[Saved] - ./data/solutions/MARIE_1_inp_MSphere_HeadCoil1z.mat
```

仅看到迭代次数、`Solving System ...` 或 `Performing Co-simulation ...` 不代表仿真最终成功；后续仍可能在场计算或保存阶段失败。

#### 4.5.2 先检查文件，再加载大结果

本次单通道示例的 `solution` 结构约为 `1.68 GB`。先用 `whos -file` 检查，避免不必要地占用 MATLAB 内存：

```matlab
resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat');

assert(isfile(resultFile), '未找到结果文件：%s', resultFile)
whos('-file', resultFile)

R = load(resultFile, 'solution');
solution = R.solution;
fieldnames(solution)
```

当前完整 WSVIE 结果常见字段包括：

```text
Jcb, netp, JcbRx, JcbTx, e_field, h_field, snr_field, txe_field
```

字段随线圈类型变化。访问子字段前应使用 `isfield` 或 `fieldnames`，不要假定每个算例同时含有 `Rx` 与 `Tx`。

#### 4.5.3 判定线圈模式

```matlab
fieldnames(solution.h_field)
fieldnames(solution.e_field)
```

| 字段 | 含义 | 应优先查看 |
| --- | --- | --- |
| `Rx` | 接收线圈模式 | `h_field.Rx.b1m`、接收 SNR、接收电场。 |
| `Tx` | 发射线圈模式 | `h_field.Tx.b1p`、发射效率和吸收功率。 |

若结果仅有 `Rx`，访问 `solution.e_field.Tx` 或 `solution.h_field.Tx` 会报“无法识别的字段名称”。这不是计算失败，而是该线圈被定义为纯接收线圈。

本次 `inp_MSphere_HeadCoil1z.json` 使用 `Head_Receive_Array_1_Coil_z.msh`，因此仅保存 `Rx` 结果，符合预期。

#### 4.5.4 网络参数：匹配、谐振和端口数

```matlab
assert(isfield(solution, 'netp'), '结果中没有网络参数 netp');
SP = solution.netp.SP_s;
ZP = solution.netp.ZP_s;

size(SP)
Sdiag_dB = 20*log10(abs(diag(SP)))
Zdiag = diag(ZP)

visualize_s_parameters(SP)
visualize_z_parameters(ZP)
```

| 指标 | 含义与判读 |
| --- | --- |
| `size(SP)` | 最终网络端口数；`1x1` 表示单端口，多通道阵列通常为 `NxN`。 |
| `Sdiag_dB` | 反射系数。小于 `-15 dB` 通常可接受，小于 `-20 dB` 较好。 |
| `Zdiag` | 输入阻抗。若参考阻抗为 50 Ω，匹配后应接近 `50 + j0 Ω`。 |
| 非对角 `SP(i,j)` | 端口耦合。数值越低，隔离通常越好；须结合线圈设计目标判断。 |

本次示例的实际结果为：

```text
SP_s: 1x1
S11: -57.63 dB
Z11: 49.9 + j0.1 Ω
```

这说明自动调谐和 50 Ω 匹配已成功，且匹配裕量很高。`visualize_s_parameters` 的色标固定在 `-40` 到 `-5 dB`；当 S11 低于 `-40 dB` 时，热图会呈黑色，但图中的数字标签仍是正确结果，不能将黑色误判为零或失败。

求解日志中出现的 `Port: 1 ... Port: 4` 是内部激励/求解通道。最终网络端口数应以 `size(solution.netp.SP_s)` 为准，不能仅依据迭代日志判定为四端口网络。

#### 4.5.5 B1- 接收灵敏度与数值完整性

对于 Rx 算例，绘制端口 1 的中间切片：

```matlab
assert(isfield(solution.h_field, 'Rx'), '当前结果不是 Rx 场');
B1m = solution.h_field.Rx.b1m;

fprintf('B1- 尺寸: %s\n', mat2str(size(B1m)));
fprintf('NaN 数量: %d\n', nnz(isnan(B1m)));
fprintf('Inf 数量: %d\n', nnz(isinf(B1m)));
fprintf('|B1-| 最大值: %.4g T\n', max(abs(B1m(:))));
fprintf('|B1-| 平均值: %.4g T\n', mean(abs(B1m(:))));

figure
imagesc(squeeze(abs(B1m(:,:,round(end/2),1))))
axis image off
colormap turbo
colorbar
title('|B1-|：中间切片，端口 1')
```

检查要点：

1. `NaN` 和 `Inf` 数量应为零。
2. 图像应在体模区域内呈连续空间分布，不应出现整幅图为零、大面积随机斑点或孤立异常高值。
3. 对同一模型、频率和激励，重复计算的图形形态应基本一致。
4. `B1-` 的绝对值受激励归一化、端口定义和匹配校准影响；不要脱离这些条件与其他论文或系统的数值直接比较。

本次示例为 3 T、2 mm 多层球体体模和单接收线圈。中间切片中出现球形体模内部连续的 `|B1-|` 分布，说明场计算及保存正常；它只能作为流程验证，不能直接视为真实头部接收阵列性能。

#### 4.5.6 电场、SNR 和发射效率

先列出实际字段，再编写相应的可视化代码：

```matlab
fieldnames(solution.e_field)
fieldnames(solution.e_field.Rx)    % 仅在存在 Rx 时执行
fieldnames(solution.snr_field)
fieldnames(solution.txe_field)
```

- Rx 算例优先查看 `snr_field`、`B1-` 及接收电场/损耗相关量。
- Tx 算例优先查看 `B1+`、`txe_field` 和吸收功率等量。
- 不同版本或 runner 保存的子字段可能不同，因此先列字段，再按实际字段访问。

`txe_field.TXE` 是平方型指标。绘制常用的 `B1+` 发射效率时，应使用：

```matlab
TXE2 = real(solution.txe_field.TXE);
TXEeff = 1e6 * sqrt(max(TXE2,0));  % µT/sqrt(W)
z = round(size(TXEeff,3)/2);

figure('Color','w');
imagesc(squeeze(TXEeff(:,:,z))');
axis image off; set(gca,'YDir','normal');
colormap(lipari(256));
cb = colorbar; cb.Label.String = '\muT/\surdW';
title('Transmit efficiency');
```

完整的正交切片、统计、UITXE 对比和纯 Rx 解释限制见 [`MARIE_可视化脚本使用指南.md`](MARIE_可视化脚本使用指南.md) 第 10.4 节。

#### 4.5.7 可用于研究前的额外验证

一次仿真成功只证明软件、许可证、MEX 和当前输入可以正常工作，并不等于结果已完成研究层面的验证。进入真实人体模型或线圈设计前，至少应额外完成：

1. 网格/体素分辨率收敛性检查。
2. 与解析解、文献、商业电磁仿真器或实验测量的交叉验证。
3. 明确端口参考阻抗、激励幅值、相位和场量归一化方式。
4. 多通道线圈的逐端口匹配与端口间耦合检查。
5. 保存每项结果对应的 JSON、线圈网格、人体模型和 MARIE/MATLAB 版本。

### 4.3 runner 的实际执行阶段

`MARIE_runner` 按以下顺序执行：

1. `load_inputs`：读取 JSON 并初始化电磁常数、数值容差和函数句柄；
2. `geo_assembly`：构造体素仿体、线圈、导线和屏蔽体几何；
3. `wsvie_assembly`：组装 WSVIE 系统矩阵；
4. `solver_wsvie`：求解积分方程；
5. `co_simulation`：执行调谐、匹配、去耦和失谐联合仿真；
6. `em_ehfield_wsvie`：计算电场、磁场、SNR 和发射效率；
7. 将 `MREDM.fields` 保存为结果文件中的变量 `solution`。

`load_inputs` 在未检测到并行池时会自动运行：

```matlab
parpool('IdleTimeout', 240)
```

因此第一次运行时看到并行池启动信息是正常现象。

### 4.4 成功标志

运行过程中应依次看到：

```text
Loading inputs ...
Geometry Construction ...
Assembling Integral Equation Operators ...
Solving System ...
Performing Co-simulation ...
Computing electromagnetic fields ...
Storing Fields ...

[MARIE 3.0] Simulation completed successfully.
```

内置算例的输出文件为：

```text
data/solutions/MARIE_1_inp_MSphere_HeadCoil1z.mat
```

文件命名规则：

```text
MARIE_<TMD值>_<输入JSON文件名（不含扩展名）>.mat
```

## 5. 检查和读取结果

### 5.1 确认文件存在

```matlab
resultFile = fullfile('data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat');

assert(isfile(resultFile), '未找到 MARIE 输出文件');
whos('-file', resultFile)
```

结果文件采用 `-v7.3` 格式，内部主要变量为 `solution`。

### 5.2 加载并查看层级

```matlab
S = load(resultFile, 'solution');
solution = S.solution;

fieldnames(solution)
```

根据当前源码，常见字段可能包括：

```text
Jcb / JcbRx / JcbTx      电流系数
netp                     网络参数和联合仿真结果
e_field                  电场及损耗相关量
h_field                  磁场、B1+、B1-
snr_field                SNR 图和平均值
txe_field                发射效率图和平均值
```

字段是否存在取决于线圈的 Tx/Rx 类型和具体输入。应先用 `isfield` 检查，不要假定所有结果都同时存在。

递归查看结构：

```matlab
disp(fieldnames(solution))

if isfield(solution, 'h_field')
    disp(fieldnames(solution.h_field))
end

if isfield(solution, 'e_field')
    disp(fieldnames(solution.e_field))
end

if isfield(solution, 'netp')
    disp(fieldnames(solution.netp))
end
```

### 5.3 结果保存机制与注意事项

`MARIE_runner` 在所有求解和场计算完成后执行：

```matlab
solution = MREDM.fields;

save(fullfile('./data/solutions/', ...
    ['MARIE_', num2str(MREDM.inputs.tmd), '_', ...
     input_file(1:end-5), '.mat']), ...
    'solution', '-v7.3');
```

文件命名规则为：

```text
MARIE_<TMD>_<输入JSON基本名>.mat
```

例如：

```text
输入：inp_5T_1H_Sphere200_8LoopRx.json
TMD：1
输出：data/solutions/MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat
```

`-v7.3` 用于支持超过 2 GB 的大型场数据。常规结果只保存顶层变量 `solution=MREDM.fields`，不保存完整的 `MREDM`，因此不包含输入 JSON 原文、体模结构、线圈网格、积分算子和求解器配置。

保存目录使用相对路径 `./data/solutions/`。运行 Runner 前必须保证 MATLAB 当前目录为：

```text
/home/<user>/marie-tools
```

相同 case 再次运行时，`save` 会覆盖同名 MAT 文件。若仿真在保存之前失败，则旧的同名文件仍可能存在，不能仅凭“文件存在”判断本次运行成功。

此外，`TMD=1` 完成自动调谐后，优化结果会写回线圈同名 JSON。结果 MAT 中没有完整保存最终集总元件列表，因此正式运行前后都应归档线圈 JSON：

```matlab
coilJson = fullfile(pwd, 'data', 'coils', 'wire_files', ...
    'Custom', 'Sphere8Rx_R115_H140_Span50.json');

copyfile(coilJson, fullfile(pwd, 'data', 'solutions', ...
    'Sphere8Rx_before_optimization.json'));

% 执行自己的 Runner
RUN_5T_8CH_SPHERE;

% Runner 内含 clearvars，返回后需要重新构造路径
cd('/home/<user>/marie-tools');
coilJson = fullfile(pwd, 'data', 'coils', 'wire_files', ...
    'Custom', 'Sphere8Rx_R115_H140_Span50.json');
copyfile(coilJson, fullfile(pwd, 'data', 'solutions', ...
    'Sphere8Rx_after_optimization.json'));
```

### 5.4 关闭 MATLAB 后重新打开常规结果

重新登录服务器并启动 MATLAB 后执行：

```matlab
cd('/home/<user>/marie-tools');
startup;

resultFile = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');

assert(isfile(resultFile), '结果文件不存在：%s', resultFile);
whos('-file', resultFile)
```

`whos('-file',...)` 只查看文件目录和变量大小，不把大型场数据全部载入内存。确认顶层变量为 `solution` 后再加载：

```matlab
R = load(resultFile, 'solution');
solution = R.solution;
clear R;

disp(fieldnames(solution));
```

验证核心结果：

```matlab
assert(isfield(solution,'netp'), '缺少网络参数');
assert(isfield(solution,'h_field'), '缺少磁场结果');
assert(isfield(solution,'snr_field'), '缺少 SNR 结果');

disp(size(solution.netp.SP_s));
disp(size(solution.h_field.Rx.b1m));
disp(size(solution.snr_field.SNR));
```

对于纯 Rx 项目，重点字段为：

```matlab
SP    = solution.netp.SP_s;
ZP    = solution.netp.ZP_s;
B1m   = solution.h_field.Rx.b1m;
SNR   = solution.snr_field.SNR;
SNRav = solution.snr_field.SNR_avg;
```

MAT v7.3 虽然基于 HDF5，但当前 Runner 把结果封装在一个顶层结构 `solution` 中，针对深层字段的真正局部读取能力有限。大型结果应先用 `whos('-file',...)` 检查，并确保有足够内存后再加载整个 `solution`。

### 5.5 关闭 MATLAB 后重新打开 BASIS/UISNR 结果

`BASIS_runner` 保存的是顶层变量 `BASIS`，位置由输入 JSON 的 `BasisFile` 决定，通常位于 `data/bases/`：

```matlab
cd('/home/<user>/marie-tools');
startup;

basisFile = fullfile(pwd, 'data', 'bases', ...
    'Sphere200_5T_PWC_CylSupport_UISNR.mat');

assert(isfile(basisFile), 'BASIS 文件不存在：%s', basisFile);
whos('-file', basisFile)

Q = load(basisFile, 'BASIS');
BASIS = Q.BASIS;
clear Q;

disp(fieldnames(BASIS));
assert(isfield(BASIS,'UISNR'));
assert(isfield(BASIS,'wUISNR'));
assert(isfield(BASIS,'cUISNR'));
```

常用数据：

```matlab
UISNR  = BASIS.UISNR;
wUISNR = BASIS.wUISNR;
cUISNR = BASIS.cUISNR;
```

`geo_flag=2` 生成的 BASIS 还应包含 `Substrate`，用于理想表面电流可视化。

### 5.6 重新打开后恢复几何显示

结果 MAT 不包含完整几何。关闭 MATLAB 后不能执行：

```matlab
visualize_geometry(solution)   % 错误用法
```

应根据原输入 JSON 重建几何，然后把结果附加到新的 `MREDM`：

```matlab
cd('/home/<user>/marie-tools');
startup;

input_file = 'inp_5T_1H_Sphere200_8LoopRx.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);
MREDM.fields = solution;

figure('Color','w');
visualize_geometry(MREDM);
view(3);
axis equal;
rotate3d on;
```

注意：如果自动调谐已经改写线圈 JSON，重建出来的是调谐后的电路参数。几何坐标通常不变，但为了严格复现，仍应使用当次运行归档的 JSON、MSH、体模和输入文件。

### 5.7 保存后处理数据和图片

不要把后处理变量重新写回原始 `MARIE_*.mat`。建议创建独立的派生文件：

```matlab
processed = struct();
processed.source_result = resultFile;
processed.created = char(datetime('now','Format','yyyy-MM-dd HH:mm:ss'));
processed.SdB = 20*log10(abs(solution.netp.SP_s));
processed.SNR_avg = solution.snr_field.SNR_avg;
processed.center_slice = round(size(solution.snr_field.SNR,3)/2);

processedFile = fullfile(pwd, 'data', 'solutions', ...
    'Processed_5T_8ch_Sphere200.mat');
save(processedFile, 'processed', '-v7.3');
```

保存图像：

```matlab
figureDir = fullfile(pwd, 'data', 'solutions', 'figures_5T_8ch');
if ~exist(figureDir,'dir'), mkdir(figureDir); end

exportgraphics(gcf, fullfile(figureDir,'SNR_center_slice.png'), ...
    'Resolution',300);
```

建议保持三层数据关系：

```text
原始输入和模型       JSON / MSH / phantom MAT
原始求解结果         MARIE_*.mat / BASIS*.mat
派生数据与图片       Processed_*.mat / figures_*/
```

### 5.8 记录日志并防止把旧结果当作新结果

运行前记录开始时间，并把旧的同名结果移走：

```matlab
expectedResult = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');

archiveDir = fullfile(pwd, 'data', 'solutions', 'previous_runs');
if ~exist(archiveDir,'dir'), mkdir(archiveDir); end

if isfile(expectedResult)
    stamp = char(datetime('now','Format','yyyyMMdd_HHmmss'));
    [~,name,ext] = fileparts(expectedResult);
    movefile(expectedResult, fullfile(archiveDir, ...
        [name '_' stamp ext]));
end

logFile = fullfile(pwd, 'data', 'solutions', ...
    ['run_' char(datetime('now','Format','yyyyMMdd_HHmmss')) '.log']);
setappdata(groot,'MARIE_RUN_STARTED',now);
diary(logFile);

try
    RUN_5T_8CH_SPHERE;
catch ME
    diary off;
    if isappdata(groot,'MARIE_RUN_STARTED')
        rmappdata(groot,'MARIE_RUN_STARTED');
    end
    rethrow(ME);
end

% Runner 开头的 clearvars 会清除普通工作区变量，因此重新构造路径
diary off;
cd('/home/<user>/marie-tools');
runStarted = getappdata(groot,'MARIE_RUN_STARTED');
rmappdata(groot,'MARIE_RUN_STARTED');
expectedResult = fullfile(pwd, 'data', 'solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');

assert(isfile(expectedResult), '本次运行没有生成预期结果');
info = dir(expectedResult);
assert(info.datenum >= runStarted, '结果文件不是本次运行生成的');
```

完成标志必须同时满足：

1. 日志出现 `[MARIE 3.0] Simulation completed successfully.`；
2. 预期文件存在；
3. 修改时间晚于本次启动时间；
4. `whos('-file',...)` 可正常读取；
5. `solution` 包含目标字段和预期端口数。

## 6. 内置 Rx 算例的结果可视化

项目自带的全部可视化函数、调用条件、绘图效果和已知源码限制，见 [MARIE_可视化脚本使用指南.md](MARIE_可视化脚本使用指南.md)。

### 6.1 查看 SNR

该算例的线圈 JSON 将激励类型定义为 `Rx`，因此重点结果是接收灵敏度和 SNR。

```matlab
assert(isfield(solution, 'snr_field'), '结果中没有 snr_field');

SNR = solution.snr_field.SNR;
k = round(size(SNR, 3) / 2);

figure;
imagesc(squeeze(SNR(:, :, k)).');
axis image;
set(gca, 'YDir', 'normal');
colorbar;
title(sprintf('SNR central slice, z-index = %d', k));

fprintf('Average SNR: %.6g\n', solution.snr_field.SNR_avg);
```

### 6.2 查看单通道 B1-

```matlab
assert(isfield(solution, 'h_field') && ...
       isfield(solution.h_field, 'Rx'), ...
       '结果中没有 Rx 磁场');

B1m = abs(solution.h_field.Rx.b1m(:, :, :, 1));
k = round(size(B1m, 3) / 2);

figure;
imagesc(squeeze(B1m(:, :, k)).');
axis image;
set(gca, 'YDir', 'normal');
colorbar;
title(sprintf('|B1^-|, port 1, z-index = %d', k));
```

### 6.3 查看 S 参数

```matlab
if isfield(solution, 'netp') && isfield(solution.netp, 'SP_s')
    visualize_s_parameters(solution.netp.SP_s);
else
    warning('结果中没有 netp.SP_s');
end
```

### 6.4 查看几何

在交互式 MATLAB 会话中运行 `MARIE_runner` 后，完整变量 `MREDM` 仍位于工作区，可直接调用：

```matlab
visualize_geometry(MREDM)
```

保存的结果文件只包含 `solution = MREDM.fields`，不包含完整几何结构。因此关闭 MATLAB 后仅加载结果文件时，不能直接调用 `visualize_geometry(solution)`。

## 7. JSON 输入参数说明

本节的完整字段规则、当前仓库全部模型候选和预检查脚本，见 [MARIE_JSON文件配置指南.md](MARIE_JSON文件配置指南.md)。

内置配置：

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

| 字段 | 含义 | 路径或取值规则 |
| --- | --- | --- |
| `B0` | 主磁场强度，单位 T | 必填数值 |
| `Nucleus` | 核种 | 当前示例为 `1H` |
| `Basis_Functions_VIE` | VIE 体基函数 | `0` = PWC，`1` = PWL |
| `BodyFile` | 体素模型 | 相对于 `data/bodies/` |
| `CoilFile` | 表面线圈网格 | 相对于 `data/coils/coil_files/`，可为空 |
| `WireFile` | 导线线圈网格 | 相对于 `data/coils/wire_files/`，可为空 |
| `ShieldFile` | 屏蔽体网格 | 相对于 `data/coils/shield_files/`，可为空 |
| `SurfaceBasisSupportFile` | 表面支撑基网格 | 相对于 `data/coils/basis_files/` |
| `TMD` | 联合仿真开关 | `0` = 关闭，`1` = 开启 |
| `BasisFile` | 预计算电磁基/MRGF 文件 | 相对于 `data/bases/` |

对 `MARIE_runner`，`CoilFile`、`WireFile` 和 `ShieldFile` 可以为空，但至少要提供实际激励：

- 提供表面线圈时填写 `CoilFile`；
- 提供导线线圈时填写 `WireFile`；
- 提供屏蔽体时填写 `ShieldFile`；
- 三者均为空时，代码尝试从 `BasisFile` 读取外部电磁基。

当线圈、导线或屏蔽模型已提供时，runner help 说明 `BasisFile` 不作为外部激励使用。内置算例提供了 `WireFile`，因此其 `BasisFile` 不决定本次激励。

## 8. 创建自己的仿真任务

完整的自定义案例可参考 [MARIE_5T_8通道Loop球形体模仿真操作指南.md](MARIE_5T_8通道Loop球形体模仿真操作指南.md)，其中包含 200 mm 球形 phantom、8 通道 Rx Loop、自动调谐、UISNR/BASIS 和论文格式后处理图的两条计算链。

从零创建体模、Wire 线圈、表面 Coil、Shield，并将它们组合为一个可验证仿真项目，参见 [MARIE_模型设计与组合教程.md](MARIE_模型设计与组合教程.md)。

### 8.1 复制输入 JSON

不要直接覆盖内置示例，先复制一份：

```bash
cd /home/<user>/marie-tools/data/inputs
cp inp_MSphere_HeadCoil1z.json inp_my_case.json
```

编辑 `inp_my_case.json`，修改磁场、模型、线圈和联合仿真设置。确保引用的文件已放入对应 `data/` 子目录。

### 8.2 修改 runner 中的输入文件名

`MARIE_runner.m` 当前将输入文件名硬编码为：

```matlab
input_file = 'inp_MSphere_HeadCoil1z.json';
```

由于 runner 开头执行 `clearvars`，不能在调用 runner 前通过工作区变量覆盖它。运行自定义任务前，需要将该行改为：

```matlab
input_file = 'inp_my_case.json';
```

更稳妥的研究工作流是复制 runner，并保留原始文件：

```bash
cp /home/<user>/marie-tools/src/src_runners/MARIE_runner.m \
   /home/<user>/marie-tools/MARIE_runner_my_case.m
```

然后只修改副本中的 `input_file`。运行：

```matlab
cd('/home/<user>/marie-tools')
startup
MARIE_runner_my_case
```

### 8.3 运行前核验输入文件

```matlab
cfgFile = fullfile('data', 'inputs', 'inp_my_case.json');
cfg = jsondecode(fileread(cfgFile));
disp(cfg)

assert(isfile(fullfile('data', 'bodies', cfg.BodyFile)), ...
    'BodyFile 不存在');

if ~isempty(cfg.WireFile)
    assert(isfile(fullfile('data', 'coils', 'wire_files', cfg.WireFile)), ...
        'WireFile 不存在');
end

if ~isempty(cfg.CoilFile)
    assert(isfile(fullfile('data', 'coils', 'coil_files', cfg.CoilFile)), ...
        'CoilFile 不存在');
end

if ~isempty(cfg.ShieldFile)
    assert(isfile(fullfile('data', 'coils', 'shield_files', cfg.ShieldFile)), ...
        'ShieldFile 不存在');
end
```

## 9. 其他 runner

四种 Runner 的算法原理、适用场景、前置条件、输入输出和执行模板已单独整理为：[`MARIE_Runner算法与使用指南.md`](MARIE_Runner算法与使用指南.md)。本节仅保留快速索引。

当前 `src/src_runners/` 实际包含：

| Runner | 用途 | 前置条件 | 输出 |
| --- | --- | --- | --- |
| `MARIE_runner` | 完整 WSVIE 仿真 | JSON、人体/仿体、线圈或电磁基 | `MARIE_*.mat` |
| `BASIS_runner` | 生成电磁场基、MRGF 算子、UISNR/UITXE；表面支撑基还生成理想电流模式 | 合适的 basis 输入和支撑几何 | `data/bases/` 下的指定文件 |
| `MRGF_runner` | 使用预计算基和压缩算子的快速 WSVIE | 先由 `BASIS_runner` 生成兼容 basis 文件 | `MRGF_*.mat` |
| `CO_SIMULATION_runner` | 仅执行电路联合仿真与 PSO 调谐/匹配/去耦 | 预计算 Y 参数和带集总元件定义的线圈 JSON | `CoSimulation_*.mat` |

### 9.1 BASIS_runner

源码支持两类基：

```matlab
geo_flag = 2;  % 表面支撑基
geo_flag = 3;  % 偶极子支撑基
```

它会保存总电场基、总磁场基、MRGF 算子、UISNR、UITXE，以及表面支撑基对应的理想电流模式。

### 9.2 MRGF_runner

该 runner 不能直接替代 `MARIE_runner`。它要求 `BasisFile` 中已经包含：

```text
Ue, Ub, U_hat_inv, S_hat_inv, V_hat_inv, X
```

因此应先生成与人体模型、频率和基设置兼容的预计算文件。

### 9.3 CO_SIMULATION_runner

它用于已有 EM 场和网络参数后的电路优化，主要输出：

```text
YP_s, ZP_s, SP_s, SP_p, M_cal, figure_freq
```

当前脚本内的 `B0`、Y 参数文件和线圈 JSON 同样是硬编码参数，使用前应复制 runner 并修改副本。

> 版本提醒：README 表格提到 `TMD_runner.m`，但当前仓库实际没有该文件。当前可用的独立电路入口是 `CO_SIMULATION_runner.m`。以本地实际文件为准。

## 10. 常见问题

### 10.1 输入 `startup` 后没有输出

这是正常现象。它只把当前仓库递归加入 MATLAB 路径。

### 10.2 Linux 提示找不到 `startup`、`installer` 或 `MARIE_runner`

这些是 MATLAB 命令。应进入 MATLAB GUI，或使用：

```bash
/path/to/MATLAB/R2025b/bin/matlab -batch "cd('/home/<user>/marie-tools'); startup; MARIE_runner"
```

### 10.3 找不到 JSON、模型或线圈文件

首先检查 MATLAB 当前目录：

```matlab
pwd
```

必须为：

```text
/home/<user>/marie-tools
```

其次核验 JSON 中路径是相对于各 `data/` 子目录填写的，而不是任意绝对路径。

### 10.4 没有生成结果文件

检查命令窗口是否出现：

```text
[MARIE 3.0] Simulation completed successfully.
```

再检查：

```matlab
dir(fullfile('data', 'solutions', '*.mat'))
```

如果 runner 在矩阵组装或求解阶段报错，保存步骤不会执行。

### 10.5 许可证错误

在 Linux shell 中检查：

```bash
echo "$MLM_LICENSE_FILE"
```

应为：

```text
27000@<license-server>
```

### 10.6 MEX 或编译器错误

在 MATLAB 中检查：

```matlab
mex -setup C++
disp(mex.getCompilerConfigurations('C++', 'Selected'))
```

安装器已成功运行过时，不要因普通仿真报错而盲目重复编译；应先看错误发生在加载、几何、组装、求解还是后处理阶段。

### 10.7 内存或运行时间较长

人体模型分辨率、线圈网格规模、PWC/PWL 基函数和端口数都会影响资源消耗。首次验证优先使用内置的 2 mm 多层球体和单通道线圈；确认完整流程后再换用 `Hugo_Head_3T.mat` 或多通道线圈。

### 10.8 仿真异常、中断与应急处理

#### 10.8.1 先理解当前版本的“可恢复性”

当前 `MARIE_runner`、`MRGF_runner`、`BASIS_runner` 和 `CO_SIMULATION_runner` 都是在最后阶段才通过 `save(...,'-v7.3')` 写入最终结果。源码没有实现分阶段 checkpoint，也没有“从上一次迭代继续”的恢复入口。

因此：

- 在几何构造、矩阵组装、GMRES 求解、联合仿真或场计算期间中断，通常需要从头重新运行该 case；
- 只有日志、输入 JSON、Runner 副本和已经完整写入的 MAT 文件可用于复盘；
- 不要把一个刚创建、但无法由 `whos('-file',...)` 正常读取的 MAT 当作可恢复结果；
- 对耗时项目，应先做低分辨率试运行，再执行正式 case。

#### 10.8.2 运行前的最低保护措施

每个正式 case 都应使用独立名称，并在运行前保存输入快照。以 `MyCase` 为例：

```bash
cd /home/<user>/marie-tools
mkdir -p runs/MyCase logs
cp --preserve=mode,timestamps data/inputs/inp_MyCase.json runs/MyCase/
cp --preserve=mode,timestamps RUN_MyCase.m runs/MyCase/
```

若 `TMD=1`，自动调谐可能在最终结果保存前改写线圈 JSON；必须额外备份对应线圈文件：

```bash
cp --preserve=mode,timestamps \
  data/coils/wire_files/Custom/MyCoil.json \
  runs/MyCase/MyCoil_before_TMD.json
```

在 MATLAB GUI 中运行前启用日志：

```matlab
cd('/home/<user>/marie-tools')
startup

logFile = fullfile(pwd, 'logs', ...
    ['MyCase_' char(datetime('now','Format','yyyyMMdd_HHmmss')) '.log']);
diary(logFile)
diary on

RUN_MyCase

diary off
```

如果错误导致 `RUN_MyCase` 未走到最后一行，手动执行 `diary off`。日志文件仍会保留错误堆栈和已经完成的阶段。

#### 10.8.3 建模完成后、求解前如何检查

不要第一次就进入完整求解。可只执行加载和几何构造，检查模型、端口和离散规模：

```matlab
cd('/home/<user>/marie-tools')
startup

input_file = 'inp_MyCase.json';
MREDM = load_inputs(input_file);
MREDM = geo_assembly(MREDM, 1);   % 1 = 常规 MARIE 几何模式

visualize_geometry(MREDM)

disp(MREDM.inputs)
disp(MREDM.dimensions)

if ~isempty(MREDM.WIE.coil)
    fprintf('Wire segments: %d\n', MREDM.dimensions.N_wie);
    fprintf('Wire ports: %d\n', MREDM.dimensions.M_ports);
end
if ~isempty(MREDM.SIE.coil)
    fprintf('Surface current DoFs: %d\n', MREDM.dimensions.N_sie);
    fprintf('Surface ports: %d\n', MREDM.dimensions.N_ports);
end
```

重点检查：

- 体模、线圈和屏蔽体的相对位置、尺寸和单位是否合理；
- 线圈是否穿入体模，或与屏蔽体意外重叠；
- 端口数量是否符合设计；
- `N_wie`、`N_sie`、体素网格规模是否超出服务器内存预算；
- JSON 中引用的是本 case 的文件，而不是旧 case 的线圈或 BASIS 文件。

`load_inputs` 会在不存在并行池时启动 `parpool`。只做建模检查后可关闭空闲并行池：

```matlab
p = gcp('nocreate');
if ~isempty(p)
    delete(p)
end
```

这不会删除仿真数据，只会关闭 MATLAB worker 进程。

#### 10.8.4 发生普通 MATLAB 错误时

当 MATLAB 返回到 `>>` 提示符，说明主进程仍可用。此时不要立即再次执行 Runner，也不要先运行 `installer`。按下面顺序处理：

1. 复制完整错误文本，包括第一条错误、所有 `出错 <函数> (第 N 行)` 和调用栈；
2. 记录错误发生前最后一条阶段提示，例如 `Geometry Construction`、`Assembling ...`、`Solving System` 或 `Storing Fields`；
3. 关闭日志 `diary off`，保存当前日志；
4. 检查是否已经产生了结果文件；只有可读取的完整 MAT 才可保留；
5. 判断故障属于输入、几何、MEX、内存、许可证还是数值求解，再针对性修改。

要在下一次运行时停在出错位置，可启用 MATLAB 调试：

```matlab
dbstop if error
RUN_MyCase
```

MATLAB 会在出错行暂停。检查变量后用以下命令关闭断点，避免后续每次都暂停：

```matlab
dbclear if error
```

#### 10.8.5 如何安全停止正在运行的仿真

停止的优先级应从温和到强制。

**MATLAB GUI 仍有响应时**：在 MATLAB Command Window 中按 `Ctrl+C`。对普通 MATLAB 循环通常会很快中断；在 `parfor`、GPU 运算、MEX 调用或大型线性代数调用中，MATLAB 可能要等当前不可中断计算点结束后才响应。等待其回到 `>>`，不要连续多次关闭窗口。

**终端批处理仍有响应时**：在运行 `matlab -batch ...` 的终端按一次 `Ctrl+C`，然后等待 MATLAB 退出并写完终端错误信息。不要在结果处于 `Storing Fields ...` 时直接强杀进程。

**MATLAB 已经返回提示符，但并行 worker 仍占资源时**：

```matlab
p = gcp('nocreate');
if ~isempty(p)
    delete(p)
end
```

**GUI/终端完全无响应时**：新开第二个 SSH 终端，只针对确认无误的 MATLAB 主进程操作。

```bash
ps -u "$USER" -o pid,ppid,etime,%cpu,%mem,cmd | grep '[m]atlab'
```

先向明确的主进程 PID 发送中断信号，例如 PID 为 `123456`：

```bash
kill -INT 123456
```

等待一段时间后仍未退出，才使用正常终止信号：

```bash
kill -TERM 123456
```

`kill -KILL 123456` 只能作为最后手段。它不会执行 MATLAB 清理逻辑，可能留下并行 worker、占用的 GPU/内存，以及不完整的 MAT 文件。不要使用按进程名批量终止的命令，以免误杀其他人的仿真。

#### 10.8.6 中断或崩溃后怎样恢复

重新打开 MATLAB 后，先检查现有输出，不要立即覆盖：

```matlab
cd('/home/<user>/marie-tools')
resultFile = fullfile(pwd, 'data', 'solutions', 'MARIE_1_inp_MyCase.mat');

if isfile(resultFile)
    whos('-file', resultFile)
else
    fprintf('No result file was created.\n')
end
```

如果 `whos('-file',...)` 报错、文件大小明显异常，或其中没有顶层 `solution`，将该文件移入 `data/_trash/<时间戳>/` 隔离，保留日志后从头运行。不要直接覆盖失败文件，否则会失去排错证据。

如果失败发生在 `TMD=1` 的联合仿真阶段，比较活动线圈 JSON 与 `*_before_TMD.json` 备份。未确认优化是否完成前，不要把被回写的元件值当作正式设计。

#### 10.8.7 断开 SSH、关闭 MobaXterm 或网络中断

通过 X11 打开的 MATLAB GUI 与 SSH 会话绑定。关闭 MobaXterm、网络断开或 X11 连接异常时，GUI 会话可能退出或无法可靠交互。耗时正式仿真建议改用后台批处理，并将日志写入明确文件：

```bash
cd /home/<user>/marie-tools
mkdir -p logs
nohup /path/to/MATLAB/R2025b/bin/matlab -batch \
  "cd('/home/<user>/marie-tools'); startup; RUN_MyCase" \
  > logs/MyCase_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo $!
```

最后一行打印的数字是后台 MATLAB 的 PID，应记录到 case 目录。断线后重新登录可查看：

```bash
ps -p <PID> -o pid,etime,%cpu,%mem,cmd
tail -n 50 logs/MyCase_<时间戳>.log
```

当日志包含 `[MARIE 3.0] Simulation completed successfully.` 和 `[Saved]` 时，才认为后台 case 完成。

#### 10.8.8 常见突发情况速查

| 情况 | 立即动作 | 后续处理 |
| --- | --- | --- |
| JSON/模型找不到 | 停止，不要重装 | 检查 MATLAB 当前目录、JSON 文件名和 `data/` 相对路径 |
| 几何图明显错位 | 不进入组装/求解 | 检查单位、坐标系、线圈与体模文件的对应关系 |
| MEX `GLIBCXX` 或 `.mexa64` 错误 | 保存完整报错 | 使用与 MATLAB 兼容的编译器重编译；不要只替换系统库 |
| 内存不足或系统变慢 | 尽量 `Ctrl+C`，避免强杀 | 先关闭并行池、降低分辨率或改用 PWC；检查 `free -h` 和磁盘空间 |
| 迭代时间异常长/不收敛 | 记录端口号、迭代次数和残差 | 用更小案例复现，核对端口、材料、网格与预条件设置 |
| 许可证 Error 5 | 检查 `MLM_LICENSE_FILE` 和服务状态 | `source ~/.bashrc`；检查 `matlab-licensing.service` |
| SSH 断开 | 重新登录后先检查 PID 和日志 | 正式长任务使用 `nohup` 批处理，不依赖 GUI 会话 |
| 磁盘满或保存失败 | 立刻停止提交新任务 | `df -h`、隔离无用派生结果；不要删除未核对的 BASIS/正式 MAT |
| `TMD=1` 后失败 | 不要直接重跑 | 比较、备份或恢复线圈 JSON，避免在未知元件状态上继续优化 |
| MATLAB GUI 无响应 | 新 SSH 终端确认 PID | 依次 `INT`、`TERM`，仅最后使用 `KILL` |
| 结果图异常但 Runner 成功 | 不要立即发表/比较 | 检查 S 参数、场单位、掩膜、端口模式与网格收敛性 |

## 11. 结果数据清理

### 11.1 清理原则

清理前先把数据分为四类：

| 类型 | 示例 | 建议 |
| --- | --- | --- |
| 原始输入 | JSON、MSH、phantom MAT、Runner | 保留并纳入版本管理 |
| 原始结果 | `MARIE_*.mat`、`MRGF_*.mat`、BASIS MAT | 正式 case 至少保留一份 |
| 派生结果 | PNG、FIG、`Processed_*.mat` | 可按需要重新生成 |
| 失败或过期数据 | 损坏 MAT、旧测试、错误参数结果 | 先隔离，复核后删除 |

不要直接清空 `data/`，也不要删除以下内容来解决普通仿真错误：

- `src/` 源码；
- `data/bodies/` 中仍被输入 JSON 引用的体模；
- `data/coils/` 中仍被项目使用的网格和电路 JSON；
- 已编译的 `.mexa64`；
- 正在运行的仿真所使用或写入的文件。

### 11.2 先统计磁盘占用

在 Linux shell 中进入仓库：

```bash
cd /home/<user>/marie-tools
du -sh data/solutions data/bases data/bodies data/coils
du -ah data/solutions | sort -h | tail -n 30
du -ah data/bases | sort -h | tail -n 30
```

在 MATLAB 中查看结果大小和修改时间：

```matlab
cd('/home/<user>/marie-tools');

files = dir(fullfile(pwd,'data','solutions','*.mat'));
T = struct2table(files);
if ~isempty(T)
    T.SizeGB = T.bytes/1024^3;
    disp(sortrows(T(:,{'name','SizeGB','date'}),'SizeGB','descend'));
end
```

不要仅根据文件名判断是否可删。先关联对应输入 JSON、Runner、日志和研究记录。

### 11.3 识别失败或损坏的 MAT 文件

仿真在最终 `save` 之前失败时通常不会生成新 MAT；但以下情况仍可能留下问题文件：

- 上一次成功运行留下的同名旧结果；
- 保存过程中断电或进程被终止，产生不完整 MAT；
- 字段缺失，说明运行没有完成预期阶段；
- 端口数量或体素尺寸与当前 case 不一致。

先做轻量检查：

```matlab
root = fullfile(pwd,'data','solutions');
files = dir(fullfile(root,'*.mat'));

for k = 1:numel(files)
    p = fullfile(files(k).folder,files(k).name);
    fprintf('\n[%s] %.3f GB\n',files(k).name,files(k).bytes/1024^3);
    try
        w = whos('-file',p);
        fprintf('  Top-level variables: %s\n', ...
            strjoin({w.name},', '));
    catch ME
        fprintf(2,'  INVALID/UNREADABLE: %s\n',ME.message);
    end
end
```

对准备保留的常规结果逐个深度检查；一次只加载一个大型文件：

```matlab
candidate = fullfile(pwd,'data','solutions', ...
    'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat');

R = load(candidate,'solution');
assert(isfield(R.solution,'netp'));
assert(isfield(R.solution.netp,'SP_s'));
assert(isfield(R.solution,'h_field'));
assert(isfield(R.solution,'snr_field'));
assert(isequal(size(R.solution.netp.SP_s),[8 8]));
clear R;
```

对于 BASIS：

```matlab
Q = load(fullfile(pwd,'data','bases', ...
    'Sphere200_5T_PWC_CylSupport_UISNR.mat'),'BASIS');
assert(isfield(Q.BASIS,'UISNR'));
assert(isfield(Q.BASIS,'wUISNR'));
assert(isfield(Q.BASIS,'Substrate'));
clear Q;
```

### 11.4 先隔离，不立即删除

推荐把疑似失败、过期或不再需要的数据移动到带时间戳的隔离目录：

```matlab
trashRoot = fullfile(pwd,'data','_trash', ...
    char(datetime('now','Format','yyyyMMdd_HHmmss')));
mkdir(trashRoot);

solutionsRoot = fullfile(pwd,'data','solutions');
candidate = fullfile(solutionsRoot, ...
    'MARIE_1_failed_test.mat');

assert(isfile(candidate),'待隔离文件不存在');
assert(startsWith(string(candidate),string(solutionsRoot)+filesep), ...
    '拒绝移动 data/solutions 之外的文件');

info = dir(candidate);
fprintf('Move %.3f GB: %s\n',info.bytes/1024^3,candidate);
movefile(candidate,trashRoot);
```

Linux shell 中移动单个明确文件：

```bash
cd /home/<user>/marie-tools
stamp=$(date +%Y%m%d_%H%M%S)
mkdir -p "data/_trash/$stamp"
mv -- "data/solutions/MARIE_1_failed_test.mat" "data/_trash/$stamp/"
```

隔离后重新运行后处理或正式 case，确认没有脚本依赖该文件，再决定是否永久删除。

### 11.5 永久删除隔离数据

先再次列出隔离内容和总大小：

```bash
cd /home/<user>/marie-tools
find data/_trash -maxdepth 2 -type f -printf '%TY-%Tm-%Td %TH:%TM %12s %p\n'
du -sh data/_trash
```

只删除已经核对过的明确文件：

```bash
rm -- "data/_trash/20260805_210000/MARIE_1_failed_test.mat"
```

删除一个已核对的空隔离目录：

```bash
rmdir -- "data/_trash/20260805_210000"
```

不要使用以下宽泛命令：

```text
# Public snapshot: destructive cleanup command removed; use an exact reviewed manifest.
# Public snapshot: destructive cleanup command removed; use an exact reviewed manifest.
find data -delete
```

在 MATLAB 中永久删除单个明确文件：

```matlab
candidate = fullfile(pwd,'data','_trash','20260805_210000', ...
    'MARIE_1_failed_test.mat');

assert(isfile(candidate));
fprintf('Deleting: %s\n',candidate);
delete(candidate);
```

### 11.6 清理不需要的派生图和后处理文件

图片和派生 MAT 通常可以从原始结果重新生成，但清理前应确认后处理脚本仍然存在。

先隔离整个明确的图像目录：

```matlab
figureDir = fullfile(pwd,'data','solutions','figures_old_test');
trashRoot = fullfile(pwd,'data','_trash', ...
    char(datetime('now','Format','yyyyMMdd_HHmmss')));
mkdir(trashRoot);

assert(isfolder(figureDir));
movefile(figureDir,trashRoot);
```

对于 `Processed_*.mat`，先确认其中没有唯一的 ROI、人工标注或统计结果。如果可以由当前后处理脚本完整重建，才按同样方式隔离。

### 11.7 清理 BASIS 文件前的检查

BASIS 文件通常很大，但生成成本也很高。只有满足以下条件时才建议清理：

1. 已确认没有 MRGF 输入 JSON 引用该文件；
2. 已确认没有后处理脚本使用其 UISNR、wUISNR 或 Substrate；
3. 保留了生成它的体模、支撑网格、输入 JSON 和 Runner；
4. 接受未来重新生成所需的计算时间。

搜索引用：

```bash
cd /home/<user>/marie-tools
rg -n "Sphere200_5T_PWC_CylSupport_UISNR.mat" .
```

若服务器没有 `rg`：

```bash
grep -R -n -- "Sphere200_5T_PWC_CylSupport_UISNR.mat" .
```

### 11.8 失败自动调谐后的清理与恢复

`TMD=1` 可能在最终 MAT 保存前就改写线圈 JSON。因此失败运行的清理不能只删除 MAT 和日志，还要核对线圈 JSON。

如果保存了调谐前副本，可恢复：

```matlab
beforeJson = fullfile(pwd,'data','solutions', ...
    'Sphere8Rx_before_optimization.json');
activeJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere8Rx_R115_H140_Span50.json');

assert(isfile(beforeJson));
copyfile(beforeJson,activeJson,'f');
```

恢复前先把失败运行改写后的 JSON 移入隔离目录，避免丢失排错证据。

### 11.9 推荐的保留策略

每个正式 case 建议保留：

- 一个未经修改的输入包；
- 调谐前和调谐后的线圈 JSON；
- 最终原始 `MARIE_*.mat`；
- 对应的 BASIS/UISNR 文件；
- Runner 和后处理脚本；
- 日志与最终图片；
- 一个包含核心指标的轻量 `Processed_*.mat`。

可以优先清理：

- 明确损坏且无法加载的 MAT；
- 已被正式结果替代的短流程测试；
- 可重复生成的旧 PNG/FIG；
- 无脚本引用且确认不再使用的中间 BASIS；
- 重复下载或重复复制的结果文件。

## 12. 推荐的实际工作顺序

1. 用内置 `inp_MSphere_HeadCoil1z.json` 跑通 `MARIE_runner`；
2. 确认结果文件存在并查看 `fieldnames(solution)`；
3. 绘制内置算例的 SNR、B1- 和 S 参数；
4. 复制 JSON 与 runner，为研究任务建立独立文件；
5. 一次只修改一类输入（模型、线圈或 B0），并保留每次运行的 JSON；
6. 将 JSON、runner 副本和结果文件使用相同 case 名称管理；
7. 只有明确需要重复加速时，才进入 `BASIS_runner` + `MRGF_runner` 流程；
8. 只有已有网络参数、且目标是调谐匹配时，才单独使用 `CO_SIMULATION_runner`。

## 13. 最小命令清单

GUI 会话：

```matlab
cd('/home/<user>/marie-tools')
startup
MARIE_runner

resultFile = fullfile('data', 'solutions', ...
    'MARIE_1_inp_MSphere_HeadCoil1z.mat');
whos('-file',resultFile)
S = load(resultFile,'solution');
solution = S.solution;
fieldnames(solution)
```

SSH 批处理：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
cd /home/<user>/marie-tools
/path/to/MATLAB/R2025b/bin/matlab -batch "startup; MARIE_runner"
```

---

本指南仅描述当前仓库源码能够确认的行为。MARIE 属于研究型内部电磁仿真套件，README 明确提示代码可能存在缺陷；用于研究数据前，应对模型、网格、收敛性、端口定义和场归一化进行独立验证。
