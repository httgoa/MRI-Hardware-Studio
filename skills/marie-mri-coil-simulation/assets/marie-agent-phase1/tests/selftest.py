#!/usr/bin/env python3
"""Phase 2B isolated fake-runner tests. Never invokes MATLAB."""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime,timedelta
from runtime import atomic_json,consume_approval,create_json_exclusive,reconcile,run_fixture
WORKER=Path(__file__).with_name("fake_worker.py")
def execution(root,name):
    d=root/"runs"/name/"executions"/"test"; (d/"logs").mkdir(parents=True); (d/"snapshots").mkdir()
    atomic_json(d/"execution.json",{"schema_version":2,"case_tag":name,"run_id":"test","stage":"fake","state":"launching"})
    return d
def wait_state(path,wanted,timeout=5):
    end=time.time()+timeout
    while time.time()<end:
        value=json.loads(path.read_text())
        if value["state"] in wanted:return value
        time.sleep(.05)
    raise AssertionError(f"timeout waiting for {wanted}")
def worker(root,d,lock,command,allowed,active=None):
    args=[sys.executable,str(WORKER),str(root),str(d),str(lock),json.dumps(command),allowed]
    if active:args.append(str(active))
    return args
def main():
  with tempfile.TemporaryDirectory(prefix="marie-phase2b-") as temp:
    root=Path(temp); (root/"runs").mkdir(); fake=root/"_agent_tests"/"bin"/"fake_exec.py"; fake.parent.mkdir(parents=True)
    fake.write_text('#!/usr/bin/env python3\nimport os,signal,sys,time\nmode=sys.argv[1]\nprint(mode)\n'+      'time.sleep(float(sys.argv[2])) if mode=="sleep" else None\n'+      'os.kill(os.getpid(),signal.SIGTERM) if mode=="term" else None\n'+      'raise SystemExit(42 if mode=="fail42" else 0)\n')
    fake.chmod(0o700); allowed=hashlib.sha256(fake.read_bytes()).hexdigest()
    ok=execution(root,"ok"); assert run_fixture(root,ok,[str(fake),"ok"],root/"runs"/"ok.lock",allowed)==0
    assert json.loads((ok/"execution.json").read_text())["state"]=="succeeded"; assert (ok/"exitcode").read_text()=="0\n"
    bad=execution(root,"bad"); assert run_fixture(root,bad,[str(fake),"fail42"],root/"runs"/"bad.lock",allowed)==42
    assert json.loads((bad/"execution.json").read_text())["state"]=="failed"; assert (bad/"exitcode").read_text()=="42\n"
    term=execution(root,"term"); assert run_fixture(root,term,[str(fake),"term"],root/"runs"/"term.lock",allowed)==-15
    assert json.loads((term/"execution.json").read_text())["state"]=="interrupted"
    forbidden=execution(root,"forbidden"); assert run_fixture(root,forbidden,["/bin/true"],root/"runs"/"forbidden.lock",allowed)==70
    assert not (forbidden/"exitcode").exists() and (forbidden/"wrapper.exitcode").read_text()=="70\n"
    first=execution(root,"case_a"); second=execution(root,"case_b"); shared=root/"runs"/"shared.case.lock"
    p=subprocess.Popen(worker(root,first,shared,[str(fake),"sleep","1"],allowed))
    wait_state(first/"execution.json",{"running"})
    assert run_fixture(root,second,[str(fake),"ok"],shared,allowed)==8; p.wait(timeout=4)
    active=root/"active.json"; active.write_text('{"seed":1}\n')
    alias=root/"active-alias.json"; alias.symlink_to(active)
    one=execution(root,"json_a"); two=execution(root,"json_b")
    p=subprocess.Popen(worker(root,one,root/"runs"/"a.lock",[str(fake),"sleep","1"],allowed,active))
    wait_state(one/"execution.json",{"running"})
    assert run_fixture(root,two,[str(fake),"ok"],root/"runs"/"b.lock",allowed,alias)==8; p.wait(timeout=4)
    detached=execution(root,"tmux"); session="marie_phase2b_selftest"
    subprocess.run(["tmux","kill-session","-t",session],capture_output=True)
    command=worker(root,detached,root/"runs"/"tmux.lock",[str(fake),"sleep",".4"],allowed)
    result=subprocess.run(["tmux","new-session","-d","-s",session,*command]); assert result.returncode==0
    final=wait_state(detached/"execution.json",{"succeeded","failed"},6); assert final["state"]=="succeeded"
    events=[json.loads(x) for x in (ok/"events.jsonl").read_text().splitlines()]
    assert [x["revision"] for x in events]==[1,2]
    approval=execution(root,"approval"); digest="abc123"
    create_json_exclusive(approval/"approval.json",{"approved":True,"scope":"exact-run","gate_digest":digest,
      "expires_at":(datetime.now().astimezone()+timedelta(minutes=5)).isoformat(),"consumed_at":None})
    assert consume_approval(approval,digest,"test") and not consume_approval(approval,digest,"test")
    unknown=execution(root,"unknown"); assert reconcile(unknown,False,False)=="startup_unknown"
    orphan=execution(root,"orphan"); atomic_json(orphan/"execution.json",{"state":"running","revision":0})
    assert reconcile(orphan,False,False)=="orphaned"
    print(json.dumps({"success":True,"tests":["exit0","exit42","signal","forbidden_executable","case_lock","canonical_json_alias_lock","tmux_detached","event_revision","approval_single_use","startup_unknown","orphan_recovery"],"matlab_invoked":False}))
  return 0
if __name__=="__main__":raise SystemExit(main())
