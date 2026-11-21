import json, hashlib
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
d = json.load(open('work/season-values.json', encoding='utf-8'))['vals']
FIELD = {'threeValue': ('T', 'value'), 'help': ('H', 'x'), 'pressure': ('P', 'force'), 'presDisplay': ('P', 'disp')}
pairs = {}
for attr, (part, f) in FIELD.items():
    rows = []
    for a, b in zip(SEASONS, SEASONS[1:]):
        A, B = d[part][a], d[part][b]
        for pid in sorted(A, key=int):
            if pid in B and (A[pid]['MIN'] or 0) >= 500 and (B[pid]['MIN'] or 0) >= 500:
                rows.append({'pid': int(pid), 'pair': f'{a}->{b}', 'prev': A[pid][f], 'next': B[pid][f]})
    pairs[attr] = rows
out = {'pairs': pairs, 'rules': '相鄰季；兩季 Base Totals MIN 都 >=500；prev/next 為原始量（T: vol*(acc-rep)；H: -shrunk；P: force／presDisplay 原始 disp）；presDisplay 僅報告用'}
json.dump(out, open('h1-pairs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
h = hashlib.sha256(open('h1-pairs.json', 'rb').read()).hexdigest()
open('h1-pairs.sha256', 'w').write(h + '  h1-pairs.json\n')
print(h, {k: len(v) for k, v in pairs.items()})
