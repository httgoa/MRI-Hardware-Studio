function audit = VALIDATE_UISNR_CONTRACT_TEMPLATE(reference,candidate)
% Fail-closed comparison of two UISNR compatibility tuples.
arguments
    reference (1,1) struct
    candidate (1,1) struct
end
fields={'body_sha256','materials_sha256','registration_sha256','grid_sha256', ...
    'idxs_sha256','b0_tesla','nucleus','frequency_hz','vie_basis', ...
    'boundaries_sha256','source_support_sha256','field_convention', ...
    'b1minus_convention','noise_convention','temperature_k','magnetization_convention', ...
    'mode_ordering','cutoff_policy','voxel_volume_m3'};
mismatches=strings(0,1);
for k=1:numel(fields)
    f=fields{k};
    if ~isfield(reference,f)||~isfield(candidate,f)||~isequaln(reference.(f),candidate.(f))
        mismatches(end+1,1)=string(f); %#ok<AGROW>
    end
end
audit=struct('schema_version','uisnr_compatibility_audit_v01','compatible',isempty(mismatches), ...
    'required_fields',{fields},'mismatches',mismatches);
assert(audit.compatible,'UISNR:Compatibility','Compatibility tuple mismatch: %s',strjoin(mismatches,', '));
end
