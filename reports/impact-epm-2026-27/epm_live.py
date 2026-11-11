"""2026-27 自製 EPM 式影響力（只顯示，不進 OVR／卡片／DIQ）。

三個來源合成一個先驗，再以當季 stints 做 RAPM：
  當季 box 先驗  fit.py 凍結的 box→O/D 權重（reports/ovr-rapm-calibrated-2025-26）套在 2026-27 每 100 回合數據，
                 再依 fit.py 的 Poisson 抽樣變異往 log(mpg) 角色先驗收縮
  生涯 RAPM 先驗 reports/impact-rapm/rapm-prior.csv 的 pooledO/pooledD（2022-26）；新秀沒有
  合併         精度加權（1/變異）：box 變異 ＝ B×Poisson 變異 ＋ box 模型誤差；生涯變異 ＝ c ÷ pooledPoss。
               當季回合越少 → box 變異越大 → 越靠生涯（老將）或角色先驗（新秀）。
  RAPM         rapm.fit_rapm(obs, players, prior) 只用 2026-27 stints，λ 由 rapm.py 的 CV 選
  在場減不在場 rapm.onoff() 在 2026-27 stints 上算，交易球員依在場回合加權

用法：python -I reports/impact-epm-2026-27/epm_live.py        （也可 import：run()）
輸出：epm-live.csv、epm-live-summary.json；凍結權重快取 box-weights.json（不存在時才重建）。
"""
import csv, importlib.util, json, sys, tempfile
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STINTS = ROOT / 'reports/defense-seventh/2026-27/stints/stints.jsonl'
GAMES = ROOT / 'data/season-source-2026-27/player-games.json'
BIO = ROOT / 'data/defense-seventh/2026-27/bio.json'
RANKING_DIR = ROOT / 'reports/ovr-inseason-2026-27/live'
RAPM_PLAIN = ROOT / 'reports/impact-rapm/rapm.csv'
RAPM_PRIOR = ROOT / 'reports/impact-rapm/rapm-prior.csv'
WEIGHTS = HERE / 'box-weights.json'
MIN_C_POSS = 1000          # 校準 c 只用 2025-26 回合 ≥ 此值的人
SEASON = '2026-27'
SUM = ['PTS', 'FGM', 'FGA', 'FG3A', 'FTA', 'AST', 'TOV', 'OREB', 'DREB', 'STL', 'BLK', 'PF']


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rapm_mod():
    return _load(ROOT / 'reports/impact-rapm/rapm.py', 'rapm_mod')


def _csv(path, enc='utf-8'):
    return list(csv.DictReader(open(path, encoding=enc)))


