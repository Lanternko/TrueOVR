"""inseason／card 0.2.10g（E-192）：用人層（L、a）改四季滑動窗口。Win11 繼承 Win10，多做：
  ap（可出賽場次）＝P（出賽）＋C（教練決定未上場）；pl＝P；分類規則 = e094_t.classify（BASE_OPTS：疑似輪休 S 開、inactive 無原因碼歸 U）。
  L = log1p(窗口加權 MIN ÷ 窗口加權 ap)；a = 窗口加權 pl ÷ 窗口加權 ap。權重、c、本季逐場 u 全部同 Win10.sums10（E-175 U 臂）。
  y、v（年齡 ≤23／≥31）與 d（球隊勝率）不做窗口：y、v 用目標時點年齡；d 不在 Y0 設計矩陣內（b8_ydL＝0）。
出缺勤來源：2022-23～2024-25＝data/defense-seventh/<季>/boxes（建成 avail-hist-0210g.json.gz，build_avail_0210g.py）；
  2025-26＝data/season-source/dnp-2025-26.json（card 0.2.10 以來的來源）；本季＝data/defense-seventh/<本季>/boxes（只列上場名單的 ACTIVE 球員，
  沒有 INACTIVE 名單，所以本季的 C 只含「有穿球衣沒上場」）。2021-22 以前沒有 boxes：窗口權重在 2025-26 季末（card）與 2026-27 全季都碰不到它（k＝4 在 c＝82 權重 0；2026-27 的第 4 季是 2022-23）。
用法：W=Win11()；tabs,gd=W.cur_tabs()；W.usage_at(g, tabs, S, G) -> {'L','a','has'}（卡片名單 D.pids 長度向量）。"""
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import window8 as W8
import window10 as W10

L = W8.L
ROOT, HERE = W8.ROOT, W8.HERE
TARGET, PRIOR, G_TOTAL = W10.TARGET, W10.PRIOR, W10.G_TOTAL
BIRTHDATES = ROOT / 'data/defense-seventh' / TARGET / 'birthdates.json'   # scripts/fetch_birthdates_2026_27.mjs 產出的凍結檔（commonplayerinfo BIRTHDATE）
AVAIL_HIST = HERE / 'avail-hist-0210g.json.gz'
HIST_SEASONS = ['2022-23', '2023-24', '2024-25']
DNP_PRIOR = ROOT / 'data/season-source/dnp-2025-26.json'
# 與 e094_t 同值
INJ_KEYS = ('INJURY', 'ILLNESS', 'CONCUSSION', 'RECONDITIONING', 'PERSONAL', 'SUSPENSION', 'NOT_WITH_TEAM', 'TRADE')
COACH_CODES = ('DNP_COACH', 'INACTIVE_COACH', 'INACTIVE_GLEAGUE_ON_ASSIGNMENT', 'INACTIVE_GLEAGUE_TWOWAY')
SUS_MIN_PLAYED, SUS_MIN_AVG, SUS_RUN = 10, 24.0, 3
INACTIVE_NOREASON_TO_COACH = False   # BASE_OPTS
AGE_Y, AGE_V = 23, 31
USAGE_SWITCH_ENV = 'USAGE_WIN'       # '0'＝關掉窗口，回 0.2.10f（凍結 2025-26 用人特徵）
AGE_START_ENV = 'AGE_START'          # '0'＝y、v 回 0.2.10g 的舊行為（本季 bio AGE＝抓取當下年齡，季中過生日會跳）；預設 0.2.10h：開季當天足歲，整季固定


def minutes_of(s):
    """'PT35M56.00S'（或 '35:56'）-> 35.9333；空字串／缺 -> 0。"""
    if not s:
        return 0.0
    if 'M' not in s:                  # 少數舊場次是 'MM:SS'
        m, sec = s.split(':')
        return float(m or 0) + float(sec or 0) / 60.0
    s = s[2:] if s.startswith('PT') else s
    m, rest = s.split('M')
    return float(m or 0) + float(rest.rstrip('S') or 0) / 60.0


def box_rows(box):
    """一場 boxscore（頂層 data.game 或其外層 dict）-> (gid, [[pid, tid, status, reason, mn], ...])。"""
    g = box['data']['game'] if 'data' in box else box['game'] if 'game' in box else box
    rows = []
    for k in ('homeTeam', 'awayTeam'):
        t = g[k]
        for p in t['players']:
            rows.append([int(p['personId']), int(t['teamId']), p.get('status', ''), (p.get('notPlayingReason', '') or '').strip(),
                         minutes_of((p.get('statistics') or {}).get('minutes'))])
    return g['gameId'], rows


