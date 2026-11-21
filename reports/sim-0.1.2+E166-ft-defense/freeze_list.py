"""Freeze the j1 group before any E-166 run: non-C, 2022-25 pooledD >= 1.5, pooledPoss >= 5000, in the WinImp population (F-103 / od_split.py). Read-only."""
import csv, json, sys
sys.stdout.reconfigure(encoding='utf-8')
names = [json.loads(l)['avg']['name'] for l in open('reports/sim-0.1.0+E135-dblthreat-phys/checkpoint-ch1-60.jsonl', encoding='utf-8') if l.strip()]
POS = {r['name']: r['pos'] for r in csv.DictReader(open('reports/sim-0.1.0+E076-physique-dedup/winimp-dedup.csv', encoding='utf-8-sig'))}
RP = {r['name']: r for r in csv.DictReader(open('reports/sim-0.1.0+E085-physedge/rapm-2022-25.csv', encoding='utf-8')) if r['name']}
N = [n for n in names if n in RP and float(RP[n]['pooledPoss']) >= 5000]
G = sorted(n for n in N if float(RP[n]['pooledD']) >= 1.5 and POS.get(n, '?') != 'C')
json.dump({'population': sorted(N), 'j1': G}, open('reports/sim-0.1.2+E166-ft-defense/frozen-groups.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(N), len(G))
