function estimate = PROBE_UISNR_RESOURCES_TEMPLATE(nVox,nModes,opts)
% Conservative storage/RAM estimate before a UISNR run.
arguments
    nVox (1,1) double {mustBeInteger,mustBePositive}
    nModes (1,1) double {mustBeInteger,mustBePositive}
    opts.block_size (1,1) double {mustBeInteger,mustBePositive} = 4096
    opts.complex_bytes (1,1) double {mustBePositive} = 16
    opts.real_bytes (1,1) double {mustBePositive} = 8
    opts.persistent_copies (1,1) double {mustBePositive} = 2.5
end
fieldBytes=3*nVox*nModes*opts.complex_bytes;
phiBytes=nModes*nModes*opts.complex_bytes;
weightBytes=nVox*nModes*opts.complex_bytes;
mapBytes=nVox*opts.real_bytes;
blockBytes=4*opts.block_size*nModes*opts.complex_bytes;
estimate=struct('schema_version','uisnr_resource_probe_v01','voxel_count',nVox, ...
    'mode_count',nModes,'block_size',opts.block_size,'field_bytes',fieldBytes, ...
    'phi_bytes',phiBytes,'full_weight_bytes',weightBytes,'map_bytes',mapBytes, ...
    'estimated_block_working_bytes',blockBytes,'uisnr_only_persistent_bytes',fieldBytes+phiBytes+mapBytes, ...
    'full_weight_persistent_bytes',fieldBytes+phiBytes+mapBytes+weightBytes, ...
    'required_free_bytes_uisnr_only',opts.persistent_copies*(fieldBytes+phiBytes+mapBytes), ...
    'note','Validate against a bounded native probe; this arithmetic estimate excludes solver operators and MATLAB overhead.');
end
