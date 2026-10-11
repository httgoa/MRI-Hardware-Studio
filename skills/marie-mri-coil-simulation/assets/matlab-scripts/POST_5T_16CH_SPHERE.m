%% POST_5T_16CH_SPHERE
% Postprocess a MARIE 5 T / 1H / 16-channel double-row Rx loop array.
% Output figures are written next to the result MAT file in a case folder.
% SP_p and SPm_plot_Rx are used for Rx matching; off-diagonal SP_s is used
% for coupling. Tx SAR plots are generated only from genuine Tx fields.

close all;
clearvars;
clc;

%% User configuration
projectRoot = getenv('MARIE_ROOT');
if isempty(projectRoot)
    error('MARIE:Config', 'Set MARIE_ROOT to the active marie-tools workspace.');
end
arrayResultName = ...
    'MARIE_0_inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90_FINAL.mat';
legacyArrayResultName = ...
    'MARIE_1_inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.mat';
acceptedTmdResultName = ...
    'TMD_5T_Sphere200_16LoopRx_DoubleRow_H90_20260807_070421.mat';
bodyRelativePath = fullfile('Scatterers','4mm', ...
    'Sphere_D200mm_4mm_eps50_sig0p6_5T.mat');
basisResultName = 'Sphere200_5T_PWC_CylSupport_UISNR.mat';

% Leave empty for an Rx-only result. Set this to a Tx/TxRx solution MAT
% name only when it contains h_field.Tx.b1p and e_field.Tx.e_b.
txResultName = '';
txWeightsUser = [];

outputFolderName = 'figures_5T_16ch_H90';
exportResolution = 300;
roiRadiusMM = 40;
sMatrixColorLimitsDB = [-40 -5];
sweepYLimitsDB = [-40 0];
efficiencyColorLimitsPercent = [0 100];
txDisplayPercentile = 99;
defaultMassDensityKgM3 = 1000;

cd(projectRoot);
startup;

%% Load and validate data
resultFile = fullfile(projectRoot,'data','solutions',arrayResultName);
if ~isfile(resultFile)
    legacyResultFile = fullfile(projectRoot,'data','solutions', ...
        legacyArrayResultName);
    assert(isfile(legacyResultFile), ...
        'Neither final nor legacy result MAT file exists');
    warning(['Final fixed-circuit result is missing. Falling back to ' ...
        'legacy TMD=1 result: %s'],legacyResultFile);
    resultFile = legacyResultFile;
end
bodyFile = fullfile(projectRoot,'data','bodies',bodyRelativePath);
basisFile = fullfile(projectRoot,'data','bases',basisResultName);
outDir = fullfile(projectRoot,'data','solutions',outputFolderName);

assert(isfile(resultFile),'Result MAT file is missing: %s',resultFile);
assert(isfile(bodyFile),'Body MAT file is missing: %s',bodyFile);
assert(isfile(basisFile),'UISNR BASIS MAT file is missing: %s',basisFile);
if ~exist(outDir,'dir'), mkdir(outDir); end

R = load(resultFile,'solution','network_meta');
B = load(bodyFile,'RHBM');
Q = load(basisFile,'BASIS');
solution = R.solution;
RHBM = B.RHBM;
BASIS = Q.BASIS;

assert(isfield(solution,'netp') && isfield(solution.netp,'SP_s'), ...
    'solution.netp.SP_s is missing');
assert(isfield(solution.netp,'SP_p'), ...
    'solution.netp.SP_p is missing');
assert(isfield(solution,'h_field') && isfield(solution.h_field,'Rx') && ...
       isfield(solution.h_field.Rx,'b1m'), ...
    'Rx B1- fields are missing');
assert(isfield(solution,'snr_field') && isfield(solution.snr_field,'SNR'), ...
    'Array SNR is missing');
assert(isfield(BASIS,'UISNR'),'BASIS.UISNR is missing');

SPs = solution.netp.SP_s;
SPp = solution.netp.SP_p;
nPorts = size(SPs,1);
assert(isequal(size(SPs),[16 16]),'Expected a 16-by-16 SP_s matrix');
assert(numel(SPp)==16,'Expected one preamplifier-loaded value per Rx port');

