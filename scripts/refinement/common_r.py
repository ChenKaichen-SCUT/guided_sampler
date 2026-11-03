import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'round6'))
from common6 import *
BASE=ROOT/'results/refinement'
MAN=ROOT/'manifests/refinement'
def attempt(stage,name):
    p=BASE/stage/name;p.mkdir(parents=True,exist_ok=False);return p
