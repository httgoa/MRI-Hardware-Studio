#!/usr/bin/env python3
"""Bind an explicit approval statement to one prepared MARIE execution."""
import json, re, secrets, sys
from datetime import datetime, timedelta
from pathlib import Path
SAFE=re.compile(r"^[A-Za-z0-9._-]+$")
def fail(msg,code=2): print(msg,file=sys.stderr); raise SystemExit(code)
def main():
    if len(sys.argv)!=4: fail(f"Usage: {sys.argv[0]} <CaseTag> <RunID> <approval-statement>")
    case,run,statement=sys.argv[1:]
    if not SAFE.fullmatch(case) or not SAFE.fullmatch(run): fail("Invalid CaseTag or RunID")
    if len(statement.strip())<8: fail("Approval statement is too short",3)
    root=Path(__file__).resolve().parents[2]
    path=root/"runs"/case/"executions"/run/"execution.json"
    if not path.is_file(): fail(f"Execution not found: {path}",4)
    execution=json.loads(path.read_text(encoding="utf-8"))
    if execution.get("state")!="prepared": fail(f"Execution is not prepared: {execution.get('state')}",5)
    target=path.parent/"approval.json"
    if target.exists(): fail(f"Approval already exists: {target}",6)
    approved_at=datetime.now().astimezone()
    value={"schema_version":1,"approval_id":secrets.token_hex(16),"scope":"exact-run",
      "case_tag":case,"run_id":run,"approved":True,
      "approved_at":approved_at.isoformat(timespec="seconds"),
      "expires_at":(approved_at+timedelta(hours=1)).isoformat(timespec="seconds"),
      "consumed_at":None,"gate_digest":execution.get("gate_digest"),
      "statement":statement.strip(),
      "warning":"This is a tool audit record, not cryptographic proof of human identity."}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(target.relative_to(root)); return 0
if __name__=="__main__": raise SystemExit(main())
