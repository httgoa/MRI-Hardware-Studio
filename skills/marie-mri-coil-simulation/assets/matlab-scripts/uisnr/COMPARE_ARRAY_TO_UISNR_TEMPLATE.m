function [arraySnr,ratio,metrics] = COMPARE_ARRAY_TO_UISNR_TEMPLATE(b1mArray,noiseArray,uisnrReference,opts)
% Compare a finite array with a compatible pointwise UISNR reference.
arguments
    b1mArray {mustBeNumeric}
    noiseArray {mustBeNumeric}
    uisnrReference (:,1) double
    opts.scale (1,1) double = 1
    opts.cutoff_rel (1,1) double {mustBePositive} = 1e-12
    opts.upper_bound_tolerance (1,1) double {mustBeNonnegative} = 1e-6
end
assert(size(b1mArray,1)==numel(uisnrReference),'UISNR:Dimension','Voxel count mismatch.');
[arraySnr,audit]=POST_UISNR_FINAL_MAP_TEMPLATE(b1mArray,noiseArray,scale=opts.scale,cutoff_rel=opts.cutoff_rel);
ratio=nan(size(arraySnr)); use=uisnrReference>0 & isfinite(uisnrReference);
ratio(use)=arraySnr(use)./uisnrReference(use);
worst=max(ratio(use)); violations=nnz(ratio(use)>1+opts.upper_bound_tolerance);
metrics=struct('schema_version','array_to_uisnr_v01','voxel_count',nnz(use), ...
    'ratio_median',median(ratio(use)),'ratio_p90',prctile(ratio(use),90), ...
    'ratio_max',worst,'upper_bound_tolerance',opts.upper_bound_tolerance, ...
    'upper_bound_violation_count',violations,'array_kernel',audit);
assert(violations==0,'UISNR:UpperBound','Finite-array SNR exceeds compatible UISNR at %d voxels.',violations);
end
