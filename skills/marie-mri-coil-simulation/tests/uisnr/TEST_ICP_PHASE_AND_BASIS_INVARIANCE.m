function TEST_ICP_PHASE_AND_BASIS_INVARIANCE
rng(7103,'twister'); nVox=19; nModes=8;
A=randn(nModes)+1i*randn(nModes); phi=A'*A+0.5*eye(nModes);
b=randn(nVox,nModes)+1i*randn(nVox,nModes); rows=(1:9)';
[w,q,m]=EXTRACT_ICP_TARGET_TEMPLATE(b,phi,rows,cutoff_rel=1e-13);
assert(m.max_signal_relative_error<2e-12);
theta=0.731; [wr,qr]=EXTRACT_ICP_TARGET_TEMPLATE(exp(1i*theta)*b,phi,rows,cutoff_rel=1e-13);
expected=exp(-1i*theta)*w;
assert(norm(wr-expected,'fro')/norm(expected,'fro')<2e-12);
assert(norm(qr-q)/norm(q)<2e-12);
fprintf('TEST_ICP_PHASE_AND_BASIS_INVARIANCE PASS\n');
end
