import sys,pathlib,csv,collections,hashlib,json,os,subprocess,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from common import *
BASE=ROOT/'results/round5'
OLD=ROOT/'results/round4'
def rows(p):
    return [json.loads(l) for l in pathlib.Path(p).open()] if pathlib.Path(p).exists() else []
def csvwrite(p,records,fields=None):
    records=list(records)
    if fields is None: fields=list(dict.fromkeys(k for r in records for k in r))
    with pathlib.Path(p).open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
