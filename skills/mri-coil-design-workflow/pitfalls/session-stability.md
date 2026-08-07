# Pitfalls — Session & Process Stability

Almost every "mysteriously hangs / results come back empty / CST crashes" issue when driving CST traces back to something here. Rule version: `foundations/cst-red-lines.md#Session and Process Safety`.

### A second COM client fights for the channel → permanent hang
- **Symptom**: a call hangs forever with no error at `connect()` / `active_project()`; or schematic/3D VBA fails silently.
- **Root cause**: the MCP server already holds the CST COM connection. Starting another independent `cst.interface`/`win32com` client → two clients contend for the same COM channel → deadlock.
- **Workaround**: **never** start an independent COM client while the MCP holds its connection. Do everything through MCP tools or in-process VBA (`cst_execute_vba_tool` / the `de`/`project`/`model3d` objects inside `cst_run_python_tool`). This is the #1 cause of "hangs".
- **Origin**: multiple early sessions.
- **Rule anchor**: → red-lines "Never start an independent COM client".

### Zombie mcp_server processes saturate the API channel
- **Symptom**: updates/exports fail silently or hang; field reads/combine/export all behave as "empty"; eventually the foreground CST DESIGN ENVIRONMENT crashes and disappears (leaving only background `CSTDCSolverServer`/`cstd.exe`).
- **Root cause**: multiple `mcp_server.py` zombie processes (especially from **different python environments** — the `.mcp.json` `.venv` proper instance plus a manually-started conda zombie) running simultaneously, with both clients fighting over the same COM channel.
- **Workaround**: keep only the latest pair before starting work. Diagnose with: `wmic process where "name='python.exe'" get ProcessId,CommandLine | grep mcp_server` to count processes; `tasklist | grep "DESIGN ENVIRONMENT"` to confirm the foreground is still alive. `taskkill //PID <zombie> //F`, keeping only the `.venv` one. After a CST crash, the MCP stdio pipe also breaks and needs `/mcp` reconnect or a session restart (the agent cannot self-heal the reconnect).
- **Origin**: 2026-07 session-stability investigation.
- **Rule anchor**: → red-lines "Keep only one live MCP server".

### Batch abort/close cascades and takes down the entire Design Environment
- **Symptom**: a single cleanup action closed the user's other projects + disconnected, killing the whole DE instance.
- **Root cause**: batch `abort_solver`/`close` triggers a cascade within one DE instance, collaterally hitting other open projects in the same instance.
- **Workaround**: drive **one project/one action at a time** (import the pipeline module inside `cst_run_python_tool` and run a single case), keeping progress visible to the user and stoppable. Clean up cautiously, one item at a time. Switch projects with `project.close()` → sleep 2 → `de.open_project()`, never in batch.
- **Origin**: FD_Optimize M3 segment sweep.
- **Rule anchor**: → red-lines "Session and Process Safety".

### The GUI window doesn't repaint after MCP builds in the background (not a data loss)
- **Symptom**: after the MCP finishes building geometry/schematic, the already-open CST GUI tree/3D viewport appears blank.
- **Root cause**: the MCP drives CST over a background COM connection and doesn't pump the foreground window message loop.
- **Workaround**: this is a **display lag, not data loss** — `Solid.GetNumberOfShapes()`/`Block` iteration returns the real content, and `save()` writes to disk correctly. `ScreenUpdating`/`Plot.Update`/`ResetViewToStructure` do not fix the foreground window. The user **closing and reopening the project** reloads correctly from disk. So `save()` after every stage.
- **Origin**: confirmed empirically 2026-07-14.

### "MCP is alive" ≠ "project is usable"
- **Symptom**: assuming that because CST is running the project must be loaded, then getting empty reads afterward.
- **Workaround**: confirm the active project with `cst_project_info_tool`; with multiple projects open, `de.active_project()` is unreliable — use the handle returned by `open_project(path)`.
