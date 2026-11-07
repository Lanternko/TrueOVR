"""F-130 decomposition. cwd = repo root. Reads rr-f130.jsonl (sim, B2 k=2) + real130.json. Writes decomp130.json. Measurement only."""
import json, sys, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/F130-team-ftdraw-spread-diag/'
TI = json.load(open('reports/E140-foul-on-recal/team-ids.json', encoding='utf-8'))
nm = [t.get('name') or t.get('abbr') or str(t['id']) for t in TI]
S = [{'g': 0, 'poss': 0, 'fga': 0, 'oreb': 0, 'fta': 0, 'ft': {}, 'pl': {}} for _ in range(30)]
nseed = 0
for line in open(D + 'rr-f130.jsonl', encoding='utf-8'):
    r = json.loads(line); nseed += 1
    for k, T in r['tally'].items():
        s = S[int(k)]
        for a in ('poss', 'fga', 'oreb', 'fta'): s[a] += T[a]
        s['g'] += T['games']
        for a, v in T['ft'].items(): s['ft'][a] = s['ft'].get(a, 0) + v
        for pid, P in T['players'].items():
            q = s['pl'].setdefault(pid, {'name': P['name'], 'ftr': P['ftr'], 'fga': 0, 'fta': 0, 'ft': {}})
            q['fga'] += P['fga']; q['fta'] += P['fta']
            for a, v in P['ft'].items(): q['ft'][a] = q['ft'].get(a, 0) + v
G = np.array([s['g'] for s in S], float)
sim = {k: np.array([s[k] for s in S]) / G for k in ('poss', 'fga', 'oreb', 'fta')}
kind = lambda s, ks: sum(s['ft'].get(k, 0) for k in ks)
sim['shoot'] = np.array([kind(s, ('shooting', 'andOne')) for s in S]) / G
sim['andone'] = np.array([kind(s, ('andOne',)) for s in S]) / G
sim['nons'] = np.array([kind(s, ('nonShooting', 'intentional')) for s in S]) / G
sim['tech'] = np.array([kind(s, ('technical',)) for s in S]) / G
R = json.load(open(D + 'real130.json', encoding='utf-8'))
RT = [R['team'][str(i)] for i in range(30)]
m48 = np.array([t['min48'] for t in RT]); Gr = np.array([t['g'] for t in RT], float)
real = {k: np.array([t[k] for t in RT]) / m48 for k in ('fga', 'oreb', 'fta')}
tot = np.array([sum(t['ft'].values()) for t in RT], float)
for k2, ks in (('shoot', ('shooting',)), ('nons', ('nonshooting', 'other')), ('tech', ('technical',))):
    real[k2] = np.array([sum(t['ft'].get(k, 0) for k in ks) for t in RT]) / tot * real['fta']
sd = lambda x: float(np.std(x))
cor = lambda a, b: float(np.corrcoef(a, b)[0, 1])
res = {'nseed': nseed, 'games_per_team_sim': float(G.mean())}
res['repro'] = {'sd_real_fta': sd(real['fta']), 'sd_sim_fta': sd(sim['fta']), 'r': cor(sim['fta'], real['fta']), 'mean_real': float(real['fta'].mean()), 'mean_sim': float(sim['fta'].mean())}
print('REPRO', res['repro'])
sq = np.array([t['fta2'] / t['g'] for t in RT]); smean = np.array([t['fta'] for t in RT]) / m48
sdg = np.sqrt(np.maximum(sq - smean ** 2, 0))
noise = float(np.sqrt(np.mean(sdg ** 2 / Gr)))
res['real_noise_sd'] = noise; res['real_sd_denoised'] = float(np.sqrt(max(sd(real['fta']) ** 2 - noise ** 2, 0)))
print('noise', noise, 'denoised', res['real_sd_denoised'])
comp = {}
for k in ('fta', 'shoot', 'nons', 'tech', 'fga', 'poss', 'oreb'):
    s = sim[k]; r = real.get(k)
    comp[k] = {'mean_sim': float(s.mean()), 'sd_sim': sd(s), 'mean_real': None if r is None else float(r.mean()), 'sd_real': None if r is None else sd(r), 'r': None if r is None else cor(s, r)}
for k in ('shoot', 'nons', 'tech'):
    comp[k]['cov_share_sim'] = float(np.cov(sim[k], sim['fta'], bias=True)[0, 1] / sim['fta'].var())
    comp[k]['cov_share_real'] = float(np.cov(real[k], real['fta'], bias=True)[0, 1] / real['fta'].var())
    comp[k]['var_gap'] = float(sim[k].var() - real[k].var())
res['components'] = comp
sw = {}
for k in ('shoot', 'nons', 'tech'):
    t = sim['fta'] - sim[k] + real[k]; sw[k] = {'sd': sd(t), 'r_vs_real': cor(t, real['fta'])}
