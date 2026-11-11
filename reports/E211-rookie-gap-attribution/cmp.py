import csv, sys, statistics as st
def load(p, key): return {(r['season'], str(r['playerId'])): float(r[key]) for r in csv.DictReader(open(p, encoding='utf-8'))}
a = load(sys.argv[1], sys.argv[2]); b = load(sys.argv[3], sys.argv[4])
ks = [k for k in a if k in b]
d = [a[k] - b[k] for k in ks]
print(len(ks), 'maxabs', round(max(abs(x) for x in d), 4), 'mean', round(st.fmean(d), 4), 'n>0.01', sum(abs(x) > 0.01 for x in d))
