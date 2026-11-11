"""E-229b M0：每場兩隊陣容對梯度對手（同每日流程 team_ratings_sim.mjs，200 局）→ margin。屬性＝d 之前最近一份 live ranking。
python -I -X utf8 sim_m0.py [workers] → work/m0.json {gid: {home: margin, away: margin}}（逐批寫檔，可續跑）"""
import json, os, sys, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import team_ratings_daily as M
LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
OUT = os.path.join(HERE, 'work', 'm0.json')
CHUNK = 40


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    games = json.load(open(os.path.join(HERE, 'work', 'games.json')))
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    teams = json.loads((M.E208 / 'inputs.json').read_text(encoding='utf-8'))['teams']; tids = sorted(teams)
    ladder = json.loads(M.LADDER.read_text(encoding='utf-8'))
    byf = collections.defaultdict(list)
    for g in games:
        for s in ('home', 'away'):
            if f"{g['gid']}|{s}" not in done:
                byf[g['folder']].append((g['gid'], s, g[s], g['rot_' + s]))
    t0 = time.time()
    for f, items in sorted(byf.items()):
        live_dir = M.Path(LIVE) / f
        meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
        rows = M.read_csv(live_dir / 'ranking.csv')
        cn = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-')
        cc = M.ROOT / f'reports/{cn}/ranking.csv'
        if not cc.exists():
            cc = M.ROOT / 'reports/card-0.2.12b/ranking.csv'
        card_rows = M.read_csv(cc)
        live_pids = {int(r['playerId']) for r in rows}
        for i in range(0, len(items), CHUNK):
            part = items[i:i + CHUNK]
            jobs = [{'team': tid, 'ver': f'{gid}{s}', 'roster': rot} for gid, s, tid, rot in part]
            need = {p for j in jobs for p, _ in j['roster']} - live_pids
            inp = {**M.engine_inputs(rows, card_rows, M.base_profiles(need, M.load_base_cards())), 'jobs': jobs, 'teamIds': tids, 'ladder': ladder}
            sim = M.run_sim(inp, 200, max(1, min(workers, len(jobs))))
            for gid, s, tid, rot in part:
                o = sim['res'][(tid, f'{gid}{s}')]
                done[f'{gid}|{s}'] = o['msum'] / o['n']
            json.dump(done, open(OUT, 'w'))
            print(f, i + len(part), '/', len(items), f'{time.time() - t0:.0f}s', flush=True)
    print('DONE', len(done), flush=True)


if __name__ == '__main__':
    main()
