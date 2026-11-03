import sys,pathlib,json,subprocess,itertools,hashlib,math,os
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/refinement'))
from independent import *
from common_r import write,digest
variant=sys.argv[1];out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
exe=ROOT/('build/budget_delivery_math_release' if variant=='release' else 'build/budget_delivery_math_sanitize')
manifest={'coefficients':[-6,6],'moduli':[1,16],'floor_sum_n':[0,12],'residue_moduli':[1,8],'residue_all_intervals':True,'signed_starts':[-3,0,3],'residue_lengths':[0,1,7],'domain_t':[-24,24],'seed':0,'script_sha256':digest(__file__),'binary_sha256':digest(exe)};write(out/'manifest.json',manifest)
err=open(out/'stderr.log','w');env=os.environ.copy();env.update(ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
p=subprocess.Popen([exe],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,env=env)
calls=0

def call(j,allow_error=False):
    global calls
    calls+=1;p.stdin.write(json.dumps(j)+'\n');p.stdin.flush();line=p.stdout.readline();assert line,('CLI terminated',p.poll());r=json.loads(line)
    if not allow_error:assert r['ok'],r
    return r if allow_error else r['result']
try:
    cases=[];expected=[]
    for a in range(-6,7):
        for c in range(-6,7):
            if c:cases.append(['div',str(a),str(c)]);expected.append([str(a//c),str(-((-a)//c))])
    for n,m,a,c in itertools.product(range(13),range(1,17),range(-6,7),range(-6,7)):
        cases.append(['floor_sum',*[str(x) for x in [n,m,a,c]]]);expected.append(str(sum((a*i+c)//m for i in range(n))))
    for start,length,m in itertools.product([-3,0,3],[0,1,7],range(1,9)):
        for a,c in itertools.product(range(-m,m+1),repeat=2):
            for lo in range(m):
                for hi in range(lo,m):
                    cases.append(['count',*[str(x) for x in [start,length,a,c,m,lo,hi]]]);expected.append(str(sum(lo<=(a*t+c)%m<=hi for t in range(start,start+length))))
    write(out/'arithmetic_cases.json',{'count':len(cases),'sha256':hashlib.sha256(json.dumps(cases,separators=(',',':')).encode()).hexdigest()})
    for begin in range(0,len(cases),5000):
        actual=call({'op':'arithmetic','cases':cases[begin:begin+5000]});assert actual==expected[begin:begin+5000],('arithmetic',begin,next((i for i,(a,b) in enumerate(zip(actual,expected[begin:begin+5000])) if a!=b),None))
    counts={'arithmetic':len(cases)};del cases,expected
    hits=0
    for a,c,bit,desired in itertools.product(range(-6,7),range(-6,7),range(4),[False,True]):
        actual=call({'op':'hits','a':str(a),'c':str(c),'bit':bit,'desired':desired,'intervals':[['-24','-3'],['0','0'],['4','24']]})
        matches=[t for t in range(-24,25) if (t<=-3 or t>=4) and bool(((c+a*t)%(1<<(bit+1)))&(1<<bit))==desired]
        exp=sorted(sorted([t for t in matches if t>0])[:2]+sorted([t for t in matches if t<0],reverse=True)[:2],key=lambda t:(abs(t),t));assert list(map(int,actual['parameters']))==exp,(a,c,bit,desired,actual,exp);hits+=1
    for a,c,bit,desired in [(1,0,63,True),(0,-1,63,True),(2,0,0,True),(-1,1<<100,32,True)]:
        r=call({'op':'hits','a':str(a),'c':str(c),'bit':bit,'desired':desired,'intervals':[[None,None]]});assert all(bool(((c+a*int(t))%(1<<(bit+1)))&(1<<bit))==desired for t in r['parameters'])
    counts['hits']=hits+4
    x,y=z3.Ints('x y');b=z3.Bool('b');base=[x>=-3,x<4,-2*x<3,x==2,x!=1,2*x==3]
    formulas=base+[z3.Or(a,c) for a,c in itertools.product(base,repeat=2)]+[z3.Not(a) for a in base]+[z3.Implies(base[0],base[1]),z3.Xor(base[0],base[1]),z3.If(b,base[0],base[1]),z3.Or(b,base[0]),z3.And(x+y==15,z3.Or(x==0,x==10)),z3.And(x*x>=0,y>=-4)]
    checked=0
    for f in formulas:
        ast,ns,vs=export(f)
        for start in [-3,0,2,4]:
            m=[1 if z3.is_bool(v) else 15-start if str(v)=='y' else start for v in vs]
            if not evaluate(ast,m)[0]:continue
            d=[[i,'-1' if str(v)=='y' else '1'] for i,v in enumerate(vs) if z3.is_int(v) and not (str(f).find('x*x')>=0 and str(v)=='x')]
            r=call({'op':'domain','ast':ast,'assignment':list(map(str,m)),'direction':d},True)
            if not r['ok']:
                assert 'unsupported' in r['error'],r;continue
            for t in range(-24,25):
                model=m.copy()
                for i,v in d:model[i]+=int(v)*t
                valid=evaluate(ast,model)[0];inside=any((lo=='-inf' or int(lo)<=t) and (hi=='+inf' or t<=int(hi)) for lo,hi in r['result']);assert valid==inside,(str(f),m,d,t,r);checked+=1
    ast,_,_=export(z3.And(x+y==15,z3.Or(x==0,x==10)))
    assert call({'op':'domain','ast':ast,'assignment':['0','15'],'direction':[[0,'1'],[1,'-1']]})==[['0','0'],['10','10']]
    counts['domain_points']=checked
    eqcases=[z3.And(2*x+3*y==0,4*x+6*y==0,0*x==0),z3.And(x==0,y==0),z3.Or(x==0,y==0),z3.And(2*x+3*y==0,z3.Int('z')>=-5)]
    for f in eqcases:
        a,_,_=export(f);r=call({'op':'algebra','ast':a})
        for d in r['directions']:
            v={i:int(x) for i,x in d['coefficients']};assert math.gcd(*v.values())==1 and v[min(v)]>0
            for eq in r['equalities']:assert sum(int(c)*v.get(i,0) for i,c in eq['coefficients'])==0
    counts['direction_systems']=len(eqcases)
    obs=[z3.Or(x==0,z3.Not(x==1)),z3.And(x>=0,z3.Or(x==1,x==2)),z3.And(z3.If(x>0,x,-x)>=0,z3.Or(x==0,x==1)),z3.And(x+y>=0,x+y<=5)]
    nobs=0
    for f in obs:
        a,ns,vs=export(f)
        for value in [-((1<<64)+1),-1,0,1,2,1<<31,1<<32,1<<63]:
            mm=[value for v in vs];valid,tr=evaluate(a,mm);actual=call({'op':'observe','ast':a,'assignment':list(map(str,mm))});assert actual['legal']==valid;assert {i:int(v) for i,z,o,v in actual['trace']}=={i:v for i,(bits,v) in tr.items()}
            ov,ot=official_trace(f,{str(v):mm[i] for i,v in enumerate(vs)});assert (ov,ot)==(valid,{i:v for i,(bits,v) in tr.items()});nobs+=1
    counts['official_traces']=nobs
    p.stdin.close();assert p.wait(timeout=20)==0;err.close();assert 'runtime error:' not in (out/'stderr.log').read_text();write(out/'summary.json',{'passed':True,'counts':counts,'calls':calls})
    print('independent math/observation PASS',variant,counts)
except BaseException as e:
    write(out/'failure.json',{'error':repr(e),'calls':calls});p.kill();raise
