"""E-162：從 bref adv html 取 PER／USG%／TS%（對齊同 c0d_collect.bpm_parse／build_bpm），並建 P15／P30 候選 pkl。
用法（repo root）：python -I -B -X utf8 <本檔>"""
import csv, html, json, pickle, re, statistics as st, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E142-card-target'))
import c0d_collect as C
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
WS = {'P15': 0.15, 'P30': 0.30}
F = ['per', 'usg_pct', 'ts_pct']


def parse(path):
    s = open(path, encoding='utf-8').read(); i = s.find('id="advanced"'); s = s[i:s.find('</table>', i)]; out = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)*([^<]+)', row) or re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row)
        if not m: continue
        nm = html.unescape(m.group(1)); k = C.norm(nm)
        if k in out: continue
        v = {}
        for f in F + ['bpm', 'games', 'mp']:
            x = re.search(rf'data-stat="{f}"[^>]*>([^<]*)<', row)
            v[f] = x.group(1) if x else ''
        out[k] = (nm, v)
    return out


def table(s):
    _, pop_all = C.population(s)
    byn = defaultdict(list)
    for pid, nm in pop_all.items(): byn[C.norm(nm)].append(pid)
    res, rows_bpm = {}, {}
    for k, (nm, v) in parse(C.EXT / f'bpm/adv{C.END[s]}.html').items():
        ps = byn.get(k, [])
        if len(ps) == 1:
            rows_bpm[ps[0]] = v
            try: res[ps[0]] = {f: float(v[f]) for f in F}
            except ValueError: pass
    return res, rows_bpm


def mix(t6, per, w):
    ids = sorted(set(t6) & set(per))
    o = [t6[i][1] for i in ids]; p = [per[i] for i in ids]
    mo, so, mp, sp = st.mean(o), st.pstdev(o), st.mean(p), st.pstdev(p)
    zz = [(1 - w) * (a - mo) / so + w * (b - mp) / sp for a, b in zip(o, p)]
    mz, sz = st.mean(zz), st.pstdev(zz)
    new = {}
    for i, v in zip(ids, zz):
        O = (v - mz) / sz * so
        new[i] = (O + t6[i][2], O, t6[i][2])
    return {i: new.get(i, t6[i]) for i in t6}, len(ids)


def main():
    info = {}
    for s in SEAS:
        tb, rb = table(s)
        # 核對：對齊結果與 bpm csv 的 playerId 集合、bpm 值一致
        ref = {int(r['playerId']): r for r in csv.DictReader(open(C.EXT / f'bpm/bpm_{s}.csv', encoding='utf-8-sig'))}
        same_ids = set(rb) == set(ref)
        same_bpm = all(rb[i]['bpm'] == ref[i]['bpm'] for i in ref if i in rb)
        t6 = pickle.load(open(ROOT / f'reports/E142-card-target/phase1-work/cands/T6-{s}.pkl', 'rb'))
        have = [i for i in t6 if i in tb]
        miss = len(t6) - len(have)
        info[s] = {'t6_n': len(t6), 'per_matched': len(have), 'per_missing': miss, 'miss_frac': miss / len(t6), 'align_ids_equal_bpm_csv': same_ids,
                   'align_bpm_values_equal': same_bpm, 'n_table': len(tb)}
        pickle.dump(tb, open(HERE / f'work/adv-{s}.pkl', 'wb'))
        if miss / len(t6) > 0.03:
            info[s]['STOP'] = True
        for arm, w in WS.items():
            new, n = mix(t6, {i: tb[i]['per'] for i in tb}, w)
            pickle.dump(new, open(HERE / f'work/cands/{arm}-{s}.pkl', 'wb'))
            info[s][f'{arm}_mixed_n'] = n
    (HERE / 'work/per-align.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
