function report = POST_UISNR_CONVERGENCE_TEMPLATE(referenceMap,candidateMap,mask,opts)
% Same-grid UISNR convergence metrics on an explicit non-background mask.
arguments
    referenceMap {mustBeNumeric}
    candidateMap {mustBeNumeric}
    mask {mustBeNumericOrLogical}
    opts.label (1,1) string = "candidate/reference"
end
assert(isequal(size(referenceMap),size(candidateMap),size(mask)),'UISNR:Dimension','Map/mask sizes differ.');
use=logical(mask)&isfinite(referenceMap)&isfinite(candidateMap)&referenceMap>0;
assert(any(use(:)),'UISNR:ROI','No valid positive reference voxels in mask.');
r=double(referenceMap(use)); c=double(candidateMap(use)); rel=(c-r)./r;
cc=corrcoef(r,c); if isscalar(cc),rho=1;else,rho=cc(1,2);end
report=struct('schema_version','uisnr_convergence_v01','label',opts.label, ...
    'voxel_count',numel(r),'median_relative_change',median(rel), ...
    'p10_relative_change',prctile(rel,10),'p90_relative_change',prctile(rel,90), ...
    'max_absolute_relative_change',max(abs(rel)),'map_correlation',rho, ...
    'reference_median',median(r),'candidate_median',median(c));
end
