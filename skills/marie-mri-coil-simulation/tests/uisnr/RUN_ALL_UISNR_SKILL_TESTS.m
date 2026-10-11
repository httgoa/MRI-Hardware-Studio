function RUN_ALL_UISNR_SKILL_TESTS(skillRoot)
arguments
    skillRoot (1,1) string = string(fileparts(fileparts(fileparts(mfilename('fullpath')))))
end
templateDir=fullfile(skillRoot,'assets','matlab-scripts','uisnr');
testDir=fullfile(skillRoot,'tests','uisnr'); addpath(templateDir,testDir); cleanup=onCleanup(@()rmpath(templateDir,testDir));
TEST_UISNR_QUADRATIC_FORM;
TEST_UISNR_STREAMING_PARITY;
TEST_ICP_PHASE_AND_BASIS_INVARIANCE;
TEST_UISNR_ROI_ORDERING;
TEST_COMPLEX_CURRENT_DIAGNOSTICS;
fprintf('RUN_ALL_UISNR_SKILL_TESTS PASS\n');
end
