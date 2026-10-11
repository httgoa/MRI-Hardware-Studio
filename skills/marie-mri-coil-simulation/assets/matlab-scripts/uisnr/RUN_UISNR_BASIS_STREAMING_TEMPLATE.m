function metrics = RUN_UISNR_BASIS_STREAMING_TEMPLATE(cfg)
% Callback-based, non-overwriting blockwise UISNR writer.
% Required cfg: n_voxels, n_modes, phi, read_b1m(first,last), output_file.
arguments
    cfg (1,1) struct
end
required={'n_voxels','n_modes','phi','read_b1m','output_file'};
for k=1:numel(required),assert(isfield(cfg,required{k}),'UISNR:Config','Missing cfg.%s',required{k});end
assert(isa(cfg.read_b1m,'function_handle'),'UISNR:Config','read_b1m must be a function handle.');
assert(~isfile(cfg.output_file),'UISNR:NoOverwrite','Output already exists: %s',cfg.output_file);
block=getfield_default(cfg,'block_size',4096);
cutoff=getfield_default(cfg,'cutoff_rel',1e-12);
scale=getfield_default(cfg,'scale',1);
outDir=fileparts(cfg.output_file); assert(isfolder(outDir),'UISNR:OutputDirectory','Output directory must pre-exist.');
tmp=[cfg.output_file '.partial']; assert(~isfile(tmp),'UISNR:NoOverwrite','Partial output already exists.');
cleanup=onCleanup(@()preserve_partial(tmp));
m=matfile(tmp,'Writable',true); m.uisnr=zeros(cfg.n_voxels,1); m.completed=false;
rankSeen=[]; totalClipped=0; started=tic;
for first=1:block:cfg.n_voxels
    last=min(first+block-1,cfg.n_voxels);
    b=cfg.read_b1m(first,last);
    assert(all(size(b)==[last-first+1 cfg.n_modes]),'UISNR:BlockDimension','read_b1m returned wrong shape.');
    [u,audit]=POST_UISNR_FINAL_MAP_TEMPLATE(b,cfg.phi,scale=scale,block_size=block,cutoff_rel=cutoff);
    m.uisnr(first:last,1)=u; rankSeen=audit.effective_rank; totalClipped=totalClipped+audit.negative_values_clipped;
end
metrics=struct('schema_version','uisnr_streaming_run_v01','completed',true, ...
    'voxel_count',cfg.n_voxels,'mode_count',cfg.n_modes,'block_size',block, ...
    'cutoff_rel',cutoff,'effective_rank',rankSeen,'negative_values_clipped',totalClipped, ...
    'elapsed_s',toc(started),'output_file',cfg.output_file);
m.metrics=metrics; m.completed=true;
assert(~isfile(cfg.output_file),'UISNR:NoOverwrite','Output appeared during run: %s',cfg.output_file);
movefile(tmp,cfg.output_file); clear cleanup
end

function value=getfield_default(s,name,default)
if isfield(s,name),value=s.(name);else,value=default;end
end
function preserve_partial(~)
% Intentionally preserve a partial file as restart/failure evidence.
end
