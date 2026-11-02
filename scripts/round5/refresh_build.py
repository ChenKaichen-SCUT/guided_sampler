"""Regenerate in a scratch tree; install only changed files, preserving old evidence."""
from common5 import *
from patch_sources import patch
import tempfile,shutil
variant,attempt=sys.argv[1:3];assert not (BASE/'W_STARTED.json').exists();tree=ROOT/f'worktrees/round5_{variant}';prefix=ROOT/f'deps/round5_{variant}'
out=BASE/'build_logs'/('refresh_'+variant+'_'+attempt);out.mkdir(exist_ok=False)
with tempfile.TemporaryDirectory(prefix='r5-refresh-') as tmp:
    p=pathlib.Path(tmp)
    for d in ['z3/src/util','z3/src/smt','z3/src/sampler','z3/src/ast','HighDiv/src/main','HighDiv/src/sampler']:(p/d).mkdir(parents=True)
    patch(p,variant);changed=[]
    for f in p.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(p);data=f.read_bytes().replace(str(p).encode(),str(tree).encode());target=tree/rel
        if not target.exists() or target.read_bytes()!=data:target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(data);changed.append(str(rel))
    write(out/'changes.json',changed)
for cmd in [['make','-C',tree/'z3/build','-j','8'],['make','-C',tree/'z3/build','-j','8','install'],['make','-C',tree/'HighDiv','-j','4',f'Z3_PREFIX={prefix}',f'CXXFLAGS={"-O3 -DNDEBUG" if variant=="release" else "-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"} -std=c++20 -Wall']]:subprocess.run(list(map(str,cmd)),check=True)
write(out/'summary.json',{'passed':True,'library_sha256':digest(prefix/'lib/libz3.so'),'binary_sha256':digest(tree/'HighDiv/highdiv')})
