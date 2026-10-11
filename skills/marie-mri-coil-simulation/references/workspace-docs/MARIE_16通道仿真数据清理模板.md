# MARIE 16 通道仿真数据清理模板

## 1. 使用范围

本文用于清理以下 5 T、16 通道双排 Loop 球形体模案例：

```text
线圈 case：Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5
输入名称：inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90
结果标签：5T_Sphere200_16LoopRx_DoubleRow_H90
```

提供两种方案：

- **方案 1**：只删除仿真结果、缓存和迭代备份，保留几何、电路主 JSON、输入、脚本和文档。
- **方案 2**：删除当前 case 的全部可生成数据，包括结果、缓存、几何、电路主 JSON 和输入；保留源码、脚本、文档、共享体模和 UISNR basis。

以下命令必须在 Linux 服务器上执行。先预览，再确认删除。

## 2. 公共初始化

```bash
cd /home/<user>/marie-tools || exit 1

ROOT="$(pwd -P)"
EXPECTED="/home/<user>/marie-tools"

if [ "$ROOT" != "$EXPECTED" ]; then
    echo "路径错误，停止清理：$ROOT"
    exit 1
fi

CASE="Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5"
INPUT="inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90"
TAG="5T_Sphere200_16LoopRx_DoubleRow_H90"

# 没有匹配文件时，让通配符展开为空，避免把原始模式传给 rm。
shopt -s nullglob
```

路径检查是安全边界，不应删除。若服务器实际项目路径不同，应先人工核对并同时修改 `cd` 和 `EXPECTED`。

## 3. 方案 1：只清除仿真数据

### 3.1 删除内容

- 完整 `TMD=1` 仿真结果；
- 最终 `TMD=0` 固定电路结果；
- Stage A 原始网络 `YPn`；
- 完整 pre-TMD `MREDM` 检查点；
- 各轮独立 TMD MAT 结果；
- 后处理图片、CSV 和汇总文件；
- TMD 过程中产生的线圈 JSON 备份。

### 3.2 保留内容

- 当前 `.msh` 几何；
- 当前活动线圈 `.json`；
- 输入 JSON；
- 建模、运行和后处理脚本；
- 操作指南、体模和 UISNR basis。

注意：当前活动线圈 JSON 可能包含最后一轮 TMD 回写值。若希望从原始种子重新开始，应执行方案 2 后重新生成 case，或者在清理前人工恢复已确认的种子 JSON。

### 3.3 预览

先执行公共初始化，再运行：

```bash
targets=(
    data/solutions/MARIE_*_"${INPUT}"*.mat
    data/solutions/YPn_"${TAG}"*.mat
    data/solutions/MREDM_preTMD_"${TAG}"*.mat
    data/solutions/TMD_"${TAG}"*.mat
    data/coils/wire_files/Custom/"${CASE}".json.before_TMD_*
    data/coils/wire_files/Custom/"${CASE}".json.before_*
    data/coils/wire_files/Custom/"${CASE}".json.after_*
    data/coils/wire_files/Custom/"${CASE}".json.seed_*
    data/coils/wire_files/Custom/"${CASE}".json.failed_*
)

printf '将删除以下文件：\n'
printf '  %s\n' "${targets[@]}"

if [ -d data/solutions/figures_5T_16ch_H90 ]; then
    echo "  data/solutions/figures_5T_16ch_H90/"
fi
```

仔细检查输出。不得出现 8 通道结果、共享体模、UISNR basis 或其他几何 case。

### 3.4 执行

```bash
read -r -p "输入 DELETE 确认清理仿真数据：" answer

if [ "$answer" = "DELETE" ]; then
    rm -f -- "${targets[@]}"
    # 公共技能快照不执行递归删除；请先生成并人工复核精确文件清单，再逐项删除。
    echo "方案 1 清理完成。"
else
    echo "已取消。"
fi
```

清理后，几何和输入仍存在，可以直接重新执行 Stage A：

```matlab
cd('/home/<user>/marie-tools');
startup;
PRECOMPUTE_5T_16CH_EM_NETWORK;
```

## 4. 方案 2：清除当前 case 的全部数据

本方案清除当前 H90/Z25/Span50/Stagger22.5 case 的全部可生成数据，但不删除工作流脚本和文档。

### 4.1 额外删除内容

