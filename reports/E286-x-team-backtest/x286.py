"""E-286 共用：先 import E-285 x_lib（patch e227_model 認 'statsx'），再 import E-228 t_lib。不改兩邊凍結檔。"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REP, 'E285-transformer-def-inputs'))
import x_lib as X  # noqa: E402
sys.path.insert(0, os.path.join(REP, 'E228-transformer-team-rating'))
import t_lib as T  # noqa: E402
import numpy as np, torch  # noqa: E402
from e227_model import LineupNet  # noqa: E402
KIND = {'B': 'stats', 'X': 'statsx'}
ARMNAME = {'B': 'R2-stats', 'X': 'R2-statsX'}


def use_kind(kind):
    T.KIND = kind; T.F = X.n_feat(kind)


def ctx(arm, wpat, prior, dev='cpu'):
    """t_lib.Ctx 同邏輯，權重路徑與特徵種類換掉。wpat 含 {}＝seed。"""
    use_kind(KIND[arm])
    C = T.Ctx.__new__(T.Ctx)
    C.dev = dev; C.nets = []
    for sd in range(5):
        n = LineupNet(T.F); n.load_state_dict(torch.load(wpat.format(sd), map_location='cpu')); n.eval(); C.nets.append(n.to(dev))
    C.tab = T.load_player_table(prior); C.B = X.base_feats(prior, KIND[arm])
    C.med_h = float(np.median([d['heightInches'] for d in C.tab.values() if d.get('heightInches') is not None]))
    import csv, gzip
    poss = 0.0; gids = set()
    with gzip.open(os.path.join(T.E227, 'data', f'stints-train-{prior}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['possa'] != '' and r['possb'] != '':
                poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
    C.avg_poss = poss / 2 / len(gids)
    return C
