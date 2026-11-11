import json,sys
def tally(files):
    c={'ctl':0,'pass':0,'other':0,'touch':0,'tov':0,'games':0}
    for f in files:
        r=json.load(open(f,encoding='utf-8'));c['games']+=len(r['matches'])
        for t in r['teams']:
            for p in t['players']:
                s=p['stats'];c['ctl']+=s.get('e069Ctl',0);c['pass']+=s.get('e069Pass',0);c['other']+=s.get('e069Other',0);c['touch']+=s.get('e069Touch',0);c['tov']+=s.get('tov',0)
    return c
if __name__=='__main__':
    c=tally(sys.argv[1:]);n=len(sys.argv)-1
    print(json.dumps(c))
