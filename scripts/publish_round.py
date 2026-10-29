#!/usr/bin/env python3
from common import *

def main():
    remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip();assert remote=='https://github.com/ChenKaichen-SCUT/guided_sampler.git'
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();assert branch=='round1-ab-guidance'
    local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p=subprocess.run(['git','push','-u','origin',branch],cwd=ROOT,text=True,capture_output=True)
    receipt={'command':['git','push','-u','origin',branch],'local_sha':local,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    if p.returncode==0:
        check=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt['remote_sha']=check;receipt['verified']=check==local
    else:receipt['verified']=False
    write(ROOT/'build/publish_receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));sys.exit(0 if receipt['verified'] else 1)
if __name__=='__main__':main()
