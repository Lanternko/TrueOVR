"""抓取 2kratings.com 的 NBA 2K27 評分，對應到我們的卡片板球員。

流程
----
1. 從 robots.txt 公告的 post-sitemap 取全站球員頁 slug，建立「正規化名字 → slug」索引。
   sitemap1 之前被 403 擋過，這裡只再試一次；再擋就放棄它，不重試（寫 `.giveup` 標記）。
2. 用重音正規化 + Jr./III 後綴容錯 + 人工別名表，把卡片板的球員對應到 slug。
3. 索引對不上的，再用「由名字推導 slug」直接試一次球員頁。
4. 逐一抓球員頁，從 JSON-LD 的 additionalProperty 取各項屬性，位置從簡介段落取。

禮貌抓取：本地 HTML cache（可續跑，已快取/已確認 404 的頁面不會重抓）、
每次請求間 sleep 10 秒、帶一般瀏覽器 User-Agent。
遇 403/429/503：停 5 分鐘後對同一頁重試一次；仍被擋就放棄那一頁。
連續 3 個頁面重試後仍被擋，就整輪中止抓取（不是整個程式崩潰），用已抓到的資料繼續分析。
不換 IP、不偽造 cookie、不用無頭瀏覽器、不解 CAPTCHA，不做任何繞過 bot 偵測的事。

本輪抓取量很大，網站又會擋爬，因此這支腳本设计成「可重複呼叫、每次只抓一部分」：
用 --max-new 限制這次呼叫最多發出幾個新的（非快取）網路請求，讓外層可以分批在前景執行，
每批幾分鐘內跑完，跑完看進度再跑下一批，直到抓完或被擋停止。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = HERE / 'cache'
CARD_CSV = ROOT / 'reports/ovr-calibrated-2025-26/ranking.csv'
OUT_CSV = HERE / '2k27_ratings.csv'
UNMATCHED = HERE / 'unmatched.csv'

BASE = 'https://www.2kratings.com'
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
SLEEP = 10.0
BLOCK_WAIT = 300.0        # 被擋（403/429/503）後，停 5 分鐘再重試同一頁一次
MAX_CONSEC_BLOCKED = 3    # 連續 3 個頁面重試後仍被擋，本輪中止抓取

SITEMAPS = ['post-sitemap1.xml', 'post-sitemap2.xml', 'post-sitemap3.xml']
NO_RETRY_SITEMAPS = {'post-sitemap1.xml'}   # 上一輪已確認被擋，這輪只再試一次，不重試

# 歷史球隊 / 經典隊伍的條目 slug 會帶年份或 all-time 字樣，只保留現役球員的純名字 slug
HISTORIC_RE = re.compile(r'-(?:19|20)\d\d-\d\d-|-all-time-|-all-decade-|^wnba-|-fiba-')

SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

# 手動別名：卡片板名字 -> 2kratings 的 slug（正規化比對仍對不上的情況）
ALIASES: dict[str, str] = {
    'Egor Dëmin': 'egor-demin',
    'Nikola Topić': 'nikola-topic',
    'Vít Krejčí': 'vit-krejci',
    'Kristaps Porziņģis': 'kristaps-porzingis',
    'Yanic Konan Niederhäuser': 'yanic-konan-niederhauser',
    'Alperen Şengün': 'alperen-sengun',
    'Jakob Pöltl': 'jakob-poeltl',
    'Nicolas Claxton': 'nic-claxton',
    'Cameron Thomas': 'cam-thomas',
    'Cameron Johnson': 'cameron-johnson',
    'Kenyon Martin Jr.': 'kj-martin',
    'Ronald Holland II': 'ron-holland',
    'Ronald Holland': 'ron-holland',
    'Nah’Shon Hyland': 'bones-hyland',
    'Nahshon Hyland': 'bones-hyland',
    'Gregory Jackson II': 'gg-jackson',
    'Gregory Jackson': 'gg-jackson',
}

ATTRS = [
    'Three-Point Shot', 'Mid-Range Shot', 'Close Shot', 'Free Throw', 'Layup',
    'Driving Dunk', 'Standing Dunk', 'Post Control', 'Draw Foul', 'Speed', 'Strength',
    'Agility', 'Vertical', 'Stamina', 'Hustle', 'Ball Handle', 'Speed with Ball',
    'Pass Accuracy', 'Pass Vision', 'Pass IQ', 'Block', 'Steal', 'Interior Defense',
    'Perimeter Defense', 'Help Defense IQ', 'Defensive Rebound', 'Offensive Rebound',
    'Offensive Consistency', 'Defensive Consistency', 'Shot IQ', 'Intangibles',
]

POS_SHORT = {
    'point-guard': 'PG', 'shooting-guard': 'SG', 'small-forward': 'SF',
    'power-forward': 'PF', 'center': 'C',
}


# ---------------------------------------------------------------- 名字正規化

def strip_accents(s: str) -> str:
    s = s.replace('’', "'").replace('đ', 'd').replace('Đ', 'D')
    s = s.replace('ø', 'o').replace('Ø', 'O')
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def norm_key(name: str, drop_suffix: bool = False) -> str:
    s = strip_accents(name).lower()
    s = s.replace('.', '').replace("'", '').replace('’', '')
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    parts = s.split()
    if drop_suffix and len(parts) > 2 and parts[-1] in SUFFIXES:
        parts = parts[:-1]
    return ' '.join(parts)


def guess_slug(name: str) -> str:
    s = strip_accents(name).lower()
    s = s.replace('.', '').replace("'", '').replace('’', '')
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s


# ---------------------------------------------------------------- 抓取 / cache

class Fetcher:
    def __init__(self, max_new: int = 10 ** 9) -> None:
        CACHE.mkdir(parents=True, exist_ok=True)
        self.sess = requests.Session()
        self.sess.headers.update(HEADERS)
        self.network_calls = 0
        self.new_fetches = 0
        self.max_new = max_new
        self.blocked_streak = 0
        self.aborted = False
        self.errors: list[tuple[str, str]] = []

    def _cached_path(self, cache_name: str) -> Path:
        return CACHE / f'{cache_name}.html'

    def _miss_path(self, cache_name: str) -> Path:
        return CACHE / f'{cache_name}.404'

    def _giveup_path(self, cache_name: str) -> Path:
        return CACHE / f'{cache_name}.giveup'

    def status_of(self, cache_name: str) -> str:
        """供呼叫端判斷目前狀態，不發任何請求：
        'cached'    已有快取頁面
        'unavail'   已確認 404 或已放棄重試（giveup），不會再嘗試
        'pending'   這輪預算用盡或已中止，還沒試，之後可續跑
        'new'       還沒試過，這次呼叫 get() 會真的發請求
        """
        if self._cached_path(cache_name).exists() and self._cached_path(cache_name).stat().st_size > 2000:
            return 'cached'
        if self._miss_path(cache_name).exists() or self._giveup_path(cache_name).exists():
            return 'unavail'
        if self.aborted or self.new_fetches >= self.max_new:
            return 'pending'
        return 'new'

    def get(self, path: str, cache_name: str, retry_on_block: bool = True) -> str | None:
        """回傳 HTML；404／放棄／預算用盡／中止後都回 None（呼叫端用 status_of 分辨原因）。"""
        cached = self._cached_path(cache_name)
        if cached.exists() and cached.stat().st_size > 2000:
            return cached.read_text(encoding='utf-8', errors='replace')
        miss = self._miss_path(cache_name)
        giveup = self._giveup_path(cache_name)
        if miss.exists() or giveup.exists():
            return None
        if self.aborted or self.new_fetches >= self.max_new:
            return None
        self.new_fetches += 1

        attempts = 2 if retry_on_block else 1
        status = None
        for attempt in range(attempts):
            if self.network_calls:
                time.sleep(SLEEP if attempt == 0 else BLOCK_WAIT)
            self.network_calls += 1
            try:
                r = self.sess.get(f'{BASE}/{path}', timeout=30)
            except requests.RequestException as exc:                 # 網路層錯誤如實記錄
                self.errors.append((path, f'RequestException: {exc}'))
                return None
            status = r.status_code
            if status == 200:
                cached.write_text(r.text, encoding='utf-8')
                self.blocked_streak = 0
                return r.text
            self.errors.append((path, f'HTTP {status}'))
            if status == 404:
                miss.write_text('404', encoding='utf-8')
                return None
            if status not in (403, 429, 503):
                return None
            if attempt == 0 and retry_on_block:
                print(f'   {path} 回 HTTP {status}，停 5 分鐘後重試一次', file=sys.stderr)
                continue

        if status in (403, 429, 503):
            if retry_on_block:
                self.blocked_streak += 1
                print(f'   {path} 重試後仍回 HTTP {status}（連續第 {self.blocked_streak} 個頁面被擋）',
                      file=sys.stderr)
                if self.blocked_streak >= MAX_CONSEC_BLOCKED:
                    self.aborted = True
                    print(f'!! 連續 {self.blocked_streak} 個頁面被擋，本輪中止抓取新頁面；'
                          f'已快取的資料保留，之後可續跑', file=sys.stderr)
            else:
                giveup.write_text(str(status), encoding='utf-8')
                print(f'   {path} 回 HTTP {status}，放棄（不重試，已標記 giveup）', file=sys.stderr)
        return None


# ---------------------------------------------------------------- 解析

def parse_player(html: str) -> dict[str, object]:
    rec: dict[str, object] = {}
    m = re.search(r'"name":\s*"NBA 2K(\d+) Rating",\s*"value":\s*(\d+)', html)
    if m:
        rec['gameYear'] = f'2K{m.group(1)}'
        rec['overall'] = int(m.group(2))
    for a in ATTRS:
        m = re.search(r'"name":\s*"%s Attribute",\s*"value":\s*(\d+)' % re.escape(a), html)
        if m:
            rec[a] = int(m.group(1))
    # 位置：簡介段落 "plays at the <a href="/lists/power-forward">...</a> or <a ...>"
    bio = re.search(r'plays at the (.{0,220}?) position', html, re.S)
    pos: list[str] = []
    if bio:
        for p in re.findall(r'/lists/([a-z\-]+)"', bio.group(1)):
            if p in POS_SHORT and POS_SHORT[p] not in pos:
                pos.append(POS_SHORT[p])
    rec['pos2k'] = '/'.join(pos)
    m = re.search(r'"memberOf":\s*\{[^}]*?"name":\s*"([^"]+)"', html, re.S)
    if m:
        rec['team2k'] = m.group(1)
    return rec


# ---------------------------------------------------------------- 主流程

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-new', type=int, default=10 ** 9,
                         help='這次呼叫最多發出幾個新的（非快取）網路請求，用於分批前景執行')
    args = parser.parse_args()

    cards = list(csv.DictReader(CARD_CSV.open(encoding='utf-8')))
    print(f'卡片板球員：{len(cards)}')

    f = Fetcher(max_new=args.max_new)

    # 1) 從 sitemap 建 slug 索引
    index: dict[str, tuple[str, str]] = {}      # norm key -> (slug, display name)
    index_ns: dict[str, tuple[str, str]] = {}   # 去後綴 key
    n_slugs = 0
    for sm in SITEMAPS:
        retry = sm not in NO_RETRY_SITEMAPS
        xml = f.get(sm, sm.replace('.xml', ''), retry_on_block=retry)
        if xml is None:
            print(f'  跳過 sitemap {sm}（狀態：{f.status_of(sm.replace(".xml", ""))}）')
            continue
        for slug in re.findall(r'<loc>https://www\.2kratings\.com/([a-z0-9\-]+)/?</loc>', xml):
            if HISTORIC_RE.search(slug) or slug.startswith(('teams', 'lists', 'wnba')):
                continue
            n_slugs += 1
            k = norm_key(slug.replace('-', ' '))
            index.setdefault(k, (slug, slug))
            index_ns.setdefault(norm_key(slug.replace('-', ' '), drop_suffix=True), (slug, slug))
    print(f'sitemap slug 索引：{n_slugs} 筆（{len(index)} 個唯一 key）')

    # 2) 對應
    resolved: list[tuple[dict, str, str]] = []   # (card row, slug, 對應方式)
    unresolved: list[dict] = []
    for row in cards:
        name = row['name']
        if name in ALIASES:
            resolved.append((row, ALIASES[name], 'alias'))
            continue
        k = norm_key(name)
        if k in index:
            resolved.append((row, index[k][0], 'exact'))
            continue
        kns = norm_key(name, drop_suffix=True)
        if kns in index_ns:
            resolved.append((row, index_ns[kns][0], 'suffix'))
            continue
        if kns in index:
            resolved.append((row, index[kns][0], 'suffix'))
            continue
        unresolved.append(row)
    print(f'索引直接對上：{len(resolved)}；待猜 slug：{len(unresolved)}')

    # 3) 猜 slug 直接試球員頁
    still_missing: list[tuple[dict, list[str]]] = []
    pending_guess: list[tuple[dict, list[str]]] = []
    for row in unresolved:
        name = row['name']
        cands: list[str] = []
        g = guess_slug(name)
        cands.append(g)
        parts = g.split('-')
        if len(parts) > 2 and parts[-1] in SUFFIXES:
            cands.append('-'.join(parts[:-1]))
        hit = None
        any_pending = False
        for c in cands:
            st = f.status_of(c)
            if st == 'pending':
                any_pending = True
                continue
            if f.get(c, c) is not None:
                hit = c
                break
        if hit:
            resolved.append((row, hit, 'guess'))
        elif any_pending:
            pending_guess.append((row, cands))
        else:
            still_missing.append((row, cands))
    print(f'猜 slug 成功後總對應：{len(resolved)}；仍對不上：{len(still_missing)}；'
          f'待續跑：{len(pending_guess)}')

    # 4) 抓球員頁
    rows_out = []
    fetch_fail = []
    pending_fetch = []
    for i, (row, slug, how) in enumerate(resolved, 1):
        pre_status = f.status_of(slug)
        html = f.get(slug, slug)
        if html is None:
            if pre_status == 'pending':
                pending_fetch.append((row, slug))
            else:
                fetch_fail.append((row, slug))
            continue
        rec = parse_player(html)
        if 'overall' not in rec:
            fetch_fail.append((row, slug))
            continue
        out = {'name': row['name'], 'slug': slug, 'matchedBy': how,
               'overall2k': rec['overall'], 'gameYear': rec.get('gameYear', ''),
               'pos2k': rec.get('pos2k', ''), 'team2k': rec.get('team2k', '')}
        for a in ATTRS:
            out[a] = rec.get(a, '')
        rows_out.append(out)
        if i % 25 == 0:
            print(f'  已處理 {i}/{len(resolved)}（本輪新抓 {f.new_fetches}/{args.max_new}，'
                  f'網路請求 {f.network_calls}）')

    fields = ['name', 'slug', 'matchedBy', 'overall2k', 'gameYear', 'pos2k', 'team2k'] + ATTRS
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(rows_out, key=lambda r: -r['overall2k']))

    with UNMATCHED.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['name', 'cardRank', 'cardOvr', 'MIN', 'reason', 'triedSlugs'])
        for row, cands in still_missing:
            w.writerow([row['name'], row['rank'], row['ovr'], row['MIN'],
                        'slug 對不上（索引與猜測皆 404）', ' '.join(cands)])
        for row, slug in fetch_fail:
            w.writerow([row['name'], row['rank'], row['ovr'], row['MIN'],
                        '球員頁抓取或解析失敗', slug])
        for row, cands in pending_guess:
            w.writerow([row['name'], row['rank'], row['ovr'], row['MIN'],
                        '尚未嘗試（本輪預算用盡或已中止，可續跑）', ' '.join(cands)])
        for row, slug in pending_fetch:
            w.writerow([row['name'], row['rank'], row['ovr'], row['MIN'],
                        '尚未嘗試（本輪預算用盡或已中止，可續跑）', slug])

    cov = len(rows_out) / len(cards)
    n_pending = len(pending_guess) + len(pending_fetch)
    print(f'\n寫出 {OUT_CSV.name}：{len(rows_out)} 人，涵蓋率 {cov:.1%}')
    print(f'對不上 / 失敗（確認性）：{len(still_missing) + len(fetch_fail)} 人')
    print(f'待續跑（本輪未嘗試）：{n_pending} 人')
    print(f'總網路請求：{f.network_calls}，本輪新抓：{f.new_fetches}，非 200 次數：{len(f.errors)}')
    if f.aborted:
        print('!! 本輪因連續被擋而中止，建議稍後再跑一次以續抓剩餘球員', file=sys.stderr)
    if f.errors:
        print('錯誤樣本：', f.errors[:10])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
