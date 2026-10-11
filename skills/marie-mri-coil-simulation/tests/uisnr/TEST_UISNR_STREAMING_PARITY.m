function TEST_UISNR_STREAMING_PARITY
rng(7102,'twister'); nVox=101; nModes=7;
A=randn(nModes)+1i*randn(nModes); phi=A'*A+eye(nModes);
b=randn(nVox,nModes)+1i*randn(nVox,nModes);
u1=POST_UISNR_FINAL_MAP_TEMPLATE(b,phi,block_size=nVox);
u2=POST_UISNR_FINAL_MAP_TEMPLATE(b,phi,block_size=13);
u3=POST_UISNR_FINAL_MAP_TEMPLATE(b,phi,block_size=29);
assert(isequal(u1,u2)&&isequal(u1,u3));
out=string(tempname)+".mat"; cleanup=onCleanup(@()delete_if_present(out));
cfg=struct('n_voxels',nVox,'n_modes',nModes,'phi',phi, ...
    'read_b1m',@(first,last)b(first:last,:),'output_file',char(out), ...
    'block_size',13,'cutoff_rel',1e-12,'scale',1);
metrics=RUN_UISNR_BASIS_STREAMING_TEMPLATE(cfg); saved=load(out,'uisnr','completed');
assert(metrics.completed&&saved.completed&&isequal(saved.uisnr,u1));
refused=false;
try
    RUN_UISNR_BASIS_STREAMING_TEMPLATE(cfg);
catch ME
    refused=strcmp(ME.identifier,'UISNR:NoOverwrite');
end
assert(refused,'Streaming writer did not refuse overwrite.');
fprintf('TEST_UISNR_STREAMING_PARITY PASS\n');
end

function delete_if_present(path)
if isfile(path),delete(path);end
partial=path+".partial"; if isfile(partial),delete(partial);end
end
