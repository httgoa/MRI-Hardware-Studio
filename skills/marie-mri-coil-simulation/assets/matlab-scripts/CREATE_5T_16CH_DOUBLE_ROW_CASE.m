% CREATE_5T_16CH_DOUBLE_ROW_CASE
% Build a separate MARIE 5 T / 1H / 200 mm sphere / 16-channel Rx case.
% Geometry: two staggered rows of eight loops. The former radius stays at
% 115 mm; loop height is reduced so the full double-row array fits inside
% the validated R115/H140 UISNR support range (-70 mm <= z <= +70 mm).

clearvars;

projectRoot = fileparts(mfilename('fullpath'));
if isempty(projectRoot)
    projectRoot = pwd;
end
cd(projectRoot);

wireDir = fullfile(projectRoot,'data','coils','wire_files','Custom');
inputDir = fullfile(projectRoot,'data','inputs');
if ~exist(wireDir,'dir'), mkdir(wireDir); end
if ~exist(inputDir,'dir'), mkdir(inputDir); end

caseName = 'Sphere16Rx_2Row_R115_H90_Span50_Z25_Stagger22p5';
meshFile = fullfile(wireDir,[caseName '.msh']);
coilJsonFile = fullfile(wireDir,[caseName '.json']);
inputFile = fullfile(inputDir, ...
    'inp_5T_1H_Sphere200_16LoopRx_DoubleRow_H90.json');

% Geometry in metres. The original single row spans z=-70 to +70 mm.
% zHalf=45 mm and zRow=25 mm give upper/lower ranges [-20,+70] and
% [-70,+20] mm: a 40 mm axial overlap without exceeding the old range.
nPerRow = 8;
nRows = 2;
nCh = nPerRow*nRows;
Rc = 0.115;
zHalf = 0.045;
zRow = 0.025;
span = deg2rad(50);
rowStagger = deg2rad(22.5);
nArc = 24;
nSide = 16;

nodes = zeros(0,3);
loopNodeIds = cell(nCh,1);
channelInfo = table('Size',[nCh 3], ...
    'VariableTypes',{'double','double','double'}, ...
    'VariableNames',{'Channel','RowCenterZ_m','Azimuth_deg'});

for row = 1:nRows
    if row == 1
        zCenter = zRow;
        azimuthOffset = 0;
    else
        zCenter = -zRow;
        azimuthOffset = rowStagger;
    end

    for inRow = 1:nPerRow
        ch = (row-1)*nPerRow + inRow;
        phi0 = 2*pi*(inRow-1)/nPerRow + azimuthOffset;

        pTop = linspace(-span/2,span/2,nArc+1);
        top = [Rc*cos(phi0+pTop(:)), Rc*sin(phi0+pTop(:)), ...
               (zCenter+zHalf)*ones(numel(pTop),1)];

        zr = linspace(zCenter+zHalf,zCenter-zHalf,nSide+1);
        zr = zr(2:end);
        right = [Rc*cos(phi0+span/2)*ones(numel(zr),1), ...
                 Rc*sin(phi0+span/2)*ones(numel(zr),1), zr(:)];

        pBottom = linspace(span/2,-span/2,nArc+1);
        pBottom = pBottom(2:end);
        bottom = [Rc*cos(phi0+pBottom(:)), Rc*sin(phi0+pBottom(:)), ...
                  (zCenter-zHalf)*ones(numel(pBottom),1)];

        zl = linspace(zCenter-zHalf,zCenter+zHalf,nSide+1);
        zl = zl(2:end-1);
        left = [Rc*cos(phi0-span/2)*ones(numel(zl),1), ...
                Rc*sin(phi0-span/2)*ones(numel(zl),1), zl(:)];

        loop = [top; right; bottom; left];
        firstId = size(nodes,1)+1;
        ids = firstId:firstId+size(loop,1)-1;
        nodes = [nodes; loop]; %#ok<AGROW>
        loopNodeIds{ch} = ids;
        channelInfo(ch,:) = {ch,zCenter,rad2deg(phi0)};
    end
end

