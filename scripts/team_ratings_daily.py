"""每日傷病名單＋球隊評分（E-208 第二階段，spec: reports/E208-team-rating/spec-site.md）。

流程：抓傷病（ESPN → 官方傷病報告 PDF → 沿用前一份）→ 抓 NBA.com 賽程 → 組兩份分鐘（近況／今日陣容）→ 模擬（scripts/team_ratings_sim.mjs，引擎 sim 0.1.4）→ 預測勝場
→ 寫 data/season-source-2026-27/team-ratings.json 與 injuries.json。網頁由 build_teams_page.py 讀 team-ratings.json 建成 teams.html。

分鐘規則（spec: reports/E208-team-rating/spec-minutes-return.md；正規化用 minutes_rules.norm）：
- 每位目前在該隊名單的球員：分鐘＝他本季自己最近 ≤10 場「有出場（min>0）」的平均（不管當時在哪隊；0 分鐘的場次不算）。
- 候選人：該隊最近 10 場至少出場一次的人；另外，該隊最近 10 場沒出場、但自己最近 ≤10 場平均 ≥ RETURN_MIN（15）分鐘的人也算（視為傷缺復出，不是教練不用）。
  15 分鐘門檻寫死，不看結果調。本季還沒出場的人沿用季前預期 fallback。
- 分鐘分配（R-153，取代 R-151 固定分鐘表）：教練分鐘 × 焦灼比賽槽乘數，等比放大到 240、單人上限 36、不設下限。
  教練分鐘＝上面算出的近 ≤10 場有出場平均；槽＝可上場候選人依教練分鐘由多到少（同分照 OVR 再照 pid）的名次 1…10，第 11 名以後併一槽（11+）。
  min_i＝教練分鐘 × CLOSE_MULT[槽]，再同比放大到合計 240；超過 36 的人固定 36，多出的分鐘依比例分給未達上限者，反覆到收斂。
  所有人到 36 仍不足 240（<7 人）時，上限放寬到 MAX_SHORT＝40；仍不足（<6 人）就 240 平均攤。順序／名次只決定乘數，不直接決定分鐘。
  （候選人不到 8 人時仍照舊由季前預期補到 8 人。）CLOSE_MULT（R-156 重量）是資料量的常數（見檔頭附近註解），不看結果調。
- 近況（全員）：不扣人。
- 今日陣容（可用）：先拿掉傷病名單裡 Out／Doubtful／Questionable／Day-To-Day／Suspension 的人（ESPN 與官方 PDF 的狀態字都對應；Probable、Available、
  不在名單上的人照常上場），剩下的再套表。不做機率加權：同一個人不會同時在可用名單與傷兵名單。
  沒有 returnDate 時：Out／Suspension 當整季缺陣；Questionable／Doubtful／Day-To-Day 只缺今天的比賽（隔天回來）。
- 每次抓完傷病（ESPN／PDF 成功）把 injuries.json 另存 injury-snapshots/<UTC 時間戳>.json（只存不讀，之後量各狀態實際上場率）。
評分＝名單對五支「梯度對手」（E-224 B5，R-158 起；表在 data/team-ratings-gradient-ladder.json）各打 SEEDS/5 場（換主客）：ORtg／DRtg 扣「近況」版的聯盟平均（兩版共用，兩版差＝純傷兵影響）。
預測勝場＝目前勝 + 剩餘賽程逐場 Φ((marginA − marginB ± H) / σ)；H=2.5、σ=12（同 E-208）。賽程抓不到時，剩餘場次用對其他 29 隊的平均勝率。
  近況版：陣容全程不變。今日陣容版：每場依 ESPN returnDate 切換陣容——該場日期 < 傷兵 returnDate（或 ≤ 今天，ESPN 日期過期但仍列 Out）就缺陣，之後回來；
  沒有 returnDate（例如 PDF 備援）當整季缺陣。每隊依「哪些人缺陣」分成幾種陣容狀態，各模擬一次；主表的今日 Net 維持今天陣容。
子程序一律 CREATE_NO_WINDOW。失敗由呼叫端（daily_inseason_update）降級成 WARNING，不擋球員頁發布。

用法：python -I -X utf8 scripts/team_ratings_daily.py [live_dir] [--seeds N] [--workers N] [--no-fetch] [--injury-source auto|espn|pdf]
  live_dir 預設＝publish_state.json 最後發布那天的夾（內含 ranking.csv、meta.json）。
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import glob
import json
import logging
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E208 = ROOT / 'reports/E208-team-rating'
sys.path.insert(0, str(E208))
sys.path.insert(0, str(Path(__file__).resolve().parent))      # -I 不含腳本目錄
from injury_desc import injury_desc  # noqa: E402
import actual_blend  # noqa: E402  (R-171 本季實際表現殘差)
from minutes_rules import norm  # noqa: E402  (E-208 (c) 的正規化：前 10 人、240 分鐘、上限 48)

SEASON = '2026-27'
SRC = ROOT / f'data/season-source-{SEASON}'
INJURIES = SRC / 'injuries.json'
LADDER = ROOT / 'data/team-ratings-gradient-ladder.json'
SCHEDULE = SRC / 'schedule.json'
RATINGS = SRC / 'team-ratings.json'
BOXES = ROOT / f'data/defense-seventh/{SEASON}/boxes'
LEAGUE = ROOT / f'data/defense-seventh/{SEASON}/league.json'
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
SIM = ROOT / 'scripts/team_ratings_sim.mjs'
ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'
# 官方傷病報告 PDF：每 15 分鐘一份，檔名 Injury-Report_<YYYY-MM-DD>_<HH_MM><AM|PM>.pdf（美東時間、12 小時制；2026-11-02 實測 04_15AM、04_00AM、03_45AM… 都在）。
PDF_URL = 'https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d}_{t}.pdf'
PDF_LOOKBACK_H = 36
PDFTOTEXT_FALLBACK = r'C:\Program Files\Git\mingw64\bin\pdftotext.exe'
PDF_STATUS = ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available')
NBA_TEAMS = {'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI',
             'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW',
             'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL',
             'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
             'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
             'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA',
             'Washington Wizards': 'WAS'}
H, SIGMA, SEEDS, GAMES, LAST_N = 2.5, 12.0, 200, 82, 10   # H、σ 同 E-208 預註冊
RETURN_MIN = 15.0                                         # 最近 10 場沒出場、但自己平均 ≥ 此分鐘的現役球員補回輪替（寫死，不看結果調）
OUT_STATUS = {'out', 'doubtful', 'questionable', 'day-to-day', 'suspension'}   # 今日陣容（可用）預先排除的狀態（小寫；R-151）；Probable／Available 照常上場
LONG_OUT = {'out', 'suspension'}                          # 沒有 returnDate 時當整季缺陣的狀態；其餘（Questionable／Doubtful／Day-To-Day）只缺今天的比賽
CAP, MAX_SHORT = 36.0, 40.0                               # R-153：單人上限 36；可上場人數太少、全員到 36 仍不足 240 時放寬到 40
# R-153／R-156 焦灼比賽槽乘數 m_k＝該槽在焦灼場（最終分差 ≤5 或延長賽）的平均分鐘 ÷ 在全部場的平均分鐘；槽＝球員在該隊該季依場均分鐘的名次 1…10，11＝第 11 名以後。
# R-156：球員在隊期間（替這隊第一場到最後一場出賽之間、這隊的所有比賽）沒上場的場次記 0 分鐘，焦灼場與全部場同規則，場均與排名也含 0（歷史沒有傷兵資料，傷缺場次也記 0，屬近似）。
# 來源：2024-25（1230 場）＋2025-26（1230 場）例行賽 box score 合併，reports/E208-team-rating/r153_close_multipliers.py 產出
# r153-close-game-multipliers.json（延長賽分鐘先換算成 48 分鐘等比；舊 R-153 值留在 mR153 欄）。資料直接量，不擬合不挑參數。
CLOSE_MULT = (1.0572, 1.0464, 1.0428, 1.0344, 1.0505, 1.0181, 1.0338, 1.0195, 1.0175, 0.987, 0.9027)
ESPN_ABBR = {'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'WSH': 'WAS', 'UTAH': 'UTA', 'PHO': 'PHX', 'BRK': 'BKN', 'CHO': 'CHA'}
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 底卡（E-216）：引擎（2025-26 卡）和 live 排名都沒有的非新秀（上季整季缺陣的人，例如 Kyrie、Lillard、Haliburton、VanVleet）。
# 選擇規則（寫死、不看結果挑）：依賽季由近到遠，取「有這個人的最近一張」賽季卡；目前最近的是 2024-25 卡（v5 -min 主答案卡，§R.7），
# 其次 2023-24 卡。都沒有的人（沒有任何歷史卡的新人）維持聯盟平均 profile 並列進 missingProfiles。不做年齡衰退調整。
BASE_CARDS = [('24-25 卡', 'reports/ovr-inseason-2026-27/v5/cards/2024-25-v5-min.csv'),
              ('23-24 卡', 'reports/ovr-inseason-2026-27/v5/cards/2023-24-v5-min.csv')]
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina']

log = logging.getLogger('daily_inseason.team_ratings')


# ----------------------------------------------------------------- 純函式（有測試）
def nn(s: str) -> str:
    """球員姓名正規化：去重音、去 Jr./Sr./II/III/IV、只留小寫字母。"""
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', ' ', s)
    return re.sub(r'[^a-z]', '', s)


def Phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def is_out(status: str) -> bool:
    return (status or '').strip().lower() in OUT_STATUS


def is_long_out(status: str) -> bool:
    return (status or '').strip().lower() in LONG_OUT


def norm_table(items: list, total: float = 240.0) -> list:
    """items＝[[pid, 教練近況分鐘], …]（已拿掉不能上場的人）→ 依分鐘由多到少（同分維持呼叫端排好的順序，穩定排序）→ 第 k 名 × CLOSE_MULT[k]（11 名以後共用最後一格）
    → 等比放大到 total；超過 CAP（36）的人固定在 CAP，多出的分鐘依比例分給未達上限者，反覆到收斂。不設下限。
    全員到 CAP 仍不足 total（<7 人）就把上限放寬到 MAX_SHORT（40）；仍不足（<6 人）就 total/n 平均攤。"""
    items = [[p, m] for p, m in items if m > 0]
    items.sort(key=lambda t: -t[1])
    n = len(items)
    if n == 0:
        return []
    w = [m * CLOSE_MULT[min(i, len(CLOSE_MULT) - 1)] for i, (_, m) in enumerate(items)]
    for cap in (CAP, MAX_SHORT):
        if cap * n >= total - 1e-9:
            break
    else:
        return [[p, round(total / n, 6)] for p, _ in items]
    capped: set = set()
    while True:
        free = [i for i in range(n) if i not in capped]
        scale = (total - cap * len(capped)) / sum(w[i] for i in free)
        over = [i for i in free if w[i] * scale > cap + 1e-12]
        if not over:
            break
        capped.update(over)
        if len(capped) == n:
            break
    return [[items[i][0], round(cap if i in capped else w[i] * scale, 6)] for i in range(n)]


def league_rtg(path: Path, default: float = 114.0) -> float:
    """本季至今聯盟平均每百回合得分（官方 OFFRTG 的基準）；sim 的 ortg／drtg 已去中心，顯示時加回這個。讀不到回預設值。"""
    try:
        rs = json.loads(path.read_text(encoding='utf-8'))['data']['resultSets'][0]
        h = rs['headers']; ix = {k: h.index(k) for k in ('PTS', 'FGA', 'FTA', 'OREB', 'TOV')}
        pts = pos = 0.0
        for r in rs['rowSet']:
            pts += r[ix['PTS']]; pos += r[ix['FGA']] + 0.44 * r[ix['FTA']] - r[ix['OREB']] + r[ix['TOV']]
        return round(pts / pos * 100, 1) if pos > 500 else default
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return default


def own_avg(log) -> float | None:
    """球員自己的分鐘紀錄（時間順序）→ 最近 ≤LAST_N 場「有出場（>0）」的平均；沒出場過回 None。"""
    played = [m for m in log if m > 0][-LAST_N:]
    return sum(played) / len(played) if played else None


def candidate_minutes(prior: list, logs=None, roster=None) -> tuple:
    """prior＝該隊此前最多 10 場的 [[pid, min], …] 列表；logs＝{pid: 本季每場出場分鐘（時間順序、跨隊）}（None 時只用 prior）；
    roster＝目前在該隊名單的 pid（None＝不補人）。回傳 ({pid: 自己最近 ≤10 場有出場的平均分鐘}, 因 RETURN_MIN 門檻補回的 pid 集合)。"""
    seen = {p for r in prior for p, m in r if m > 0}
    def log_of(p):
        return logs.get(p, []) if logs is not None else [m for r in prior for q, m in r if q == p]
    out = {}
    for p in seen:
        a = own_avg(log_of(p))
        if a is not None:
            out[p] = a
    restored = set()
    for p in roster or ():
        if p not in seen:
            a = own_avg(log_of(p))
            if a is not None and a >= RETURN_MIN:
                out[p] = a; restored.add(p)
    return out, restored


def rotation(prior: list, fallback: list, excluded=frozenset(), logs=None, roster=None, ovr=None) -> list:
    """候選人（見 candidate_minutes）自己最近 ≤10 場有出場的平均分鐘（拿掉 excluded）→ 名次照該分鐘（同分照 OVR、再照 pid）→ × 槽乘數、等比到 240、上限 36（見 norm_table）。
    prior 為空時用 fallback（[[pid, mpg], …]，季前預期）。ovr＝{pid: OVR}，只用來排同分。
    不足 8 人（大量缺陣）時用 fallback 依序補人，補到 8 人。"""
    base = candidate_minutes(prior, logs, roster)[0] if prior else {p: m for p, m in fallback}
    items = [[p, m] for p, m in base.items() if p not in excluded]
    if len(items) < 8:
        have = {p for p, _ in items}
        for p, m in sorted(fallback, key=lambda t: -t[1]):
            if len(items) >= 8:
                break
            if p not in have and p not in excluded:
                items.append([p, max(m, 1.0)]); have.add(p)
    ovr = ovr or {}
    return norm_table(sorted(items, key=lambda t: (-t[1], -ovr.get(t[0], 0.0), t[0])))


def margin_win_prob(d: float, home: bool) -> float:
    return Phi((d + (H if home else -H)) / SIGMA)


def lineup_out(outs: list, gdate: str, today: str) -> frozenset:
    """outs＝[(pid, returnDate|None), …]（今天列 Out／Doubtful／Suspension 的人）→ gdate 那場缺陣的 pid。
    該場日期 < returnDate 缺陣；沒有 returnDate 整季缺陣；日期 ≤ 今天（含 ESPN 回歸日已過期但仍列 Out）一律缺陣。"""
    return frozenset(p for p, rd in outs if rd is None or gdate < rd or gdate <= today)


def predict_wins(wins: int, played: int, remaining: list, margin, tid: str, tids=None) -> tuple:
    """remaining＝[(homeId, awayId[, 日期]), …] 本隊的剩餘賽程；回傳 (預測最終勝場, 逐場加總的場數, 以平均勝率補的場數)。
    margin＝{tid: 對梯度對手每場分差}（陣容全程不變），或 f(tid, 日期|None)→分差（逐場陣容；日期 None＝最後狀態，用在補的場次）；後者要給 tids。
    賽程沒涵蓋到 82 場的部分（賽程抓不到、或盃賽淘汰賽未定）用對其他 29 隊的平均勝率補。"""
    mg = margin if callable(margin) else (lambda t, d: margin[t])
    tids = list(margin) if tids is None else tids
    exp = 0.0
    for g in remaining:
        h, a = g[0], g[1]; d = g[2] if len(g) > 2 else None
        if str(h) == tid:
            exp += margin_win_prob(mg(tid, d) - mg(str(a), d), True)
        else:
            exp += 1 - margin_win_prob(mg(str(h), d) - mg(tid, d), True)
    others = [o for o in tids if o != tid]
    pool = sum(0.5 * (margin_win_prob(mg(tid, None) - mg(o, None), True) + margin_win_prob(mg(tid, None) - mg(o, None), False)) for o in others) / len(others)
    rest = max(0, GAMES - played - len(remaining))
    return wins + exp + rest * pool, len(remaining), rest


def parse_espn(d: dict) -> list:
    """ESPN injuries JSON → 精簡清單（隊用 ESPN 縮寫轉成 NBA tricode）。"""
    out = []
    for t in d.get('injuries', []):
        for i in t.get('injuries', []):
            a = i.get('athlete') or {}
            ab = ((a.get('team') or {}).get('abbreviation')) or ''
            raw, comment = i.get('status') or '', (i.get('shortComment') or '')[:240]
            # ESPN 的 status 只有 Out／Day-To-Day／Suspension；官方的 Doubtful 只出現在簡評（"is listed as doubtful for Monday's game"）。
            # Day-To-Day 且簡評寫 doubtful 時升成 Doubtful（今日陣容會拿掉）；其餘 Day-To-Day（questionable／probable）保留。
            eff = 'Doubtful' if raw.lower() == 'day-to-day' and re.search(r'doubtful', comment, re.I) else raw
            out.append({'name': a.get('displayName') or '', 'team': ESPN_ABBR.get(ab, ab), 'teamName': t.get('displayName'),
                        'status': eff, 'espnStatus': raw, 'date': i.get('date'),
                        'comment': comment, 'returnDate': (i.get('details') or {}).get('returnDate')})
    return out


def attach_ids(items: list, index: dict) -> tuple:
    """index＝{nn(姓名): [(pid, tricode), …]}。先姓名（同名多人時用球隊挑）；對不上的放進 unmatched，不猜。"""
    matched, unmatched = [], []
    for it in items:
        c = index.get(nn(it['name']), [])
        if len(c) > 1:
            c = [x for x in c if x[1] == it['team']] or []
        if len(c) == 1:
            matched.append({**it, 'playerId': c[0][0]})
        else:
            matched.append({**it, 'playerId': None}); unmatched.append(it['name'])
    return matched, unmatched


def et_from_utc(u: dt.datetime) -> dt.datetime:
    """UTC（aware）→ 美東時間（aware，固定偏移）。Windows 沒有 tzdata，自己算美國夏令：3 月第二個週日 02:00 起、11 月第一個週日 02:00 止。"""
    def nth_sunday(y, m, n):
        d = dt.date(y, m, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    y = u.year
    start = dt.datetime.combine(nth_sunday(y, 3, 2), dt.time(7), dt.timezone.utc)      # 02:00 EST ＝ 07:00 UTC
    end = dt.datetime.combine(nth_sunday(y, 11, 1), dt.time(6), dt.timezone.utc)       # 02:00 EDT ＝ 06:00 UTC
    off = dt.timedelta(hours=-4 if start <= u < end else -5)
    return u.astimezone(dt.timezone(off))


def pdf_urls(now_et: dt.datetime, hours: int = PDF_LOOKBACK_H) -> list:
    """從 now_et 往回、每 15 分鐘一個時段，最多 hours 小時。回傳 [(url, 該時段的 aware 時間), …]（新→舊）。"""
    t = now_et.replace(minute=now_et.minute // 15 * 15, second=0, microsecond=0)
    out = []
    for k in range(hours * 4 + 1):
        s = t - dt.timedelta(minutes=15 * k)
        out.append((PDF_URL.format(d=s.strftime('%Y-%m-%d'), t=s.strftime('%I_%M%p')), s))
    return out


def pdf_name_to_first_last(s: str) -> str:
    """官方 'Last, First'（含 'Udeh, Jr., Ernest'、'Murphy III, Trey'）→ 'First Last'（'Ernest Udeh Jr.'）。"""
    parts = [x.strip() for x in s.split(',') if x.strip()]
    if len(parts) < 2:
        return s.strip()
    return f"{parts[-1]} {' '.join(parts[:-1])}"


_PDF_SKIP = re.compile(r'^(Injury Report:|Page \d+ of \d+|Game Date\b)')
_PDF_PLAYER = re.compile(r'^(?P<name>[^,/]+(?:, [^,/]+)+?)\s+(?P<status>' + '|'.join(PDF_STATUS) + r')\b\s*(?P<reason>.*)$')
_PDF_PREFIX = ((r'\d\d/\d\d/\d{4}', 'd'), (r'\d\d:\d\d \(ET\)', 't'), (r'[A-Z]{2,4}@[A-Z]{2,4}', 'm'))


def parse_injury_text(text: str) -> dict:
    """官方傷病報告 pdftotext -raw 輸出 → {'reportTime': 'MM/DD/YY HH:MM AM'|None, 'items': […], 'notSubmitted': [tricode…]}。
    -raw 依內容串流順序輸出：隊名在該隊第一列（接在日期／時間／對戰之後）；後面的列隊名欄是空的，沿用上一個隊名，跨頁也一樣。
    原因會折行（沒有球員名＋狀態的列）→ 接到上一位球員的原因。items 格式同 parse_espn：name（First Last）, team, teamName, status, comment…"""
    items, not_sub, report_time = [], [], None
    team = team_name = game_date = game_time = matchup = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = re.match(r'Injury Report:\s*(.+)$', line)
        if m:
            report_time = report_time or m.group(1).strip()
        if _PDF_SKIP.match(line):
            continue
        for pat, key in _PDF_PREFIX:
            m = re.match(r'(' + pat + r')(\s+|$)', line)
            if m:
                v = m.group(1)
                if key == 'd': game_date = v
                elif key == 't': game_time = v
                else: matchup = v
                line = line[m.end():].strip()
        for nm in sorted(NBA_TEAMS, key=len, reverse=True):
            if line.startswith(nm) and (len(line) == len(nm) or line[len(nm)] == ' '):
                team, team_name = NBA_TEAMS[nm], nm
                line = line[len(nm):].strip()
                break
        if not line:
            continue
        if line.upper() == 'NOT YET SUBMITTED':
            if team and team not in not_sub:
                not_sub.append(team)
            continue
        m = _PDF_PLAYER.match(line)
        if m and team:
            items.append({'name': pdf_name_to_first_last(m.group('name')), 'team': team, 'teamName': team_name, 'status': m.group('status'),
                          'date': game_date, 'gameTime': game_time, 'matchup': matchup, 'comment': m.group('reason').strip()})
        elif items:
            items[-1]['comment'] = (items[-1]['comment'] + ' ' + line).strip()
    for it in items:
        it['comment'] = it['comment'][:240]
    return {'reportTime': report_time, 'items': items, 'notSubmitted': not_sub}


# ----------------------------------------------------------------- 資料
def mins(s: str) -> float:
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', s or '')
    return int(m[1]) + float(m[2]) / 60 if m else 0.0


def load_boxes() -> tuple:
    """回傳 (hist, plog, {tid: tricode}, {pid: 名字})。hist＝每隊按時間排序的每場 [[pid, 分鐘]]（只含有出場的人；每場全隊分鐘縮放成 240，抵掉延長賽）；
    plog＝{pid: 本季每場出場分鐘（時間順序、跨隊、同樣縮放）}。"""
    games, tri, names = [], {}, {}
    for f in sorted(glob.glob(str(BOXES / '*.json'))):
        g = json.load(open(f, encoding='utf-8'))['data']['game']
        if g.get('gameStatus') != 3:
            continue
        r = {}
        for k in ('homeTeam', 'awayTeam'):
            t = g[k]
            tid = str(t['teamId']); tri[tid] = t.get('teamTricode') or tri.get(tid, '')
            for p in t['players']:
                names[p['personId']] = p.get('name') or ' '.join(filter(None, [p.get('firstName'), p.get('familyName')]))
            lst = [[p['personId'], mins(p['statistics']['minutes'])] for p in t['players']]
            lst = [[p, m] for p, m in lst if m > 0]
            tot = sum(m for _, m in lst)
            r[tid] = [[p, m * 240.0 / tot] for p, m in lst] if tot > 0 else []
        games.append((g['gameTimeUTC'], g['gameId'], r))
    games.sort(key=lambda t: (t[0], t[1]))
    hist: dict = collections.defaultdict(list)
    plog: dict = collections.defaultdict(list)
    for _, _, r in games:
        for tid, lst in r.items():
            hist[tid].append(lst)
            for p, m in lst:
                plog[p].append(m)
    return hist, plog, tri, names


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_pdf(url: str, timeout: int = 20):
    """GET 官方報告 PDF。404（該時段沒出報告）回 None；其他錯誤照丟。"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise


