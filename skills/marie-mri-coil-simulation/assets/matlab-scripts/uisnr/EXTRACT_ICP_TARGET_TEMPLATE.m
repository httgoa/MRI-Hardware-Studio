function [w,q,metrics] = EXTRACT_ICP_TARGET_TEMPLATE(b1m,phi,voxelRows,opts)
% Extract physical MARIE coefficients for selected voxels.
% b1m is [voxel,mode]; signal is formed as transpose(b1m(rows,:)).
arguments
    b1m {mustBeNumeric}
    phi {mustBeNumeric}
    voxelRows (:,1) double {mustBeInteger,mustBePositive}
    opts.cutoff_rel (1,1) double {mustBePositive} = 1e-12
end
assert(all(voxelRows<=size(b1m,1)),'UISNR:VoxelRows','voxelRows exceed b1m.');
nModes=size(b1m,2); assert(all(size(phi)==[nModes nModes]),'UISNR:Dimension','Phi dimension mismatch.');
H=(phi+phi')/2; [V,d]=eig(H,'vector'); d=real(d); [d,ord]=sort(d,'descend'); V=V(:,ord);
dmax=max(d); assert(dmax>0&&min(d)>=-opts.cutoff_rel*dmax,'UISNR:NoisePSD','Invalid Phi spectrum.');
keep=d>opts.cutoff_rel*dmax; Vk=V(:,keep); dk=d(keep);
S=transpose(b1m(voxelRows,:));
analysis=Vk*((Vk'*S)./dk);
q=real(sum(conj(S).*analysis,1));
assert(all(isfinite(q))&&all(q>0),'UISNR:QuadraticForm','Selected targets must have positive finite q.');
w=conj(analysis)./sqrt(q);
achieved=sum(S.*w,1);
signalRel=max(abs(achieved-sqrt(q))./max(sqrt(q),realmin));
metrics=struct('schema_version','uisnr_icp_target_v01','voxel_count',numel(voxelRows), ...
    'mode_count',nModes,'cutoff_rel',opts.cutoff_rel,'effective_rank',nnz(keep), ...
    'physical_weight','conj(Phi_pinv*s)/sqrt(real(s_H*Phi_pinv*s))', ...
    'signal_convention','bilinear s_transpose_w','max_signal_relative_error',signalRel);
end