t = sim['fta'] - sim['nons'] - sim['tech'] + real['nons'] + real['tech']; sw['nons+tech'] = {'sd': sd(t), 'r_vs_real': cor(t, real['fta'])}
res['swap_component_to_real'] = sw
rate_s = sim['shoot'] / sim['fga']; rate_r = real['shoot'] / real['fga']
res['shoot_rate_per_fga'] = {'mean_sim': float(rate_s.mean()), 'mean_real': float(rate_r.mean()), 'sd_sim': sd(rate_s), 'sd_real': sd(rate_r), 'r': cor(rate_s, rate_r)}
res['fga'] = {'sd_sim': sd(sim['fga']), 'sd_real': sd(real['fga']), 'r': cor(sim['fga'], real['fga'])}
cf = {}
def cfx(label, shoot):
    t = sim['fta'] - sim['shoot'] + shoot; cf[label] = {'sd': sd(t), 'r_vs_real': cor(t, real['fta']), 'sd_shoot': sd(shoot)}
cfx('sim_vol x sim_rate (=sim)', sim['fga'] * rate_s)
cfx('real_vol x sim_rate', real['fga'] * rate_s)
cfx('sim_vol x real_rate', sim['fga'] * rate_r)
cfx('real_vol x real_rate (=real shoot)', real['fga'] * rate_r)
cfx('mean_vol x sim_rate', sim['fga'].mean() * rate_s)
cfx('mean_vol x real_rate', sim['fga'].mean() * rate_r)
res['volume_rate_swap'] = cf
RP = R['player']
share_s, share_r, rs_, rr_, rin_, rfull_, cover = [], [], [], [], [], [], []
for i, s in enumerate(S):
    ps = list(s['pl'].items())
    fs = np.array([p['fga'] for _, p in ps], float); fs /= fs.sum()
    rs_.append(np.array([(p['ft'].get('shooting', 0) + p['ft'].get('andOne', 0)) / p['fga'] for _, p in ps]))
    rin_.append(np.array([p['ftr'] for _, p in ps]))
    rp = [RP[pid] for pid, _ in ps]
    fr = np.array([q['fga'] for q in rp], float); cover.append(fr.sum() / RT[i]['fga']); frs = fr / fr.sum()
    rr_.append(np.array([q['ft'].get('shooting', 0) / q['fga'] for q in rp]))
    rfull_.append(np.array([q['fta'] / q['fga'] for q in rp]))
    share_s.append(fs); share_r.append(frs)
agg = lambda sh, rt: np.array([float((sh[i] * rt[i]).sum()) for i in range(30)])
cells = {}
for a, sh in (('share_sim', share_s), ('share_real', share_r)):
    for b, rt in (('rate_sim', rs_), ('rate_real', rr_), ('rate_input', rin_)):
        v = agg(sh, rt); cells[a + ' x ' + b] = {'mean': float(v.mean()), 'sd': sd(v), 'r_vs_real_rate': cor(v, rate_r), 'r_vs_sim_rate': cor(v, rate_s)}
res['share_rate_5p'] = {'coverage_real_fga_of_5': float(np.mean(cover)), 'cover_min': float(np.min(cover)), 'cover_max': float(np.max(cover)),
                        'sim_rate_recon_r': cor(agg(share_s, rs_), rate_s), 'mean_share_overlap_L1half': float(np.mean([np.abs(share_s[i] - share_r[i]).sum() / 2 for i in range(30)])), 'cells': cells}
inp = {}
for lab, sh in (('sim_share', share_s), ('real_share', share_r)):
    a = agg(sh, rin_); b = agg(sh, rfull_)
    inp[lab] = {'sd_input': sd(a), 'sd_actual_FTr': sd(b), 'r': cor(a, b), 'mean_input': float(a.mean()), 'mean_actual': float(b.mean())}
simFTr = sim['fta'] / sim['fga']; ain = agg(share_s, rin_)
inp['engine'] = {'sd_sim_totalFTr': sd(simFTr), 'sd_sim_shootrate': sd(rate_s), 'sd_input_teamweighted': sd(ain),
                 'r_totalFTr_vs_input': cor(simFTr, ain), 'r_shootrate_vs_input': cor(rate_s, ain),
                 'slope_shootrate_on_input': float(np.polyfit(ain, rate_s, 1)[0]), 'slope_totalFTr_on_input': float(np.polyfit(ain, simFTr, 1)[0])}
