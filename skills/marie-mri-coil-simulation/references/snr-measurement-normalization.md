# MARIE SNR to Measured-SNR Normalization

Use this reference whenever a task asks for absolute SNR, comparison with an
MRI measurement, an SNR error map, or conversion of
`solution.snr_field.SNR` to a concrete acquisition protocol.

## Contents

1. [Source-confirmed MARIE definition](#1-source-confirmed-marie-definition)
2. [Acquisition-specific scaling model](#2-acquisition-specific-scaling-model)
3. [Sequence factors](#3-sequence-factors)
4. [Bandwidth, averages, and reconstruction](#4-bandwidth-averages-and-reconstruction)
5. [Receiver temperature and electronics](#5-receiver-temperature-and-electronics)
6. [Measurement protocol](#6-measurement-protocol)
7. [Calibration rule](#7-calibration-rule)
8. [Error reporting](#8-error-reporting)
9. [Required provenance record](#9-required-provenance-record)
10. [Scientific boundaries](#10-scientific-boundaries)

## 1. Source-confirmed MARIE definition

The live MARIE implementation in `src/src_physics/src_performance_metrics/em_SNR.m`
computes

```text
snr_num_scaling = res^3 * omega * M0 / sqrt(4*k_B*T0)
Phi = e_field.Rx.phi
    + e_field.Rx.phi_coil
    + e_field.Rx.phi_lump
    + netp.phi_lumped_elements.Rx
SNR(r) = snr_num_scaling * sqrt(b1m(r)^H * Phi^-1 * b1m(r))
```

The code currently uses an explicit inverse. For new diagnostic code, prefer a
Hermitian linear solve or Cholesky/eigendecomposition with a recorded cutoff;
do not alter a preserved solver result merely to change this implementation.

`em_constants.m` defines `T0 = 310 K` and derives `M0` from a fixed nucleus
density, gyromagnetic ratio, spin, field strength, and thermal equilibrium. For
1H the default density represents the MARIE water-proton reference. Verify live
source values because they are the authoritative contract.

The formula contains no explicit acquisition noise bandwidth. Interpret the
raw map as a 1 Hz noise-equivalent-bandwidth reference with equilibrium
magnetization fully available to the transverse signal, subject to MARIE's
field, port, and noise conventions. It is not yet a DICOM or scanner-protocol
SNR.

## 2. Acquisition-specific scaling model

Start with

```text
SNR_pred(r) = SNR_MARIE(r)
            * (Vvox_meas / Vvox_sim)
            * rho_H(r)
            * F_seq(r)
            * sqrt(Navg / BW_EN)
            * eta_sys(r)
            * eta_recon(r)
```

where:

- `Vvox_sim = res^3` for the current isotropic MARIE implementation;
- `Vvox_meas` is the acquired voxel volume before display interpolation;
- `rho_H` is effective proton density relative to the MARIE `M0` reference;
- `F_seq` is the pulse-sequence transverse-magnetization factor;
- `Navg` is the number of statistically independent averages;
- `BW_EN` is the reconstruction's noise-equivalent bandwidth in Hz per voxel;
- `eta_sys` represents receiver-chain effects absent from the EM/noise model;
- `eta_recon` represents reconstruction losses or scaling.

Voxel signal scales linearly with voxel volume. Do not use a linear-size ratio
or its square root. Verify whether prescribed slice thickness differs from the
effective slice profile.

## 3. Sequence factors

For an ideal spoiled GRE approximation,

```text
F_seq = sin(alpha)
      * (1-exp(-TR/T1)) / (1-cos(alpha)*exp(-TR/T1))
      * exp(-TE/T2star)
```

For an ideal spin echo approximation,

```text
F_seq = (1-exp(-TR/T1)) * exp(-TE/T2)
```

Adapt these expressions for inversion preparation, echo trains, imperfect
refocusing, actual flip-angle/B1+ maps, slice profile, receive-window decay, or
other sequence-specific behavior. Record the exact model and parameter maps.
Do not claim absolute tissue SNR without proton-density and relaxation inputs.

## 4. Bandwidth, averages, and reconstruction

Thermal-noise amplitude scales as `sqrt(BW_EN)`, so SNR scales as
`1/sqrt(BW_EN)`. Do not insert a scanner UI bandwidth until establishing
whether it means total readout bandwidth, Hz/pixel, or another vendor-specific
quantity, and whether reconstruction filtering changes the equivalent noise
bandwidth.

Independent averages increase SNR by `sqrt(Navg)`. This assumes stationary,
uncorrelated noise and no motion or drift penalty.

For parallel imaging with acceleration `R`, a conventional local relation is

```text
SNR_R(r) = SNR_full(r) / (g(r)*sqrt(R))
```

Only apply it after defining encoding direction, acceleration, sampling mask,
noise whitening, reconstruction method, calibration, and regularization. Do
not invent a g-factor from S-parameters or a receive-sensitivity montage.

FFT normalization, apodization, partial Fourier, coil compression, interpolation,
magnitude reconstruction, denoising, and regularization can all change the
measured SNR or its estimator. Record them in `eta_recon` or model them
explicitly.

## 5. Receiver temperature and electronics

MARIE's common `T0` scaling is not automatically a complete scanner noise
budget. Real sample, coil, matching components, cables, and preamplifiers may
have different effective temperatures and losses. A preamplifier noise figure
`NF_dB` alone corresponds to an amplitude efficiency

```text
eta_NF = 10^(-NF_dB/20)
```

but do not treat it as the whole receive-chain efficiency. Prefer a component
noise-wave/covariance model when available; otherwise identify `eta_sys` as an
empirical global calibration term and retain its uncertainty.

## 6. Measurement protocol

Prefer raw complex images or raw channel data. Acquire two independent images
with identical sequence and reconstruction settings. For a difference-method
estimate,

```text
signal = mean((I1 + I2)/2)
noise_sigma = std(I1 - I2)/sqrt(2)
SNR_meas = signal/noise_sigma
```

Use a local or ROI estimator appropriate to the data. For magnitude-only data,
correct Rician/noncentral-chi bias and account for coil combination; a simple
background standard deviation is generally not sufficient. Preserve pre-scan
normalization and vendor intensity-scaling metadata.

Register measurement and simulation in physical coordinates. Avoid estimating
noise after interpolation because interpolation correlates and rescales noise.
If resampling is unavoidable, characterize its noise transfer function.

## 7. Calibration rule

First apply every known physics and acquisition factor. If the receive-chain
scale remains unknown, estimate one global factor in a predefined calibration
ROI:

```text
C_cal = median_ROI(SNR_meas / SNR_pred_uncalibrated)
SNR_pred_calibrated = C_cal * SNR_pred_uncalibrated
```

Freeze that factor before evaluating test ROIs or other subjects. Never fit a
different factor per voxel, tissue, slice, or evaluation ROI; doing so removes
the spatial validation question. Prefer separate calibration and validation
datasets.

## 8. Error reporting

Report at least:

```text
relative_error(r) = (SNR_pred(r)-SNR_meas(r))/SNR_meas(r)
NRMSE = rms(SNR_pred-SNR_meas)/mean(SNR_meas)
bias = median(relative_error)
```

Also report spatial correlation and predefined deep, middle, and cortical ROI
statistics such as median, p10, and p90. Mask voxels with unreliable measured
noise estimates and state the mask rule. Include uncertainty from bandwidth,
relaxometry, proton density, registration, receiver calibration, repeatability,
and noise estimation.

## 9. Required provenance record

An absolute-SNR comparison is incomplete unless its report records:

- MARIE CaseTag, RunTag, final MAT hash, code state, B0, nucleus, frequency;
- body, materials, grid, support mask, simulated voxel volume, and temperature;
- B1- convention and full noise covariance composition;
- acquisition sequence, TR, TE, flip angle, preparation pulses, and averages;
- acquired/reconstructed voxel size and effective noise bandwidth definition;
- coil loading, tuning/matching state, cables, preamplifiers, and scanner chain;
- raw/complex/magnitude data type and SNR estimator;
- registration/resampling method, calibration ROI, validation ROIs;
- every multiplicative factor, global calibration value, uncertainty, and error metric.

If any essential factor is unavailable, publish relative spatial SNR or
normalized ROI ratios and label absolute agreement as unvalidated.

## 10. Scientific boundaries

- Do not compare DICOM intensity directly with MARIE SNR.
- Do not call the raw map an acquisition SNR without bandwidth and sequence scaling.
- Do not mix body, field strength, nucleus, grid, ROI, or normalization contracts.
- Do not infer proton density from permittivity or conductivity alone.
- Do not use per-ROI fitting to claim spatial agreement.
- Do not treat Rx-only reciprocal fields as formal Tx/SAR evidence.
- Do not claim UISNR efficiency without a compatible validated UISNR basis.
