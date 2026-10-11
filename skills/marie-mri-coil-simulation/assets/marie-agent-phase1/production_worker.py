#!/usr/bin/env python3
"""Production worker for allowlisted MARIE execution profiles."""
import fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime import atomic_text,canonical_lock,exclusive,exclusive_backup,now,transition

ALLOWED_TRAINING_STAGES={"geometry","stage_a","tmd","stage_c","post"}

def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()

def resource_check(root,directory,state):
    requested=int(state.get("resources_requested",{}).get("workers",0))
    if requested<1 or requested>64: raise RuntimeError("invalid worker budget")
    total=requested
    for path in (root/"runs").glob("*/executions/*/execution.json"):
        if path.resolve()==(directory/"execution.json").resolve():continue
        try:value=json.loads(path.read_text())
        except Exception:continue
        if value.get("state") in {"launching","running"}:
            total+=int(value.get("resources_requested",{}).get("workers",0))
    if total>96:raise RuntimeError(f"global worker budget exceeded: {total}>96")
    return requested,total

def main():
    if len(sys.argv)!=4:return 2
    case,run,session=sys.argv[1:]; root=Path(__file__).resolve().parents[2]
    directory=root/"runs"/case/"executions"/run
    state=json.loads((directory/"execution.json").read_text())
    profile=state.get("production_profile","legacy-geometry-only")
    legacy_ok=(profile=="legacy-geometry-only" and state.get("stage")=="geometry"
        and state.get("cost")=="light" and not state.get("writes_active_json"))
    training_ok=(profile=="training-closed-loop-v1" and state.get("stage") in ALLOWED_TRAINING_STAGES)
    if not (legacy_ok or training_ok):return 12
    command=state.get("command",[])
    expected_text=os.environ.get("MATLAB_BIN")
    if not expected_text:return 12
    if not command or Path(command[0]).resolve()!=Path(expected_text).resolve():return 12
    code=70; json_handle=None; gpu_handle=None
    with exclusive(root/"runs"/case/"executions"/".case.lock"):
        try:
            with exclusive(root/"runs"/".locks"/"resources.lock"):
                requested,total=resource_check(root,directory,state)
            if int(state.get("resources_requested",{}).get("gpu",0)):
                gpu_path=root/"runs"/".locks"/"gpu0.lock"; gpu_path.parent.mkdir(parents=True,exist_ok=True)
                gpu_handle=gpu_path.open("a+"); fcntl.flock(gpu_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            json_before=None; real=None
            if state.get("writes_active_json"):
                active_item=next((x for x in state.get("snapshots",[]) if x.get("label")=="active_circuit_json"),None)
                if not active_item:raise RuntimeError("JSON-writing stage lacks active_circuit_json")
                real,lock_path=canonical_lock(root,root/active_item["source"])
                lock_path.parent.mkdir(parents=True,exist_ok=True); json_handle=lock_path.open("a+")
                fcntl.flock(json_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                json_before=sha256(real)
                backup=directory/"snapshots"/f"{real.name}.before_TMD"
                exclusive_backup(real,backup)
            env=os.environ.copy()
            env.update({"MARIE_CASE_TAG":case,"MARIE_RUN_ID":run,
                "MARIE_RUN_DIR":str(directory),"MARIE_WORKERS":str(requested)})
            for item in state.get("dependencies",[]):
                env[f"MARIE_DEP_{str(item['label']).upper()}"]=str(root/item["source"])
            transition(directory,"running","production worker started",
                updates={"started_at":now(),"session":session,"wrapper_pid":os.getpid(),
                    "workers_enforced":requested,"global_workers_reserved":total,
                    "active_json_sha256_before":json_before})
            log=root/state["log"]; log.parent.mkdir(parents=True,exist_ok=True)
            with log.open("ab",buffering=0) as handle:
                code=subprocess.run(command,cwd=root,env=env,stdout=handle,stderr=subprocess.STDOUT).returncode
            target="interrupted" if code<0 else ("succeeded" if code==0 else "failed")
            json_after=sha256(real) if real else None
            updates={"finished_at":now(),"exit_code":code,"process_exit_code":code,
                "wrapper_exit_code":0,"active_json_sha256_after":json_after}
            if code<0:updates["termination_signal"]=-code
            transition(directory,target,"MATLAB process exited",updates=updates)
            atomic_text(directory/"exitcode",f"{code}\n"); atomic_text(directory/"wrapper.exitcode","0\n")
        except BlockingIOError:
            transition(directory,"launch_failed","resource or active-JSON lock conflict",
                updates={"finished_at":now(),"wrapper_exit_code":8})
            atomic_text(directory/"wrapper.exitcode","8\n"); code=8
        except Exception as exc:
            transition(directory,"internal_error","production wrapper error",
                updates={"finished_at":now(),"wrapper_exit_code":70,
                    "errors":[f"{type(exc).__name__}: {exc}"]})
            atomic_text(directory/"wrapper.exitcode","70\n"); code=70
        finally:
            if json_handle:json_handle.close()
            if gpu_handle:gpu_handle.close()
    return code
if __name__=="__main__":raise SystemExit(main())