mask = false(size(RHBM.epsilon_r));
mask(RHBM.idxS) = true;
x = squeeze(RHBM.r(:,1,1,1))*1e3;
y = squeeze(RHBM.r(1,:,1,2))*1e3;
z = squeeze(RHBM.r(1,1,:,3))*1e3;
[~,ix0] = min(abs(x));
[~,iy0] = min(abs(y));
[~,iz0] = min(abs(z));

SNR = real(solution.snr_field.SNR);
UISNR = real(BASIS.UISNR);
assert(isequal(size(SNR),size(UISNR),size(mask)), ...
    'SNR, UISNR, and body grids must match exactly');

valid = mask & isfinite(SNR) & isfinite(UISNR) & UISNR > 0;
ratio = NaN(size(SNR));
ratio(valid) = 100*SNR(valid)./UISNR(valid);
if any(ratio(valid) > 100.5)
    warning('SNR/UISNR exceeds 100%%. Verify normalization before interpretation.');
end

fprintf('Center voxel: [%.3f, %.3f, %.3f] mm\n',x(ix0),y(iy0),z(iz0));

%% Figure 01: SP_s matrix and preamplifier-loaded return-loss sweep
SdB = 20*log10(abs(SPs));
SPpDB = 20*log10(abs(SPp));
if ismatrix(SPpDB) && size(SPpDB,1)==size(SPpDB,2)
    SPpDiagonalDB = diag(SPpDB);
else
    SPpDiagonalDB = SPpDB(:);
end
targetMHz = 212.88739259;
if isfield(R,'network_meta') && isfield(R.network_meta,'frequency_Hz')
    targetMHz = R.network_meta.frequency_Hz/1e6;
end

F = [];
sweepSource = 'unavailable';
if isfield(solution.netp,'figure_freq') && ...
        isfield(solution.netp.figure_freq,'freq_range') && ...
        isfield(solution.netp.figure_freq,'freq_idx')
    F = solution.netp.figure_freq;
    sweepSource = 'final fixed-circuit result';
else
    acceptedTmdFile = fullfile(projectRoot,'data','solutions', ...
        acceptedTmdResultName);
    if isfile(acceptedTmdFile)
        accepted = load(acceptedTmdFile,'netp');
        if isfield(accepted,'netp') && ...
                isfield(accepted.netp,'figure_freq') && ...
                isfield(accepted.netp.figure_freq,'freq_range') && ...
                isfield(accepted.netp.figure_freq,'freq_idx')
            F = accepted.netp.figure_freq;
            sweepSource = ['accepted TMD round ' acceptedTmdResultName];
            warning(['Final TMD=0 result has no figure_freq. Using only the ', ...
                'frequency sweep from accepted TMD round: %s'], ...
                acceptedTmdFile);
        end
    end
end

if ~isempty(F)
    targetMHz = F.freq_range(F.freq_idx)/1e6;
else
    warning(['No compatible frequency-sweep cache was found. Figure 01 ', ...
        'will retain the final target-point S matrix and omit the sweep.']);
end

f1 = figure('Color','w','Position',[100 100 1500 620]);
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

