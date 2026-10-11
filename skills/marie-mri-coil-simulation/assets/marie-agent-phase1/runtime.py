#!/usr/bin/env python3
"""Atomic execution-state primitives. Production submission is not enabled here."""
from __future__ import annotations
import fcntl, hashlib, json, os, secrets, shutil, subprocess
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ACTIVE={"authorized","launching","running"}
TERMINAL={"succeeded","failed","interrupted","launch_failed","internal_error","startup_unknown","orphaned"}
ALLOWED={
 "prepared":{"authorized","launching","launch_failed"},
 "authorized":{"launching","launch_failed"},
 "launching":{"running","launch_failed","interrupted","internal_error","startup_unknown"},
 "running":{"succeeded","failed","interrupted","internal_error","orphaned"},
}
def now(): return datetime.now().astimezone().isoformat(timespec="microseconds")
def atomic_text(path:Path,text:str):
    path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temp.open("w",encoding="utf-8") as h: h.write(text); h.flush(); os.fsync(h.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def atomic_json(path:Path,value:dict): atomic_text(path,json.dumps(value,ensure_ascii=False,indent=2)+"\n")
def create_json_exclusive(path:Path,value:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        data=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode()
        os.write(fd,data); os.fsync(fd)
    finally: os.close(fd)
def consume_approval(directory:Path,gate_digest:str,consumer:str):
    with exclusive(directory/".state.lock"):
        path=directory/"approval.json"; value=json.loads(path.read_text(encoding="utf-8"))
        expires=datetime.fromisoformat(value["expires_at"])
        if (not value.get("approved") or value.get("scope")!="exact-run"
            or value.get("gate_digest")!=gate_digest or value.get("consumed_at")
            or expires<=datetime.now().astimezone()): return False
        value["consumed_at"]=now(); value["consumed_by_run"]=consumer; atomic_json(path,value); return True
@contextmanager
def exclusive(path:Path,blocking=True):
    path.parent.mkdir(parents=True,exist_ok=True); handle=path.open("a+")
    try:
        flags=fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(handle,flags); yield handle
    finally: handle.close()
def transition(directory:Path,target:str,reason:str,actor="wrapper",updates=None):
    state_path=directory/"execution.json"
    with exclusive(directory/".state.lock"):
        value=json.loads(state_path.read_text(encoding="utf-8")); source=value["state"]
        if target not in ALLOWED.get(source,set()): raise RuntimeError(f"invalid transition {source}->{target}")
        revision=int(value.get("revision",0))+1
        value["state"]=target; value["revision"]=revision
        if updates: value.update(updates)
        event={"event_id":secrets.token_hex(12),"revision":revision,
          "time":now(),"from":source,"to":target,"actor":actor,"reason":reason}
        events=directory/"events.jsonl"
        if events.exists():
            for line in events.read_text(encoding="utf-8").splitlines(): json.loads(line)
        fd=os.open(events,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        try: os.write(fd,(json.dumps(event,ensure_ascii=False)+"\n").encode()); os.fsync(fd)
        finally: os.close(fd)
        atomic_json(state_path,value)
        return value
def canonical_lock(root:Path,active:Path):
    real=active.resolve(); real.relative_to(root.resolve())
    key=hashlib.sha256(str(real).encode()).hexdigest()
    return real,root/"runs"/".locks"/"active-json"/f"{key}.lock"
def reconcile(directory:Path,session_exists:bool,process_alive:bool):
    value=json.loads((directory/"execution.json").read_text(encoding="utf-8"))
    if value["state"] in TERMINAL:return value["state"]
    if value["state"]=="launching" and not session_exists:
        return transition(directory,"startup_unknown","tmux disappeared before running")["state"]
    if value["state"]=="running" and not process_alive:
        code_path=directory/"exitcode"
        if code_path.exists():
            code=int(code_path.read_text().strip()); target="succeeded" if code==0 else "failed"
            return transition(directory,target,"recovered from process exitcode",updates={"process_exit_code":code,"finished_at":now()})["state"]
        return transition(directory,"orphaned","no process and no exitcode")["state"]
    return value["state"]
def exclusive_backup(source:Path,target:Path):
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with source.open("rb") as inp,os.fdopen(fd,"wb",closefd=False) as out:
            shutil.copyfileobj(inp,out); out.flush(); os.fsync(out.fileno())
    finally: os.close(fd)
def run_fixture(root:Path,directory:Path,command:list[str],case_lock:Path,allowed_sha256:str,active_json:Path|None=None):
    """Test-only execution engine used by selftest.py; command is never read from production config."""
    json_handle=None
    try:
        executable=Path(command[0]).resolve()
        executable.relative_to((root/"_agent_tests"/"bin").resolve())
        if hashlib.sha256(executable.read_bytes()).hexdigest()!=allowed_sha256:
            raise RuntimeError("fake executable hash is not allowlisted")
        if "matlab" in executable.name.lower():
            raise RuntimeError("MATLAB is forbidden in fake selftests")
        with exclusive(case_lock,blocking=False):
            if active_json:
                real,lock_path=canonical_lock(root,active_json)
                lock_path.parent.mkdir(parents=True,exist_ok=True)
                json_handle=lock_path.open("a+")
                fcntl.flock(json_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                backup=directory/"snapshots"/f"{real.name}.before_TMD"
                backup.parent.mkdir(parents=True,exist_ok=True); exclusive_backup(real,backup)
            transition(directory,"running","fake worker started",updates={"started_at":now(),"wrapper_pid":os.getpid()})
            log=directory/"logs"/"fake.log"; log.parent.mkdir(parents=True,exist_ok=True)
            with log.open("ab",buffering=0) as h: code=subprocess.run(command,stdout=h,stderr=subprocess.STDOUT).returncode
            target="interrupted" if code<0 else ("succeeded" if code==0 else "failed")
            updates={"finished_at":now(),"process_exit_code":code,"wrapper_exit_code":0}
            if code<0: updates["termination_signal"]=-code
            transition(directory,target,"fake process exited",updates=updates)
            atomic_text(directory/"exitcode",f"{code}\n"); atomic_text(directory/"wrapper.exitcode","0\n")
            return code
    except BlockingIOError:
        try: transition(directory,"launch_failed","lock conflict",updates={"finished_at":now(),"wrapper_exit_code":8})
        except RuntimeError: pass
        atomic_text(directory/"wrapper.exitcode","8\n"); return 8
    except Exception as exc:
        try: transition(directory,"internal_error","wrapper internal error",updates={"finished_at":now(),"wrapper_exit_code":70,"errors":[f"{type(exc).__name__}: {exc}"]})
        except RuntimeError: pass
        atomic_text(directory/"wrapper.exitcode","70\n"); return 70
    finally:
        if json_handle: json_handle.close()
