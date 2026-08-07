# MRI Coil Design Workflow Skill 架构说明

本文档说明最终版 `mri-coil-design-workflow` 的目录职责、内容来源和后续扩展规则。最终版采用 `skills_psh` 的分层架构，合入 `skills_ght` 的 artifact-first 执行核心、脚本、模板和增强知识库。

## 合并原则

- **入口规则采用 `skills_ght`**：`SKILL.md` 使用完整 artifact-first 流程，即离线生成 `.bas`、lint、review、批量执行、L0-L4 修复阶梯。
- **目录架构采用 `skills_psh`**：继续使用 `foundations/`、`driving/`、`recipes/`、`building-blocks/`、`pitfalls/`、`notes/`、`design-notes/` 等分层。
- **`skills_psh` 独有内容保留**：例如优化 recipe、SAR 导出旧路线、CST 官方文档 map、design notes、旧版 `build_dipole.py`。
- **`skills_ght` 独有内容保留**：例如 `templates/`、artifact pipeline、error-fixes、data-prep recipe、官方组件复现学习 recipe、repro-07/08/09、增强脚本。
- **冲突文件以 `skills_ght` 新版为主**；`skills_ght`/`skills_psh` 两份原始目录只作为一次性合并输入，合并完成后不再被引用、也不再保留过渡性备份副本。全局 SOP 规则进入 `foundations/cst-simulation-sop.md`；项目级、更具体的批处理 SOP 可由对应 recipe 模块吸收并声明优先级，例如 data-prep D1 使用 `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md` + `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md`。

## 目录职责

| 目录 | 放什么 | 不放什么 |
| --- | --- | --- |
| `foundations/` | 跨任务稳定规则：物理、红线、SOP、验证标准 | 单个 case 的临时笔记 |
| `driving/` | 如何操作 CST/MCP：工具 map、参数策略、artifact pipeline、官方文档索引 | 具体项目结果 |
| `recipes/` | 可执行任务流程，必须有清晰输入、步骤、验证门、输出 | 尚未验证的开放式想法 |
| `building-blocks/vba-blocks/` | 从真实项目提炼的已验证整块 VBA ground truth | 新拓扑草稿 |
| `building-blocks/vba-knowledge/` | Tier-B few-shot 单元知识：图元、端口、solver、schematic、field export | 完整 task recipe |
| `templates/` | Tier-A 确定性 Jinja2 VBA 模板 | 手写的一次性 VBA |
| `scripts/` | 可复用 Python 工具：render/lint/execute/repair/postproc | 项目专属临时脚本 |
| `pitfalls/` | 已验证坑点和 L2 error-fix 签名 | 普通背景知识 |
| `notes/` | 官方手册蒸馏、复现日志、经验索引 | 可直接执行的主流程 |
| `design-notes/` | roadmap 调研、未固化方向 | 已承诺可执行的步骤 |

## Artifact-First 分支管理

建模流程按三个层级管理：

1. **Tier A: `templates/`**
   - 已知、稳定、参数化的建模步骤放这里。
   - 通过 `scripts/render_templates.py` 渲染。
   - 输出 raw history block，通常没有 `Sub Main`。

2. **Tier B: `building-blocks/vba-knowledge/`**
   - 新拓扑但仍可由标准 CST VBA 片段组合时，放入这里。
   - 通过 `scripts/prepare_tierb_gen.py` 选择相关知识，主 agent 只生成一个 bounded block。
   - 生成后必须走 `scripts/lint_vba.py`。

3. **Tier C: recipe/agent reasoning**
   - 只用于真正的设计决策，例如拓扑选择、调谐方向、solver 权衡。
   - 一旦某条路径被验证，应沉淀回 Tier A 模板、Tier B 知识或 recipe。

## Recipe 添加规则

新增 recipe 时放到最接近的目录：

- `recipes/build/`：从零建模、匹配、demo、结构构建。
- `recipes/b1-sar/`：B1+、SAR、field export、后处理。
- `recipes/inspect/`：未知项目检查、结果树/参数/历史解析。
- `recipes/optimize/`：参数扫描、FoM、优化闭环。
- `recipes/data-prep/`：训练/数据准备记录生产。
- `recipes/paper-reproduction/`：多阶段论文复现（orchestrator + stage-01…stage-99 完整流水线）。
- `recipes/reference-repro/`：单图几何复现、官方组件 replay/learning（单次性学习/参照任务，范围小于 `recipes/paper-reproduction/`，两者不要混淆）。

一个 recipe 晋级为“可执行”前至少应包含：

- 输入条件和默认值策略。
- 要读的 reference 文件。
- 逐步执行顺序。
- 失败时查哪些 pitfalls/error-fixes。
- 输出路径。
- 验证门或 done criteria。

## 脚本添加规则

新增脚本放到 `scripts/`，并遵循：

- 能离线运行的步骤优先离线运行，不占用 CST 会话。
- 默认路径应从 `Path(__file__).resolve().parent.parent` 推导，不写死 `skills_psh`、`skills_ght` 或 `references/`。
- 如果脚本读取知识库：
  - VBA 单元知识读 `building-blocks/vba-knowledge/`。
  - ground-truth 块读 `building-blocks/vba-blocks/`。
  - 错误签名读 `pitfalls/error-fixes.md`。
  - 手册/复现日志读 `notes/`。
- 输出默认写到 `results/<project>/artifacts/`、`log/` 或 `output/`。

## 文档添加规则

- 稳定规则进入 `foundations/`。
- 操作 CST/MCP 的方法进入 `driving/`。
- 已踩坑且可复用的失败模式进入 `pitfalls/`。
- 官方手册蒸馏和 case 复现经验进入 `notes/`。
- 还不能直接执行的研究想法进入 `design-notes/`。

## 重要保留内容

来自 `skills_psh` 的关键保留：

- `recipes/optimize/parameter-sweep-fom-optimization.md`
- `recipes/b1-sar/sar-field-export.md`
- `driving/cst-official-docs-map.md`
- `design-notes/`
- `scripts/build_dipole.py`

来自 `skills_ght` 的关键保留：

- `driving/artifact-pipeline.md`
- `templates/*.vba.j2`
- `scripts/render_templates.py`
- `scripts/lint_vba.py`
- `scripts/batch_execute.py`
- `scripts/apply_error_fix.py`
- `scripts/prepare_tierb_gen.py`
- `scripts/prepare_l3_repair.py`
- `scripts/extract_component_history.py`
- `pitfalls/error-fixes.md`
- `recipes/data-prep/data-prep-complete-case.md`
- `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md`
- `recipes/reference-repro/official-component-repro-learning.md`
- `recipes/reference-repro/paper-figure-device-geometry.md`

## 维护检查清单

每次扩展后检查：

- `SKILL.md` 是否指向新路径。
- 新 recipe 是否有验证门。
- 新脚本是否不依赖旧 `references/` 目录。
- 新模板是否能被 `render_templates.py` 找到。
- 新坑点是否同步到 `pitfalls/mcp-pitfalls.md` 或 `pitfalls/error-fixes.md`。
- 覆盖旧文档时，把旧文档里未被吸收的独有内容**直接合并进当前文件**（而不是另存一份备份/存档副本）；确认后旧文档直接删除，不留过渡性引用。
- 全局逐 case SOP 维护在 `foundations/cst-simulation-sop.md`。项目级 SOP 内容应整合进最接近的 recipe 模块并在入口中声明优先级；不要留下没有路由的平行 SOP 文档。Data-prep D1 的当前上游 SOP 是 `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md`，其关键 SAR/record/case-matrix规则已由 D1 模块承接。
