function outputs = PLOT_COMPLEX_CURRENT_DIAGNOSTICS_TEMPLATE(vertices,faces,Jface,divergence,outDir,opts)
% Export minimum complex surface-current diagnostics. Jface is [face,3].
arguments
    vertices (:,3) double
    faces (:,3) double {mustBeInteger,mustBePositive}
    Jface (:,3) {mustBeNumeric}
    divergence (:,1) {mustBeNumeric}
    outDir (1,1) string
    opts.prefix (1,1) string = "complex_current"
end
assert(size(Jface,1)==size(faces,1)&&numel(divergence)==size(faces,1),'UISNR:Dimension','Face data mismatch.');
assert(isfolder(outDir),'UISNR:OutputDirectory','Output directory must pre-exist.');
centroids=(vertices(faces(:,1),:)+vertices(faces(:,2),:)+vertices(faces(:,3),:))/3;
mag=sqrt(sum(abs(Jface).^2,2)); [~,imax]=max(abs(Jface),[],2);
lin=sub2ind(size(Jface),(1:size(Jface,1))',imax); phase=angle(Jface(lin));
f1=figure('Visible','off','Color','w','Position',[50 50 1400 650]);
tiledlayout(1,3,'Padding','compact'); draw_scalar(vertices,faces,mag,'|J|'); draw_scalar(vertices,faces,phase,'phase of max component'); draw_scalar(vertices,faces,abs(divergence),'|div_s J|');
p1=fullfile(outDir,opts.prefix+"_magnitude_phase_divergence.png"); exportgraphics(f1,p1,'Resolution',180); close(f1);
theta=[0 pi/2 pi 3*pi/2]; labels=["0","pi/2","pi","3pi/2"];
f2=figure('Visible','off','Color','w','Position',[50 50 1400 1050]); tiledlayout(2,2,'Padding','compact');
step=max(1,ceil(size(faces,1)/1500)); use=1:step:size(faces,1);
for k=1:4
    nexttile; patch('Faces',faces,'Vertices',vertices,'FaceVertexCData',mag,'FaceColor','flat','EdgeColor','none','FaceAlpha',.35); hold on
    jt=real(Jface*exp(1i*theta(k))); quiver3(centroids(use,1),centroids(use,2),centroids(use,3),jt(use,1),jt(use,2),jt(use,3),0.8,'k');
    axis equal off; view(35,20); title("real(J exp(i theta)), theta="+labels(k));
end
p2=fullfile(outDir,opts.prefix+"_instantaneous_phase4.png"); exportgraphics(f2,p2,'Resolution',180); close(f2);
f3=figure('Visible','off','Color','w','Position',[50 50 1200 600]); tiledlayout(1,2,'Padding','compact');
draw_scalar(vertices,faces,abs(divergence),'|div_s J|');
nexttile; patch('Faces',faces,'Vertices',vertices,'FaceVertexCData',mag,'FaceColor','flat','EdgeColor','none','FaceAlpha',.45); hold on
draw_stream_proxy(faces,centroids,real(Jface),mag); axis equal off; view(35,20); title('centroid-adjacency streamline proxy, real(J)');
p3=fullfile(outDir,opts.prefix+"_divergence_streamline_proxy.png"); exportgraphics(f3,p3,'Resolution',180); close(f3);
outputs=struct('schema_version','complex_current_diagnostics_v01','magnitude_phase_divergence',p1, ...
    'instantaneous_phase4',p2,'divergence_streamline_proxy',p3, ...
    'phase_definition','phase of maximum-magnitude Cartesian component', ...
    'streamline_status','centroid-adjacency diagnostic proxy; not a geodesic integral curve or physical conductor');
end

function draw_scalar(v,f,c,t)
nexttile; patch('Faces',f,'Vertices',v,'FaceVertexCData',c,'FaceColor','flat','EdgeColor','none'); axis equal off; view(35,20); colorbar; title(t); camlight headlight; lighting gouraud
end

function draw_stream_proxy(faces,c,j,mag)
n=size(faces,1); edgeOwner=containers.Map('KeyType','char','ValueType','any'); adj=cell(n,1);
for i=1:n
    e=sort([faces(i,[1 2]);faces(i,[2 3]);faces(i,[3 1])],2);
    for k=1:3
        key=sprintf('%d_%d',e(k,1),e(k,2));
        if isKey(edgeOwner,key)
            other=edgeOwner(key); adj{i}(end+1)=other; adj{other}(end+1)=i;
        else
            edgeOwner(key)=i;
        end
    end
end
[~,seeds]=sort(mag,'descend'); seeds=seeds(1:min(30,n));
for seed=seeds(:)'
    path=seed; current=seed; visited=false(n,1); visited(current)=true;
    for step=1:50
        nbr=adj{current}; nbr=nbr(~visited(nbr)); if isempty(nbr),break,end
        delta=c(nbr,:)-c(current,:); score=real(delta*transpose(j(current,:)))./max(vecnorm(delta,2,2),realmin);
        [best,which]=max(score); if best<=0,break,end
        current=nbr(which); visited(current)=true; path(end+1)=current; %#ok<AGROW>
    end
    if numel(path)>3,p=c(path,:);plot3(p(:,1),p(:,2),p(:,3),'k-','LineWidth',.8);end
end
end
