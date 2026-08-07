# CST Official Manual Map (outline of all 12 manuals + MRI-relevance tags)

> Source: `D:\ght\softwares\MRI_agent_softwares\Documentation\` (12 PDFs).
> Purpose: rather than reading every manual cover-to-cover, build a lookup map of "which book covers what, which chapter is useful for MRI", enabling **read-on-demand**.
> Relevance: Primary=core MRI reading / Situational=consult for a specific scenario / Low=basically irrelevant (recorded so nothing is missed).
> Read-depth status: Done=closely read and distilled / Outlined=table of contents extracted / Registered=logged only.

---

## Primary manuals

### 1. High Frequency Simulation (119p) [Done]
→ Distilled into [[cst-hf-fundamentals]]. The main arena for MRI coil RF simulation.
Key chapters: ch2 workflow (p19), ch3 solver selection/port types/antenna calculations (p67-117).

### 2. Circuit Simulation & SAM (89p) [Done]
→ Distilled into [[cst-circuit-sam]]. Tuning/matching + co-sim + SAM multi-task.
Key chapters: ch2 circuit building/tasks (p11), ch4 co-sim (p63), ch6 3D embedding + AC combine field output (p74).

### 3. Getting Started (72p) [Outlined] — pending close-read (basic-operations dictionary)
- ch3 User Interface (p14): interface/ribbon/navigation tree
- **ch4 Structure Modeling (p23)**: Primary — the core of modeling: basic shapes, boolean, pick points/edges/faces, local WCS, **History List/History Tree (p45)**, curve/trace/bond wire creation, local modifications
- **ch5 Post-Processing (p58)**: Primary — Parametric Result Storage, **Result Templates framework (p60)**, preloaded templates
> Use: the authoritative reference for modeling operations/history syntax/post-processing templates during reproduction. The history commands behind our dipole reproduction all trace back to this.

---

## Situational manuals

### 4. Low Frequency Simulation (97p) [Outlined] — CST EM STUDIO (potentially relevant to gradient coils/static field)
- ch2 workflow (p14): **Define Coils (p21)** [situational], boundaries/symmetry, tetrahedral/hexahedral/planar magnetostatic solving
- ch3 solvers: **Magnetostatic Solver (p62)** — nonlinear ferromagnetics, **inductance calculation (p63)**, **Current/Voltage Coils, Coil Segments (p63-66)**, permanent magnets, Current Paths, **Homogeneous Magnetic Field (p68)**; Electrostatic/Stationary Current/LF Freq/LF Time/Partial RLC/Drift-Diffusion solvers
> Mapping to MRI: the static main field B0, **gradient coils**, shimming — close-read this if the project extends into gradient/shimming hardware. The RF coil itself uses the HF manual.

### 5. Thermal and Mechanical Simulation (72p) [Outlined] — CST MPHYSICS (MRI System has a thermal task)
- ch2: structural-mechanics workflow; **Coupled EM-CHT Simulation (p26)** [situational] — one-way/two-way EM-thermal coupling, Loss Import
- ch3: Mechanical / **Thermal & Conjugate Heat Transfer solvers (p43)**, material thermal properties, thermal boundaries, point/surface/3D thermal monitors, steady-state/transient thermal solver parameters
> Mapping to MRI: **SAR-induced tissue heating**, coil-loss heat generation. Directly corresponds to the MRI System case's thermal task; close-read the EM-CHT chapter when reproducing MRI System in Phase 2.

### 6. Cable Simulation (78p) [Registered] — CST Cable Studio
Cable-bundle simulation; ch3 Examples (p29). Low MRI relevance (unless modeling coil feed cables/EMC). Registered only.

### 7. PCB and Package Simulation (102p) [Registered] — CST PCB Studio
PCB/package SI/PI/IR-drop; ch3 Examples (p44). Low MRI relevance. Registered only.

---

## Basically irrelevant (registered for reference, not read)

### 8. Charged Particle Simulation (105p) [Registered] — CST Particle Studio, particle beams/electron guns, unrelated to MRI.
### 9. FEST3D User Manual (633p) [Registered] — a dedicated waveguide-filter tool, unrelated to MRI.
### 10. SPARK3D User Manual (170p) [Registered] — multipactor/breakdown analysis, unrelated to MRI.
### 11. Release Notes (5p) [Registered] — 2024 version changes, skim if needed.

---

## 检索策略（怎么用这张地图）
1. **建模/history/后处理模板问题** → Getting Started ch4/ch5。
2. **RF 求解器/端口/mesh/farfield** → HF 手册（已有蒸馏笔记，笔记不够再回原文）。
3. **调谐匹配/co-sim/AC combine/SAM 任务** → Circuit&SAM 手册（已蒸馏）。
4. **静磁/梯度线圈/电感** → Low Frequency 手册 ch3。
5. **SAR 升温/热耦合** → Thermal 手册 ch2-3。
6. 具体对话框/API 细节 → Online Help（见阶段1 [[cst-help-index]]，待建）。

## 待细读清单（阶段2按需触发）
- [ ] Getting Started ch4/ch5 —— 复现第一个 case 前快速细读（建模+后处理模板）。
- [ ] Thermal ch2-3 EM-CHT —— 复现 MRI System 热任务时。
- [ ] Low Frequency ch3 coils —— 若扩展到梯度/静磁场硬件时。
