# UISNR Convergence and Validation

## Numerical acceptance

Require finite outputs, bounded Hermitian error, a positive-semidefinite noise matrix within documented tolerance, an explicit cutoff and effective rank, nonnegative quadratic forms after only tolerance-scale clipping, and repeatable hashes or numerical tolerances.

## Regression matrix

- Compare the quadratic form against a high-accuracy linear solve for synthetic positive-definite matrices.
- Verify invariance under consistent invertible mode transformations and individual mode scaling.
- Compare monolithic and blockwise evaluation; repeat with different block sizes and voxel orders.
- Verify `idxS` extraction and three-dimensional writeback ordering.
- Check cutoff sensitivity and report effective rank and condition estimate.
- Check mode-prefix behavior. Large decreases require investigation; tiny changes near a moving cutoff must be interpreted with the recorded numerical policy.
- Require `SNR_array/UISNR <= 1 + tolerance` under an identical compatibility tuple. Treat a systematic excess as a convention or implementation defect first.

## Resolution and source-space convergence

Compare Coarse/Medium/Fine only on a common physical ROI and matched voxel locations or an explicitly documented interpolation. Report median, P10, P90 and worst-region relative change, map correlation, noise spectrum/effective rank, and relevant subspace principal angles. Do not use zero-padded background in statistics.

Mode-count convergence, body-grid convergence, support-mesh convergence, and dipole-shell distance/thickness convergence are distinct studies. Passing one does not prove the others. A Fine `geo_flag=2` result remains a constrained optimum; closeness to ultimate performance requires a converged, more complete source-space reference.

## Hodge validation

When decomposing an ICP on a discrete surface, report tangency, reconstruction residual, divergence/curl residuals, component inner products in the correct mass matrix, harmonic dimension versus topology, and covariance under global complex phase rotation. Do not treat a project-local Hodge implementation as a stable generic API until these tests pass on synthetic surfaces with known topology.

## Publication gate

Publish a convergence claim only with the complete compatibility tuple, ROI/mask provenance, active-voxel ordering, numerical cutoff, source-space classification, and raw per-resolution metrics. Keep engineering, diagnostic, and research-validated labels distinct.
