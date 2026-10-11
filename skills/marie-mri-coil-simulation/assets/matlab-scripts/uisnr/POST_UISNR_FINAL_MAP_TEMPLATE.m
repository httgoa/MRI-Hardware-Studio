function [uisnr,metrics] = POST_UISNR_FINAL_MAP_TEMPLATE(b1m,phi,opts)
% Stable blockwise B1-/Phi to UISNR kernel. b1m is [voxel,mode].
arguments
    b1m {mustBeNumeric}
    phi {mustBeNumeric}
    opts.scale (1,1) double = 1
    opts.block_size (1,1) double {mustBeInteger,mustBePositive} = 4096
    opts.cutoff_rel (1,1) double {mustBePositive} = 1e-12
    opts.negative_rel_tol (1,1) double {mustBeNonnegative} = 1e-10
end

nModes=size(b1m,2);
assert(ismatrix(phi)&&all(size(phi)==[nModes nModes]),'UISNR:Dimension','Phi dimension mismatch.');
assert(all(isfinite(b1m(:)))&&all(isfinite(phi(:))),'UISNR:Finite','Inputs must be finite.');
H=(phi+phi')/2;
hermErr=norm(phi-phi','fro')/max(norm(phi,'fro'),eps);
[V,d]=eig(H,'vector'); d=real(d); [d,ord]=sort(d,'descend'); V=V(:,ord);
dmax=max(d); assert(dmax>0,'UISNR:NoiseRank','Phi has no positive eigenvalue.');
negativeTol=opts.cutoff_rel*dmax;
assert(min(d)>=-negativeTol,'UISNR:NoisePSD','Phi is not PSD within the declared tolerance.');
keep=d>opts.cutoff_rel*dmax;
Vk=V(:,keep); dk=d(keep);

nVox=size(b1m,1); uisnr=zeros(nVox,1);
qMin=inf; qMax=0; clipped=0;
for first=1:opts.block_size:nVox
    last=min(first+opts.block_size-1,nVox);
    S=transpose(b1m(first:last,:));
    A=Vk*((Vk'*S)./dk);
    q=real(sum(conj(S).*A,1));
    localScale=max(max(abs(q)),1);
    small=q<0 & q>=-opts.negative_rel_tol*localScale;
    clipped=clipped+nnz(small); q(small)=0;
    assert(all(isfinite(q))&&all(q>=0),'UISNR:QuadraticForm','Invalid quadratic form.');
    uisnr(first:last)=opts.scale*sqrt(q(:));
    qMin=min(qMin,min(q)); qMax=max(qMax,max(q));
end
metrics=struct('schema_version','uisnr_final_map_v01','voxel_count',nVox, ...
    'mode_count',nModes,'block_size',opts.block_size,'cutoff_rel',opts.cutoff_rel, ...
    'effective_rank',nnz(keep),'phi_hermitian_relative_error',hermErr, ...
    'phi_min_eigenvalue',min(d),'phi_max_eigenvalue',dmax, ...
    'phi_condition_retained',dmax/min(dk),'negative_values_clipped',clipped, ...
    'q_min',qMin,'q_max',qMax,'scale',opts.scale);
end