def base_class(status, reason, mn):
    if mn > 0:
        return 'P'
    if 'REST' in reason:
        return 'R'
    if any(k in reason for k in INJ_KEYS):
        return 'U'
    if reason in COACH_CODES:
        return 'C'
    if reason == '':
        if status == 'ACTIVE':
            return 'C'
        if status == 'INACTIVE':
            return 'C' if INACTIVE_NOREASON_TO_COACH else 'U'
    return 'U'


def classify(games):
    """games：[(gi, [[pid, tid, status, reason, mn], ...]), ...]（gi 升冪＝日期序）-> [(gi, pid, class)]。
    疑似輪休（S）：(球員, 隊) 有出賽 ≥10 場且場均 ≥24 分鐘，其「連續 C」不足 3 場者改 S（e094_t.classify 同規則，序列＝該隊賽程）。"""
    rows = []
    sched = defaultdict(list)
    for gi, pl in games:
        for pid, tid, status, reason, mn in pl:
            rows.append([pid, tid, gi, base_class(status, reason, mn), mn])
        for tid in {r[1] for r in pl}:
            sched[tid].append(gi)
    sidx = {t: {gi: i for i, gi in enumerate(sorted(set(v)))} for t, v in sched.items()}
    by = defaultdict(list)
    for k, r in enumerate(rows):
        by[(r[0], r[1])].append(k)
    for (pid, tid), ks in by.items():
        played = [rows[k][4] for k in ks if rows[k][3] == 'P']
        if len(played) < SUS_MIN_PLAYED or float(np.mean(played)) < SUS_MIN_AVG:
            continue
        seq = ['X'] * len(sidx[tid])
        where = {}
        for k in ks:
            i = sidx[tid][rows[k][2]]
            seq[i] = rows[k][3]
            where[i] = k
        i = 0
        while i < len(seq):
            if seq[i] != 'C':
                i += 1
                continue
            j = i
            while j + 1 < len(seq) and seq[j + 1] == 'C':
                j += 1
            if j - i + 1 < SUS_RUN:
                for q in range(i, j + 1):
                    rows[where[q]][3] = 'S'
            i = j + 1
    return [(r[2], r[0], r[3]) for r in rows]


def hist_games(s):
    """過去季 s 的出缺勤列 {gid: [[pid, tid, status, reason, mn], ...]}。2025-26 讀 dnp json，其餘讀 avail-hist 快取。"""
    if s == PRIOR:
        d = json.loads(DNP_PRIOR.read_text(encoding='utf-8'))['games']
        return {g: [[int(p[0]), int(p[1]), p[2], p[3], float(p[4])] for p in v['players']] for g, v in d.items()}
    with gzip.open(AVAIL_HIST, 'rt', encoding='utf-8') as fh:
        return json.load(fh)[s]


def cur_games(data26, gids):
    """本季：gids（依 gi 序）每場的 boxes（canonical data/defense-seventh/<本季>/boxes；history 截斷目錄不含 boxes，只取 gids 內的場次）。"""
    bd = ROOT / 'data/defense-seventh' / TARGET / 'boxes'
    out = []
    for gi, g in enumerate(gids):
        p = bd / f'{g}.json'
        if not p.exists():
            continue
        gid, rows = box_rows(json.loads(p.read_text(encoding='utf-8')))
        assert gid == g, (gid, g)
        out.append((gi, rows))
    return out


