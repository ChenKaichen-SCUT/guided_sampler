#!/usr/bin/env python3
import pathlib,sys,subprocess
from common import ROOT
root=pathlib.Path(sys.argv[1]);subprocess.run([sys.executable,ROOT/'scripts/patch_round2_host.py',root],check=True)
p=root/'HighDiv/makefile';s=p.read_text().replace(f'-I{ROOT}/include/round2',f'-I{ROOT}/include/round3 -I{ROOT}/include/round2');p.write_text(s)
p=root/'HighDiv/src/main/main.cpp';s=p.read_text().replace('mode=="a_observe_test"','(mode=="observe_trace"||mode=="a_observe_test")').replace('mode=="a_only_v2"','mode=="apply_trace"||mode=="a_only_v2"');p.write_text(s)
p=root/'HighDiv/src/sampler/liasampler.cpp';s=p.read_text().replace('while (!session->stop())','while (!session->stop()&&!session->cdcl_cap_reached())').replace('if (!session->stop() && session->remaining() >= 1.0)','if (!session->stop() && !session->cdcl_cap_reached() && session->remaining() >= 1.0)');p.write_text(s)
