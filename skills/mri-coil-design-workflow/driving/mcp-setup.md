# CST MCP Setup

Verified working recipe for launching the CST MCP server on this machine (confirmed 2026-07-11: connect → list results → read 1D result on the Dipole project all succeeded).

## Prerequisites (verify BEFORE first run)

### CST Studio Suite
- **Version**: CST Studio Suite **2024** (or newer; the bundled `_cst_results.cp310-win_amd64.pyd` requires the 2024 release stack). Older 202x releases likely need a matching Python (this skill has only been validated against 2024).
- **License features required** for the MRI workflows in this skill:
  - **HF Time Domain solver** (used by mri_coil / single-coil / body-coil / spine — all TD Hex).
  - **HF Frequency Domain solver** (used by dipole from-scratch & patch — tet 2nd order).
  - **Circuit / Design Studio** (schematic + lumped elements + S-parameter task + AC co-simulation).
  - Optional: **MRI Toolbox** (only needed if you rely on the pre-installed "Calc B1+" template; our `cst_calc_b1_field_tool` runs the same math directly and does NOT require this license).
  - Optional: **CST Voxel Family** license (only needed to load Gustav/Laura/Ella voxel human models — e.g. MRI System supp case). Without it, replace voxel models with a homogeneous phantom.
  - Optional: **Multiphysics / Thermal** license (Bioheat solver — MRI System full pipeline only).
- Verify with `cst_detect_tool`: it reports the exe path + running PIDs. Real license issues surface at first solve as `License checkout failed`.

### OS / hardware
- **Windows** (this stack uses COM/`pythoncom`; Linux is not supported by CST natively).
- **RAM**: 16 GB minimum for the demo dipole; **32 GB+ recommended** for lossy-body B1+ (the muscle/Gustav cases can allocate 5–15 GB per solve). HDF5 field export of 300+ mm phantom at 1 mm step easily hits 1–5 GB temp file.
- **Disk**: keep 10–20 GB free next to `results/` — B1+ pipeline writes raw H-field (.h5) + subvolume ASCII dumps + PNGs; a typical run uses 100–500 MB.
- **GPU**: not required (this skill does not enable GPU solver acceleration by default).

### Python version constraint (hard ceiling — verify FIRST)
- **Python must be 3.6–3.11.** CST's `cst` package (the `cst.interface` / `cst.results` bindings) **fails to import on Python 3.12+**. This is a hard ceiling, easy to miss on a fresh machine with a modern default Python — the MCP will start but `cst_detect_tool` reports `cst_interface_importable: false` and every CST action fails.
- On this machine we use the **3.10 `mri_agent` env** (CST 2024's result module is `_cst_results.cp310-win_amd64.pyd`, compiled for 3.10). Do NOT use CST's bundled 3.9 or a system 3.12+.

### Python packages (in the mri_agent env, once)
```
pip install "mcp[cli]" anyio fastmcp numpy scipy matplotlib h5py
```
- **Warning — hidden-dependency trap**: the MCP's `pyproject.toml` declares ONLY `mcp` as a dependency. The B1+/SAR/plotting scripts (`compute_b1plus.py`, `export_native_sar.py`, `plot_*.py`) need `h5py numpy scipy matplotlib` installed **manually** or they `ImportError` at post-processing time — the server itself starts fine, so this surfaces late (mid-pipeline), not at launch. Install all of them up front.
- **`h5py` is mandatory** for `compute_b1plus.py` / `export_native_sar.py` (HDF5 raw field → B1+/SAR pipeline). Missing it is the single most common "post-processing fails" root cause on a fresh env. Verify: `python -c "import h5py; print(h5py.__version__)"` — should print 3.x.
- `numpy` / `scipy` / `matplotlib` for `plot_field.py` / `plot_b1_profiles.py` / `compute_b1plus.py` / `plan_export_box.py`.
- `mcp[cli]` / `anyio` / `fastmcp` for the MCP server itself.
- CST ships its own `cst.interface` / `cst.results` at `<CST_INSTALL_ROOT>\AMD64\python_cst_libraries\` — the MCP auto-injects that path; do NOT pip install a competing `cst` package.

### Version portability (CST 2024 ↔ 2026)
- The MCP source uses **no CST-version-specific API** — portability across CST releases is entirely via the `CST_INSTALL_ROOT` / `CST_DESIGN_ENVIRONMENT_EXE` env vars below. Point them at any installed release (matching the Python-version constraint above) and the same server works.
- `cst_automation.py` carries a hardcoded `DEFAULT_CST_EXE` / `DEFAULT_CST_ROOT` fallback constant, but it is **only used when the env vars are unset**. Since `.mcp.json` sets both env vars to this machine's real path (`D:\ght\softwares\MRI_agent_softwares`), the hardcoded default is never reached — do NOT "fix" that constant to match your install; set the env vars instead.

## Paths

| Thing | Path |
| --- | --- |
| MCP server | `D:\ght\SAIS\MRI_agent\external\CST-MCP\mcp_server.py` |
| Python (use this) | `C:\Users\admin\.conda\envs\mri_agent\python.exe` (conda env `mri_agent`, Python 3.10) |
| CST install root | `D:\ght\softwares\MRI_agent_softwares` |
| CST executable | `D:\ght\softwares\MRI_agent_softwares\AMD64\CST DESIGN ENVIRONMENT_AMD64.exe` |

Use the **3.10 mri_agent env**, not CST's bundled 3.9 Python. CST 2024's result module is `_cst_results.cp310-win_amd64.pyd` (compiled for 3.10), and the MCP framework deps (`mcp[cli]`, anyio, fastmcp) are installed there.

## Required environment variables

Set before starting the server (the MCP reads `CST_INSTALL_ROOT` and injects CST's `python_cst_libraries` + AMD64 DLL dir automatically):

```
CST_INSTALL_ROOT=D:\ght\softwares\MRI_agent_softwares
CST_DESIGN_ENVIRONMENT_EXE=D:\ght\softwares\MRI_agent_softwares\AMD64\CST DESIGN ENVIRONMENT_AMD64.exe
```

## Registering the MCP server with Claude Code

Add to the project's MCP config (e.g. `.mcp.json` or via `claude mcp add`). Shape:

```json
{
  "mcpServers": {
    "cst-studio-suite": {
      "command": "C:\\Users\\admin\\.conda\\envs\\mri_agent\\python.exe",
      "args": ["D:\\ght\\SAIS\\MRI_agent\\external\\CST-MCP\\mcp_server.py"],
      "env": {
        "CST_INSTALL_ROOT": "D:\\ght\\softwares\\MRI_agent_softwares",
        "CST_DESIGN_ENVIRONMENT_EXE": "D:\\ght\\softwares\\MRI_agent_softwares\\AMD64\\CST DESIGN ENVIRONMENT_AMD64.exe"
      }
    }
  }
}
```

## Smoke test without Claude (direct python)

From `external/CST-MCP`, with the two env vars set:

```python
import mcp_server as m
m.cst_detect_tool()      # -> cst_exe_exists True, cst_interface_importable True, running PIDs
m.cst_connect_tool()     # -> connected True, active project info
```

If `cst_detect_tool` shows `cst_interface_importable: false`, the env vars are wrong or missing.