assert(all(cellfun(@numel,loopNodeIds)==80));
assert(isequal(channelInfo.Channel.',1:nCh));

% MARIE's 16-channel receiver template contains one port followed by seven
% tuning capacitors per channel. Mesh point elements must follow that order.
lumpedLocal = 1:10:71;
nPoint = nCh*numel(lumpedLocal);
nLine = sum(cellfun(@numel,loopNodeIds));

fid = fopen(meshFile,'w');
assert(fid>0,'Cannot create %s',meshFile);
cleanup = onCleanup(@() fclose(fid));
fprintf(fid,'$MeshFormat\n2.2 0 8\n$EndMeshFormat\n');
fprintf(fid,'$Nodes\n%d\n',size(nodes,1));
for i = 1:size(nodes,1)
    fprintf(fid,'%d %.16g %.16g %.16g\n',i,nodes(i,1),nodes(i,2),nodes(i,3));
end
fprintf(fid,'$EndNodes\n');
fprintf(fid,'$Elements\n%d\n',nPoint+nLine);

eid = 0;
for ch = 1:nCh
    ids = loopNodeIds{ch};
    for k = lumpedLocal
        eid = eid+1;
        fprintf(fid,'%d 15 2 %d %d %d\n',eid,ch,ch,ids(k));
    end
end
for ch = 1:nCh
    ids = loopNodeIds{ch};
    for k = 1:numel(ids)
        eid = eid+1;
        fprintf(fid,'%d 1 2 %d %d %d %d\n', ...
            eid,ch,ch,ids(k),ids(mod(k,numel(ids))+1));
    end
end
fprintf(fid,'$EndElements\n');
clear cleanup;

% Create a constrained, fully symmetric seed circuit. Build the 16-channel
% circuit by cloning the valid 8-channel template twice. Some MARIE source
% distributions contain a malformed Head_Receive_Array_16_Coils.json, while
% the 8-channel template has the exact port-plus-seven-capacitor layout.
templateJson = fullfile(projectRoot,'data','coils','wire_files', ...
    'Head_Receivers','Head_Receive_Array_8_Coils.json');
assert(exist(templateJson,'file')==2, ...
    'MARIE 8-channel receiver template is missing: %s',templateJson);

coilCfg = jsondecode(fileread(templateJson));
E8 = coilCfg.coil_configuration.elements;
E8 = E8(:);
assert(numel(E8)==64,'Expected 64 circuit elements in the 8-channel template');
assert(sum(strcmp({E8.type},'port'))==8,'Expected 8 Rx ports in the template');
E = [E8; E8];
for ch = 1:nCh
    idx = (ch-1)*8 + (1:8);
    for k = idx
        E(k).number = k;
        E(k).excitation.entity = ch;
        E(k).excitation.TxRx = 'Rx';
    end
end
assert(numel(E)==128,'Expected 128 circuit elements in the 16-channel circuit');
assert(sum(strcmp({E.type},'port'))==nCh,'Expected 16 Rx ports');

% These are bounded seed values, not final design values. TMD writes its
% optimized values back into this JSON; preserve a version-controlled copy.
seedPort = [26.4530e-12,23.7565e-9,27.1397e-12];
seedSegmentC = 2.7894e-12;

for ch = 1:nCh
    idx = (ch-1)*8 + (1:8);
    E(idx(1)).value = seedPort;
    E(idx(1)).optim.boolean = 1;
    % The MARIE counter advances by 3 port variables and 7 tuning
    % elements per channel. Compensate that 10-value offset so each row
    % shares one Cp1/Ls/Cp2/Cseg set, while the two rows remain separate.
    if ch <= 8
        E(idx(1)).optim.symmetry = 1000 - 10*(ch-1);
        tuneSym = 5000 - 10*(ch-1);
    else
        E(idx(1)).optim.symmetry = 2000 - 10*(ch-9);
        tuneSym = 6000 - 10*(ch-9);
    end
    E(idx(1)).optim.minim = [5e-12,5e-9,5e-12];
    E(idx(1)).optim.maxim = [80e-12,60e-9,80e-12];

    for k = 2:8
        E(idx(k)).value = seedSegmentC;
        E(idx(k)).optim.boolean = 1;
        E(idx(k)).optim.symmetry = tuneSym;
        E(idx(k)).optim.minim = 1.5e-12;
        E(idx(k)).optim.maxim = 5.0e-12;
    end
end

coilCfg.coil_configuration.name = [caseName '.json'];
coilCfg.coil_configuration.elements = E;
fid = fopen(coilJsonFile,'w');
assert(fid>0,'Cannot create %s',coilJsonFile);
fprintf(fid,'%s',jsonencode(coilCfg,PrettyPrint=true));
fclose(fid);

inputs = struct( ...
    'B0',5.0, ...
    'Nucleus','1H', ...
    'Basis_Functions_VIE',0, ...
    'BodyFile','Scatterers/4mm/Sphere_D200mm_4mm_eps50_sig0p6_5T.mat', ...
    'CoilFile','', ...
    'WireFile',['Custom/' caseName '.msh'], ...
    'ShieldFile','', ...
    'SurfaceBasisSupportFile','', ...
    'TMD',1, ...
    'BasisFile','');
fid = fopen(inputFile,'w');
assert(fid>0,'Cannot create %s',inputFile);
fprintf(fid,'%s',jsonencode(inputs,PrettyPrint=true));
fclose(fid);

writetable(channelInfo,fullfile(wireDir,[caseName '_channel_layout.csv']));

fprintf('Created geometry: %s\n',meshFile);
fprintf('Created circuit:  %s\n',coilJsonFile);
fprintf('Created input:    %s\n',inputFile);
fprintf('16 loops: upper channels 1-8 at z=+25 mm; lower channels 9-16 at z=-25 mm and +22.5 deg stagger.\n');
