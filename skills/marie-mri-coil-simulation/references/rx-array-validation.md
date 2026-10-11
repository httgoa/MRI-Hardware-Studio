# Rx Array Validation Reference

Use the following checks after a MARIE pure-Rx simulation.

```matlab
SPsDB = 20*log10(abs(solution.netp.SP_s));
SPpDB = 20*log10(abs(solution.netp.SP_p));
F = solution.netp.figure_freq;
nPorts = size(SPsDB,1);

couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;
[worstCouplingDB,idx] = max(couplingDB,[],'all');
[rowPort,colPort] = ind2sub(size(couplingDB),idx);

targetMHz = solution.netp.figure_freq.freq_range(F.freq_idx)/1e6;
resonanceMHz = NaN(nPorts,1);
for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    [~,k] = min(curve);
    resonanceMHz(p) = F.freq_range(k)/1e6;
end

fprintf('SP_p range: %.2f to %.2f dB\n',min(SPpDB),max(SPpDB));
fprintf('Worst Sij: S%d%d = %.2f dB\n',rowPort,colPort,worstCouplingDB);
fprintf('Maximum resonance offset: %.3f MHz\n', ...
    max(abs(resonanceMHz-targetMHz)));
```

Starting gate values for a symmetric receive array are `SP_p < -15 dB`, resonance offset below `0.5 MHz`, channel mismatch spread below `3 dB`, and worst geometric/network coupling below `-12 dB`. Treat these as engineering gates, not universal acceptance standards.

For the 5 T fixed-32-channel helmet project, Grade A retains those formal
thresholds. Its documented Grade-B exploratory gate requires at least 28/32
ports below `-15 dB`, every remaining port below `-12 dB`, worst off-diagonal
coupling below `-10.5 dB`, no more than four unique pairs at or above `-12 dB`,
and every exception in the frozen adjacency table. Grade B only authorizes an
`exploratory_conditionally_accepted` Stage C and remains ineligible for a
formal/research-validated baseline. Noise correlation, field integrity, SNR,
and g-factor are mandatory post-Stage-C checks; they cannot be inferred from
bench-style S-parameters alone.

For a double-row array, inspect coupling blocks separately: upper-to-upper, lower-to-lower, aligned upper-to-lower, and staggered upper-to-lower. The worst matrix entry alone cannot explain which geometry correction is needed.

For absolute SNR, measured-SNR comparisons, or error maps, additionally follow
[`snr-measurement-normalization.md`](snr-measurement-normalization.md). The raw
MARIE SNR includes a physical equilibrium-magnetization and thermal-noise scale,
but it does not by itself represent a particular pulse sequence, receiver
bandwidth, acquisition voxel, reconstruction, or scanner electronics chain.
