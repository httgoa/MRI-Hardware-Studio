# MARIE 3.0 帮助文档（中文）

MARIE（Magnetic Resonance Integral Equation Suite，磁共振积分方程套件）是一个面向 MRI 电磁仿真的研究型工具箱。它使用 MATLAB 作为主控环境，并通过 C++ MEX 例程加速积分方程组装与计算。

项目主页：https://cmr.cloudmrhub.com/apps/marie/

## 1. 目录结构

| 目录 | 用途 |
| --- | --- |
| `src/` | MARIE 的核心源代码。 |
| `src/src_geometry/` | GMSH 表面网格和导线线圈格式的解析与几何构建。 |
| `src/src_integral_equations/` | 积分方程实现，包括 WIE、SIE、VIE、WVIE、SVIE 和 WSVIE。 |
| `src/src_solver/` | 迭代求解器（GMRES），并支持 GPU 加速。 |
| `src/src_mathematics/` | SVD、Tucker、Tensor Train（张量列车）及 ACA 矩阵压缩方法。 |
| `src/src_physics/` | 电磁场、SNR 和相关物理量的计算。 |
| `src/src_utils/` | JSON 输入、数据管理及通用工具函数。 |
| `src/src_runners/` | 仿真运行入口脚本。 |
| `data/` | 输入模型、预计算基、仿真结果等数据。 |

`data/` 下的主要子目录：

| 目录 | 内容 |
| --- | --- |
| `data/bases/` | 电磁基文件，包括 UISNR 与 MRGF 相关数据。 |
| `data/bodies/` | 人体模型或散射体体素模型，通常为 `.mat` 文件。 |
| `data/coils/` | 线圈、导线、屏蔽和基函数支撑面网格及配置。 |
| `data/inputs/` | JSON 格式的仿真输入文件。 |
| `data/solutions/` | 已完成仿真的结果文件。 |

## 2. 安装与初始化

### 软件要求

1. MATLAB R2023a 或更高版本。
2. 可用的 C++ 编译器，用于构建 MEX 文件。
3. 仓库内已包含 GMSH 2.8.5。

### 首次编译

以下命令必须在 **MATLAB 命令窗口** 中执行，而不是 Linux Bash 终端：

```matlab
cd('/home/<user>/marie-tools')
mex -setup C++
installer
startup
```

说明：

- `installer` 编译全部 C++ MEX 加速例程；正常情况下只需首次安装时运行一次。
- `startup` 将工具箱及其子目录加入当前 MATLAB 搜索路径。每次新开 MATLAB 会话后都需要运行一次。
- 若更换 MATLAB 版本、编译器或 MEX 文件损坏，需要重新运行 `installer`。

Linux 服务器使用网络许可证时，启动 MATLAB 前需要使许可证地址可见，例如：

```bash
export MLM_LICENSE_FILE=27000@<license-server>
/path/to/MATLAB/R2025b/bin/matlab
```

## 3. 基本使用流程

1. 在 `data/inputs/` 中选择一个 JSON 输入文件。
2. 修改运行脚本中的 `input_file`，或根据研究目标创建新的 JSON 输入文件。
3. 在 MATLAB 中进入工具箱根目录并运行 `startup`。
4. 选择相应的运行入口脚本。
5. 在 `data/solutions/` 或指定的基文件位置检查输出。

最小示例：

```matlab
cd('/home/<user>/marie-tools')
startup
MARIE_runner
```

默认的完整仿真示例使用 `inp_MSphere_HeadCoil1z.json`。该文件位于 `data/inputs/`。

## 4. 运行入口（Runners）

| 脚本 | 用途 |
| --- | --- |
| `MARIE_runner.m` | 执行完整 WSVIE 仿真。 |
| `BASIS_runner.m` | 生成电磁基、UISNR、理想电流模式以及 MRGF 算子。 |
| `MRGF_runner.m` | 执行基于 MRGF 的降阶 WSVIE 仿真，以缩短重复计算时间。 |
| `TMD_runner.m` | 基于预先计算的 Y 参数进行自动调谐、匹配、去耦、前置放大器去耦和失谐优化。 |

### 4.1 `MARIE_runner`：完整 WSVIE 仿真

运行：

```matlab
MARIE_runner
```

工作流程：

1. 读取用户指定的输入 JSON 文件。
2. 构建线圈、人体及离散化几何。
3. 组装 WSVIE（Wire-Surface-Volume Integral Equation）算子。
4. 求解线性方程组。
5. 执行电路协同仿真，例如调谐、匹配和去耦。
6. 计算电磁场、SNR 和发射相关量。
7. 保存结果。

输出文件默认保存为：

```text
data/solutions/MARIE_<tmd>_<输入文件名>.mat
```

其中 `<tmd>` 是输入配置中的协同仿真相关标志。

### 4.2 `BASIS_runner`：生成电磁基、UISNR 和 MRGF

