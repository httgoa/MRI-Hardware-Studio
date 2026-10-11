%% POST_5T_8CH_SPHERE
% MARIE 3.0 后处理：5 T、8通道Loop接收阵列、200 mm均匀球形体模。
%
% 主要输出：
%   1. SP_s矩阵和前放加载回波损耗频扫；
%   2. 八通道B1-中心横断面；
%   3. phantom、阵列SNR、UISNR和SNR/UISNR效率图；
%   4. x、y、z三条正交中心线上的SNR/UISNR定量剖线；
%   5. 中心线CSV和数值摘要MAT文件。
%
% 重要说明：
%   - SP_s非对角元素用于检查通道互耦；
%   - 纯Rx匹配应检查SP_p或SPm_plot_Rx，不能只看SP_s对角线；
%   - SNR/UISNR只有在体模、频率、网格和归一化一致时才有意义。

close all;
clearvars;
clc;

%% 1. 用户配置区
% 修改项目路径或结果文件名时，优先只改本节。
projectRoot = getenv('MARIE_ROOT');
if isempty(projectRoot)
    error('MARIE:Config', 'Set MARIE_ROOT to the active marie-tools workspace.');
end

arrayResultName = 'MARIE_1_inp_5T_1H_Sphere200_8LoopRx.mat';
bodyRelativePath = fullfile('Scatterers','4mm', ...
    'Sphere_D200mm_4mm_eps50_sig0p6_5T.mat');
basisResultName = 'Sphere200_5T_PWC_CylSupport_UISNR.mat';

% 发射结果文件。留空表示尝试从arrayResultName读取Tx字段；如果收发
% 仿真分开运行，则填写包含真实h_field.Tx和e_field.Tx的MAT文件名。
txResultName = '';

% 自定义复数Tx权重。留空时使用总损耗约束下最大化球心B1+的幅相shim；
% 非空时长度必须等于Tx端口数。无论哪种输入，随后都会归一化到1 W。
txWeightsUser = [];

% 当体模没有mass_rho字段时使用的质量密度，仅适合当前均匀水样球体。
% 人体模型必须提供逐体素质量密度，不能使用这一统一回退值。
defaultMassDensityKgM3 = 1000;

% 发射图色轴采用体模内有限值的该百分位，避免少量热点压低主体对比度。
txDisplayPercentile = 99;

% 输出目录及图片分辨率。
outputFolderName = 'figures_5T_8ch';
exportResolution = 300;

% 中央球形ROI半径。40 mm对应直径80 mm的ROI。
roiRadiusMM = 40;

% 仅用于画图显示，不改变原始数据。
sMatrixColorLimitsDB = [-40 -5];
sweepYLimitsDB = [-40 0];
efficiencyColorLimitsPercent = [0 100];

cd(projectRoot);
startup;

%% 2. 构造路径并检查输入文件
resultFile = fullfile(projectRoot,'data','solutions',arrayResultName);
bodyFile = fullfile(projectRoot,'data','bodies',bodyRelativePath);
basisFile = fullfile(projectRoot,'data','bases',basisResultName);
outDir = fullfile(projectRoot,'data','solutions',outputFolderName);

if ~exist(outDir,'dir')
    mkdir(outDir);
end

assert(isfile(resultFile),'Regular-array result is missing: %s',resultFile);
assert(isfile(bodyFile),'Body model is missing: %s',bodyFile);
assert(isfile(basisFile), ...
    ['UISNR/BASIS result is missing. Run RUN_5T_SPHERE_UISNR ', ...
     'before this postprocessor: %s'],basisFile);

%% 3. 只加载后处理所需顶层变量
% 常规阵列结果只保存solution；体模和UISNR结果分别保存RHBM和BASIS。
R = load(resultFile,'solution');
B = load(bodyFile,'RHBM');
Q = load(basisFile,'BASIS');

solution = R.solution;
RHBM = B.RHBM;
BASIS = Q.BASIS;

% 发射结果可以与接收结果来自同一个solution，也可以来自单独的Tx仿真。
if isempty(txResultName)
    txSolution = solution;
    txResultFile = resultFile;
