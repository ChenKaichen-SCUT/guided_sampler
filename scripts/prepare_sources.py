#!/usr/bin/env python3
"""Reproduce the fixed public inputs; existing source/input directories are read only."""
import io,tarfile,urllib.request,shutil,tempfile
from common import *
SHA='f2c6e1756b13281d96cbf90a8bd940129e56cce4'
def main():
    if not UP.exists():
        url=f'https://codeload.github.com/laigroup/HighDiv/tar.gz/{SHA}'
        with urllib.request.urlopen(url) as response,tempfile.TemporaryDirectory() as temp:
            archive=pathlib.Path(temp)/'upstream.tar.gz'
            with open(archive,'wb') as f:shutil.copyfileobj(response,f)
            with tarfile.open(archive) as tf:
                root=pathlib.Path(temp)/'extract';root.mkdir()
                for member in tf.getmembers():
                    target=(root/member.name).resolve()
                    if not target.is_relative_to(root.resolve()) or member.issym() or member.islnk():raise RuntimeError('Unsafe archive member')
                tf.extractall(root)
            sources=list(root.iterdir());assert len(sources)==1;shutil.copytree(sources[0],UP)
    manifest=read(ROOT/'manifests/upstream.json')
    for entry in manifest['files']:assert digest(UP/entry['path'])==entry['sha256'],entry['path']
    INPUTS.mkdir(exist_ok=True)
    for entry in read(ROOT/'manifests/inputs.json'):
        target=ROOT.parent/entry['path']
        if not target.exists():
            assert entry['public_source'];shutil.copyfile(UP/entry['public_source'],target)
        assert digest(target)==entry['sha256'],entry['path']
    print('Verified fixed upstream and eight public input byte hashes; existing files were not overwritten.')
if __name__=='__main__':main()
