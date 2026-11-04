"""Export accepted projected assignments; does not claim to audit legality."""
import argparse,json,pathlib
ap=argparse.ArgumentParser();ap.add_argument('directory',type=pathlib.Path);args=ap.parse_args()
count=0
with (args.directory/'accepted.samples').open('w') as out:
    for line in (args.directory/'receipts.jsonl').read_text().splitlines():
        row=json.loads(line)
        if not row.get('accepted'):continue
        out.write(str(count)+': '+''.join(k+':'+v+';' for k,v in sorted(row['assignment'].items()))+'\n');count+=1
print(json.dumps(dict(exported_models=count,path=str(args.directory/'accepted.samples'))))
