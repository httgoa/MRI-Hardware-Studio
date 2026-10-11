% FINALIZE_5T_16CH_FROM_CHECKPOINT
% Stage C: apply the accepted fixed circuit and compute final fields/SNR.
% Reuse a full pre-TMD checkpoint when available; otherwise perform one
% conventional full solve with TMD disabled before geometry assembly.

close all
clearvars
clc

input_file = 'inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json';
caseTag = '5T_Sphere200_16LoopRx_DoubleRow_H90';
acceptedTmdRun = '20260807_070421';
checkpointFile = fullfile(pwd,'data','solutions', ...
    ['MREDM_preTMD_' caseTag '.mat']);
coilJson = fullfile(pwd,'data','coils','wire_files','Custom', ...
    'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5.json');
acceptedCoilSnapshot = [coilJson '.accepted_' acceptedTmdRun];

assert(exist(coilJson,'file')==2,'Accepted current coil JSON is missing');
if exist(acceptedCoilSnapshot,'file')~=2
    copyfile(coilJson,acceptedCoilSnapshot);
    fprintf('[Saved accepted circuit snapshot] %s\n',acceptedCoilSnapshot);
end

if exist(checkpointFile,'file')==2
    fprintf('Loading full pre-TMD checkpoint ...\n');
    load(checkpointFile,'MREDM','network_meta');
    assert(abs(network_meta.frequency_Hz/1e6-212.88739259)<1e-6);
    finalizationMode = 'full pre-TMD checkpoint';
else
    warning(['Full pre-TMD checkpoint is missing. Running one conventional ', ...
        'TMD=0 full EM solve with the accepted current coil JSON.']);

    fprintf('Loading inputs ...\n');
    MREDM = load_inputs(input_file);

    % This assignment must precede geo_assembly. It prevents temporary TMD
    % ports and ensures the current JSON values are treated as fixed.
    MREDM.inputs.tmd = 0;
    assert(MREDM.inputs.tmd==0,'Stage C must run with TMD disabled');

    fprintf('Geometry Construction ...\n');
    MREDM = geo_assembly(MREDM,1);

    fprintf('Assembling Integral Equation Operators ...\n');
    MREDM = wsvie_assembly(MREDM,1);

    fprintf('Solving System ...\n');
    MREDM = solver_wsvie(MREDM);

    network_meta = struct;
    network_meta.case_tag = caseTag;
    network_meta.input_file = input_file;
    network_meta.created = char(datetime('now','Format','yyyyMMdd''T''HHmmss'));
    network_meta.frequency_Hz = MREDM.emc.freq;
    network_meta.finalization_mode = 'conventional TMD=0 full run';
    finalizationMode = network_meta.finalization_mode;
end

% Use the element values currently stored in the coil JSON without PSO.
MREDM.inputs.tmd = 0;
network_meta.finalization_mode = finalizationMode;
network_meta.accepted_tmd_run = acceptedTmdRun;
network_meta.accepted_coil_snapshot = acceptedCoilSnapshot;

fprintf('Applying accepted fixed circuit ...\n');
MREDM = co_simulation(MREDM);

fprintf('Computing electromagnetic fields and performance metrics ...\n');
MREDM = em_ehfield_wsvie(MREDM);

solution = MREDM.fields;
outputFile = fullfile(pwd,'data','solutions', ...
    ['MARIE_0_' input_file(1:end-5) '_FINAL.mat']);
save(outputFile,'solution','network_meta','-v7.3');

fprintf('\n[Stage C completed] %s\n',outputFile);
fprintf('[Finalization mode] %s\n',finalizationMode);
fprintf('[Accepted TMD run] %s\n',acceptedTmdRun);