else
    txResultFile = fullfile(projectRoot,'data','solutions',txResultName);
    assert(isfile(txResultFile),'Transmit result is missing: %s',txResultFile);
    T = load(txResultFile,'solution');
    txSolution = T.solution;
end

assert(isfield(solution,'netp') && isfield(solution.netp,'SP_s'), ...
    'solution.netp.SP_s is missing');
assert(isfield(solution,'h_field') && isfield(solution.h_field,'Rx'), ...
    'Rx magnetic fields are missing');
assert(isfield(solution,'snr_field') && isfield(solution.snr_field,'SNR'), ...
    'Array SNR is missing');
assert(isfield(BASIS,'UISNR'),'BASIS.UISNR is missing');

%% 4. 建立体模掩膜、坐标轴和中心体素索引
% MARIE坐标单位是m；显示和CSV输出统一换算为mm。
mask = false(size(RHBM.epsilon_r));
mask(RHBM.idxS) = true;

x = squeeze(RHBM.r(:,1,1,1))*1e3;
y = squeeze(RHBM.r(1,:,1,2))*1e3;
z = squeeze(RHBM.r(1,1,:,3))*1e3;

% 选取距离0 mm最近的体素。即使网格不精确包含原点也能工作。
[~,ix0] = min(abs(x));
[~,iy0] = min(abs(y));
[~,iz0] = min(abs(z));

fprintf('Selected center voxel: x=%.3f, y=%.3f, z=%.3f mm\n', ...
    x(ix0),y(iy0),z(iz0));

%% 5. 检查阵列SNR和UISNR是否可以逐体素比较
SNR = real(solution.snr_field.SNR);
UISNR = real(BASIS.UISNR);

assert(isequal(size(SNR),size(UISNR)), ...
    'SNR and UISNR grids differ; do not interpolate silently');
assert(isequal(size(SNR),size(mask)), ...
    'SNR and body-mask grids differ');

% ratio使用百分数。体模外、非有限值和UISNR<=0的位置保持NaN。
ratio = NaN(size(SNR));
valid = mask & isfinite(SNR) & isfinite(UISNR) & UISNR>0;
ratio(valid) = 100*SNR(valid)./UISNR(valid);

if any(ratio(valid)>100.5)
    warning(['SNR/UISNR exceeds 100%%. Check grid, frequency, material ', ...
        'properties and normalization before interpreting the result.']);
end

%% 6. Figure 1：SP_s矩阵和前放加载频扫
SP = solution.netp.SP_s;
SdB = 20*log10(abs(SP));
nPorts = size(SP,1);
F = solution.netp.figure_freq;
targetMHz = F.freq_range(F.freq_idx)/1e6;

f1 = figure('Color','w','Position',[100 100 1250 470]);
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

