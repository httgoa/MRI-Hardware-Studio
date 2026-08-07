# CST Official Docs Map — PDF manuals + HTML Online Help

When a CST behavior/setting/solver choice is unclear, **query the official CST 2024 docs instead of guessing**. Three tiers, use together:
1. **PDF manuals** (`Documentation/`) — concepts, workflows, solver theory, GUI settings, physics (the "why/what"). Broad, chapter-level.
2. **HTML Online Help** (CST install, 5362 pages) — per-object / per-dialog / per-method detail incl. VBA & Python API pages (the fine-grained "what/how"). See "HTML Online Help" section below.
3. **Vendored API/VBA refs** (`vendor/cst-runtime-cli/devkit/references/cst-official-api-reference.md`, `vba-official-reference.md`) — quick callable Python/VBA signatures.

**PDF location (this machine):** `C:\Users\psh21\Desktop\project\CST+Agent_claude\Documentation\` — 11 PDFs, CST Studio Suite **2024.0** (dated 8/2/2023), ~1550 pages total.

> Warning: `Documentation\cst_studio_suite_help.htm` is **NOT content** — it's an orphaned RoboHelp launcher (its JS deps aren't in that folder, so it won't open there). The real HTML help is the install's `Online Help\` tree (below).

## How to read them (rendering is NOT available; text extraction IS)

`pdftoppm`/poppler image rendering is missing, so the Read tool CANNOT render these PDF pages. Extract **text** instead:
- Quick: `pdftotext -f <first> -l <last> "<file>.pdf" - | less` (pdftotext is on PATH).
- Robust (handles the encoding + gives layout): PyMuPDF via the post-processing python. **Force UTF-8** or Windows GBK console throws `UnicodeEncodeError`:
  ```bash
  PYTHONIOENCODING=utf-8 <py> - <<'PY'
  import sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
  import fitz
  d=fitz.open(r"Documentation\CST Studio Suite - High Frequency Simulation.pdf")
  print(d[102].get_text())          # 0-indexed → prints printed page 103
  PY
  ```
  (`<py>` = `C:\ProgramData\anaconda3\envs\Cst_help\python.exe` or the MCP `.venv`; PyMuPDF `fitz` is installed there. **Page numbers below are the manual's printed page; `doc[i]` is 0-indexed, so printed page N = `doc[N-1]`** — verified: `doc[85]` returns printed p86.)
- Most manuals have **no embedded bookmarks** (only FEST3D & SPARK3D do); find a topic by scanning the printed "Table of contents" on sheets 3–5, or grep every page's text for a term.

## The 11 manuals — what each covers

| Manual (PDF) | Pages | Use it for |
| --- | --- | --- |
| **High Frequency Simulation** | 119 | **PRIMARY for MRI coils.** MWS solvers (Time/Frequency/Eigenmode/Integral/TLM), ports, boundaries, monitors, adaptive mesh, **SAR/loss**, farfield, sweeps/optimization. |
| **Circuit Simulation and SAM** | 89 | **PRIMARY for co-sim.** CST Design Studio / Schematic: tasks, **AC + Combine Results** (antenna calc from network excitation), Signal excitation setup, parameter sweep/optimization, SAM assemblies. |
| **Getting Started** | 72 | Install/licensing, GUI basics, geometry modeling, history list/tree, **Post-Processing templates & parametric result storage**. |
| **Thermal and Mechanical Simulation** | 72 | MPhysics: thermal steady/transient, CHT, mechanical; **EM→thermal (bi-directional) link** — for SAR-driven heating. |
| **Low Frequency Simulation** | 97 | EM Studio: magneto/electrostatic, LF frequency domain, coil segments, inductance, EQS/DS co-sim. |
| **PCB and Package Simulation** | 102 | PCB Studio: SI/PI, package. Not MRI-core. |
| **Cable Simulation** | 78 | Cable Studio: SI/EMC of cable harnesses. Not MRI-core. |
| **Charged Particle Simulation** | 105 | Particle Studio: PIC, tracking, guns. Not MRI-core. |
| **SPARK3D User Manual** | 170 | RF breakdown (corona/multipactor). Has bookmarks + tutorial. Not MRI-core. |
| **FEST3D User Manual** | 634 | Waveguide-component analysis. Has bookmarks + elements DB. Not MRI-core. |
| **Release Notes** | 17 | 2024 version changes. |

## Problem → manual → page (verified page numbers)

**High Frequency Simulation** (printed page):
- Which solver to use — p67; **Frequency Domain Solver** — p73 (FD workflow summary near p84); Time Domain — p70; **Eigenmode Solver** — p94 (resonance/mode frequencies).
- Integral Equation p84; Multilayer p87; Asymptotic p90.
- **Choosing the Right Port Type** — p102; Antenna Computations / farfield — p103.
- Adaptive Mesh Refinement — p41; Parameterization — p47; Parameter Sweeps — p52; Automatic Optimization — p56; Time-vs-FD comparison — p60.
- **SAR / Specific Absorption** — appears p9 onward, heaviest around solver + post-proc chapters (27 pages mention it); loss monitors near the FD workflow (~p84).
- Tetrahedral (FD/eigenmode) vs Hexahedral (TD) meshing; Symmetry planes p60+; Excitation/ports/monitors/boundaries cluster p9–24 (workflow) and p70+ (per-solver).

**Circuit Simulation and SAM** (printed page):
- Schematic View main concepts — p63; **Transient EM/Circuit Co-Simulation** — p67.
- **AC + Combine Results (Antenna Calculation from network excitation)** — **p86**; defining the **Signal excitation** (amplitude per port, via Define AC-Excitation dialog) — **p87**. This is the GUI equivalent of the VBA our skill scripts (`docombineresults` / `blocknameforcombineresults` / `SetComplexPortExcitation`+`SetPortSourceType "Signal"`); read it when combine behaves unexpectedly.
- Parameter Sweep — p37; Optimization — p40; SAM planar circuits/assemblies — p48/p55.

**Getting Started:** History List — p45, History Tree — p46 (understand `cst_add_to_history_tool` output); Post-Processing templates & parametric result storage — p58 (why the Tables tree is empty from-scratch).

**Thermal:** EM→thermal bi-directional link setup — p39; 3D field monitors / result types — p64/p68 (SAR-as-heat-source coupling).

## HTML Online Help — the fine-grained source (5362 pages, grep-able)

**Location:** `C:\Program Files (x86)\CST Studio Suite 2024\Online Help\mergedProjects\` — one HTML page per object/dialog/method, more detailed than the PDFs. Use it when you need the exact object model, a specific dialog's options, or a VBA/Python signature.

Subtrees (by htm count):
- **`3D\`** (1413) — MWS 3D modeling / solvers / mesh / monitors / post-processing. SAR physics: `3D\special_overview\special_overview_sar_calculation_overview.htm` (needs a **power-loss-density monitor**; recommends **FPBA** mesh). Combine post-proc: `3D\special_postpr\`.
- **`DES\`** (802) — Design Studio / Schematic tasks & settings (`DES\analysis\simulation\simulationtask.htm`).
- **`VBA_3D\`** (608) / **`VBA_DES\`** (156) — VBA object model. **`VBA_DES\special_vbacommands\simulationtaskobject.htm` authoritatively documents the AC-Combine VBA the skill relies on**: `docombineresults`, `blocknameforcombineresults`, `SetComplexPortExcitation(port,amp,phase)`, `SetPortSourceType(port,type)` — read it first when combine misbehaves.
- **`Python\`** (61) — Python API help (`python_overview.htm`). **`EXP_HF\`/`EXP_LF\`/`EXP_DES\`/`EXP_MP\`…** — module solver-specific pages. `sax_basic\` (315) — macro/BASIC language.

**How to query (grep + strip tags; rendering unavailable, same as PDFs):**
```bash
HELP="C:/Program Files (x86)/CST Studio Suite 2024/Online Help/mergedProjects"
grep -rli "combine results" "$HELP/3D" "$HELP/DES" | head       # locate the page
python -c "import re;t=open(r'<file>.htm',encoding='utf-8',errors='replace').read();t=re.sub(r'(?is)<(script|style).*?</\1>',' ',t);t=re.sub(r'(?s)<[^>]+>',' ',t);print(re.sub(r'\s+',' ',t)[:1500])"
```
Math is MathJax LaTeX source (readable after stripping). Always keep `errors='replace'` (Windows GBK console).

## When to consult (triggers)

- Unsure which solver/port/boundary/mesh fits a coil or phantom → **HF PDF** ch.3.
- Combine-Results / AC co-sim / Signal excitation misbehaving → **Circuit & SAM PDF** p86–87 (workflow) **+ `VBA_DES\...\simulationtaskobject.htm`** (exact VBA props).
- SAR averaging/units/monitor questions → **HF PDF** SAR sections + **`3D\...\sar_calculation_overview.htm`** (physics/monitor) + **Thermal PDF** for heating.
- "Why is my Tables/Post-Processing tree empty" / template mechanics → **Getting Started PDF** p58.
- Need an exact VBA/Python object method or a dialog's option set → **HTML Online Help** (VBA_*/DES/3D/Python), then the vendored `vba-official-reference.md` for a quick signature.

**Discipline:** these docs describe the *GUI / object model*; the MCP drives CST *headless*. Read for the concept + exact option/method names, then reproduce via `cst_*` tools / in-process VBA — do NOT instruct the user to click through the GUI while the MCP holds the COM connection.
