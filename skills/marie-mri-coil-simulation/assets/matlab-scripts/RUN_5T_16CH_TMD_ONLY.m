% RUN_5T_16CH_TMD_ONLY
% Stage B: repeatedly optimize the circuit using a precomputed raw YPn.

close all
clearvars
clc

caseTag = '5T_Sphere200_16LoopRx_DoubleRow_H90';
caseName = 'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5';
showOptimizerProgress = true;
useLossAwareTMD = true;
targetReturnDB = -15;
useCouplingConstraint = true;
targetCouplingDB = -12;
useFullHardBounds = true;

rawNetworkFile = fullfile(pwd,'data','solutions', ...
    ['YPn_' caseTag '.mat']);
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    [caseName '.json']);

assert(exist(rawNetworkFile,'file')==2,'Raw YPn file is missing');
assert(exist(coilJson,'file')==2,'Coil JSON is missing');

load(rawNetworkFile,'YPn','network_meta');
assert(exist('YPn','var')==1 && ~isempty(YPn),'YPn was not loaded');
assert(abs(network_meta.frequency_Hz/1e6-212.88739259)<1e-6, ...
    'The raw network frequency does not match this 5 T proton case');

runTag = char(datetime('now','Format','yyyyMMdd_HHmmss'));
backupJson = [coilJson '.before_TMD_' runTag];
copyfile(coilJson,backupJson);

emc = em_constants(5,'1H');
RLC_org = geo_scoil_lumped_elements(coilJson,0);
RLC_tmd = geo_scoil_lumped_elements(coilJson,1);
Q_val = co_simulation_get_Q_values(RLC_tmd);
[options_PSO_1,options_PSO_2] = co_simulation_optimization_settings();
if useLossAwareTMD
    options_PSO_2.SwarmSize = 400;
    options_PSO_2.MaxIterations = 600;
    options_PSO_2.MaxStallIterations = 100;
    options_PSO_2.FunctionTolerance = 1e-4;
    options_PSO_2.ObjectiveLimit = 0.98;
end

% A raw TMD YPn contains temporary ports for every tunable element and
% cannot be passed to co_simulation_Rx_no_optim, which expects a calibrated
% physical-port network. Use the latest completed TMD round as the visual
% baseline instead. The first round has no calibrated baseline.
SPmBefore = [];
SPpBefore = [];
baselineLabel = 'No previous calibrated TMD round';
previousFiles = dir(fullfile(pwd,'data','solutions', ...
    ['TMD_' caseTag '_*.mat']));
if ~isempty(previousFiles)
    [~,order] = sort([previousFiles.datenum],'descend');
    previousFile = fullfile(previousFiles(order(1)).folder, ...
        previousFiles(order(1)).name);
    previous = load(previousFile,'netp');
    if isfield(previous,'netp') && ...
            isfield(previous.netp,'SP_s') && ...
            isfield(previous.netp,'SP_p') && ...
            isequal(size(previous.netp.SP_s),[16 16]) && ...
            numel(previous.netp.SP_p)==16
        SPmBefore = previous.netp.SP_s;
        SPpBefore = previous.netp.SP_p;
        baselineLabel = ['Previous TMD: ' previousFiles(order(1)).name];
    else
        warning('Latest TMD file is not a compatible 16-port baseline: %s', ...
            previousFile);
    end
end

% The live plot is the optimizer objective, not an S-parameter curve. The
% physically interpretable S-parameter comparison is generated below after
% the optimizer has returned a calibrated network.
if showOptimizerProgress && usejava('desktop')
    options_PSO_1.Display = 'iter';
    options_PSO_2.Display = 'iter';
    options_PSO_1.PlotFcn = @pswplotbestf;
    options_PSO_2.PlotFcn = @pswplotbestf;
end

if useLossAwareTMD
    if useCouplingConstraint
        fprintf(['Running joint loss/coupling-aware Rx TMD using precomputed ', ...
            'YPn (SP_p < %.1f dB, off-diagonal SP_s < %.1f dB) ...\n'], ...
            targetReturnDB,targetCouplingDB);
    else
        fprintf(['Running loss-aware standalone Rx TMD using precomputed YPn ', ...
            '(SP_p < %.1f dB) ...\n'],targetReturnDB);
    end
    [return_elements,phi_lumped_elements,M_cal,YPm,ZPm,SPm,SPp,figure_freq] = ...
        co_simulation_Rx_optim_loss_aware( ...
        YPn,emc,RLC_org,RLC_tmd,Q_val,options_PSO_1,options_PSO_2, ...
        targetReturnDB,targetCouplingDB,useCouplingConstraint, ...
        useFullHardBounds);
