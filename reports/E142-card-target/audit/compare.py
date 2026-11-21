import json
a=json.load(open('main.json',encoding='utf-8'));p=json.load(open('../phase1.json',encoding='utf-8'))
mx=0;bad=[]
for s,d in p['per_season'].items():
    for c,m in d.items():
        for k,v in m.items():
            kk='k2' if k=='twok' else ('n_k2' if k=='n_twok' else k)
            w=a['per_season'][s][c].get(kk)
            if v is None or w is None:
                if v!=w: bad.append((s,c,k,v,w))
                continue
            mx=max(mx,abs(v-w))
            if abs(v-w)>1e-9: bad.append((s,c,k,v,w))
print('max abs diff',mx,'mismatch',bad[:5])
print({k:(round(v,5),round(a['oof'][('k2' if k=='twok' else k)],5)) for k,v in p['oof_diff'].items()})
print(p['bootstrap']['lower90'],a['lower90'],p['bootstrap']['upper90'],a['upper90'])
print([(p['folds'][t]['Tstar'],a['folds'][t]['Tstar']) for t in p['folds']],p['final']['Tstar'],a['final']['Tstar'])
for f in ('sens_old2k','sens_single','sens_pcteval'):
    s=json.load(open(f+'.json',encoding='utf-8'));print(f,s['verdict'],{k:round(v,4) for k,v in s['oof'].items()},round(s['lower90'],4),s['judge'],{t:v['Tstar'] for t,v in s['folds'].items()})
