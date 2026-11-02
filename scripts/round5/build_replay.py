from common5 import *
variant=sys.argv[1];tree=ROOT/f'worktrees/round5_{variant}';out=ROOT/f'build/round5-ccss-replay-{variant}'
flags=['-std=c++17','-O1','-g','-I'+str(tree/'z3/src'),'-I'+str(tree/'z3/build')]
if variant=='sanitize':flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
archives=sorted((tree/'z3/build').rglob('*.a'))
extra=[tree/'z3/build/shell/mem_initializer.o',tree/'z3/build/shell/gparams_register_modules.o',tree/'z3/build/shell/install_tactic.o']
cmd=['g++',*flags,str(ROOT/'src/round5/ccss_replay_main.cpp'),*map(str,extra),'-Wl,--start-group',*map(str,archives),'-Wl,--end-group','-pthread','-ldl','-o',str(out)]
attempt=len(list((BASE/'build_logs').glob(f'replay_{variant}_command_*.json')))+1
write(BASE/'build_logs'/f'replay_{variant}_command_{attempt:02}.json',{'command':cmd});subprocess.run(cmd,check=True)
print('Built replay',variant,digest(out))
