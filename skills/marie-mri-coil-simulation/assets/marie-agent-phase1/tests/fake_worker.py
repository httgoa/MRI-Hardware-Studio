#!/usr/bin/env python3
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime import run_fixture
root=Path(sys.argv[1]); directory=Path(sys.argv[2]); case_lock=Path(sys.argv[3])
command=json.loads(sys.argv[4]); allowed=sys.argv[5]; active=Path(sys.argv[6]) if len(sys.argv)>6 else None
raise SystemExit(run_fixture(root,directory,command,case_lock,allowed,active))