class Win11(W10.Win10):
    def __init__(self, data26=W8.DATA26):
        super().__init__(data26)
        self.use_win = __import__('os').environ.get(USAGE_SWITCH_ENV, '1') != '0'
        for s in HIST_SEASONS + [PRIOR]:
            self.T10[s]['ap'] = self._ap_tab(s)
        self.age25 = self._ages(ROOT / 'data/benchmark-source/bio.json')
        self.age_cur = self._ages(self.data26 / 'bio.json') if (self.data26 / 'bio.json').exists() else {}
        self.age_start = self._ages_at_start() if __import__('os').environ.get(AGE_START_ENV, '1') != '0' else {}
        self.age_fallback = {'bio': set(), 'bio25': set(), 'none': set()}   # age_flags 沒有 DOB 時退回哪裡（記錄用）

    def _ages_at_start(self):
        """{pid: 開季當天足歲}。開季日＝本季 player-games 最早 GAME_DATE（整季固定；ovr_history 的截斷夾最早日不變）。沒有 birthdates.json 直接報錯（不靜默退回舊行為）。"""
        import datetime as dt
        if not BIRTHDATES.exists():
            raise FileNotFoundError(f'{BIRTHDATES} 不存在：先跑 node scripts/fetch_birthdates_2026_27.mjs（或 AGE_START=0 回 0.2.10g）')
        pl = W8._rows(self.data26 / 'player-games.json')
        self.season_start = dt.date.fromisoformat(min(r['GAME_DATE'] for r in pl)[:10]) if pl else None
        if self.season_start is None:
            return {}
        out = {}
        for pid, b in json.loads(BIRTHDATES.read_text(encoding='utf-8'))['birthdates'].items():
            d = dt.date.fromisoformat(b)
            out[int(pid)] = self.season_start.year - d.year - ((self.season_start.month, self.season_start.day) < (d.month, d.day))
        return out

    @staticmethod
    def _ages(path):
        rs = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        h = rs['headers']
        return {int(r[h.index('PLAYER_ID')]): r[h.index('AGE')] for r in rs['rowSet'] if r[h.index('AGE')] is not None}

    def _ap_tab(self, s):
        D = self.D
        gi_of = {g: i for i, g in enumerate(D.gids[s])}
        hg = hist_games(s)
        games = sorted(((gi_of[g], v) for g, v in hg.items() if g in gi_of), key=lambda x: x[0])
        return self._tab_from(classify(games))

    def _tab_from(self, cls):
        D = self.D
        sel = [(gi, D.pidx[pid], c) for gi, pid, c in cls if pid in D.pidx and c in ('P', 'C')]
        gi, pi, c = (np.array([x[j] for x in sel]) for j in range(3))
        return L.Tab(gi, pi, np.ones(len(sel)), (c == 'P').astype(float), D.NP)   # agg -> (ap 加權和, pl 加權和)

    # ---------------- 本季
    def cur_tabs(self):
        t, gd = super().cur_tabs()
        pl = W8._rows(self.data26 / 'player-games.json')
        tm = W8._rows(self.data26 / 'team-games.json')
        by = {}
        for r in tm:
            if r['MIN']:
                by.setdefault(r['GAME_ID'], []).append(r)
        dates = {r['GAME_ID']: r['GAME_DATE'] for r in pl}
        gids = sorted((g for g in by if len(by[g]) == 2), key=lambda g: (dates.get(g, ''), g))
        t['ap'] = self._tab_from(classify(cur_games(self.data26, gids)))
        return t, gd

    # ---------------- 窗口用人特徵
    def usage_at(self, g, tabs, S=TARGET, G=G_TOTAL, nseas=4):
        """全 D.NP 長：L、a、has（窗口內有 ap）。MIN 取 player-games（同 mpg 窗口），ap／pl 取出缺勤。"""
        mn, _ = self.sums10('mpg', g, tabs, G, S, nseas)
        ap, pl = self.sums10('ap', g, tabs, G, S, nseas)
        has = ap > 0
        den = np.where(has, ap, 1.0)
        return {'L': np.where(has, np.log1p(mn / den), np.nan), 'a': np.where(has, pl / den, 0.0), 'has': has, 'ap': ap, 'pl': pl, 'mn': mn}

    def age_summary(self):
        """meta 用：開季日、有 DOB 人數、退回 bio 年齡的人數（age_flags 對 D.pids 全部呼叫過之後才完整）。"""
        f = self.age_fallback
        return {'seasonStart': str(self.season_start), 'birthdates': len(self.age_start), 'file': BIRTHDATES.relative_to(ROOT).as_posix(),
                'fallbackBio2627': len(f['bio']), 'fallbackBio2526': len(f['bio25']), 'noAge': len(f['none'])}

    def age_flags(self, pid):
        """(age, y, v)：0.2.10h 起用開季當天足歲（birthdates.json）；沒有 DOB 的人退回本季 bio 的 AGE，再退回 2025-26 bio（age_fallback 記人）；
        都沒有 -> (None, 0, 0)。AGE_START=0＝0.2.10g：本季 bio AGE、再 2025-26 bio。"""
        a = self.age_start.get(pid)
        if a is None:
            a = self.age_cur.get(pid)
            if self.age_start and a is not None:
                self.age_fallback['bio'].add(pid)
            elif a is None:
                a = self.age25.get(pid)
                if self.age_start:
                    self.age_fallback['bio25' if a is not None else 'none'].add(pid)
        return a, float(a is not None and a <= AGE_Y), float(a is not None and a >= AGE_V)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    W = Win11()
    print('ok', {s: len(W.T10[s]['ap'].gi) for s in HIST_SEASONS + [PRIOR]})
