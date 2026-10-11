function pool = marie_agent_configure_pool(requestedWorkers)
%MARIE_AGENT_CONFIGURE_POOL Enforce the per-execution process-worker budget.
arguments
    requestedWorkers (1,1) double {mustBeInteger,mustBePositive}
end
assert(requestedWorkers <= 64, 'MARIE:WorkerBudget', ...
    'Requested worker count exceeds the 64-worker per-run safety limit.');
pool = gcp('nocreate');
if isempty(pool)
    pool = parpool('Processes', requestedWorkers, 'IdleTimeout', 240);
elseif pool.NumWorkers ~= requestedWorkers
    error('MARIE:WorkerBudget', ...
        'Existing pool has %d workers; execution requires exactly %d.', ...
        pool.NumWorkers, requestedWorkers);
end
fprintf('MARIE_REQUESTED_WORKERS=%d\n', requestedWorkers);
fprintf('MARIE_ACTUAL_WORKERS=%d\n', pool.NumWorkers);
end
