#!/usr/bin/env python3
import pathlib,subprocess,sys
from common import ROOT
root=pathlib.Path(sys.argv[1])
subprocess.run([sys.executable,ROOT/'scripts/patch_host.py',root,'guided'],check=True)
p=root/'HighDiv/makefile';s=p.read_text().replace(f'-I{ROOT}/include',f'-I{ROOT}/include/round2 -I{ROOT}/include');p.write_text(s)
p=root/'HighDiv/src/main/main.cpp';s=p.read_text().replace('mode=="off"','mode=="a_off_test"').replace('mode=="a_only"','mode=="a_observe_test"').replace('mode=="b_only"','(mode=="a_only_v2"||mode=="a_apply_test")');s=s.replace('            else if(mode=="a_plus_b")argp->guidance_mode=3;','');p.write_text(s)
