"""E-123：重抓 2022-23 全季三分拆分（v62 fetch_data.py 同配方：leaguedashptstats CatchShoot/PullUpShot + leaguedashplayerptshot 四個防守距離），
只寫本資料夾 data/（不動 v62 raw/）。請求間隔 >=1.2 秒，失敗最多重試 3 次。用法（repo 根）：python -I -X utf8 reports/card-0.2.7+E123-tail-3pt-rim-pres/work/fetch_t2223.py"""
import urllib.request, urllib.parse, json, time, hashlib, os, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RAW = os.path.join(ROOT, 'data')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://www.nba.com/', 'Origin': 'https://www.nba.com',
     'Accept': 'application/json', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true'}
SEASON = '2022-23'
DEF = ['0-2 Feet - Very Tight', '2-4 Feet - Tight', '4-6 Feet - Open', '6+ Feet - Wide Open']
last = [0.0]; manifest = []
def fetch(url):
    for a in range(3):
        wait = 1.2 - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40).read()
        except Exception as e:
            print('retry', a + 1, str(e)[:100], url[-80:], flush=True); time.sleep(3 * (a + 1))
    raise SystemExit('FAILED after 3 retries: ' + url)
def call(ep, params, name):
    path = os.path.join(RAW, name)
    url = 'https://stats.nba.com/stats/%s?%s' % (ep, urllib.parse.urlencode(params))
    if os.path.exists(path): body = open(path, 'rb').read()
    else:
        body = fetch(url); open(path, 'wb').write(body)
    j = json.loads(body); rs = j['resultSets'][0]
    manifest.append({'file': name, 'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'rows': len(rs['rowSet']),
                     'fetchedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(name, len(rs['rowSet']), flush=True)
COMMON = {'LeagueID': '00', 'SeasonType': 'Regular Season', 'PerMode': 'Totals', 'PlayerOrTeam': 'Player', 'LastNGames': '0', 'Month': '0',
          'OpponentTeamID': '0', 'Period': '0', 'PORound': '0'}
EMPTY_PT = ['College', 'Conference', 'Country', 'Division', 'DraftPick', 'DraftYear', 'GameScope', 'Height', 'Location', 'Outcome',
            'PlayerExperience', 'PlayerPosition', 'SeasonSegment', 'StarterBench', 'VsConference', 'VsDivision', 'Weight']
EMPTY_SH = ['GeneralRange', 'DribbleRange', 'ShotDistRange', 'ShotClockRange', 'TouchTimeRange', 'Outcome', 'Location', 'SeasonSegment',
            'VsConference', 'VsDivision', 'GameSegment', 'PlayerExperience', 'PlayerPosition', 'StarterBench', 'College', 'Conference',
            'Country', 'Division', 'DraftPick', 'DraftYear', 'Height', 'Weight']
for kind, tag in (('CatchShoot', 'cs'), ('PullUpShot', 'pu')):
    p = {**COMMON, 'Season': SEASON, 'PtMeasureType': kind, 'TeamID': '0', 'DateFrom': '', 'DateTo': '', **{k: '' for k in EMPTY_PT}}
    call('leaguedashptstats', p, f'{SEASON}-full-{tag}.json')
for i, dd in enumerate(DEF):
    p = {**COMMON, 'Season': SEASON, 'CloseDefDistRange': dd, 'TeamID': '0', 'DateFrom': '', 'DateTo': '', **{k: '' for k in EMPTY_SH}}
    call('leaguedashplayerptshot', p, f'{SEASON}-full-def{i}.json')
json.dump({'note': 'E-123 2022-23 T 重抓；v62 fetch_data.py 配方', 'entries': manifest}, open(os.path.join(RAW, 'manifest-t2223.json'), 'w', encoding='utf8'), indent=1)
