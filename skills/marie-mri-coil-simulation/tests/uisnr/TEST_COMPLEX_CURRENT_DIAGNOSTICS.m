function TEST_COMPLEX_CURRENT_DIAGNOSTICS
v=[0 0 0;1 0 0;0 1 0;0 0 1]; f=[1 2 3;1 2 4;1 3 4;2 3 4];
J=[1 1i 0;1i 0 1;0 1 1i;1 -1i 1]/sqrt(2); div=[1;-1;0.5;-0.5];
out=string(tempname); mkdir(out); cleanup=onCleanup(@()remove_temp(out));
files=PLOT_COMPLEX_CURRENT_DIAGNOSTICS_TEMPLATE(v,f,J,div,out,prefix="synthetic");
assert(isfile(files.magnitude_phase_divergence));
assert(isfile(files.instantaneous_phase4));
assert(isfile(files.divergence_streamline_proxy));
fprintf('TEST_COMPLEX_CURRENT_DIAGNOSTICS PASS\n');
end

function remove_temp(path)
if ~isfolder(path),return,end
files=dir(fullfile(path,'*')); files=files(~[files.isdir]);
for k=1:numel(files),delete(fullfile(files(k).folder,files(k).name));end
rmdir(path);
end