运行前，在 `src/src_runners/BASIS_runner.m` 中设置：

```matlab
input_file = 'inp_Duke_StadiumTriangular.json';
geo_flag = 2;
```

然后运行：

```matlab
BASIS_runner
```

`geo_flag` 的含义：

| 值 | 基类型 |
| --- | --- |
| `2` | 表面支撑电磁基（surface-supported basis）。 |
| `3` | 偶极子支撑电磁基（dipole-supported basis）。 |

该流程会组装 VIE 算子、生成入射场基、逐个求解基向量对应的 VIE，并保存总电场基、总磁场基、MRGF 算子、UISNR、UITXE；表面支撑基还包括理想电流模式。

### 4.3 `MRGF_runner`：基于 MRGF 的快速仿真

当已存在与人体模型和激励设置匹配的电磁基/MRGF 文件时，运行：

```matlab
MRGF_runner
```

它用于降阶 WSVIE 计算。使用前请确认输入 JSON 中引用的基文件与当前人体模型、频率、网格和线圈设置一致；不一致会使结果不可靠。

### 4.4 `TMD_runner`：调谐、匹配和去耦优化

运行：

```matlab
TMD_runner
```

该入口基于预计算的 Y 参数，针对接收、发射或收发一体线圈执行自动调谐（Tuning）、匹配（Matching）、去耦（Decoupling）、前置放大器去耦和失谐（Detuning）优化。它需要相应的线圈网络和外部求解器数据已经准备好。

## 5. 输入文件

MARIE 的仿真设置由 `data/inputs/` 内的 JSON 文件控制。完整 WSVIE 仿真的输入至少涉及：

1. 主磁场强度。
2. VIE 基函数类型：PWC 或 PWL。
3. 人体模型。
4. 线圈模型，可为空。
5. 导线模型，可为空。
6. 屏蔽模型，可为空。
7. 电磁基的支撑衬底；在完整 WSVIE 计算中通常忽略。
8. 协同仿真启用标志。
9. 电磁基/MRGF 文件的保存或读取位置；当未提供线圈、导线或屏蔽模型时，可作为外部激励使用。

建议从已有的输入文件复制并按需修改，先保留原有字段名和数据结构。修改前可备份文件，例如：

```matlab
copyfile('data/inputs/inp_MSphere_HeadCoil1z.json', ...
         'data/inputs/inp_my_case.json')
```

然后在运行脚本中指定：

```matlab
input_file = 'inp_my_case.json';
```

## 6. 常见操作

### 新开 MATLAB 后如何继续使用

```matlab
cd('/home/<user>/marie-tools')
startup
```

通常不需要重复运行 `installer`。

### 如何确认 MEX 编译正常

在 MATLAB 中执行：

```matlab
which solve_st
```

应返回 `Cpp_Assembly/bin/solve_st.mexa64`。若提示 MEX 无效，通常是 MATLAB 自带的 C++ 运行库与编译该文件的 GCC 版本不兼容；应使用兼容编译器重新运行 `installer`，不要替换 MATLAB 安装目录中的动态库。

### 如何避免在错误目录运行

所有 Runner 均假定当前工作目录为 MARIE 根目录。运行前执行：

```matlab
cd('/home/<user>/marie-tools')
startup
```

## 7. 术语说明

| 缩写 | 含义 |
| --- | --- |
| WIE | Wire Integral Equation，导线积分方程。 |
| SIE | Surface Integral Equation，表面积分方程。 |
| VIE | Volume Integral Equation，体积分方程。 |
| WSVIE | Wire-Surface-Volume Integral Equation，导线-表面-体积分方程。 |
| MRGF | 用于加速仿真的模型降阶 Green 函数方法。 |
| UISNR | Ultimate Intrinsic SNR，极限本征信噪比。 |
| UITXE | Ultimate Intrinsic Transmit Efficiency，极限本征发射效率。 |
| PWC | Piecewise Constant，分段常数基函数。 |
| PWL | Piecewise Linear，分段线性基函数。 |
| MEX | MATLAB 可加载的已编译 C/C++ 扩展模块。 |

## 8. 注意事项

- MARIE 是研究用途的内部电磁仿真工具，结果应通过网格收敛性、物理合理性和必要的实验数据进行验证。
- 完整 WSVIE 仿真可能占用大量内存和 CPU 时间；并行池工作进程数应与服务器可用内存相匹配。
- `startup` 仅在当前 MATLAB 会话有效；建议将其加入个人 MATLAB 启动脚本，或在每次运行前显式执行。
- 仓库 README 中标注的独立 `doc/` 文档目录仍处于“Coming Soon”状态；本文件依据当前 README、`startup.m` 和各 Runner 源码注释整理。

## 9. 许可证与声明

MARIE 采用 MIT License 发布。本工具仅供研究使用；项目维护者不对软件缺陷或由此产生的结果承担责任。

