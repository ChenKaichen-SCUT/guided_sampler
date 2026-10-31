#!/usr/bin/env python3
from common import *
root=pathlib.Path(sys.argv[2]);stage=sys.argv[1];assert stage in ('M','S')
subprocess.run([sys.executable,ROOT/'scripts/patch_round3_host.py',root],check=True)
p=root/'HighDiv/makefile';s=p.read_text().replace(f'-I{ROOT}/include/round3',f'-I{ROOT}/include/round4');p.write_text(s)
p=root/'HighDiv/src/main/main.cpp';s=p.read_text().replace('mode=="observe_trace"','mode=="M_observe"||mode=="observe_trace"').replace('mode=="apply_trace"','mode=="M_apply"||mode=="apply_trace"');p.write_text(s)