% 左图包括SP_s对角线和非对角线。评价去耦时只使用非对角线。
nexttile;
imagesc(SdB,sMatrixColorLimitsDB);
axis image; set(gca,'YDir','normal');
set(gca,'XTick',1:nPorts,'YTick',1:nPorts);
xlabel('Excited port'); ylabel('Observed port');
title(sprintf('SP_s at %.3f MHz (dB)',targetMHz));
colormap(gca,hot(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        text(col,row,sprintf('%.1f',SdB(row,col)), ...
            'HorizontalAlignment','center','Color','c','FontSize',9);
    end
end

% 右图是前置放大器加载条件下的Rx回波损耗频扫。
nexttile; hold on;
if isfield(F,'SPm_plot_Rx') && ~isempty(F.SPm_plot_Rx)
    for p = 1:nPorts
        curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
        plot(F.freq_range/1e6,curve,'LineWidth',1.5, ...
            'DisplayName',sprintf('S_{%d%d}',p,p));
    end
    xline(targetMHz,'k--','Target');
    yline(-15,'r:','-15 dB');
    ylim(sweepYLimitsDB); grid on;
    xlabel('Frequency (MHz)'); ylabel('Return loss (dB)');
    title('Preamplifier-loaded Rx frequency sweep');
    legend('Location','eastoutside');
else
    text(0.5,0.5,'No Rx frequency sweep', ...
        'HorizontalAlignment','center');
    axis off;
end

exportgraphics(f1,fullfile(outDir,'01_Sparams_and_sweep.png'), ...
    'Resolution',exportResolution);

%% 7. Figure 2：八通道B1-中心横断面
B1m = solution.h_field.Rx.b1m;
assert(size(B1m,4)==8,'Expected eight Rx B1- field maps');

% 先求全部通道的共同最大值，保证八幅图使用相同色标。
b1Display = abs(B1m(:,:,iz0,:))*1e6;  % T -> microT
b1ColorMax = max(b1Display,[],'all','omitnan');

f2 = figure('Color','w','Position',[100 100 1450 650]);
tiledlayout(2,4,'Padding','compact','TileSpacing','compact');
for p = 1:8
    map = squeeze(b1Display(:,:,1,p));
    map(~mask(:,:,iz0)) = NaN;
    nexttile;
    imagesc(x,y,map'); axis image xy;
    clim([0 b1ColorMax]);
    xlabel('x (mm)'); ylabel('y (mm)');
    title(sprintf('|B1-|, Rx %d (microT)',p));
    colormap(gca,hot(256)); colorbar;
end

exportgraphics(f2,fullfile(outDir,'02_B1minus_8channels.png'), ...
    'Resolution',exportResolution);

%% 7A. Figure 2B：接收噪声协方差及归一化噪声相关矩阵
% MARIE的接收总噪声矩阵由体模损耗、线圈导体损耗、集总元件损耗和
% co-simulation额外元件损耗组成。它正是em_SNR中使用的矩阵。
RxE = solution.e_field.Rx;
PhiNoise = RxE.phi + RxE.phi_coil + RxE.phi_lump;
if isfield(solution.netp,'phi_lumped_elements') && ...
        isfield(solution.netp.phi_lumped_elements,'Rx')
    PhiNoise = PhiNoise + solution.netp.phi_lumped_elements.Rx;
end

% 消除浮点误差造成的微小非厄米分量。
PhiNoise = 0.5*(PhiNoise + PhiNoise');
assert(size(PhiNoise,1)==nPorts && size(PhiNoise,2)==nPorts, ...
    'Rx noise covariance dimensions do not match the number of ports');

noiseStd = sqrt(max(real(diag(PhiNoise)),0));
noiseDenominator = noiseStd*noiseStd.';
noiseCorrelation = NaN(size(PhiNoise));
validNoise = noiseDenominator>0;
noiseCorrelation(validNoise) = ...
    PhiNoise(validNoise)./noiseDenominator(validNoise);

f2b = figure('Color','w','Position',[100 100 1050 440]);
tiledlayout(1,2,'Padding','compact','TileSpacing','compact');

nexttile;
imagesc(abs(PhiNoise)); axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Rx port'); ylabel('Rx port');
title('|Total noise covariance \Phi|');
colormap(gca,turbo(256)); colorbar;

nexttile;
imagesc(abs(noiseCorrelation),[0 1]);
axis image; set(gca,'YDir','normal');
xticks(1:nPorts); yticks(1:nPorts);
xlabel('Rx port'); ylabel('Rx port');
title('Normalized noise correlation magnitude');
colormap(gca,turbo(256)); colorbar;
for row = 1:nPorts
    for col = 1:nPorts
        text(col,row,sprintf('%.2f',abs(noiseCorrelation(row,col))), ...
            'HorizontalAlignment','center','Color','w','FontSize',8);
    end
end

exportgraphics(f2b,fullfile(outDir, ...
    '02B_Rx_noise_covariance.png'),'Resolution',exportResolution);

%% 8. 计算中央球形ROI统计量
X = RHBM.r(:,:,:,1);
Y = RHBM.r(:,:,:,2);
Z = RHBM.r(:,:,:,3);
roiRadiusM = roiRadiusMM*1e-3;
roi = mask & valid & (X.^2+Y.^2+Z.^2 <= roiRadiusM^2);
roiValues = ratio(roi);

assert(~isempty(roiValues),'The configured central ROI contains no data');
ratioMean = mean(roiValues,'omitnan');
ratioMedian = median(roiValues,'omitnan');
ratioMin = min(roiValues,[],'omitnan');
ratioMax = max(roiValues,[],'omitnan');

%% 9. Figure 3：phantom、SNR、UISNR和效率中心横断面
f3 = figure('Color','w','Position',[100 50 520 1350]);
tiledlayout(4,1,'Padding','compact','TileSpacing','compact');

nexttile;
anatomy = RHBM.epsilon_r(:,:,iz0);
anatomy(~mask(:,:,iz0)) = NaN;
imagesc(x,y,anatomy'); axis image xy;
title('Phantom epsilon_r');
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,gray(256)); colorbar;

nexttile;
snrMap = SNR(:,:,iz0);
snrMap(~mask(:,:,iz0)) = NaN;
imagesc(x,y,snrMap'); axis image xy;
title('8-channel optimal-combination SNR');
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar;

nexttile;
uisnrMap = UISNR(:,:,iz0);
uisnrMap(~mask(:,:,iz0)) = NaN;
imagesc(x,y,uisnrMap'); axis image xy;
title('UISNR');
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar;

nexttile;
ratioMap = ratio(:,:,iz0);
imagesc(x,y,ratioMap'); axis image xy;
clim(efficiencyColorLimitsPercent);
title(sprintf(['SNR/UISNR (%%), ROI mean %.1f%%, ', ...
    'median %.1f%%, max %.1f%%'],ratioMean,ratioMedian,ratioMax));
xlabel('x (mm)'); ylabel('y (mm)');
colormap(gca,hot(256)); colorbar; hold on;

% 青色虚线圆表示中心横断面上的ROI边界。
theta = linspace(0,2*pi,300);
plot(roiRadiusMM*cos(theta),roiRadiusMM*sin(theta), ...
    'c:','LineWidth',1.5);

exportgraphics(f3,fullfile(outDir,'03_SNR_UISNR_efficiency.png'), ...
    'Resolution',exportResolution);

%% 10. Figure 4：x、y、z三条正交中心线的SNR/UISNR剖线
% x剖线：改变x，固定y和z为距离0最近的体素。
% y剖线：改变y，固定x和z为距离0最近的体素。
% z剖线：改变z，固定x和y为距离0最近的体素。
profileX = squeeze(ratio(:,iy0,iz0));
profileY = squeeze(ratio(ix0,:,iz0));
profileZ = squeeze(ratio(ix0,iy0,:));

% 每条剖线在中央+-roiRadiusMM范围内的统计量。
xRoiValues = profileX(abs(x)<=roiRadiusMM & isfinite(profileX));
yRoiValues = profileY(abs(y)<=roiRadiusMM & isfinite(profileY));
zRoiValues = profileZ(abs(z)<=roiRadiusMM & isfinite(profileZ));

profileMean = [mean(xRoiValues,'omitnan'), ...
               mean(yRoiValues,'omitnan'), ...
               mean(zRoiValues,'omitnan')];
profileMax = [max(xRoiValues,[],'omitnan'), ...
              max(yRoiValues,[],'omitnan'), ...
              max(zRoiValues,[],'omitnan')];

f4 = figure('Color','w','Position',[100 100 1450 430]);
tiledlayout(1,3,'Padding','compact','TileSpacing','compact');

nexttile;
plot(x,profileX,'b-','LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
yline(100,'k:'); grid on;
xlabel('x (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('x centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(1),profileMax(1)));
ylim(efficiencyColorLimitsPercent);

nexttile;
plot(y,profileY,'r-','LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
yline(100,'k:'); grid on;
xlabel('y (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('y centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(2),profileMax(2)));
ylim(efficiencyColorLimitsPercent);

nexttile;
plot(z,profileZ,'Color',[0.15 0.60 0.25],'LineWidth',2); hold on;
xline(-roiRadiusMM,'c:'); xline(roiRadiusMM,'c:');
yline(100,'k:'); grid on;
xlabel('z (mm)'); ylabel('SNR/UISNR (%)');
title(sprintf('z centerline: mean %.1f%%, max %.1f%%', ...
    profileMean(3),profileMax(3)));
ylim(efficiencyColorLimitsPercent);

sgtitle(sprintf(['Orthogonal centerline efficiency; center voxel ', ...
    '(%.1f, %.1f, %.1f) mm'],x(ix0),y(iy0),z(iz0)));

exportgraphics(f4,fullfile(outDir, ...
    '04_SNR_UISNR_centerline_profiles.png'), ...
    'Resolution',exportResolution);

%% 10A. Figure 5：真实Tx结果的SAR、B1+效率和局部SAR效率
% 只有结果中同时存在h_field.Tx.b1p和e_field.Tx.e_b时才进行发射评估。
% 纯Rx结果虽然可能带有txe_field，但那是互易性回退指标，不满足正式
% Tx功率归一化和SAR评价的条件，因此本节不会使用它代替真实Tx字段。
hasTx = isfield(txSolution,'h_field') && ...
        isfield(txSolution.h_field,'Tx') && ...
        isfield(txSolution.h_field.Tx,'b1p') && ...
        isfield(txSolution,'e_field') && ...
        isfield(txSolution.e_field,'Tx') && ...
        isfield(txSolution.e_field.Tx,'e_b');

txSummary = struct('available',false,'source_file',txResultFile);

if hasTx
    TxH = txSolution.h_field.Tx;
    TxE = txSolution.e_field.Tx;
    B1pPorts = TxH.b1p;
    Eports = TxE.e_b;
    nTx = size(B1pPorts,4);

    assert(isequal(size(B1pPorts,1),size(mask,1)) && ...
           isequal(size(B1pPorts,2),size(mask,2)) && ...
           isequal(size(B1pPorts,3),size(mask,3)), ...
        'Tx B1+ grid differs from the body grid');
    assert(size(Eports,5)==nTx,'Tx E-field and B1+ port counts differ');

    % 构造Tx总损耗矩阵，用于把驱动权重归一化到1 W总耗散功率。
    PhiTx = TxE.phi + TxE.phi_coil + TxE.phi_lump;
    if isfield(txSolution.netp,'phi_lumped_elements') && ...
            isfield(txSolution.netp.phi_lumped_elements,'Tx')
        PhiTx = PhiTx + txSolution.netp.phi_lumped_elements.Tx;
    end
    PhiTx = 0.5*(PhiTx + PhiTx');

    % 默认发射shim：在w'*PhiTx*w约束下最大化球心|B1+|。
    % 若提供txWeightsUser，则使用用户指定的相对幅度和相位。
    centerB1p = squeeze(B1pPorts(ix0,iy0,iz0,:));
    assert(any(abs(centerB1p)>0),'All Tx B1+ values are zero at the center');
    if isempty(txWeightsUser)
        txWeights = PhiTx\conj(centerB1p);
        txShimDescription = ...
            'Loss-optimal complex shim maximizing B1+ at body center';
    else
        assert(numel(txWeightsUser)==nTx, ...
            'txWeightsUser length must equal the number of Tx ports');
        txWeights = txWeightsUser(:);
        txShimDescription = 'User-specified complex shim';
    end
    dissipatedPowerW = real(txWeights'*PhiTx*txWeights);
    assert(isfinite(dissipatedPowerW) && dissipatedPowerW>0, ...
        'Tx loss matrix does not produce positive dissipated power');
    txWeights = txWeights/sqrt(dissipatedPowerW);  % w'*PhiTx*w = 1 W

    % 合成复数B1+。归一化后其数值对应1 W总耗散下的场强。
    B1pCombined = zeros(size(mask),'like',B1pPorts);
    for p = 1:nTx
        B1pCombined = B1pCombined + B1pPorts(:,:,:,p).*txWeights(p);
    end
    B1pEfficiency = abs(B1pCombined)*1e6;  % microT/sqrt(W)

    % 按MARIE原始pabs实现使用E场的三个笛卡尔分量。
    ql = size(Eports,4);
    assert(mod(ql,3)==0,'Unexpected Tx E-field basis dimension');
    componentStride = ql/3;
    Ecombined = zeros(size(Eports,1),size(Eports,2), ...
        size(Eports,3),ql,'like',Eports);
    for p = 1:nTx
        Ecombined = Ecombined + Eports(:,:,:,:,p).*txWeights(p);
    end
    Ex = Ecombined(:,:,:,1);
    Ey = Ecombined(:,:,:,1+componentStride);
    Ez = Ecombined(:,:,:,1+2*componentStride);

    % 体素吸收功率密度pabs = sigma*|E|^2/2，单位W/m^3。
    pabsCombined = 0.5*RHBM.sigma_e.* ...
        (abs(Ex).^2 + abs(Ey).^2 + abs(Ez).^2);

    % 优先使用体模逐体素质量密度；均匀球缺失时回退到1000 kg/m^3。
    if isfield(RHBM,'mass_rho') && ...
            isequal(size(RHBM.mass_rho),size(mask))
        massDensity = double(RHBM.mass_rho);
        badDensity = mask & (~isfinite(massDensity) | massDensity<=0);
        if any(badDensity,'all')
            warning('Invalid mass density inside body; applying configured fallback');
            massDensity(badDensity) = defaultMassDensityKgM3;
        end
    else
        warning(['RHBM.mass_rho is missing; using %.1f kg/m^3. ', ...
            'This fallback is only appropriate for the current uniform sphere.'], ...
            defaultMassDensityKgM3);
        massDensity = defaultMassDensityKgM3*ones(size(mask));
    end

    % 这是点式体素SAR，不是IEC/IEEE规定的1 g或10 g质量平均SAR。
    voxelSAR = NaN(size(mask));
    voxelSAR(mask) = pabsCombined(mask)./massDensity(mask);  % W/kg

    % 局部SAR效率是同一位置的B1+除以sqrt(voxel SAR)。它用于场形态
    % 诊断，不等同于以峰值10 g SAR归一化的法规/设计SAR效率。
    localSAREfficiency = NaN(size(mask));
    validSAR = mask & isfinite(voxelSAR) & voxelSAR>0;
    localSAREfficiency(validSAR) = ...
        B1pEfficiency(validSAR)./sqrt(voxelSAR(validSAR));

    % 三行分别为SAR、B1+效率和局部SAR效率；三列为轴位、冠状和矢状面。
    metricVolumes = {voxelSAR,B1pEfficiency,localSAREfficiency};
    metricNames = {'Voxel SAR','B1+ efficiency','Local SAR efficiency'};
    metricUnits = {'W/kg','microT/sqrt(W)','microT/sqrt(W/kg)'};
    metricCLim = zeros(3,2);
    for m = 1:3
        values = metricVolumes{m}(mask & isfinite(metricVolumes{m}));
        values = sort(values(:));
        percentileIndex = max(1,min(numel(values), ...
            ceil(txDisplayPercentile/100*numel(values))));
        metricCLim(m,:) = [0 values(percentileIndex)];
    end

    f5 = figure('Color','w','Position',[50 50 1450 1200]);
    layout5 = tiledlayout(3,3,'Padding','compact','TileSpacing','compact');
    planeNames = {'Axial z=0','Coronal y=0','Sagittal x=0'};
    planeXLabels = {'x','x','y'};

    for m = 1:3
        V = metricVolumes{m};
        planeData = {V(:,:,iz0)',squeeze(V(:,iy0,:))', ...
                     squeeze(V(ix0,:,:))'};
        planeX = {x,x,y};
        planeY = {y,z,z};
        for plane = 1:3
            nexttile(layout5,(m-1)*3+plane);
            imagesc(planeX{plane},planeY{plane},planeData{plane});
            axis image xy; clim(metricCLim(m,:));
            xlabel(sprintf('%s (mm)',planeXLabels{plane}));
            if plane==1
                ylabel('y (mm)');
            else
                ylabel('z (mm)');
            end
            title(sprintf('%s: %s',metricNames{m},planeNames{plane}));
            colormap(gca,hot(256));
            cb = colorbar; cb.Label.String = metricUnits{m};
        end
    end
    sgtitle(sprintf(['Tx assessment: 1 W total ', ...
        'dissipated-power normalization; display P%d'],txDisplayPercentile));

    exportgraphics(f5,fullfile(outDir, ...
        '05_Tx_SAR_B1p_SAReff_orthogonal_planes.png'), ...
        'Resolution',exportResolution);

    txSummary.available = true;
    txSummary.shim_description = txShimDescription;
    txSummary.weights_1sqrtW = txWeights;
    txSummary.Phi_total = PhiTx;
    txSummary.normalization_W = real(txWeights'*PhiTx*txWeights);
    txSummary.B1p_efficiency_center_uT_sqrtW = ...
        B1pEfficiency(ix0,iy0,iz0);
    txSummary.voxel_SAR_max_W_kg = max(voxelSAR,[],'all','omitnan');
    txSummary.warning = ...
        'Voxel SAR and local SAR efficiency are not 1g/10g mass averaged.';
else
    warning(['Transmit assessment skipped: %s has no real h_field.Tx.b1p ', ...
        'and e_field.Tx.e_b. Run a Tx or TxRx simulation; Rx-only txe_field ', ...
        'is not sufficient for formal SAR assessment.'],txResultFile);
end

%% 11. 导出中心线数据到CSV
% 使用长表格式，方便Excel、Python、Origin或R按axis分组绘图。
profileAxis = [repmat("x",numel(x),1); ...
               repmat("y",numel(y),1); ...
               repmat("z",numel(z),1)];
coordinateMM = [x(:); y(:); z(:)];
efficiencyPercent = [profileX(:); profileY(:); profileZ(:)];
insidePhantom = isfinite(efficiencyPercent);

profileTable = table(profileAxis,coordinateMM,efficiencyPercent, ...
    insidePhantom,'VariableNames', ...
    {'Axis','Coordinate_mm','SNR_UISNR_percent','InsidePhantom'});
writetable(profileTable,fullfile(outDir, ...
    '04_SNR_UISNR_centerline_profiles.csv'));

%% 12. 保存数值摘要，供后续批量比较
summary = struct();
summary.frequency_MHz = targetMHz;
summary.SdB = SdB;
summary.SNR_avg = solution.snr_field.SNR_avg;
summary.SNR_UISNR_ROI_radius_mm = roiRadiusMM;
summary.SNR_UISNR_ROI_mean_percent = ratioMean;
summary.SNR_UISNR_ROI_median_percent = ratioMedian;
summary.SNR_UISNR_ROI_min_percent = ratioMin;
summary.SNR_UISNR_ROI_max_percent = ratioMax;
summary.center_voxel_mm = [x(ix0) y(iy0) z(iz0)];
summary.centerline.axis = {'x','y','z'};
summary.centerline.coordinate_mm = {x,y,z};
summary.centerline.SNR_UISNR_percent = {profileX,profileY,profileZ};
summary.centerline.ROI_mean_percent = profileMean;
summary.centerline.ROI_max_percent = profileMax;
summary.noise_covariance.total = PhiNoise;
summary.noise_covariance.correlation = noiseCorrelation;
summary.transmit = txSummary;

save(fullfile(outDir,'summary_metrics.mat'),'summary');

%% 13. 命令行摘要
fprintf('\nFigures and tables saved to: %s\n',outDir);
fprintf('3-D ROI SNR/UISNR: mean %.2f%%, median %.2f%%, min %.2f%%, max %.2f%%\n', ...
    ratioMean,ratioMedian,ratioMin,ratioMax);
fprintf('Centerline ROI means [x y z] = [%.2f %.2f %.2f] %%\n',profileMean);
fprintf('Centerline ROI maxima [x y z] = [%.2f %.2f %.2f] %%\n',profileMax);