else
    fprintf('Running original standalone Rx TMD using precomputed YPn ...\n');
    [return_elements,phi_lumped_elements,M_cal,YPm,ZPm,SPm,SPp,figure_freq] = ...
        co_simulation_Rx_optim(YPn,emc,RLC_org,RLC_tmd,Q_val, ...
        options_PSO_1,options_PSO_2);
end

% This writes optimized element values back to coilJson.
N_ports = geo_scoil_print_lumped_elements( ...
    coilJson,RLC_org,RLC_tmd,return_elements);

netp = struct;
netp.YP_s = YPm;
netp.ZP_s = ZPm;
netp.SP_s = SPm;
netp.SP_p = SPp;
netp.figure_freq = figure_freq;
netp.phi_lumped_elements = phi_lumped_elements;
netp.M_cal = M_cal;
netp.N_ports = N_ports;

SPsDB = 20*log10(abs(SPm));
SPpDB = 20*log10(abs(SPp(:)));
F = figure_freq;
targetMHz = F.freq_range(F.freq_idx)/1e6;
nPorts = numel(SPpDB);
resonanceMHz = NaN(nPorts,1);
minimumDB = NaN(nPorts,1);

fprintf('Port | SP_p target | minimum | f_min MHz | status\n');
for p = 1:nPorts
    curve = 20*log10(abs(squeeze(F.SPm_plot_Rx(p,p,:))));
    [minimumDB(p),k] = min(curve);
    resonanceMHz(p) = F.freq_range(k)/1e6;
    if abs(resonanceMHz(p)-targetMHz) >= 0.5
        status = "DETUNED";
    elseif SPpDB(p) >= targetReturnDB
        status = "SHALLOW_MATCH";
    else
        status = "PASS";
    end
    fprintf('%4d | %11.3f | %7.3f | %9.4f | %s\n', ...
        p,SPpDB(p),minimumDB(p),resonanceMHz(p),status);
end

couplingDB = SPsDB;
couplingDB(1:nPorts+1:end) = -Inf;
[worstCouplingDB,index] = max(couplingDB,[],'all');
[rowPort,colPort] = ind2sub(size(couplingDB),index);

assert(nPorts==16,'This runner expects 16 physical Rx ports');
upperPorts = 1:8;
lowerPorts = 9:16;

upperBlock = SPsDB(upperPorts,upperPorts);
upperBlock(1:9:end) = -Inf;
[worstUpperDB,index] = max(upperBlock,[],'all');
[localRow,localCol] = ind2sub([8 8],index);
worstUpperPorts = [upperPorts(localRow) upperPorts(localCol)];

lowerBlock = SPsDB(lowerPorts,lowerPorts);
lowerBlock(1:9:end) = -Inf;
[worstLowerDB,index] = max(lowerBlock,[],'all');
[localRow,localCol] = ind2sub([8 8],index);
worstLowerPorts = [lowerPorts(localRow) lowerPorts(localCol)];

crossBlock = SPsDB(upperPorts,lowerPorts);
[worstCrossDB,index] = max(crossBlock,[],'all');
[localRow,localCol] = ind2sub([8 8],index);
worstCrossPorts = [upperPorts(localRow) lowerPorts(localCol)];

