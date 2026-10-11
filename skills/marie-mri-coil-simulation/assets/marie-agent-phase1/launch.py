#!/usr/bin/env python3
"""Validate and submit a prepared execution to detached tmux."""
import hashlib,json,os,re,shutil,subprocess,sys,time
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime import consume_approval,exclusive,transition
SAFE=re.compile(r"^[A-Za-z0-9._-]+$")
def fail(msg,code=2): print(msg,file=sys.stderr); raise SystemExit(code)
def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()
def validate(root,case,run):
    directory=root/"runs"/case/"executions"/run; path=directory/"execution.json"
    if not path.is_file(): fail(f"Execution not found: {path}",3)
    state=json.loads(path.read_text(encoding="utf-8"))
    if state.get("case_tag")!=case or state.get("run_id")!=run: fail("Execution identity mismatch",4)
    if state.get("state")!="prepared" or not state.get("launch_available",False):
        fail(f"Execution is not launchable: state={state.get('state')} launch_available={state.get('launch_available')}",5)
    command=state.get("command")
    if not isinstance(command,list) or len(command)<3: fail("Invalid execution command",4)
    expected_text=os.environ.get("MATLAB_BIN")
    if not expected_text: fail("MATLAB_BIN is not configured",4)
    expected=Path(expected_text).resolve()
    if Path(command[0]).resolve()!=expected: fail("Unexpected MATLAB executable",4)
    for item in state.get("snapshots",[]):
        source=(root/item["source"]).resolve()
        try: source.relative_to(root)
        except ValueError: fail(f"Snapshot source escapes workspace: {item['source']}",4)
        if not source.is_file() or sha256(source)!=item["sha256"]:
            fail(f"Prepared source drifted: {item['source']}",10)
    for item in state.get("dependencies",[]):
        source=(root/item["source"]).resolve()
        try: source.relative_to(root)
        except ValueError: fail(f"Dependency escapes workspace: {item['source']}",4)
        if not source.is_file() or sha256(source)!=item["sha256"]:
            fail(f"Prepared dependency drifted: {item['source']}",10)
    if state.get("approval_required"):
        apath=directory/"approval.json"
        if not apath.is_file(): fail("Protected execution requires approval.json",6)
        approval=json.loads(apath.read_text(encoding="utf-8"))
        expires=datetime.fromisoformat(approval.get("expires_at","1970-01-01T00:00:00+00:00"))
        if (not approval.get("approved") or approval.get("scope")!="exact-run"
            or approval.get("gate_digest")!=state.get("gate_digest")
            or approval.get("consumed_at") is not None
            or expires<=datetime.now().astimezone()):
            fail("Approval is absent, false, or stale",6)
    return directory,state
def main():
    args=sys.argv[1:]; check=bool(args and args[-1]=="--check")
    if check: args.pop()
    if len(args)!=2: fail(f"Usage: {sys.argv[0]} <CaseTag> <RunID> [--check]")
    case,run=args
    if not SAFE.fullmatch(case) or not SAFE.fullmatch(run): fail("Invalid CaseTag or RunID")
    root=Path(__file__).resolve().parents[2]; directory,state=validate(root,case,run)
    if shutil.which("tmux") is None: fail("tmux not found",7)
    session=f"marie_{state['stage']}_{hashlib.sha256(f'{case}/{run}'.encode()).hexdigest()[:12]}"
    if subprocess.run(["tmux","has-session","-t",session],capture_output=True).returncode==0: fail(f"tmux session already exists: {session}",8)
    profile=state.get("production_profile","legacy-geometry-only")
    legacy_ok=(profile=="legacy-geometry-only" and state.get("stage")=="geometry"
        and state.get("cost")=="light" and not state.get("writes_active_json"))
    training_ok=(profile=="training-closed-loop-v1" and state.get("stage") in
        {"geometry","stage_a","tmd","stage_c","post"})
    if not (legacy_ok or training_ok):
        fail("Execution is outside the production profile allowlist",12)
    if check:
        print(json.dumps({"launchable":True,"submission_enabled":True,"session":session,
          "execution":str(directory.relative_to(root)),
          "checked_at":datetime.now().astimezone().isoformat(timespec="seconds")})); return 0
    case_lock=root/"runs"/case/"executions"/".case.lock"
    with exclusive(case_lock):
        if state.get("approval_required") and not consume_approval(directory,state.get("gate_digest",""),run):
            fail("Protected execution approval could not be consumed",6)
        transition(directory,"launching","authorized production-profile tmux submission",updates={"session":session})
        worker=root/"tools"/"marie-agent"/"production_worker.py"
        result=subprocess.run(["tmux","new-session","-d","-s",session,sys.executable,str(worker),case,run,session],cwd=root)
        if result.returncode:
            transition(directory,"launch_failed","tmux creation failed",updates={"wrapper_exit_code":9})
            fail("tmux submission failed",9)
    deadline=time.time()+15
    while time.time()<deadline:
        current=json.loads((directory/"execution.json").read_text())
        if current["state"]!="launching":
            print(json.dumps({"session":session,"state":current["state"],"run_id":run})); return 0
        time.sleep(.1)
    print(json.dumps({"session":session,"state":"launching","warning":"startup confirmation timeout"}))
    return 0
if __name__=="__main__": raise SystemExit(main())
