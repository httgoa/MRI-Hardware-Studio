function evidence = RUN_UISNR_GEOMETRY_GATE_TEMPLATE(cfg)
% Generic pre-BASIS geometry/visual-evidence gate driven by callbacks.
arguments
    cfg (1,1) struct
end
required={'case_tag','input_json','run_dir','geometry_callback','visual_callback','input_sha256'};
for k=1:numel(required),assert(isfield(cfg,required{k}),'UISNR:Config','Missing cfg.%s',required{k});end
assert(isfile(cfg.input_json)&&isfolder(cfg.run_dir),'UISNR:Path','Input or run directory missing.');
assert(isa(cfg.geometry_callback,'function_handle')&&isa(cfg.visual_callback,'function_handle'), ...
    'UISNR:Callback','Callbacks must be function handles.');
geometry=cfg.geometry_callback(cfg);
assert(isstruct(geometry)&&isfield(geometry,'passed')&&geometry.passed,'UISNR:GeometryGate','Native geometry gate failed.');
views=cfg.visual_callback(cfg,geometry);
assert(isstruct(views)&&all(isfield(views,{'front','side','top','configuration'})), ...
    'UISNR:VisualEvidence','Four visual-evidence paths are required.');
names=fieldnames(views); for k=1:numel(names),assert(isfile(views.(names{k})),'UISNR:VisualEvidence','Missing view %s.',names{k});end
evidence=struct('schema_version','uisnr_geometry_gate_v01','completed',true, ...
    'case_tag',cfg.case_tag,'input_json',cfg.input_json,'input_sha256',cfg.input_sha256, ...
    'geometry',geometry,'views',views,'classification','geometry-only; no BASIS or UISNR claim');
end
