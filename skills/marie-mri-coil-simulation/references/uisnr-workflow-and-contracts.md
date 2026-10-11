# UISNR Workflow and Contracts

## Scope

Use this contract for MARIE BASIS generation, UISNR postprocessing, ideal-current extraction, convergence studies, and finite-array comparison. Treat live source and frozen run evidence as authoritative.

## Result classes

- `geo_flag=2`: report `surface-support-constrained optimal SNR` unless a project defines a more precise name.
- `geo_flag=3`: report `dipole-shell UISNR approximation` until source distance, shell thickness, grid, quadrature, rank, and mode-count convergence pass.
- Use `UISNR` without a qualifier only after source-space completeness and numerical convergence are supported by evidence.

## Spatial sets

Keep these sets separate in every manifest and metric file:

- `Omega_support`: active body/evaluation voxels, normally `RHBM.idxS`.
- `Omega_primary`: design and reporting ROI.
- `Omega_diagnostic`: optional local diagnostic ROIs.

Native UISNR is a pointwise optimization. Every voxel has its own optimal mode coefficient vector. It is not one current pattern optimized for the spatial mean. Any shared ICP target made from multiple voxels is a separate spatial aggregation model; record its voxel weights and normalization explicitly. Never include background zeros in ROI statistics or call an unlabeled geometric mask anatomical.

## Compatibility tuple

Require equality of body file and hash, material map, registration, voxel grid and ordering, `idxS`, B0/nucleus/frequency, VIE basis, electromagnetic boundaries, source support and hash, field convention, B1- convention, noise convention, temperature, magnetization scaling, mode ordering, rank/cutoff policy, and voxel-volume factor. A circuit or finite-array geometry change does not invalidate an otherwise identical reference BASIS, but every array needs its own frozen-circuit field and noise result.

## Production sequence

1. Freeze the compatibility tuple, paths, hashes, ROI masks, output RunTag, and result class.
2. Capture front/side/top and spatial-configuration views tied to geometry/input hashes.
3. Run native geometry, rank, memory, disk, and runtime probes. Require non-overwriting output, checkpoints, failure evidence, and explicit authorization for high-cost work.
4. Build the basis in bounded blocks. Write large artifacts directly to the data plane and record block size, worker count, seeds, code hash, ordering, and restart state.
5. Hermitianize and audit the noise matrix. Use Cholesky/linear solves for well-conditioned positive-definite matrices or an eigen/SVD pseudoinverse with a recorded relative cutoff. Use explicit `inv(Phi)` only in a clearly labeled native-compatibility comparison.
6. Compute pointwise UISNR blockwise. Save a map on `Omega_support`; do not materialize full-volume weights unless required.
7. Extract only requested voxel/ROI ICP coefficients with the physical complex convention in `uisnr-icp-complex-conventions.md`.
8. Run invariance, streaming-parity, ordering, convergence, and finite-array upper-bound tests.
9. Report numerical completion separately from `research-validated` status.

## Required run evidence

Record input/body/support/runner hashes, logical path and realpath, filesystem and free space, MATLAB and code state, field/noise conventions, `idxS` count and ordering hash, mode count, cutoff, effective rank, noise spectrum and Hermitian error, block size, workers, elapsed time, ROI definitions, result class, warnings, and exact output files.

Read `uisnr-convergence-validation.md` before publishing a resolution comparison or claiming ultimate performance.
