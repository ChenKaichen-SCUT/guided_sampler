#!/usr/bin/env python3
"""Non-force publication of the complete audited third-round branch."""
from common import *
def main():
 branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();assert branch=='round3-a-semantic-diagnosis'
 remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip();assert remote=='https://github.com/ChenKaichen-SCUT/guided_sampler.git'
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),'Commit the full delivery before publication'
 assert read(ROOT/'results/round3_semantics/audit_summary.json')['passed'];assert read(ROOT/'archives/round3_semantics/verification.json')['passed']
 manifest=read(ROOT/'archives/round3_semantics/manifest.json')
 for part in manifest['parts']:
  p=ROOT/'archives/round3_semantics'/part['file'];assert digest(p)==part['sha256'];subprocess.run(['git','ls-files','--error-unmatch',p.relative_to(ROOT)],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
 local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();cmd=['git','push','-u','origin',branch];r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 receipt={'command':cmd,'local_sha':local,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'verified':False}
 if r.returncode==0:
  receipt['remote_sha']=subprocess.check_output(['git','ls-remote','origin','refs/heads/'+branch],cwd=ROOT,text=True).split()[0];receipt['verified']=receipt['remote_sha']==local
 write(ROOT/'build/round3-publish-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False));sys.exit(0 if receipt['verified'] else 1)
if __name__=='__main__':main()
