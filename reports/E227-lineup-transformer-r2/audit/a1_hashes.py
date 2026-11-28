import json, hashlib, subprocess
R='reports/E227-lineup-transformer-r2/'
m=json.load(open(R+'manifest.json',encoding='utf8'))
def show(c,p):
    r=subprocess.run(['git','show',f'{c}:{p}'],capture_output=True,creationflags=0x08000000)
    return r.stdout if r.returncode==0 else None
sh=lambda b:hashlib.sha256(b).hexdigest()
tot=crlf=bad=0
for sec,d in m.items():
    if not isinstance(d,dict): continue
    for k,h in d.items():
        if not isinstance(h,str) or len(h)!=64: continue
        p=(R+k) if not k.startswith('../') else 'reports/'+k[3:]
        res=[]
        for c in ('2b37fac','3db92f9'):
            b=show(c,p)
            if b is None: res.append(None); continue
            if sh(b)==h: res.append('raw')
            elif sh(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))==h: res.append('crlf')
            else: res.append(False)
        tot+=1
        if False in res or None in res: bad+=1; print('BAD',sec,k,res)
        elif 'crlf' in res: crlf+=1
print('total',tot,'match_raw',tot-crlf-bad,'match_after_LF->CRLF',crlf,'bad',bad)
