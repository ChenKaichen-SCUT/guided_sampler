"""Bind before common barrier; exec the native process without extra RNG draws."""
import os,sys,json,time,pathlib
job=json.loads(pathlib.Path(sys.argv[1]).read_text());os.sched_setaffinity(0,{job['cpu']});ready=pathlib.Path(job['ready']);ready.write_text(json.dumps({'pid':os.getpid(),'cpu':job['cpu'],'affinity':sorted(os.sched_getaffinity(0)),'monotonic_ready':time.monotonic()}))
gate=pathlib.Path(job['gate'])
while not gate.exists():time.sleep(.01)
os.chdir(job['cwd']);os.execvpe(job['command'][0],job['command'],job['environment'])