nexttile;
imagesc(SdB,sMatrixColorLimitsDB);
axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Excited port'); ylabel('Observed port');
title(sprintf('SP_s at %.3f MHz (dB)',targetMHz));
colormap(gca,hot(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        text(col,row,sprintf('%.1f',SdB(row,col)), ...
            'HorizontalAlignment','center','Color','c','FontSize',7);
    end
end

nexttile; hold on;
if ~isempty(F) && isfield(F,'SPm_plot_Rx') && ~isempty(F.SPm_plot_Rx)
    for p = 1:nPorts
        curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
        plot(F.freq_range/1e6,curve,'LineWidth',1.15, ...
            'DisplayName',sprintf('S_{%d%d}',p,p));
    end
    xline(targetMHz,'k--','Target');
    yline(-15,'r:','-15 dB');
    ylim(sweepYLimitsDB); grid on;
    xlabel('Frequency (MHz)'); ylabel('Return loss (dB)');
    title(sprintf('Preamplifier-loaded Rx sweep (%s)',sweepSource), ...
        'Interpreter','none');
    legend('Location','eastoutside','NumColumns',2);
else
    text(0.5,0.5,'Frequency sweep unavailable', ...
        'HorizontalAlignment','center');
    axis off;
end
exportgraphics(f1,fullfile(outDir,'01_Sparameters_and_Rx_sweep.png'), ...
    'Resolution',exportResolution);

%% Figure 02: all 16 channel B1- maps in a 4-by-4 layout
B1m = solution.h_field.Rx.b1m;
assert(size(B1m,4)==nPorts,'Rx B1- port count does not match SP_s');
b1Display = abs(B1m(:,:,iz0,:))*1e6;
b1ColorMax = max(b1Display,[],'all','omitnan');
if ~isfinite(b1ColorMax) || b1ColorMax <= 0, b1ColorMax = 1; end

f2 = figure('Color','w','Position',[40 40 1750 1120]);
tiledlayout(4,4,'Padding','compact','TileSpacing','compact');
for p = 1:nPorts
    map = squeeze(b1Display(:,:,1,p));
    map(~mask(:,:,iz0)) = NaN;
    nexttile;
    imagesc(x,y,map'); axis image xy;
    clim([0 b1ColorMax]);
    xlabel('x (mm)'); ylabel('y (mm)');
    title(sprintf('|B1-|, Rx %d (microT)',p));
    colormap(gca,hot(256)); colorbar;
end
sgtitle(sprintf('16-channel |B1-| at z = %.1f mm',z(iz0)));
exportgraphics(f2,fullfile(outDir,'02_B1minus_16channels.png'), ...
    'Resolution',exportResolution);

%% Figure 03: total receive-noise covariance and correlation
assert(isfield(solution,'e_field') && isfield(solution.e_field,'Rx'), ...
    'Rx electric-field data required for noise covariance is missing');
RxE = solution.e_field.Rx;
PhiNoise = RxE.phi + RxE.phi_coil + RxE.phi_lump;
if isfield(solution.netp,'phi_lumped_elements') && ...
        isfield(solution.netp.phi_lumped_elements,'Rx')
    PhiNoise = PhiNoise + solution.netp.phi_lumped_elements.Rx;
end
PhiNoise = 0.5*(PhiNoise + PhiNoise');
assert(isequal(size(PhiNoise),[nPorts nPorts]), ...
    'Noise covariance size does not match the number of ports');

noiseStd = sqrt(max(real(diag(PhiNoise)),0));
denom = noiseStd*noiseStd.';
noiseCorrelation = NaN(nPorts);
validNoise = denom > 0;
noiseCorrelation(validNoise) = PhiNoise(validNoise)./denom(validNoise);

f3 = figure('Color','w','Position',[100 100 1450 620]);
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');
nexttile;
imagesc(abs(PhiNoise)); axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Rx port'); ylabel('Rx port');
title('|Total noise covariance Phi|');
colormap(gca,turbo(256)); colorbar;

nexttile;
imagesc(abs(noiseCorrelation),[0 1]); axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Rx port'); ylabel('Rx port');
title('Normalized noise correlation magnitude');
colormap(gca,turbo(256)); colorbar;
exportgraphics(f3,fullfile(outDir,'03_Rx_noise_covariance.png'), ...
    'Resolution',exportResolution);

%% ROI statistics and Figure 04: SNR, UISNR, and efficiency
X = RHBM.r(:,:,:,1);
Y = RHBM.r(:,:,:,2);
Z = RHBM.r(:,:,:,3);
roiRadiusM = roiRadiusMM*1e-3;
roi = valid & (X.^2 + Y.^2 + Z.^2 <= roiRadiusM^2);
roiValues = ratio(roi);
assert(~isempty(roiValues),'Central ROI contains no valid SNR/UISNR values');
ratioMean = mean(roiValues,'omitnan');
ratioMedian = median(roiValues,'omitnan');
ratioMin = min(roiValues,[],'omitnan');
ratioMax = max(roiValues,[],'omitnan');

f4 = figure('Color','w','Position',[100 30 650 1650]);
tiledlayout(4,1,'Padding','compact','TileSpacing','compact');

nexttile;
plotMap(x,y,RHBM.epsilon_r(:,:,iz0),mask(:,:,iz0),'Phantom epsilon_r','');
nexttile;
plotMap(x,y,SNR(:,:,iz0),mask(:,:,iz0), ...
    sprintf('%d-channel optimal-combination SNR',nPorts),'');
nexttile;
plotMap(x,y,UISNR(:,:,iz0),mask(:,:,iz0),'UISNR','');
nexttile;
plotMap(x,y,ratio(:,:,iz0),mask(:,:,iz0), ...
    sprintf('SNR/UISNR (%%): ROI mean %.1f%%, max %.1f%%',ratioMean,ratioMax),'%');
clim(efficiencyColorLimitsPercent); hold on;
theta = linspace(0,2*pi,300);
plot(roiRadiusMM*cos(theta),roiRadiusMM*sin(theta),'c:','LineWidth',1.5);
exportgraphics(f4,fullfile(outDir,'04_SNR_UISNR_efficiency.png'), ...
    'Resolution',exportResolution);

%% Figure 05: orthogonal central SNR/UISNR profiles
profileX = squeeze(ratio(:,iy0,iz0));
profileY = squeeze(ratio(ix0,:,iz0));
profileZ = squeeze(ratio(ix0,iy0,:));
profiles = {profileX,profileY,profileZ};
axesMM = {x,y,z};
axisNames = {'x','y','z'};
profileMean = NaN(1,3);
profileMax = NaN(1,3);

f5 = figure('Color','w','Position',[100 100 1450 460]);
tiledlayout(1,3,'Padding','compact','TileSpacing','compact');
for k = 1:3
    values = profiles{k};
    coordinate = axesMM{k};
    inRoi = abs(coordinate) <= roiRadiusMM & isfinite(values);
    profileMean(k) = mean(values(inRoi),'omitnan');
    profileMax(k) = max(values(inRoi),[],'omitnan');
    nexttile;
    plot(coordinate,values,'LineWidth',2); hold on;
    xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:'); yline(100,'k:');
    grid on; ylim(efficiencyColorLimitsPercent);
    xlabel(sprintf('%s (mm)',axisNames{k})); ylabel('SNR/UISNR (%)');
    title(sprintf('%s centerline: mean %.1f%%, max %.1f%%', ...
        axisNames{k},profileMean(k),profileMax(k)));
end
sgtitle(sprintf('SNR/UISNR central profiles at [%.1f %.1f %.1f] mm', ...
    x(ix0),y(iy0),z(iz0)));
exportgraphics(f5,fullfile(outDir,'05_SNR_UISNR_centerline_profiles.png'), ...
    'Resolution',exportResolution);

%% Optional Figure 06: Tx SAR, B1+ efficiency, and local SAR efficiency
txSummary = exportTxAssessment(projectRoot,txResultName,solution,RHBM,mask, ...
    ix0,iy0,iz0,x,y,z,outDir,exportResolution,txDisplayPercentile, ...
    defaultMassDensityKgM3,txWeightsUser);

%% Save numeric products for repeatable analysis
profileAxis = [repmat("x",numel(x),1); repmat("y",numel(y),1); repmat("z",numel(z),1)];
coordinateMM = [x(:); y(:); z(:)];
efficiencyPercent = [profileX(:); profileY(:); profileZ(:)];
profileTable = table(profileAxis,coordinateMM,efficiencyPercent, ...
    isfinite(efficiencyPercent),'VariableNames', ...
    {'Axis','Coordinate_mm','SNR_UISNR_percent','InsidePhantom'});
writetable(profileTable,fullfile(outDir,'05_SNR_UISNR_centerline_profiles.csv'));

couplingDB = SdB;
couplingDB(1:nPorts+1:end) = -Inf;
[worstCouplingDB,worstIndex] = max(couplingDB,[],'all');
[worstRow,worstCol] = ind2sub(size(couplingDB),worstIndex);

summary = struct();
summary.result_file = resultFile;
summary.frequency_MHz = targetMHz;
summary.SP_s_dB = SdB;
summary.SP_p_dB = SPpDB;
summary.SP_p_diagonal_dB = SPpDiagonalDB;
summary.worst_coupling = sprintf('S%d%d = %.3f dB',worstRow,worstCol,worstCouplingDB);
summary.SNR_avg = solution.snr_field.SNR_avg;
summary.roi_radius_mm = roiRadiusMM;
summary.roi_SNR_UISNR_percent = struct('mean',ratioMean,'median',ratioMedian, ...
    'min',ratioMin,'max',ratioMax);
summary.center_voxel_mm = [x(ix0) y(iy0) z(iz0)];
summary.centerline_mean_percent = profileMean;
summary.centerline_max_percent = profileMax;
summary.noise_covariance = PhiNoise;
summary.noise_correlation = noiseCorrelation;
summary.transmit = txSummary;
save(fullfile(outDir,'summary_metrics.mat'),'summary','-v7.3');

fprintf('\nSaved postprocessing outputs to: %s\n',outDir);
fprintf('Rx SP_p diagonal range: %.2f to %.2f dB\n', ...
    min(SPpDiagonalDB),max(SPpDiagonalDB));
fprintf('Worst SP_s coupling: S%d%d = %.2f dB\n', ...
    worstRow,worstCol,worstCouplingDB);
fprintf('ROI SNR/UISNR: mean %.2f%%, median %.2f%%, max %.2f%%\n', ...
    ratioMean,ratioMedian,ratioMax);

function plotMap(x,y,data,mask,titleText,colorbarLabel)
    map = data;
    map(~mask) = NaN;
    imagesc(x,y,map');
    axis image xy;
    xlabel('x (mm)'); ylabel('y (mm)'); title(titleText);
    colormap(gca,hot(256));
    cb = colorbar;
    if ~isempty(colorbarLabel), cb.Label.String = colorbarLabel; end
end

function txSummary = exportTxAssessment(projectRoot,txResultName,rxSolution, ...
        RHBM,mask,ix0,iy0,iz0,x,y,z,outDir,resolution,displayPercentile, ...
        defaultDensity,txWeightsUser)
    txSummary = struct('available',false,'source_file','','reason','');
    if isempty(txResultName)
        txSolution = rxSolution;
        txSummary.source_file = 'Rx result';
    else
        txFile = fullfile(projectRoot,'data','solutions',txResultName);
        if ~isfile(txFile)
            txSummary.reason = sprintf('Tx result is missing: %s',txFile);
            warning('%s',txSummary.reason);
            return;
        end
        T = load(txFile,'solution');
        txSolution = T.solution;
        txSummary.source_file = txFile;
    end

    required = isfield(txSolution,'h_field') && isfield(txSolution.h_field,'Tx') && ...
        isfield(txSolution.h_field.Tx,'b1p') && isfield(txSolution,'e_field') && ...
        isfield(txSolution.e_field,'Tx') && isfield(txSolution.e_field.Tx,'e_b');
    if ~required
        txSummary.reason = 'No genuine Tx b1p/e_b fields; Tx assessment skipped.';
        warning('%s',txSummary.reason);
        return;
    end

    try
        B1pPorts = txSolution.h_field.Tx.b1p;
        Eports = txSolution.e_field.Tx.e_b;
        nTx = size(B1pPorts,4);
        assert(size(Eports,5)==nTx,'Tx E-field port dimension is inconsistent');

        TxE = txSolution.e_field.Tx;
        PhiTx = TxE.phi + TxE.phi_coil + TxE.phi_lump;
        if isfield(txSolution.netp,'phi_lumped_elements') && ...
                isfield(txSolution.netp.phi_lumped_elements,'Tx')
            PhiTx = PhiTx + txSolution.netp.phi_lumped_elements.Tx;
        end
        PhiTx = 0.5*(PhiTx + PhiTx');

        centerB1p = squeeze(B1pPorts(ix0,iy0,iz0,:));
        if isempty(txWeightsUser)
            w = PhiTx\conj(centerB1p);
            shimText = 'Loss-optimal center B1+ shim';
        else
            assert(numel(txWeightsUser)==nTx,'Tx weight count does not match port count');
            w = txWeightsUser(:);
            shimText = 'User-specified Tx shim';
        end
        powerW = real(w'*PhiTx*w);
        assert(isfinite(powerW) && powerW>0,'Tx loss normalization is invalid');
        w = w/sqrt(powerW);

        B1p = sum(B1pPorts.*reshape(w,1,1,1,[]),4);
        b1pEfficiency = abs(B1p)*1e6;

        Ecombined = sum(Eports.*reshape(w,1,1,1,1,[]),5);
        ql = size(Ecombined,4);
        assert(mod(ql,3)==0,'Unexpected Tx E-field component layout');
        stride = ql/3;
        pabs = 0.5*RHBM.sigma_e.*(abs(Ecombined(:,:,:,1)).^2 + ...
            abs(Ecombined(:,:,:,1+stride)).^2 + ...
            abs(Ecombined(:,:,:,1+2*stride)).^2);
        if isfield(RHBM,'mass_rho') && isequal(size(RHBM.mass_rho),size(mask))
            rho = RHBM.mass_rho;
            rho(~isfinite(rho) | rho<=0) = defaultDensity;
        else
            rho = defaultDensity*ones(size(mask));
        end
        voxelSAR = NaN(size(mask));
        voxelSAR(mask) = pabs(mask)./rho(mask);
        localSAREff = NaN(size(mask));
        validSAR = mask & voxelSAR>0 & isfinite(voxelSAR);
        localSAREff(validSAR) = b1pEfficiency(validSAR)./sqrt(voxelSAR(validSAR));

        metrics = {voxelSAR,b1pEfficiency,localSAREff};
        names = {'Voxel SAR','B1+ efficiency','Local SAR efficiency'};
        units = {'W/kg','microT/sqrt(W)','microT/sqrt(W/kg)'};
        f = figure('Color','w','Position',[40 40 1550 1220]);
        tiledlayout(3,3,'Padding','compact','TileSpacing','compact');
        for m = 1:3
            values = metrics{m}(mask & isfinite(metrics{m}));
            vmax = prctile(values,displayPercentile);
            planes = {metrics{m}(:,:,iz0)',squeeze(metrics{m}(:,iy0,:))', ...
                squeeze(metrics{m}(ix0,:,:))'};
            planeX = {x,x,y}; planeY = {y,z,z};
            planeNames = {'Axial z=0','Coronal y=0','Sagittal x=0'};
            for p = 1:3
                nexttile;
                imagesc(planeX{p},planeY{p},planes{p}); axis image xy;
                clim([0 vmax]); colormap(gca,hot(256));
                xlabel('Coordinate (mm)'); ylabel('Coordinate (mm)');
                title(sprintf('%s: %s',names{m},planeNames{p}));
                cb = colorbar; cb.Label.String = units{m};
            end
        end
        sgtitle(sprintf('Tx assessment, 1 W total loss normalization: %s',shimText));
        exportgraphics(f,fullfile(outDir,'06_Tx_SAR_B1p_SAReff_orthogonal_planes.png'), ...
            'Resolution',resolution);

        txSummary.available = true;
        txSummary.reason = 'Voxel SAR only; this is not 1g/10g mass-averaged SAR.';
        txSummary.shim = shimText;
        txSummary.weights_1sqrtW = w;
        txSummary.center_B1p_uT_sqrtW = b1pEfficiency(ix0,iy0,iz0);
        txSummary.max_voxel_SAR_W_kg = max(voxelSAR,[],'all','omitnan');
    catch ME
        txSummary.reason = sprintf('Tx assessment skipped: %s',ME.message);
        warning('%s',txSummary.reason);
    end
end
