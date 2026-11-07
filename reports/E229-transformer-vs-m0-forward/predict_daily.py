"""E-229 每日前向預測記錄器：M0 跑完之後，對「M0 今天日期（美東）起算 +1 天內、尚未開賽」的比賽記下 T 與 M0 的賽前預測。
  python -I -X utf8 predict_daily.py            # 正式：寫 log/<美東今天>.json（同一天多次執行＝附加紀錄，評估取每場「開賽前最後一筆」）
  python -I -X utf8 predict_daily.py --smoke    # smoke：寫 log/<日期>-smoke.json，容許 M0 資料過期；評估一律排除 -smoke
T 與 M0 用「同一份」M0 評分檔（R-160 起 team-ratings.json 改由 T 產生，M0 另存 team-ratings-m0.json）的今日陣容與分鐘（teams[tid].today.rotation）；T 邊際 = 該陣容依分鐘 Gumbel top-5 抽樣（N=2000）餵 E-227 R2-stats
五個 seed 平均，×聯盟每隊每場回合數/100（prior 2025-26 train stints），主客各當 A／B 平均（E-228 方法）。M0 邊際 = 兩隊今日 margin 之差。
pX = Φ((邊際+2.5)/12)（H、σ 同 M0）。不讀任何比賽結果。"""
import argparse, datetime as dt, json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
SD = os.path.join(ROOT, 'data', 'season-source-2026-27')
H_ADV, SIGMA = 2.5, 12.0


def et_from_utc(u):       # 同 scripts/team_ratings_daily.py（Windows 沒有 tzdata）
    def nth_sunday(y, m, n):
        d = dt.date(y, m, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    y = u.year
    start = dt.datetime.combine(nth_sunday(y, 3, 2), dt.time(7), dt.timezone.utc)
    end = dt.datetime.combine(nth_sunday(y, 11, 1), dt.time(6), dt.timezone.utc)
    return u.astimezone(dt.timezone(dt.timedelta(hours=-4 if start <= u < end else -5)))


def Phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', action='store_true'); ap.add_argument('--allow-stale', action='store_true')
    ap.add_argument('--draws', type=int, default=2000); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--ratings', default=os.path.join(SD, 'team-ratings-m0.json')); ap.add_argument('--schedule', default=os.path.join(SD, 'schedule.json'))
    ap.add_argument('--log-dir', default=os.path.join(HERE, 'log')); ap.add_argument('--include-started', action='store_true', help='僅供測試：不篩開賽時間')
    a = ap.parse_args()
    t0 = time.time(); now = dt.datetime.now(dt.timezone.utc); et_today = et_from_utc(now).date().isoformat()
    tr = json.load(open(a.ratings, encoding='utf-8')); sch = json.load(open(a.schedule, encoding='utf-8'))
    m0_today = tr['today']
    if m0_today != et_today and not (a.smoke or a.allow_stale):
        print(f'M0 資料過期（ratings.today={m0_today}，現在美東日期={et_today}），不記錄'); return 2
    d0 = dt.date.fromisoformat(m0_today); dates = {d0.isoformat(), (d0 + dt.timedelta(days=1)).isoformat()}
    tip = sch.get('tipoff') or {}
    games = []
    for gid, d, h, aw in sch['games']:
        if d not in dates:
            continue
        tp = tip.get(gid)
        if tp is None:
            continue        # 沒有開賽時間無法確認賽前 → 不記
        tpu = dt.datetime.fromisoformat(tp.replace('Z', '+00:00'))
        if tpu > now or a.include_started:
            games.append((gid, d, str(h), str(aw), tp))
    os.makedirs(a.log_dir, exist_ok=True)
    fn = os.path.join(a.log_dir, f'{et_today}{"-smoke" if a.smoke else ""}.json')
    if not games:
        print('沒有符合的賽前場次', m0_today); return 0
    import numpy as np, torch
    torch.set_num_threads(a.threads)
    import e229_live
    rot = {tid: [(int(r['pid']), float(r['min'])) for r in t['today']['rotation']] for tid, t in tr['teams'].items()}
    names = {int(r['pid']): r['name'] for t in tr['teams'].values() for r in t['today']['rotation']}
    C, info = e229_live.make_ctx(et_today, names=names)
    recs = []; gen = now.isoformat(timespec='seconds')
    for gid, d, h, aw, tp in games:
        Rh, lh, rh = C.prep(rot[h]); Ra, la, ra = C.prep(rot[aw])
        rng = np.random.default_rng([229, int(gid)])
        x = C.net100(C.draw(Rh, lh, rh, rng, a.draws), C.draw(Ra, la, ra, rng, a.draws))     # [5 seed, N]
        mT = float((x.mean(1) * C.avg_poss / 100).mean())
        mM = float(tr['teams'][h]['today']['margin'] - tr['teams'][aw]['today']['margin'])
        recs.append(dict(game_id=gid, date=d, home=h, away=aw, homeAbbr=tr['teams'][h]['abbr'], awayAbbr=tr['teams'][aw]['abbr'],
                         pT=Phi((mT + H_ADV) / SIGMA), pM0=Phi((mM + H_ADV) / SIGMA), marginT=mT, marginM0=mM,
                         tipoff=tp, generated=gen, m0GeneratedAt=tr.get('generatedAt'), m0Today=m0_today, smoke=bool(a.smoke)))
    old = json.load(open(fn, encoding='utf-8')) if os.path.exists(fn) else {'records': []}
    old['records'] += recs; old['featureInfo'] = info; old['method'] = dict(draws=a.draws, K=e229_live.K_PRIOR_MIN, avg_poss=C.avg_poss, H=H_ADV, sigma=SIGMA)
    tmp = fn + '.tmp'; json.dump(old, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, fn)
    print(f'E229 記錄 {len(recs)} 場 -> {os.path.basename(fn)}，{time.time() - t0:.0f}s'); return 0


if __name__ == '__main__':
    sys.exit(main())
