# MARIE Storage Layout and Migration Contract

## Scope

Use this contract for disk-capacity planning, high-cost simulations, UISNR/BASIS work, migration, archival, and cleanup. The active workspace Harness is authoritative when it defines stricter rules.

## Storage tiers

| Tier | Default root | Keep here |
|---|---|---|
| SSD control | `/home/<user>/marie-tools` | source, Git, cases, inputs, runners, docs, manifests, metrics, lightweight figures |
| HDD data | `/mnt/data/<user>/marie` | large bodies, YPn, MREDM, FINAL MAT, BASIS, checkpoints, full run outputs, archives |

Use `/mnt/data/shared/` only with explicit shared ownership and immutable hashes. Keep project data under `/mnt/data/<user>/marie/projects/<ProjectID>/` and expose it through stable project-local symlinks where required.

## Canonical project layout

```text
/mnt/data/<user>/marie/
  shared/{bodies,validated_bases}/
  projects/<ProjectID>/
    runs/<CaseTag>/<RunTag>/
    artifacts/bases/<CompatibilityTag>/
    large_assets/
    scratch/
    trash/<timestamp>/
    archive/
  legacy/
```

Keep `projects/<ProjectID>/{cases,tools,docs}` as regular SSD directories. Symlink only large-data ownership boundaries such as `runs`, `artifacts/bases`, or stable large-body directories.

## Manifest requirements

For every authoritative large artifact, record:

```yaml
storage:
  logical_path:
  physical_path:
  realpath:
  filesystem_source:
  filesystem_type:
  mount_options:
  storage_tier: ssd-control | hdd-data
  size_bytes:
  sha256:
  link_type: regular | symlink | hardlink
```

Use project-relative paths or `AssetRoot` in portable inputs. Freeze resolved absolute paths only in RunTag evidence.

## Capacity gate

Before a high-cost run:

1. Check `df -hT`, `df -ihT`, `findmnt`, destination ownership, and write access.
2. Reject a destination mounted `ro` or outside the declared project data root.
3. Require free destination bytes at least `2.5 * estimated_persistent_output_bytes`.
4. Project after-run reserves: system disk `max(15%, 200 GiB)`; data disk `max(10%, 500 GiB)`.
5. Include MAT v7.3 temporary saves, checkpoints, failure evidence, and log growth in the estimate.
6. Use a bounded probe when output size or peak memory is unknown.
7. Stop prepared tasks on failure; never clean unrelated data automatically.

For UISNR, allocate separate compatibility-tagged directories and budget coarse/medium/fine runs independently. Reuse one validated BASIS across finite arrays only when the complete physics and normalization tuple matches.

## Migration sequence

1. Inventory files, references, inode/link counts, processes, sizes, and hashes.
2. Produce an exact source-to-target manifest.
3. Quiesce writers and confirm the HDD destination is writable.
4. Copy without deleting the source; preserve timestamps where useful.
5. Verify file sizes and SHA-256, then verify the directory inventory.
6. Switch the logical directory to a symlink and record `realpath`.
7. Run session bootstrap, `load_inputs`, geometry-only, and read-only result regression.
8. Confirm a fresh session can resolve the same paths.
9. Request separate approval before isolating or deleting the SSD source.
10. Record the architecture change and evidence.

Cross-filesystem hardlinks are unavailable. Treat copied files as new physical objects until hashes prove equality. A move to same-filesystem trash is recoverable isolation and releases no capacity.

## Retention

- Keep accepted/final results, validated BASIS, complete provenance, and hashes.
- Keep one restart checkpoint and adopted raw Stage-A YPn until the case closes.
- Mark duplicate MREDM, superseded checkpoints, regenerable full-resolution figures, scratch, and failed partial saves as cleanup candidates.
- Isolate failures first. Permanently delete only an exact reviewed manifest after explicit authorization.
- After cleanup, verify protected artifacts, broken symlinks, references, and actual `df` capacity change.