除方案 1 内容外，还删除：

- 当前线圈 `.msh`；
- 当前活动线圈 JSON；
- 通道布局 CSV；
- 当前输入 JSON；
- 该线圈 JSON 的全部后缀备份。

### 4.2 预览

重新执行公共初始化，再运行：

```bash
targets=(
    data/solutions/MARIE_*_"${INPUT}"*.mat
    data/solutions/YPn_"${TAG}"*.mat
    data/solutions/MREDM_preTMD_"${TAG}"*.mat
    data/solutions/TMD_"${TAG}"*.mat
    data/coils/wire_files/Custom/"${CASE}".msh
    data/coils/wire_files/Custom/"${CASE}".json
    data/coils/wire_files/Custom/"${CASE}"_channel_layout.csv
    data/coils/wire_files/Custom/"${CASE}".json.*
    data/inputs/"${INPUT}".json
)

printf '将删除当前 16 通道 case 的全部数据：\n'
printf '  %s\n' "${targets[@]}"

if [ -d data/solutions/figures_5T_16ch_H90 ]; then
    echo "  data/solutions/figures_5T_16ch_H90/"
fi
```

### 4.3 执行

```bash
read -r -p "输入 DELETE-ALL 确认彻底清理：" answer

if [ "$answer" = "DELETE-ALL" ]; then
    rm -f -- "${targets[@]}"
    # 公共技能快照不执行递归删除；请先生成并人工复核精确文件清单，再逐项删除。
    echo "方案 2 清理完成。"
else
    echo "已取消。"
fi
```

清理后必须重新建立几何、电路和输入：

```matlab
cd('/home/<user>/marie-tools');
startup;
CREATE_5T_16CH_DOUBLE_ROW_CASE;
```

随后按标准三阶段流程运行：

```matlab
PRECOMPUTE_5T_16CH_EM_NETWORK;  % Stage A
RUN_5T_16CH_TMD_ONLY;           % Stage B，可运行多轮
% 接受最终电路后执行 Stage C
```

## 5. 不得删除的共享数据

两种方案均不删除：

```text
data/bases/Sphere200_5T_PWC_CylSupport_UISNR.mat
data/bodies/Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat
```

它们由 8 通道、16 通道和后续对比案例共享。

## 6. 默认保留的脚本与文档

```text
CREATE_5T_16CH_DOUBLE_ROW_CASE.m
PRECOMPUTE_5T_16CH_EM_NETWORK.m
RUN_5T_16CH_TMD_ONLY.m
FINALIZE_5T_16CH_FROM_CHECKPOINT.m
RUN_5T_16CH_SPHERE.m
POST_5T_16CH_SPHERE.m
MARIE_5T_16通道Loop球形体模仿真操作指南.md
MARIE_TMD模块使用教程.md
MARIE_16通道仿真数据清理模板.md
```

这些属于可复用工作流，不属于仿真数据。只有明确决定废弃整个 16 通道工作流时才考虑删除。

## 7. 清理后检查

### 7.1 方案 1

```bash
test -f "data/coils/wire_files/Custom/${CASE}.msh" && echo "几何保留：OK"
test -f "data/coils/wire_files/Custom/${CASE}.json" && echo "电路 JSON 保留：OK"
test -f "data/inputs/${INPUT}.json" && echo "输入保留：OK"

find data/solutions -maxdepth 2 \
  \( -name "*${INPUT}*" -o -name "*${TAG}*" \) -print
```

最后一条命令正常情况下不应再列出该 case 的结果文件。

### 7.2 方案 2

```bash
find data/coils/wire_files/Custom -maxdepth 1 -name "${CASE}*" -print
find data/inputs -maxdepth 1 -name "${INPUT}*" -print
find data/solutions -maxdepth 2 \
  \( -name "*${INPUT}*" -o -name "*${TAG}*" \) -print
```

正常情况下三条命令均不应输出当前 case 的数据。

## 8. 清理其他 16 通道几何

旧的 H140/Z50 或其他几何必须单独修改：

```bash
CASE="对应线圈 case 名称"
INPUT="对应输入文件名，不含 .json"
TAG="对应 YPn/TMD 结果标签"
```

修改后必须先运行预览。不要用 H90 的变量值批量删除所有 `Sphere16Rx*`，否则可能删除仍需保留的几何对照数据。
