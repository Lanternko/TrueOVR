import json,sys,urllib.request,urllib.parse,hashlib
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36','Referer':'https://www.nba.com/','Origin':'https://www.nba.com','Accept':'application/json, text/plain, */*','Accept-Language':'en-US,en;q=0.9','x-nba-stats-origin':'stats','x-nba-stats-token':'true'}
for s in ['2025-26','2024-25','2023-24','2022-23']:
    q=dict(College='',Conference='',Country='',DateFrom='',DateTo='',Division='',DraftPick='',DraftYear='',GameScope='',GameSegment='',Height='',LastNGames='0',LeagueID='00',Location='',Month='0',OpponentTeamID='0',Outcome='',PORound='0',PerMode='Totals',PlayerExperience='',PlayerOrTeam='Player',PlayerPosition='',PtMeasureType='CatchShoot',Season=s,SeasonSegment='',SeasonType='Regular Season',StarterBench='',TeamID='0',VsConference='',VsDivision='',Weight='')
    u='https://stats.nba.com/stats/leaguedashptstats?'+urllib.parse.urlencode(q)
    try:
        b=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40).read()
    except Exception as e:
        print(s,'FAIL',repr(e)); sys.exit(1)
    open(f'data/catchshoot-{s}.json','wb').write(b)
    j=json.loads(b); rs=j['resultSets'][0]
    print(s,len(rs['rowSet']),hashlib.sha256(b).hexdigest()[:12],rs['headers'])
