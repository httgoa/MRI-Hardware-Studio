function TEST_UISNR_QUADRATIC_FORM
rng(7101,'twister'); nVox=73; nModes=9;
A=randn(nModes)+1i*randn(nModes); phi=A'*A+0.2*eye(nModes);
b1m=randn(nVox,nModes)+1i*randn(nVox,nModes);
[u,m]=POST_UISNR_FINAL_MAP_TEMPLATE(b1m,phi,block_size=11,cutoff_rel=1e-13);
S=transpose(b1m); q=real(sum(conj(S).*(phi\S),1)); expected=sqrt(q(:));
assert(norm(u-expected)/norm(expected)<2e-12); assert(m.effective_rank==nModes);
B=randn(nModes)+1i*randn(nModes); while rcond(B)<1e-3,B=randn(nModes)+1i*randn(nModes);end
% Coordinate change x=B*y: s_y=B'*s_x and Phi_y=B'*Phi_x*B.
b1mY=transpose(B'*S); phiY=B'*phi*B;
uY=POST_UISNR_FINAL_MAP_TEMPLATE(b1mY,phiY,block_size=17,cutoff_rel=1e-13);
assert(norm(uY-u)/norm(u)<5e-10);
fprintf('TEST_UISNR_QUADRATIC_FORM PASS\n');
end