def build_weights():
    """呼叫 fit.main()（輸出導到暫存目錄，不動 2025-26 的檔）取凍結權重，再估 c 與 box 模型誤差。"""
    fit = _load(ROOT / 'reports/ovr-rapm-calibrated-2025-26/fit.py', 'fit_mod')
    with tempfile.TemporaryDirectory() as tmp:
        fit.OUT = Path(tmp)
        got = fit.main()
    models, train, w, rapm = got['models'], got['train'], got['weights'], got['rapm']
    shrink = got['result']['shrinkage']
    # c：2025-26 單季 RAPM 對四季值的殘差。last ⊂ pooled，Var(last−pooled) ≈ c(1/Lposs − 1/Pposs)，用比值估計
    plain = {int(r['playerId']): r for r in _csv(RAPM_PLAIN)}
    prior = {int(r['playerId']): r for r in _csv(RAPM_PRIOR)}
    cal = {}
    for side in 'OD':
        num = den = 0.0
        n = 0
        for pid, r in prior.items():
            q = plain.get(pid)
            if not q or not q['lastSeasonPoss']:
                continue
            L, P = float(q['lastSeasonPoss']), float(r['pooledPoss'])
            if L < MIN_C_POSS or P <= L:
                continue
            num += (float(r['lastSeason' + side]) - float(r['pooled' + side])) ** 2
            den += 1 / L - 1 / P
            n += 1
        cal[side] = {'c': num / den, 'players': n}
    boxerr = {}
    for side in 'OD':
        cols, mu, sd, b = models[side]
        res, wt = [], []
        for p in train:
            pred = float(b[0] + ((np.array([p[c] for c in cols]) - mu) / sd) @ b[1:])
            pp = float(rapm[p['playerId']]['pooledPoss'])
            res.append((float(rapm[p['playerId']]['pooled' + side]) - pred) ** 2 - cal[side]['c'] / pp - p['pred' + side + 'Var'])
            wt.append(min(pp, 20000))
        boxerr[side] = max(0.05, float(np.average(res, weights=wt)))
    received = fit.expected.load(fit.expected.WEIGHTS)[2]
    # 角色先驗的 log(mpg) 斜率只在 2025-26 實際分鐘範圍內可信：場均分鐘下限＝2025-26 出賽 ≥10 場者的 5 百分位
    mpgs = [p['MIN'] / p['GP'] for p in fit.features().values() if p['GP'] >= 10]
    mpg_floor = float(np.percentile(mpgs, 5))
    train_ids = {p['playerId'] for p in train}
    out = {
        'note': 'fit.py 凍結權重（2025-26 box→O/D），由 epm_live.build_weights() 產生；刪掉此檔會重建',
        'models': {s: {'cols': m[0], 'mu': [float(x) for x in m[1]], 'sd': [float(x) for x in m[2]], 'b': [float(x) for x in m[3]]} for s, m in models.items()},
        'shrinkage': shrink, 'c': cal, 'boxErrVar': boxerr,
        'mpgFloor': mpg_floor,
        'receivedLeagueMean': float(np.mean(list(received.values()))),
        'received': {str(k): float(v) for k, v in received.items()},
        'trainingPlayers': len(train_ids),
    }
    WEIGHTS.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    return out


def frozen():
    if not WEIGHTS.exists():
        return build_weights()
    return json.loads(WEIGHTS.read_text(encoding='utf-8'))


