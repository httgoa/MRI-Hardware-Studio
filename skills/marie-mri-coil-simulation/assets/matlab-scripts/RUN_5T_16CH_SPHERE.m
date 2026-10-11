% RUN_5T_16CH_SPHERE
% Dedicated MARIE runner for the double-row 16-channel 5 T Rx array.

close all
clearvars
clc

input_file = 'inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json';

fprintf('Loading inputs ...\n');
MREDM = load_inputs(input_file);

fprintf('Geometry Construction ...\n');
MREDM = geo_assembly(MREDM,1);

fprintf('Assembling Integral Equation Operators ...\n');
MREDM = wsvie_assembly(MREDM,1);

fprintf('Solving System ...\n');
MREDM = solver_wsvie(MREDM);

fprintf('Performing Co-simulation ...\n');
MREDM = co_simulation(MREDM);

fprintf('Computing electromagnetic fields ...\n');
MREDM = em_ehfield_wsvie(MREDM);

fprintf('Storing Fields ...\n');
solution = MREDM.fields;
save(fullfile('./data/solutions/', ...
    ['MARIE_',num2str(MREDM.inputs.tmd),'_',input_file(1:end-5),'.mat']), ...
    'solution','-v7.3');

fprintf('\n[MARIE 3.0] Simulation completed successfully.\n');
fprintf('[Saved] - ./data/solutions/MARIE_%d_%s.mat\n', ...
    MREDM.inputs.tmd,input_file(1:end-5));