rFTr = real['fta'] / real['fga']
inp['real_team'] = {'sd_FTr': sd(rFTr), 'sd_sim_FTr': sd(simFTr), 'r': cor(rFTr, simFTr)}
res['input_vs_actual'] = inp
res['teams'] = [{'team': nm[i], 'real_fta': float(real['fta'][i]), 'sim_fta': float(sim['fta'][i]), 'real_shoot': float(real['shoot'][i]), 'sim_shoot': float(sim['shoot'][i]),
                 'real_nons': float(real['nons'][i]), 'sim_nons': float(sim['nons'][i]), 'real_tech': float(real['tech'][i]), 'sim_tech': float(sim['tech'][i]),
                 'real_fga': float(real['fga'][i]), 'sim_fga': float(sim['fga'][i]), 'in_ftr_5p': float(ain[i]), 'real_FTr_simshare': float(agg(share_s, rfull_)[i]),
                 'real_FTr_team': float(rFTr[i]), 'sim_FTr_team': float(simFTr[i])} for i in range(30)]
json.dump(res, open(D + 'decomp130.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
rd = lambda d: {a: (round(b, 3) if isinstance(b, float) else b) for a, b in d.items()}
for k, v in comp.items(): print(k, rd(v))
for k, v in sw.items(): print('swap', k, rd(v))
print('shoot rate', rd(res['shoot_rate_per_fga'])); print('fga', rd(res['fga']))
for k, v in cf.items(): print(k, rd(v))
sr = res['share_rate_5p']; print('cover', {k: round(v, 3) for k, v in sr.items() if k != 'cells'})
for k, v in cells.items(): print(k, rd(v))
for k, v in inp.items(): print('inp', k, rd(v))
# ---- named-5 weight: sim named players (playerId>0) carry w_s of team FGA, filler (id<=0) the rest; real: same 5 players' real FGA / team FGA
wS = np.array([sum(p['fga'] for p in S[i]['pl'].values()) / S[i]['g'] for i in range(30)]) / sim['fga']
wR = np.array(cover)
nam_ft_s = np.array([sum(p['ft'].get('shooting', 0) + p['ft'].get('andOne', 0) for p in S[i]['pl'].values()) / S[i]['g'] for i in range(30)])
nam_fga_s = wS * sim['fga']
rate_named_s = nam_ft_s / nam_fga_s                      # sim named-5 shooting FT per FGA (team-level, FGA-weighted)
rate_fill_s = (sim['shoot'] - nam_ft_s) / (sim['fga'] - nam_fga_s)
nam_ft_r = np.array([sum(RP[pid]['ft'].get('shooting', 0) for pid in S[i]['pl']) for i in range(30)], float)
nam_fga_r = np.array([sum(RP[pid]['fga'] for pid in S[i]['pl']) for i in range(30)], float)
rate_named_r = nam_ft_r / nam_fga_r
# real bench rate: team shooting FT (pbp) minus named, over team FGA minus named (season totals; players' stats across teams, approximate)
gm = np.array([t['g'] for t in RT], float)
rate_bench_r = (real['shoot'] * m48 - nam_ft_r) / (real['fga'] * m48 - nam_fga_r)
wn = {'w_sim_mean': float(wS.mean()), 'w_real_mean': float(wR.mean()), 'sd_w_sim': sd(wS), 'sd_w_real': sd(wR),
      'rate_named_sim': {'mean': float(rate_named_s.mean()), 'sd': sd(rate_named_s)}, 'rate_named_real': {'mean': float(rate_named_r.mean()), 'sd': sd(rate_named_r), 'r_vs_sim': cor(rate_named_s, rate_named_r)},
      'rate_filler_sim': {'mean': float(rate_fill_s.mean()), 'sd': sd(rate_fill_s)}, 'rate_bench_real': {'mean': float(rate_bench_r.mean()), 'sd': sd(rate_bench_r), 'r_with_named_real': cor(rate_bench_r, rate_named_r)}}
cfw = {}
def cfq(label, w, rn, rf):
    sh = sim['fga'] * (w * rn + (1 - w) * rf); t = sim['fta'] - sim['shoot'] + sh
    cfw[label] = {'sd_total': sd(t), 'r_vs_real': cor(t, real['fta']), 'sd_shoot': sd(sh), 'sd_rate': sd(w * rn + (1 - w) * rf)}
cfq('sim: w_sim, named_sim, filler_sim (=sim)', wS, rate_named_s, rate_fill_s)
cfq('w_real, named_sim, filler_sim', wR, rate_named_s, rate_fill_s)
cfq('w_real, named_sim, filler=mean', wR, rate_named_s, rate_fill_s.mean())
cfq('w_sim, named_real, filler_sim', wS, rate_named_r, rate_fill_s)
cfq('w_real, named_real, bench_real (=real rate)', wR, rate_named_r, rate_bench_r)
cfq('w_real, named_real, bench=mean', wR, rate_named_r, rate_bench_r.mean())
cfq('w_sim, named_sim, bench_real', wS, rate_named_s, rate_bench_r)
wn['counterfactual'] = cfw; res['named_weight'] = wn
json.dump(res, open(D + 'decomp130.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('NAMED', json.dumps({k: v for k, v in wn.items() if k != 'counterfactual'}, ensure_ascii=False))
for k, v in cfw.items(): print(k, rd(v))