def season_box(day=None):
    """2026-27 每人（含交易分隊）累計 → {pid: {name, MIN, GP, poss, 各項 per-100, last_date}}。"""
    d = json.loads(GAMES.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    rows = [r for r in d['rowSet'] if r[h['MIN']]]
    team = defaultdict(lambda: defaultdict(float))
    for r in rows:
        t = team[r[h['TEAM_ID']]]
        t['poss'] += r[h['FGA']] - r[h['OREB']] + r[h['TOV']] + 0.44 * r[h['FTA']]
        t['min'] += r[h['MIN']]
    acc = {}
    for r in rows:
        t = team[r[h['TEAM_ID']]]
        a = acc.setdefault(r[h['PLAYER_ID']], {'name': r[h['PLAYER_NAME']], 'poss': 0.0, 'MIN': 0.0, 'GP': 0, **{k: 0.0 for k in SUM}})
        a['poss'] += r[h['MIN']] * t['poss'] / (t['min'] / 5)
        a['MIN'] += r[h['MIN']]; a['GP'] += 1
        for k in SUM:
            a[k] += r[h[k]] or 0
    cutoff = max(r[h['GAME_DATE']] for r in rows)
    return {pid: a for pid, a in acc.items() if a['poss'] > 0}, cutoff


def heights():
    d = json.loads(BIO.read_text(encoding='utf-8'))['data']['resultSets']
    rs = d[0] if isinstance(d, list) else d
    h = {k: i for i, k in enumerate(rs['headers'])}
    out = {r[h['PLAYER_ID']]: float(r[h['PLAYER_HEIGHT_INCHES']]) for r in rs['rowSet'] if r[h['PLAYER_HEIGHT_INCHES']]}
    rk = sorted(p for p in RANKING_DIR.glob('*/ranking.csv'))
    rank_h = {}
    if rk:
        for r in _csv(rk[-1]):
            if r.get('heightInches'):
                rank_h[int(r['playerId'])] = float(r['heightInches'])
    return out, rank_h


def run(write=True):
    rapm = _rapm_mod()
    F = frozen()
    box, cutoff = season_box()
    bio_h, rank_h = heights()
    prior_csv = {int(r['playerId']): r for r in _csv(RAPM_PRIOR)}
    received, rec_mean = {int(k): v for k, v in F['received'].items()}, F['receivedLeagueMean']
    notes = {'heightFromBio': 0, 'heightFromRanking': 0, 'heightLeagueMean': 0, 'receivedRookieLeagueMean': 0, 'onoffSavedZero': len(box)}

    # --- 當季 box 預測與抽樣變異 ---
    pred = {}
    for pid, a in box.items():
        per = lambda k: a[k] / a['poss'] * 100
        if pid in bio_h:
            ht = bio_h[pid]; notes['heightFromBio'] += 1
        elif pid in rank_h:
            ht = rank_h[pid]; notes['heightFromRanking'] += 1
        else:
            ht = None
        if pid not in received:
            notes['receivedRookieLeagueMean'] += 1
        x = {'pts': per('PTS'), 'tsa': (a['FGA'] + 0.44 * a['FTA']) / a['poss'] * 100, 'fg3a': per('FG3A'), 'fta': per('FTA'),
             'ast': per('AST'), 'receivedFgm': received.get(pid, rec_mean) * per('FGM'), 'tov': per('TOV'), 'oreb': per('OREB'),
             'dreb': per('DREB'), 'stl': per('STL'), 'blk': per('BLK'), 'pf': per('PF'), 'onoffSaved': 0.0, 'height': ht}
        r = {'mpg': a['MIN'] / a['GP']}
        for side in 'OD':
            m = F['models'][side]
            cols, mu, sd, b = m['cols'], np.array(m['mu']), np.array(m['sd']), np.array(m['b'])
            xv = np.array([x[c] if x[c] is not None else mu[i] for i, c in enumerate(cols)])
            if 'height' in cols and x['height'] is None and side == 'D':
                notes['heightLeagueMean'] += 1
            r[side] = float(b[0] + ((xv - mu) / sd) @ b[1:])
            r[side + 'Var'] = sum((b[1 + i] / sd[i]) ** 2 * x[c] * 100 / a['poss'] for i, c in enumerate(cols) if c not in ('height', 'onoffSaved'))
        pred[pid] = r

    # --- 角色先驗收縮（凍結 a,b,tau2）、與生涯合併 ---
    out = {}
    for pid, r in pred.items():
        row = {'playerId': pid, 'name': box[pid]['name'], 'poss2627': box[pid]['poss'], 'mpg': r['mpg']}
        pr = prior_csv.get(pid)
        has_career = pr is not None and float(pr['pooledPoss']) > 0
        for side in 'OD':
            s = F['shrinkage'][side]
            role = s['priorIntercept'] + s['priorLogMpgSlope'] * np.log(max(r['mpg'], F['mpgFloor']))
            B = s['tau2'] / (s['tau2'] + r[side + 'Var'])
            boxv = role + B * (r[side] - role)
            vbox = B * r[side + 'Var'] + F['boxErrVar'][side]
            row['box' + side], row['boxVar' + side] = boxv, vbox
            if has_career:
                cval = float(pr['pooled' + side])
                vc = F['c'][side]['c'] / float(pr['pooledPoss'])
                row['career' + side] = cval
                row['prior' + side] = (boxv / vbox + cval / vc) / (1 / vbox + 1 / vc)
            else:
                row['career' + side] = None
                row['prior' + side] = boxv
        out[pid] = row

    # --- RAPM（只用 2026-27 stints）與在場減不在場 ---
    obs = list(rapm.observations([SEASON], reader=lambda s: open(STINTS, encoding='utf-8')))
    players = sorted({p for o in obs for p in o[2] + o[3]})
    fit, info = rapm.fit_rapm(obs, players, {p: (v['priorO'], v['priorD']) for p, v in out.items()})
    oo = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in rapm.onoff(obs):
        w = r['onPoss']
        oo[r['playerId']][0] += w
        oo[r['playerId']][1] += w * r['onNet'] if 'onNet' in r else 0
        oo[r['playerId']][2] += w * r['onOffNet'] if 'onOffNet' in r else 0
    rows = []
    for pid in players:
        f = fit[pid]
        v = out.get(pid)
        if v is None:   # stints 有、player-games 沒有（不應發生）：回合改用 stints 的
            continue
        w, on, off = oo[pid] if pid in oo else (0, 0, 0)
        rows.append({'playerId': pid, 'name': v['name'], 'O': f['O'], 'D': f['D'], 'net': f['O'] + f['D'], 'poss2627': v['poss2627'],
                     'careerO': v['careerO'], 'careerD': v['careerD'], 'boxO': v['boxO'], 'boxD': v['boxD'],
                     'priorO': v['priorO'], 'priorD': v['priorD'],
                     'onNet': on / w if w else None, 'onoffNet': off / w if w else None, 'onPoss': w, 'stintPoss': f['poss']})
    rows.sort(key=lambda r: -r['net'])
    summary = {
        'season': SEASON, 'dataCutoff': cutoff, 'players': len(rows), 'rookiesNoCareer': sum(r['careerO'] is None for r in rows),
        'lambda': info['lambda'], 'cvWeightedMSE': {str(k): v for k, v in info['cvWeightedMSE'].items()}, 'intercept': info['intercept'],
        'cCareerNoise': {s: F['c'][s] for s in 'OD'}, 'boxModelErrorVar': F['boxErrVar'],
        'shrinkageFrozen2025_26': F['shrinkage'], 'inputsNotes': notes,
        'disclosure': [
            'onoffSaved 特徵在 2026-27 一律設 0（沒有當季 on/off 抽樣的 v45 特徵）',
            'receivedFgm 用 2025-26 的接球出手占比乘當季 FGM 每 100 回合；2025-26 沒有的人（新秀）用聯盟平均占比',
            'height 取 2026-27 bio，新秀缺的用 ranking.csv heightInches，仍缺才用訓練平均',
            '回合數 poss2627 ＝ MIN × 球隊回合 ÷ (球隊分鐘/5)（同 fit.py）；onPoss 是 stints 在場回合（攻防合計）',
            '角色先驗的 mpg 下限＝2025-26 出賽≥10 場者的 5 百分位（低於此不外推，否則上場一兩分鐘的人會被推到很低）',
            '角色先驗收縮用 2025-26 凍結的 priorIntercept/priorLogMpgSlope/tau2，不用當季小樣本重估',
            'box 變異＝B×Poisson 變異＋box 模型誤差（訓練殘差扣掉生涯噪音與 Poisson 變異，下限 0.05）；這一項是為了避免 Poisson 單獨讓當季 box 在中等回合數就壓過生涯',
            'c（生涯噪音）＝Σ(單季−四季)² ÷ Σ(1/Lposs−1/Pposs)，限 2025-26 回合 ≥1000；含真實能力變動，所以是偏保守的上界',
        ],
    }
    if write:
        with open(HERE / 'epm-live.csv', 'w', encoding='utf-8', newline='') as fh:
            wr = csv.writer(fh)
            wr.writerow(['playerId', 'name', 'O', 'D', 'net', 'poss2627', 'careerO', 'careerD', 'boxO', 'boxD', 'priorO', 'priorD', 'onNet', 'onoffNet', 'onPoss'])
            fmt = lambda x, n=3: '' if x is None else round(x, n)
            for r in rows:
                wr.writerow([r['playerId'], r['name'], fmt(r['O']), fmt(r['D']), fmt(r['net']), round(r['poss2627'], 1), fmt(r['careerO']), fmt(r['careerD']),
                             fmt(r['boxO']), fmt(r['boxD']), fmt(r['priorO']), fmt(r['priorD']), fmt(r['onNet'], 2), fmt(r['onoffNet'], 2), round(r['onPoss'])])
        (HERE / 'epm-live-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return rows, summary


if __name__ == '__main__':
    r, s = run()
    print(json.dumps({k: s[k] for k in ['dataCutoff', 'players', 'rookiesNoCareer', 'lambda', 'cCareerNoise', 'boxModelErrorVar', 'inputsNotes']}, ensure_ascii=False, indent=1))