reciprocityAbs = max(abs(SPm-SPm.'),[],'all');
reciprocityRel = reciprocityAbs/max(max(abs(SPm),[],'all'),realmin);

metrics = struct;
metrics.target_MHz = targetMHz;
metrics.SPp_target_dB = SPpDB;
metrics.minimum_dB = minimumDB;
metrics.resonance_MHz = resonanceMHz;
metrics.worst_coupling_dB = worstCouplingDB;
metrics.worst_coupling_ports = [rowPort colPort];
metrics.worst_upper_coupling_dB = worstUpperDB;
metrics.worst_upper_coupling_ports = worstUpperPorts;
metrics.worst_lower_coupling_dB = worstLowerDB;
metrics.worst_lower_coupling_ports = worstLowerPorts;
metrics.worst_cross_coupling_dB = worstCrossDB;
metrics.worst_cross_coupling_ports = worstCrossPorts;
metrics.reciprocity_absolute_error = reciprocityAbs;
metrics.reciprocity_relative_error = reciprocityRel;
metrics.match_pass = all(SPpDB < targetReturnDB);
metrics.resonance_pass = max(abs(resonanceMHz-targetMHz)) < 0.5;
metrics.coupling_pass = worstCouplingDB < targetCouplingDB;
metrics.reciprocity_pass = reciprocityRel < 1e-6;
metrics.loss_aware_tmd = useLossAwareTMD;
metrics.coupling_constrained_tmd = useLossAwareTMD && useCouplingConstraint;
metrics.target_return_dB = targetReturnDB;
metrics.target_coupling_dB = targetCouplingDB;
metrics.full_hard_bounds = useFullHardBounds;
metrics.worst_loaded_return_dB = max(SPpDB);
metrics.worst_loaded_margin_dB = targetReturnDB-max(SPpDB);

fprintf('Worst coupling: S%d%d = %.2f dB\n', ...
    rowPort,colPort,worstCouplingDB);
fprintf('Worst upper/lower/cross coupling: %.2f / %.2f / %.2f dB\n', ...
    worstUpperDB,worstLowerDB,worstCrossDB);
fprintf('SP_s reciprocity relative error: %.3e\n',reciprocityRel);
fprintf('Match / resonance / coupling / reciprocity pass: %d / %d / %d / %d\n', ...
    metrics.match_pass,metrics.resonance_pass,metrics.coupling_pass, ...
    metrics.reciprocity_pass);
fprintf('Worst loaded-match margin relative to %.1f dB: %.3f dB\n', ...
    targetReturnDB,metrics.worst_loaded_margin_dB);

figureDir = fullfile(pwd,'data','solutions','TMD_progress');
if ~exist(figureDir,'dir')
    mkdir(figureDir);
end

progressFigure = plot_tmd_sparameter_progress( ...
    SPmBefore,SPpBefore,SPm,SPp,figure_freq,targetMHz,targetReturnDB, ...
    runTag,baselineLabel);
progressPng = fullfile(figureDir,['TMD_Sparameters_' runTag '.png']);
progressFig = fullfile(figureDir,['TMD_Sparameters_' runTag '.fig']);
exportgraphics(progressFigure,progressPng,'Resolution',220);
savefig(progressFigure,progressFig);

tmdResultFile = fullfile(pwd,'data','solutions', ...
    ['TMD_' caseTag '_' runTag '.mat']);
save(tmdResultFile,'netp','return_elements','metrics', ...
    'network_meta','backupJson','coilJson','-v7.3');

simulationLogFile = fullfile(pwd, ...
    'MARIE_5T_16通道Loop球形体模仿真日志.md');
append_tmd_run_log(simulationLogFile,runTag,caseTag,caseName, ...
    useLossAwareTMD,useCouplingConstraint,targetReturnDB,targetCouplingDB, ...
    useFullHardBounds,rawNetworkFile,coilJson,backupJson,tmdResultFile, ...
    progressPng,baselineLabel,metrics);

fprintf('[Updated coil JSON] %s\n',coilJson);
fprintf('[Backup coil JSON]  %s\n',backupJson);
fprintf('[Saved TMD result]   %s\n',tmdResultFile);
fprintf('[Saved S-parameter figure] %s\n',progressPng);
fprintf('[Updated simulation log] %s\n',simulationLogFile);

function fig = plot_tmd_sparameter_progress( ...
    SPsBefore,SPpBefore,SPsAfter,SPpAfter,figureFreq,targetMHz, ...
    targetReturnDB,runTag,baselineLabel)
%PLOT_TMD_SPARAMETER_PROGRESS Compare the previous and current TMD rounds.

    afterDB = 20*log10(max(abs(SPsAfter),realmin));
    loadedAfterDB = 20*log10(max(abs(SPpAfter(:)),realmin));
    nPorts = numel(loadedAfterDB);
    hasBaseline = ~isempty(SPsBefore) && ~isempty(SPpBefore);
    if hasBaseline
        beforeDB = 20*log10(max(abs(SPsBefore),realmin));
        loadedBeforeDB = 20*log10(max(abs(SPpBefore(:)),realmin));
    end

    fig = figure('Color','w','Name',['TMD S-parameter progress ' runTag], ...
        'Position',[80 80 1500 850]);
    tiledlayout(2,2,'TileSpacing','compact','Padding','compact');

    nexttile;
    if hasBaseline
        imagesc(beforeDB,[-40 0]);
        axis image; set(gca,'YDir','normal'); colorbar;
        xlabel('Excited port'); ylabel('Observed port');
        title('Previous TMD: SP_s at target (dB)');
    else
        axis off;
        text(0.5,0.55,'No previous calibrated TMD round', ...
            'HorizontalAlignment','center','FontWeight','bold');
        text(0.5,0.43,'The raw 128-port YPn is not a valid 16-port S-parameter baseline', ...
            'HorizontalAlignment','center');
        title('Previous-round baseline unavailable');
    end

    nexttile;
    imagesc(afterDB,[-40 0]);
    axis image; set(gca,'YDir','normal'); colorbar;
    xlabel('Excited port'); ylabel('Observed port');
    title('Current TMD: SP_s at target (dB)');

    nexttile;
    if hasBaseline
        bar(1:nPorts,[loadedBeforeDB loadedAfterDB],'grouped');
        legend({'Previous','Current'},'Location','best');
    else
        bar(1:nPorts,loadedAfterDB);
        legend({'Current'},'Location','best');
    end
    hold on;
    yline(targetReturnDB,'r:',sprintf('%.1f dB',targetReturnDB), ...
        'LineWidth',1.2);
    grid on; xlim([0.5 nPorts+0.5]);
    xlabel('Port'); ylabel('Preamp-loaded reflection (dB)');
    title('SP_p at target: previous versus current TMD');

    nexttile; hold on;
    colors = lines(nPorts);
    for p = 1:nPorts
        curve = 20*log10(max(abs(squeeze( ...
            figureFreq.SPm_plot_Rx(p,p,:))),realmin));
        plot(figureFreq.freq_range/1e6,curve, ...
            'Color',colors(p,:),'LineWidth',1.0, ...
            'DisplayName',sprintf('S_{%d%d}',p,p));
    end
    xline(targetMHz,'k--','Target','LineWidth',1.2);
    yline(targetReturnDB,'r:',sprintf('%.1f dB',targetReturnDB), ...
        'LineWidth',1.2);
    grid on; ylim([-40 0]);
    xlabel('Frequency (MHz)'); ylabel('Return loss (dB)');
    title('Current TMD: preamplifier-loaded Rx sweep');
    legend('Location','eastoutside','NumColumns',2);

    sgtitle({['TMD S-parameter progress - ' strrep(runTag,'_',' ')], ...
        strrep(baselineLabel,'_',' ')});
end

function append_tmd_run_log(logFile,runTag,caseTag,caseName, ...
    useLossAwareTMD,useCouplingConstraint,targetReturnDB,targetCouplingDB, ...
    useFullHardBounds,rawNetworkFile,coilJson,backupJson,tmdResultFile, ...
    progressPng,baselineLabel,metrics)
%APPEND_TMD_RUN_LOG Append one completed TMD round to the case Markdown log.

    isNewLog = exist(logFile,'file')~=2;
    fid = fopen(logFile,'a','n','UTF-8');
    assert(fid>=0,'Cannot open the simulation log: %s',logFile);
    cleanupObj = onCleanup(@() fclose(fid));

    if isNewLog
        fprintf(fid,'# MARIE 5 T 16通道 Loop 球形体模仿真日志\n\n');
        fprintf(fid,['本文件由 `RUN_5T_16CH_TMD_ONLY.m` 在每轮成功结束后', ...
            '自动追加。人工分析应写在对应轮次的“备注”下。\n\n']);
    end

    if useLossAwareTMD && useCouplingConstraint
        modeName = 'joint loss/coupling-aware minimax';
    elseif useLossAwareTMD
        modeName = 'loss-aware minimax';
    else
        modeName = 'original MARIE';
    end

    if metrics.match_pass && metrics.resonance_pass && ...
            metrics.coupling_pass && metrics.reciprocity_pass
        decision = '通过，可进入候选冻结与 Stage C';
    else
        decision = '未全部通过，继续 Stage B 或返回几何优化';
    end

    fprintf(fid,'## TMD 轮次 %s\n\n',runTag);
    fprintf(fid,'- Case tag：`%s`\n',caseTag);
    fprintf(fid,'- Case name：`%s`\n',caseName);
    fprintf(fid,'- 优化模式：`%s`\n',modeName);
    fprintf(fid,'- 目标回波损耗：`%.1f dB`\n',targetReturnDB);
    fprintf(fid,'- 目标非对角互耦：`%.1f dB`\n',targetCouplingDB);
    fprintf(fid,'- 使用完整 JSON 硬边界：`%d`\n',useFullHardBounds);
    fprintf(fid,'- 对比基线：`%s`\n',baselineLabel);
    fprintf(fid,'- 原始网络：`%s`\n',rawNetworkFile);
    fprintf(fid,'- 当前线圈 JSON：`%s`\n',coilJson);
    fprintf(fid,'- 运行前 JSON 备份：`%s`\n',backupJson);
    fprintf(fid,'- TMD 结果：`%s`\n',tmdResultFile);
    fprintf(fid,'- S 参数图：`%s`\n\n',progressPng);

    fprintf(fid,'### 数值验收\n\n');
    fprintf(fid,'| 指标 | 结果 | 门槛 | 通过 |\n');
    fprintf(fid,'|---|---:|---:|:---:|\n');
    fprintf(fid,'| 最差前放加载匹配 | %.3f dB | < %.1f dB | %d |\n', ...
        metrics.worst_loaded_return_dB,targetReturnDB,metrics.match_pass);
    fprintf(fid,'| 最差匹配裕量 | %.3f dB | > 0 dB | %d |\n', ...
        metrics.worst_loaded_margin_dB,metrics.match_pass);
    fprintf(fid,'| 最大谐振偏移 | %.6f MHz | < 0.5 MHz | %d |\n', ...
        max(abs(metrics.resonance_MHz-metrics.target_MHz)), ...
        metrics.resonance_pass);
    fprintf(fid,'| 最差非对角互耦 S%d%d | %.3f dB | < %.1f dB | %d |\n', ...
        metrics.worst_coupling_ports(1),metrics.worst_coupling_ports(2), ...
        metrics.worst_coupling_dB,targetCouplingDB,metrics.coupling_pass);
    fprintf(fid,'| 上排最差互耦 S%d%d | %.3f dB | 记录 | - |\n', ...
        metrics.worst_upper_coupling_ports(1), ...
        metrics.worst_upper_coupling_ports(2), ...
        metrics.worst_upper_coupling_dB);
    fprintf(fid,'| 下排最差互耦 S%d%d | %.3f dB | 记录 | - |\n', ...
        metrics.worst_lower_coupling_ports(1), ...
        metrics.worst_lower_coupling_ports(2), ...
        metrics.worst_lower_coupling_dB);
    fprintf(fid,'| 跨排最差互耦 S%d%d | %.3f dB | 记录 | - |\n', ...
        metrics.worst_cross_coupling_ports(1), ...
        metrics.worst_cross_coupling_ports(2), ...
        metrics.worst_cross_coupling_dB);
    fprintf(fid,'| SP_s 互易性相对误差 | %.3e | < 1e-6 | %d |\n\n', ...
        metrics.reciprocity_relative_error,metrics.reciprocity_pass);

    fprintf(fid,'### 逐端口结果\n\n');
    fprintf(fid,'| Port | SP_p target (dB) | Sweep min (dB) | f_min (MHz) | 状态 |\n');
    fprintf(fid,'|---:|---:|---:|---:|---|\n');
    for p = 1:numel(metrics.SPp_target_dB)
        if abs(metrics.resonance_MHz(p)-metrics.target_MHz) >= 0.5
            status = 'DETUNED';
        elseif metrics.SPp_target_dB(p) >= targetReturnDB
            status = 'SHALLOW_MATCH';
        else
            status = 'PASS';
        end
        fprintf(fid,'| %d | %.3f | %.3f | %.6f | %s |\n', ...
            p,metrics.SPp_target_dB(p),metrics.minimum_dB(p), ...
            metrics.resonance_MHz(p),status);
    end

    fprintf(fid,'\n### 本轮结论\n\n');
    fprintf(fid,'**%s**\n\n',decision);
    fprintf(fid,'备注：\n\n');
end
