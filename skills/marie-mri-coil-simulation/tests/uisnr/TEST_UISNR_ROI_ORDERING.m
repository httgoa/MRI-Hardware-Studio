function TEST_UISNR_ROI_ORDERING
rng(7104,'twister'); dims=[5 4 3]; idxS=[1 4 9 16 22 31 44 58]'; nModes=5;
A=randn(nModes)+1i*randn(nModes); phi=A'*A+eye(nModes);
b=randn(numel(idxS),nModes)+1i*randn(numel(idxS),nModes);
u=POST_UISNR_FINAL_MAP_TEMPLATE(b,phi,block_size=3);
volume=zeros(dims); volume(idxS)=u;
assert(isequal(volume(idxS),u)); assert(nnz(volume)==numel(idxS));
order=[6 1 8 3 5 2 7 4]; ur=POST_UISNR_FINAL_MAP_TEMPLATE(b(order,:),phi,block_size=2);
inverse=zeros(size(order)); inverse(order)=1:numel(order);
assert(isequal(ur(inverse),u));
mask=false(dims); mask(idxS([2 5 8]))=true;
report=POST_UISNR_CONVERGENCE_TEMPLATE(volume,volume,mask);
assert(report.voxel_count==3&&report.median_relative_change==0);
fprintf('TEST_UISNR_ROI_ORDERING PASS\n');
end
