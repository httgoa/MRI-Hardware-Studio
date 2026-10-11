% PRECOMPUTE_5T_16CH_EM_NETWORK
% Stage A: solve the fixed 3-D EM problem once and save the raw network.

close all
clearvars
clc

input_file = 'inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json';
caseTag = '5T_Sphere200_16LoopRx_DoubleRow_H90';

% A full checkpoint avoids another EM solve when final B1-/SNR fields are
% generated, but it can be very large. Enable it with the environment
% variable MARIE_SAVE_FULL_CHECKPOINT=1. YPn is always saved.
saveFullCheckpoint = strcmp(getenv('MARIE_SAVE_FULL_CHECKPOINT'),'1');

fprintf('Loading inputs ...\n');
MREDM = load_inputs(input_file);

fprintf('Geometry Construction ...\n');
MREDM = geo_assembly(MREDM,1);

fprintf('Assembling Integral Equation Operators ...\n');
MREDM = wsvie_assembly(MREDM,1);

fprintf('Solving System and computing raw network parameters ...\n');
MREDM = solver_wsvie(MREDM);

YPn = MREDM.fields.netp.YP_s;
assert(~isempty(YPn),'Raw Y-parameter matrix is empty');
assert(all(isfinite(YPn(:))),'Raw Y-parameter matrix contains NaN or Inf');

network_meta = struct;
network_meta.case_tag = caseTag;
network_meta.input_file = input_file;
network_meta.created = char(datetime('now','Format','yyyyMMdd''T''HHmmss'));
network_meta.B0_T = 5;
network_meta.nucleus = '1H';
network_meta.frequency_Hz = MREDM.emc.freq;
network_meta.raw_network_size = size(YPn);
network_meta.note = ['Valid only while geometry, body, mesh, frequency, ' ...
    'basis functions, shield and conductor model remain unchanged.'];

solutionDir = fullfile(pwd,'data','solutions');
rawNetworkFile = fullfile(solutionDir,['YPn_' caseTag '.mat']);
save(rawNetworkFile,'YPn','network_meta','-v7.3');
fprintf('[Saved raw network] %s\n',rawNetworkFile);

if saveFullCheckpoint
    checkpointFile = fullfile(solutionDir,['MREDM_preTMD_' caseTag '.mat']);
    save(checkpointFile,'MREDM','network_meta','-v7.3');
    fprintf('[Saved full checkpoint] %s\n',checkpointFile);
else
    fprintf(['[Skipped full checkpoint] Set environment variable ' ...
        'MARIE_SAVE_FULL_CHECKPOINT=1 when sufficient disk space is available.\n']);
end

fprintf('\n[Stage A completed] No TMD or field postprocessing was run.\n');
