import csv, statistics as st, json, sys
sys.dont_write_bytecode=True
rows=list(csv.DictReader(open('delta2-by-age.csv',encoding='utf-8')))
by={}
for r in rows:
    if r['attr'] in('pressure',): continue
    y,v=float(r['delta2_young']),float(r['delta2_vet'])
    by.setdefault(r['attr'],[]).append((r['start'],y,v,int(r['young_fallback']),float(r['oldShare_pooled']),float(r['oldShare_young']),float(r['oldShare_vet'])))
print('attr: median young/vet ratio over starts (non-fallback, vet>0); median oldShare pooled/young/vet')
allr=[]
for a,l in by.items():
    rs=[y/v for s,y,v,fb,*_ in l if not fb and v>0]
    allr+=rs
    print(a, round(st.median(rs),2) if rs else None, len(rs), [round(st.median([x[i] for x in l]),2) for i in (4,5,6)])
print('overall median ratio',round(st.median(allr),2),'n',len(allr),'frac>1',round(sum(r>1 for r in allr)/len(allr),2))
# live demo (W*=B0 -> identical)
bio=json.load(open('../../../data/defense-seventh/2026-27/bio.json',encoding='utf-8'))
rs_=bio['data']['resultSets'][0]; ix={h:i for i,h in enumerate(rs_['headers'])}
age={str(r[ix['PLAYER_ID']]):r[ix['AGE']] for r in rs_['rowSet']}
rk=list(csv.DictReader(open('../live/2026-10-29/ranking.csv',encoding='utf-8')))
out=[]
for r in rk:
    a=age.get(r['playerId']); out.append({'playerId':r['playerId'],'name':r['name'],'team':r['team'],'N':r['N'],'age':a,'group':'' if a is None else ('young' if float(a)<=23 else 'vet'),'ovr_base':r['ovr'],'ovr_wstar':r['ovr'],'dOVR':0.0})
names=['Cooper Flagg','Caleb Martin','Stephon Castle']
sel=[o for o in out if o['name'] in names]
with open('live-demo.csv','w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(sel)
print([ (o['name'],o['ovr_base']) for o in sel])
open('test-players.csv','w',encoding='utf-8').write('start,N,playerId,age,young,e_B0,e_Wstar,e_exp\n')
