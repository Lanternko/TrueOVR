"""F-129 D1 descriptive (raw, no ridge): opponent FTA per 100 defensive possessions by block, split by whether a center is on the defending court. cwd = repo root."""
import sys, json; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
x = players(); RD = json.load(open('reports/F129-center-ft-defense-diag/real_d1_rows.json', encoding='utf-8')); real = RD['0'] + RD['1']
LD = 'reports/F129-center-ft-defense-diag/ledgers/'
def desc(rows):
    out = {}
    for tag in ('C_on', 'C_off'):
        T = dict(poss=0, fta=0, own=0, mate=0, offl=0, nsf=0, oth=0, fga=0, shortA=0, midA=0, longA=0, shot_trips=0, sfa_short=0, sf_short=0, nC=0, **{f'opp_{z}': 0 for z in ('short','mid','long')}, **{f'ft_{z}': 0 for z in ('short','mid','long')})
        for r in rows:
            cs = [i for i in r['d'] if i in x and x[i]['pos'] == 'C']; on = len(cs) > 0
            if on != (tag == 'C_on'): continue
            dset = set(r['d']); cset = set(cs); T['poss'] += r['poss']; T['fta'] += r['fta']; T['nsf'] += sum(r['nsf'].values()); T['oth'] += r['oth']
            for k, v in r['sf'].items():
                j, z = k.split('|'); j = int(j)
                if j in cset: T['own'] += v          # center's own shooting-foul FTs
                elif j in dset: T['mate'] += v
                else: T['offl'] += v
                if z == 'short': T['sf_short'] += v
                T['ft_' + z] += v
            for z in ('short', 'mid', 'long'): T[z + 'A'] += r[z + 'A']
            for z in ('short', 'mid', 'long'): T['opp_' + z] += r[z + 'A'] + r['sfa'].get(z, 0)
            T['fga'] += r['fga']; T['sfa_short'] += r['sfa'].get('short', 0)
        p = T['poss'] / 100; out[tag] = {'poss': T['poss'], **{f'opp100_{z}': T['opp_' + z] / p for z in ('short','mid','long')}, **{f'ft100_{z}': T['ft_' + z] / p for z in ('short','mid','long')}, **{f'rate_{z}': T['ft_' + z] / T['opp_' + z] for z in ('short','mid','long')}, 'fta100': T['fta'] / p, **{k + '100': T[k] / p for k in ('own', 'mate', 'offl', 'nsf', 'oth')}, 'rim_share': T['shortA'] / T['fga'], 'rim_A100': T['shortA'] / p,
                                         'ft_per_rim_opp': T['sf_short'] / (T['shortA'] + T['sfa_short']), 'sh_ft_per_opp_all': (T['own'] + T['mate'] + T['offl']) / (T['fga'] + sum(sum(r['sfa'].values()) for r in rows if (len([i for i in r['d'] if i in x and x[i]['pos'] == 'C']) > 0) == (tag == 'C_on')))}
    on, off = out['C_on'], out['C_off']; comp = rate = 0
    for z in ('short', 'mid', 'long'):
        rb = 0.5 * (on['rate_' + z] + off['rate_' + z]); ob = 0.5 * (on['opp100_' + z] + off['opp100_' + z])
        comp += (on['opp100_' + z] - off['opp100_' + z]) * rb; rate += ob * (on['rate_' + z] - off['rate_' + z])
    out['shift_share_sh_ft100'] = {'composition_volume': comp, 'foul_rate': rate, 'total_sh': comp + rate}
    out['diff'] = {k: out['C_on'][k] - out['C_off'][k] for k in out['C_on'] if k != 'poss'}; return out
res = {'real': desc(real)}
for c in 'ab': res['sim_' + c] = desc([r for s in range(20261103, 20261119) for r in sim_load(LD + f'v-{c}-{s}.json')])
json.dump(res, open('reports/F129-center-ft-defense-diag/d1_desc.json', 'w', encoding='utf-8'), indent=1)
for k, v in res.items():
    print(k)
    for t in ('C_on', 'C_off', 'diff'): print(' ', t, {a: round(b, 3) for a, b in v[t].items() if not a.startswith(('opp','ft100','rate'))})
    print('  shift', {a: round(b, 3) for a, b in v['shift_share_sh_ft100'].items()})
