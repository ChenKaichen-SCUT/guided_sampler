from common5 import *
import tarfile
from archive_round4 import Joined
def main():
    manifest=read(ROOT/'archives/round4/manifest.json');parts=[ROOT/'archives/round4'/r['file'] for r in manifest['parts']]
    for p,r in zip(parts,manifest['parts']):assert digest(p)==r['sha256']
    checked=0
    with tarfile.open(fileobj=Joined(parts),mode='r|gz') as archive:
        for entry in archive:
            if not entry.isfile():continue
            data=archive.extractfile(entry);h=hashlib.sha256()
            for b in iter(lambda:data.read(1<<20),b''):h.update(b)
            expected=manifest['members'][entry.name]['sha256'];assert h.hexdigest()==expected
            assert digest(ROOT/entry.name)==expected,entry.name
            checked+=1
    assert checked==len(manifest['members'])
    sources={}
    freeze=read(ROOT/'manifests/round4_S_implementation.json')
    for rel,h in freeze['sources'].items():
        p=ROOT/'worktrees/round4_S_release'/rel;assert digest(p)==h['new_sha256'];sources[rel]=h['new_sha256']
    write(BASE/'readonly/restoration_verification.json',{'passed':True,'archive_members_checked':checked,'existing_raw_equals_decompressed_archive':True,'source_tree_matches_frozen_patch':sources,'new_solver_checks':0})
    print('R4 archive and actual patched sources verified',checked)
if __name__=='__main__':main()
