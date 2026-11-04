import json,pathlib,subprocess
from prepare import ROOT,write
out=ROOT/'results/verification';out.mkdir(parents=True,exist_ok=True)
for name in ['pattern_test','kernel_test','impossible_test','ccss_test']:
    p=subprocess.run([str(ROOT/'bin'/name)],capture_output=True,text=True)
    write(out/(name+'.json'),p.stdout);write(out/(name+'.stderr'),p.stderr)
    assert p.returncode==0,(name,p.stderr)
    print(name,json.loads(p.stdout)['passed'],flush=True)
