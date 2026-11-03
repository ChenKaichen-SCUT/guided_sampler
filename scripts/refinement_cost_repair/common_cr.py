import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'refinement'))
from common_r import *
BASE=ROOT/'results/refinement_cost_repair'
MAN=ROOT/'manifests/refinement_cost_repair'
def attempt(stage,name):
    p=BASE/stage/name;p.mkdir(parents=True,exist_ok=False);return p