def fetch_latest_pdf(now_et: dt.datetime, fetch=None) -> tuple:
    """往回找最近一份存在的報告 → (url, 時段時間, bytes)。連續 3 次非 404 的錯誤（網路不通）就放棄，不把 144 個時段都試完。"""
    fetch = fetch or fetch_pdf
    errs = 0
    for url, slot in pdf_urls(now_et):
        try:
            data = fetch(url)
        except Exception as e:  # noqa: BLE001
            errs += 1
            log.debug('PDF %s：%s', url, e)
            if errs >= 3:
                raise RuntimeError(f'官方 PDF 連續 {errs} 次連線失敗（{e}）') from e
            continue
        errs = 0
        if data and data[:4] == b'%PDF':
            return url, slot, data
    raise RuntimeError(f'往回 {PDF_LOOKBACK_H} 小時找不到官方傷病報告 PDF')


def pdftotext_exe() -> str:
    for c in (shutil.which('pdftotext'), PDFTOTEXT_FALLBACK):
        if c and Path(c).exists():
            return c
    raise RuntimeError('找不到 pdftotext')


def pdf_to_text(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 'r.pdf'
        src.write_bytes(data)
        r = subprocess.run([pdftotext_exe(), '-raw', '-enc', 'UTF-8', str(src), '-'], capture_output=True, timeout=60,
                           creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            raise RuntimeError(f'pdftotext exit={r.returncode}：{r.stderr.decode("utf-8", "replace").strip()[-200:]}')
        return r.stdout.decode('utf-8', 'replace')


def load_injuries(index: dict, fetch: bool = True, source: str = 'auto') -> dict:
    """傷病名單並存 injuries.json。順序：ESPN → 官方傷病報告 PDF → 沿用前一份（標 stale）。
    ESPN 成功時不抓 PDF。source＝'pdf' 強制只走 PDF（驗證用）、'espn' 只走 ESPN。"""
    prev = {}
    try:
        prev = json.loads(INJURIES.read_text(encoding='utf-8'))
    except Exception:
        pass
    now = dt.datetime.now().astimezone().isoformat(timespec='seconds')

    def save(doc):
        INJURIES.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
        INJURIES.write_text(text, encoding='utf-8')
        try:        # R-151：每次抓完傷病另存快照（只存不讀）
            snap = INJURIES.parent / 'injury-snapshots'
            snap.mkdir(parents=True, exist_ok=True)
            (snap / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')).write_text(text, encoding='utf-8')
        except OSError as e:
            log.warning('傷病快照寫入失敗（不影響評分）：%s', e)
        if doc['unmatched']:
            log.info('傷病名單 %d 人對不上球員（多半本季還沒上場）：%s', len(doc['unmatched']), '、'.join(doc['unmatched'][:30]))
        return doc

    if fetch and source in ('auto', 'espn'):
        try:
            raw = fetch_json(ESPN_URL)
            items = parse_espn(raw)
            if not items:
                raise RuntimeError('ESPN 傷病名單是空的')
            matched, unmatched = attach_ids(items, index)
            return save({'fetchedAt': now, 'source': 'espn', 'espnTimestamp': raw.get('timestamp'), 'stale': False, 'items': matched, 'unmatched': unmatched})
        except Exception as e:  # noqa: BLE001
            log.warning('ESPN 傷病抓取失敗（%s）%s', e, '；改用官方傷病報告 PDF' if source == 'auto' else '')
    if fetch and source in ('auto', 'pdf'):
        try:
            url, slot, data = fetch_latest_pdf(et_from_utc(dt.datetime.now(dt.timezone.utc)))
            parsed = parse_injury_text(pdf_to_text(data))
            if not parsed['items']:
                raise RuntimeError('官方 PDF 解析不出任何球員')
            matched, unmatched = attach_ids(parsed['items'], index)
            if parsed['notSubmitted']:
                log.info('官方報告尚未提交的球隊：%s', '、'.join(parsed['notSubmitted']))
            return save({'fetchedAt': now, 'source': 'nba-official-pdf', 'espnTimestamp': None, 'stale': False, 'pdfUrl': url,
                         'reportTime': slot.isoformat(timespec='seconds'), 'reportHeader': parsed['reportTime'], 'notSubmitted': parsed['notSubmitted'],
                         'items': matched, 'unmatched': unmatched})
        except Exception as e:  # noqa: BLE001
            log.warning('官方傷病報告 PDF 失敗（%s）；沿用前一份', e)
    if prev.get('items') is not None:
        prev['stale'] = True
        return prev
    log.warning('沒有任何傷病資料；兩個版本名單相同')
    return {'fetchedAt': None, 'source': None, 'espnTimestamp': None, 'stale': True, 'items': [], 'unmatched': []}


def load_schedule(fetch: bool = True) -> dict:
    """node scripts/fetch_schedule.mjs（失敗不覆寫舊檔），再讀 schedule.json。回傳 {} 表示沒有賽程。"""
    if fetch:
        try:
            r = subprocess.run([node_exe(), 'scripts/fetch_schedule.mjs', SEASON], cwd=str(ROOT), capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=180, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
            if r.returncode != 0:
                log.warning('fetch_schedule exit=%s：%s；沿用舊賽程檔', r.returncode, (r.stderr or r.stdout).strip()[-200:])
        except Exception as e:  # noqa: BLE001
            log.warning('fetch_schedule 失敗（%s）；沿用舊賽程檔', e)
    try:
        return json.loads(SCHEDULE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def node_exe() -> str:
    for c in (shutil.which('node'), r'C:\Program Files\nodejs\node.exe'):
        if c and Path(c).exists():
            return c
    raise RuntimeError('找不到 node')


def load_base_cards(cards=None) -> list:
    """[(標籤, {pid: 列}, {attr: 該卡分鐘加權聯盟平均})]，由近到遠。檔案不存在就略過（不擋評分）。"""
    out = []
    for label, rel in (cards if cards is not None else BASE_CARDS):
        f = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not f.exists():
            log.warning('底卡 %s 不存在，略過：%s', label, f)
            continue
        rows = read_csv(f)
        W = sum(float(r['MIN_season']) for r in rows)
        out.append((label, {int(r['playerId']): r for r in rows}, {a: sum(float(r[a]) * float(r['MIN_season']) for r in rows) / W for a in ATTRS}))
    return out


def base_profiles(pids, base_cards: list) -> dict:
    """pid → {src, ovr, pos, heightInches, off{attr}}：每人取最近一張有他的底卡；off＝該卡能力值 − 該卡自己的聯盟平均
    （相對自己那季的聯盟，不受卡片版本差影響），引擎端加在聯盟平均 profile 上。沒有任何底卡的人不在回傳裡。"""
    res = {}
    for pid in pids:
        for label, rows, mean in base_cards:
            r = rows.get(pid)
            if r is not None:
                res[pid] = {'src': label, 'ovr': float(r['ovr']), 'pos': r['pos'], 'heightInches': float(r['heightInches']),
                            'off': {a: float(r[a]) - mean[a] for a in ATTRS}}
                break
    return res


def engine_inputs(rows: list, card_rows: list, base: dict | None = None) -> dict:
    """引擎端的屬性差：live − 卡片（同 E-208 prep_forward）；卡片裡沒有或引擎沒有的人（新秀）用 live − 卡片聯盟分鐘加權平均。
    base（E-216）：沒有引擎 profile、也沒有 live 列的非新秀，改用底卡（見 BASE_CARDS）；有 live 列的人 底卡 + (live − 底卡) 等於
    原本的 live − 卡片聯盟平均，行為不變。"""
    xids = {int(k) for k in json.load(open(E208 / 'players-attrs.json', encoding='utf-8'))['players']}
    cardN = {nn(r['name']): r for r in card_rows}
    W = sum(float(r['MIN']) for r in card_rows)
    cmean = {a: sum(float(r[a]) * float(r['MIN']) for r in card_rows) / W for a in ATTRS}
    deltas, new = {}, []
    for r in rows:
        pid = int(r['playerId']); c = cardN.get(nn(r['name']))
        if pid in xids and c is not None:
            deltas[pid] = {a: float(r[a]) - float(c[a]) for a in ATTRS}
        else:
            new.append(pid); deltas[pid] = {a: float(r[a]) - cmean[a] for a in ATTRS}
    return {'attrs': ATTRS, 'deltas': {str(k): v for k, v in deltas.items()}, 'newPlayers': new,
            'base': {str(k): v for k, v in (base or {}).items() if k not in deltas and k not in xids}}


def run_sim(inp: dict, seeds: int, workers: int) -> dict:
    """平行起 node 子程序（無視窗）；每個子程序負責 jobs[i % N == shard]。回傳 {(team, ver): 累計量}。"""
    tmp = Path(tempfile.mkdtemp(prefix='team-ratings-', dir=ROOT / 'data'))
    try:
        (tmp / 'in.json').write_text(json.dumps(inp), encoding='utf-8')
        procs = [subprocess.Popen([node_exe(), str(SIM), str(tmp / 'in.json'), str(s), str(workers), str(tmp / f'out-{s}.json'), str(seeds)],
                                  cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                  creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL) for s in range(workers)]
        for p in procs:
            out, err = p.communicate(timeout=1500)
            if p.returncode != 0:
                raise RuntimeError(f'team_ratings_sim exit={p.returncode}：{(err or out).strip()[-400:]}')
        res, missing, based, excluded = {}, set(), set(), set()
        for s in range(workers):
            d = json.load(open(tmp / f'out-{s}.json', encoding='utf-8'))
            missing |= set(d['missing']); based |= set(d.get('based', [])); excluded |= set(d.get('excluded', []))
            for o in d['res']:
                res[(str(o['team']), o['ver'])] = o
        return {'res': res, 'missing': sorted(missing), 'based': sorted(based), 'excluded': sorted(excluded)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


T_DRAWS_PER_OPP = 70      # T 評分：每支對手抽的陣容數（29 隊 × 70 ≈ 2000，同 E-229b 每場 N=2000）
E229 = ROOT / 'reports/E229-transformer-vs-m0-forward'


def run_t(jobs: list, tids: list, today: str, live_dir: Path, threads: int = 4) -> dict:
    """Transformer 球隊評分（R-160，2026-11-04 起）：E-227 R2-stats 五個 seed，特徵＝e229_live 每日混合表（同 E-229b 回測）。
    每份名單依分鐘抽 5 人陣容，對其他 29 隊「近況」名單各抽 T_DRAWS_PER_OPP 個陣容（＝對聯盟平均對手），
    ORtg／DRtg＝雙方每 100 回合得分（A／B 兩個方向平均），margin＝淨值 × 聯盟每場回合數/100。回傳格式同 run_sim。"""
    import numpy as np
    import torch
    sys.path.insert(0, str(E229))
    import e229_live
    from e227_model import predict
    torch.set_num_threads(threads)
    names = {p: 1 for j in jobs for p, _ in j['roster']}
    C, info = e229_live.make_ctx(today, str(live_dir), names)
    prep = {(j['team'], j['ver']): C.prep(j['roster']) for j in jobs}
    pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    res = {}
    for j in jobs:
        tid = j['team']
        rng = np.random.default_rng([229, int(tid), sum(map(ord, j['ver']))])
        opp = np.concatenate([C.draw(*prep[(o, 'c')], rng, T_DRAWS_PER_OPP) for o in tids if o != tid])
        own = C.draw(*prep[(tid, j['ver'])], rng, len(opp))
        n = len(own)
        X = torch.from_numpy(np.concatenate([np.concatenate([own, opp], 1), np.concatenate([opp, own], 1)], 0))
        T = [X, pos.expand(2 * n, -1), side.expand(2 * n, -1)]
        pf = pa = 0.0
        for m in C.nets:
            o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy()
            pf += 100.0 * 0.5 * (o[:n, 0].mean() + o[n:, 1].mean()) / len(C.nets)
            pa += 100.0 * 0.5 * (o[:n, 1].mean() + o[n:, 0].mean()) / len(C.nets)
        res[(tid, j['ver'])] = {'msum': float(pf - pa) * C.avg_poss / 100, 'n': 1, 'pf': float(pf), 'pof': 100.0, 'pa': float(pa), 'poa': 100.0}
    missing = sorted({p for j in jobs for p, _ in j['roster'] if str(p) not in C.B})
    return {'res': res, 'missing': missing, 'based': [], 'excluded': [], 'info': info, 'avgPoss': C.avg_poss}


# ----------------------------------------------------------------- 主流程
def read_csv(p: Path) -> list:
    return list(csv.DictReader(open(p, encoding='utf-8')))


def compute(live_dir: Path, seeds: int = SEEDS, workers: int = 8, fetch: bool = True, injury_source: str = 'auto', today: str | None = None,
            engine: str = 't', out: Path | None = None) -> dict:
    t0 = time.time()
    today = today or et_from_utc(dt.datetime.now(dt.timezone.utc)).date().isoformat()      # 美東日期（賽程的 gameDateEst 也是美東）
    meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
    rows = read_csv(live_dir / 'ranking.csv')
    card_name = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-')
    card_csv = ROOT / f'reports/{card_name}/ranking.csv'
    if not card_csv.exists():
        card_csv = ROOT / 'reports/card-0.2.12b/ranking.csv'
    card_rows = read_csv(card_csv)

    hist, plog, tri, box_names = load_boxes()
    teams = json.loads((E208 / 'inputs.json').read_text(encoding='utf-8'))['teams']      # tid → {name, abbr, …}
    tids = sorted(teams)
    assert len(tids) == 30, len(tids)
    tri2tid = {v: k for k, v in tri.items()}
    live_team = {int(r['playerId']): tri2tid.get(r['team']) for r in rows}                 # 現在的球隊（交易後以 live 為準）
    ovr = {int(r['playerId']): float(r['ovr']) for r in rows}
    pname = {**box_names, **{int(r['playerId']): r['name'] for r in rows}}
    index: dict = collections.defaultdict(list)
    for pid, nm in pname.items():
        index[nn(nm)].append((pid, tri.get(live_team.get(pid) or '', '')))
    inj = load_injuries(index, fetch, injury_source)
    out_pids = collections.defaultdict(set); out_ret = collections.defaultdict(dict); all_inj = collections.defaultdict(list)
    for it in inj['items']:
        tid = tri2tid.get(it['team'])
        pid = it.get('playerId')
        if pid is not None and live_team.get(pid):
            tid = live_team[pid]            # 球員現在的隊（ESPN 與 live 不同步時以 live 為準）
        if tid is None:
            continue
        all_inj[tid].append(it)
        if pid is not None and is_out(it['status']):
            out_pids[tid].add(pid)
            if it.get('returnDate'):
                out_ret[tid][pid] = str(it['returnDate'])[:10]
            else:       # 沒有 returnDate（PDF 備援）：Out／Suspension＝整季缺陣；Questionable／Doubtful／Day-To-Day 只缺今天的比賽
                out_ret[tid][pid] = None if is_long_out(it['status']) else (dt.date.fromisoformat(today) + dt.timedelta(days=1)).isoformat()

    pre = collections.defaultdict(list)     # 季前預期（MPGhat）：沒有任何 box 時的後備
    for r in rows:
        tid = live_team.get(int(r['playerId']))
        if tid:
            pre[tid].append([int(r['playerId']), float(r['MPGhat'])])
    members = collections.defaultdict(set)      # 目前在該隊名單的人
    for pid, tid in live_team.items():
        if tid:
            members[tid].add(pid)
    lg = json.loads(LEAGUE.read_text(encoding='utf-8'))['schedule']
    played_ids = {g['id'] for g in lg}
    wl = collections.defaultdict(lambda: [0, 0])
    for g in lg:
        o = g['observed']; h = o['homeScore'] > o['awayScore']
        wl[str(g['homeId'])][0 if h else 1] += 1; wl[str(g['awayId'])][1 if h else 0] += 1
    sch = load_schedule(fetch)
    remaining = [(h, a, d) for gid, d, h, a in sch.get('games', []) if gid not in played_ids]
    rem_by = collections.defaultdict(list)
    for g in remaining:
        rem_by[str(g[0])].append(g); rem_by[str(g[1])].append(g)

    rosters, restored = {}, {}
    state_ver, final_ver, outs_of = {}, {}, {}      # 每隊：缺陣集合 → 陣容版本名；全部回歸後的版本名；[(pid, returnDate)]
    jobs = []
    rkey = lambda r: tuple((p, round(m, 6)) for p, m in r)
    for tid in tids:
        prior = hist[tid][-LAST_N:]
        moved = {p for r in prior for p, _ in r if live_team.get(p) not in (None, tid)}   # 此後被交易走的人不算進輪替
        rot = lambda excl: rotation(prior, pre[tid], excluded=moved | set(excl), logs=plog, roster=members[tid], ovr=ovr)
        restored[tid] = candidate_minutes(prior, plog, members[tid])[1] if prior else set()
        recent, today_r = rot(()), rot(out_pids[tid])
        rosters[tid] = {'c': recent, 'today': today_r}
        by_roster = {rkey(recent): 'c'}
        by_roster.setdefault(rkey(today_r), 'today')
        jobs.append({'team': tid, 'ver': 'c', 'roster': recent})
        if by_roster[rkey(today_r)] == 'today':
            jobs.append({'team': tid, 'ver': 'today', 'roster': today_r})
        outs = outs_of[tid] = list(out_ret[tid].items())
        far = '9999-12-31'
        # 今日陣容的缺陣集合也要有版本：傷兵 returnDate 都早於下一場時，剩餘賽程的狀態裡不會出現它（2026-11-03 KeyError）
        states = {lineup_out(outs, d, today) for _, _, d in rem_by[tid]} | {lineup_out(outs, far, today), frozenset(out_pids[tid])}
        state_ver[tid] = {}
        for stt in sorted(states, key=sorted):
            if stt == frozenset():
                v = 'c'
            elif stt == frozenset(out_pids[tid]):
                v = by_roster[rkey(today_r)]
            else:
                r = rot(stt); k = rkey(r)
                if k not in by_roster:
                    by_roster[k] = f's{len(by_roster)}'; jobs.append({'team': tid, 'ver': by_roster[k], 'roster': r})
                v = by_roster[k]
            state_ver[tid][stt] = v
        final_ver[tid] = state_ver[tid][lineup_out(outs, far, today)]
    live_pids = {int(r['playerId']) for r in rows}
    need = {p for j in jobs for p, _ in j['roster']} - live_pids
    if seeds % 10:
        raise ValueError(f'seeds 必須是 10 的倍數（五支梯度對手各 seeds/5 場、再平分主客），收到 {seeds}')
    if not LADDER.exists():
        raise FileNotFoundError(f'缺梯度對手表 {LADDER}；先跑 python -I -X utf8 scripts/build_gradient_ladder.py')
    ladder = json.loads(LADDER.read_text(encoding='utf-8'))
    inp = {**engine_inputs(rows, card_rows, base_profiles(need, load_base_cards())), 'jobs': jobs, 'teamIds': tids, 'ladder': ladder}
    base_used = {int(k): v for k, v in inp['base'].items()}
    ovr_src = {p: v['src'] for p, v in base_used.items()}
    ovr.update({p: v['ovr'] for p, v in base_used.items()})       # 底卡 OVR 只補 live 沒有的人（頁面上標來源）
    workers = max(1, min(workers, len(jobs)))
    used = engine
    if engine == 't':
        try:
            sim = run_t(jobs, tids, today, live_dir)
            in_jobs = {p for j in jobs for p, _ in j['roster']}
            sim['based'] = sorted(p for p in base_used if p in in_jobs)
            log.info('球隊評分（Transformer）：%d 份名單，%.0f 秒', len(jobs), time.time() - t0)
        except Exception as e:      # T 失敗退回舊模擬引擎，頁面照常發布
            log.warning('Transformer 球隊評分失敗，改用模擬引擎：%s', str(e)[-400:])
            used = 'm0'
    if used == 'm0':
        sim = run_sim(inp, seeds, workers)
        log.info('球隊評分模擬：%d 份名單 × %d 場，%d 個 worker，%.0f 秒', len(jobs), seeds, workers, time.time() - t0)

    def stat(tid, ver):
        o = sim['res'][(tid, ver)]
        return {'margin': o['msum'] / o['n'], 'ortg': 100 * o['pf'] / o['pof'], 'drtg': 100 * o['pa'] / o['poa']}
    st = {v: {t: stat(t, v if v == 'c' else state_ver[t][frozenset(out_pids[t])]) for t in tids} for v in ('c', 'today')}
    # R-171（E-253 K10）：加回本季實際表現殘差（實際 − T 賽前預期，÷(場數+10)）；ACTUAL_BLEND=0 回退
    resid = {}
    if used == 't' and actual_blend.enabled():
        try:
            resid = actual_blend.residuals(today, log=log, live_dir=live_dir)
        except Exception as e:      # 補算失敗不擋發布，照純 T
            log.warning('本季實際表現殘差失敗，排行不混實際：%s', str(e)[-400:])
    zero = {'offShr': 0.0, 'defShr': 0.0, 'netShr': 0.0, 'n': 0}
    for v in ('c', 'today'):
        for t in tids:
            r = resid.get(t, zero)
            st[v][t]['ortg'] += r['offShr']; st[v][t]['drtg'] += r['defShr']; st[v][t]['margin'] += r['netShr']
    mo = sum(st['c'][t]['ortg'] for t in tids) / 30; md = sum(st['c'][t]['drtg'] for t in tids) / 30    # 兩版共用「近況」版的聯盟平均
    mrg = {k: o['msum'] / o['n'] for k, o in sim['res'].items()}

    def margin_dated(t, d):
        """今日陣容版逐場陣容：t 隊在日期 d（None＝全部回歸後）的對梯度對手分差。"""
        return mrg[(t, final_ver[t] if d is None else state_ver[t][lineup_out(outs_of[t], d, today)])] + resid.get(t, zero)['netShr']
    n_noret = 0
    out_teams = {}
    for tid in tids:
        W, L = wl[tid]
        inj_rows = []
        for it in all_inj[tid]:
            row = {k: it.get(k) for k in ('name', 'status', 'date', 'comment', 'returnDate', 'playerId')}
            row['injury'] = injury_desc(it.get('comment'))
            pid = it.get('playerId')
            if pid is not None and pid in out_ret[tid]:
                row['missGames'] = sum(1 for g in rem_by[tid] if pid in lineup_out(outs_of[tid], g[2], today))     # 剩餘賽程裡缺陣的場數
                n_noret += out_ret[tid][pid] is None
            inj_rows.append(row)
        rec = {'name': teams[tid]['name'], 'abbr': tri.get(tid) or teams[tid]['abbr'], 'W': W, 'L': L, 'injured': inj_rows}
        for v in ('c', 'today'):
            s_ = st[v][tid]
            if v == 'c':
                pw, ng, nr = predict_wins(W, W + L, rem_by[tid], {t: st['c'][t]['margin'] for t in tids}, tid)
            else:
                pw, ng, nr = predict_wins(W, W + L, rem_by[tid], margin_dated, tid, tids)
            rec[v] = {'ortg': s_['ortg'] - mo, 'drtg': s_['drtg'] - md, 'net': (s_['ortg'] - mo) - (s_['drtg'] - md), 'margin': s_['margin'],
                      'predWins': pw, 'schedGames': ng, 'poolGames': nr,
                      'rotation': [{'pid': p, 'name': pname.get(p, str(p)), 'min': m, 'ovr': ovr.get(p), **({'ovrSrc': ovr_src[p]} if p in ovr_src else {})} for p, m in rosters[tid][v]]}
        # 舊算法（傷兵整季缺陣）的預測勝場，只供對照
        rec['today']['predWinsAllSeason'] = predict_wins(W, W + L, rem_by[tid], {t: st['today'][t]['margin'] for t in tids}, tid)[0]
        rec['today']['lineupStates'] = len({state_ver[tid][lineup_out(outs_of[tid], g[2], today)] for g in rem_by[tid]})
        c_min = dict(rosters[tid]['c'])
        rec['restored'] = [{'pid': p, 'name': pname.get(p, str(p)), 'min': c_min[p]} for p in sorted(restored[tid]) if p in c_min]
        rec['nOut'] = len(out_pids[tid])
        r = resid.get(tid)
        rec['actual'] = None if r is None else {'n': r['n'], 'k': actual_blend.K, 'off': r['off'], 'def': r['def_'], 'net': r['net'],
                                                'offShr': r['offShr'], 'defShr': r['defShr'], 'netShr': r['netShr'],
                                                'tOnlyNet': rec['today']['net'] - r['netShr']}
        out_teams[tid] = rec
    lg_rtg = league_rtg(ROOT / 'data/season-source-2026-27/team-games.json')
    doc = {'generatedAt': dt.datetime.now().astimezone().isoformat(timespec='seconds'), 'season': SEASON, 'version': meta.get('version'),
           'dataCutoff': meta.get('dataCutoff'), 'lgOrtg': lg_rtg, 'lgDrtg': lg_rtg, 'engine': 'Transformer E-227 R2-stats' if used == 't' else 'sim 0.1.4', 'engineKind': used,
           'opponent': ({'kind': 'league-pool', 'teams': 29, 'drawsPerTeam': T_DRAWS_PER_OPP, 'avgPoss': round(sim['avgPoss'], 2), 'features': sim['info']} if used == 't' else
                        {'kind': 'gradient-B5', 'teams': 5, 'gamesPerTeam': seeds // 5, 'ladderCard': ladder.get('card'), 'ladderGames': ladder.get('games'),
                         'ladder': [round(x, 2) for x in ladder['ladder']], 'mins': ladder['mins'], 'excluded': sim.get('excluded', [])}),
           'seeds': 29 * T_DRAWS_PER_OPP if used == 't' else seeds, 'H': H, 'sigma': SIGMA, 'lastN': LAST_N,
           'gamesPlayed': len(lg), 'injuries': {**{k: inj.get(k) for k in ('fetchedAt', 'source', 'espnTimestamp', 'reportTime', 'pdfUrl', 'stale', 'unmatched')}, 'outNoReturnDate': n_noret},
           'today': today, 'returnMin': RETURN_MIN,
           'actualBlend': {'on': bool(resid), 'k': actual_blend.K, 'rule': 'R-171 / E-253 K10；R-172 對今天的 T', 'games': sum(r['n'] for r in resid.values()) // 2},
           'schedule': {'fetchedAt': sch.get('fetchedAt'), 'source': sch.get('source'), 'remainingGames': len(remaining)},
           'missingProfiles': sim['missing'],
           'baseProfiles': [{'pid': p, 'name': pname.get(p, str(p)), 'team': next((tri.get(j['team']) or teams[j['team']]['abbr'] for j in jobs if p in {q for q, _ in j['roster']}), ''), 'src': v['src'], 'ovr': v['ovr']}
                            for p, v in sorted(base_used.items()) if p in set(sim['based'])], 'elapsedSec': round(time.time() - t0, 1), 'teams': out_teams}
    (out or RATINGS).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return doc


def default_live_dir() -> Path:
    cutoff = json.loads((LIVE / 'publish_state.json').read_text(encoding='utf-8'))['dataCutoff']
    return LIVE / cutoff


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('live_dir', nargs='?')
    ap.add_argument('--seeds', type=int, default=SEEDS)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-fetch', action='store_true')
    ap.add_argument('--injury-source', choices=('auto', 'espn', 'pdf'), default='auto', help='auto＝ESPN→官方 PDF→沿用前一份；pdf＝強制只走官方 PDF（驗證用）')
    ap.add_argument('--engine', choices=('t', 'm0'), default='t', help='t＝Transformer（R-160 起預設，失敗自動退回 m0）；m0＝舊模擬引擎 sim 0.1.4')
    ap.add_argument('--out', help='輸出檔（預設 data/season-source-2026-27/team-ratings.json）')
    a = ap.parse_args(argv)
    if not log.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    d = compute(Path(a.live_dir) if a.live_dir else default_live_dir(), a.seeds, a.workers, not a.no_fetch, a.injury_source,
                engine=a.engine, out=Path(a.out) if a.out else None)
    print(f"done {d['elapsedSec']}s, teams={len(d['teams'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
