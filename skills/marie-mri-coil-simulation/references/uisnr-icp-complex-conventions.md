# UISNR ICP and Complex-Current Conventions

## Signal and quadratic form

For a voxel signal column `s` and Hermitian sample-noise matrix `Phi`, use

\[
q=s^H\Phi^+s,\qquad \mathrm{UISNR}=C\sqrt{\max(\operatorname{Re}q,0)}.
\]

State whether `s` is raw `B1-`, conjugated receive sensitivity, or another reciprocity convention. Do not silently move a conjugation or a factor of two between exporters.

## Analysis direction versus physical MARIE coefficient

The abstract analysis direction is

\[
a=\Phi^+s.
\]

When the MARIE reconstruction uses the bilinear signal `s^T w`, the unit-noise physical coefficient is

\[
w=\frac{\operatorname{conj}(\Phi^+s)}
        {\sqrt{\operatorname{Re}(s^H\Phi^+s)}}.
\]

This distinction is mandatory when mapping weights back through `VK/SK` to a complex surface current. A coefficient that reproduces the scalar quadratic form is not automatically the coefficient required by the physical current convention.

## Required ICP tests

- Signal reproduction: `s.' * w` equals `sqrt(q)` within tolerance for the MARIE bilinear convention.
- Unit noise: evaluate the exact project noise bilinear form and document which coefficient orientation it expects.
- Global phase: `s -> exp(1i*theta)*s` implies `w -> exp(-1i*theta)*w`.
- Basis invariance: UISNR is invariant under an invertible mode-coordinate transformation when both signal and noise are transformed consistently.
- Near-degenerate blocks: unitary rotation inside a near-degenerate eigenspace must not alter the reconstructed physical subspace.
- Holdout: spatial targets fitted from training voxels must be evaluated on independent voxels.

## Minimum complex-current diagnostics

For complex surface current `J`, export:

1. vector magnitude `|J|`;
2. a clearly defined scalar phase, such as the phase of the largest-magnitude Cartesian component;
3. instantaneous vectors `real(J*exp(1i*theta))` for `theta=0, pi/2, pi, 3pi/2`;
4. surface divergence and streamlines;
5. for Hodge work, exact, coexact, and harmonic components plus reconstruction and orthogonality metrics.

Do not infer one manufacturable wire from `|J|` alone. Phase-orthogonal loop and figure-eight structures can overlap in magnitude while occurring at different instants. Label centroid-adjacency paths or streamlines as proxies rather than physical conductors.
