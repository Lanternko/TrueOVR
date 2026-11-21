// E-246：回測用賽前快照。每個比賽日 d 抓 DateTo＝d 前一天的整季累計（hustle／rim／three／advanced），存 snap/<d>/<kind>.json（格式同 fetch_defense_tracking）。
// 用法：node fetch_snap.mjs  （讀 work/games.json 的日期；已存在的檔跳過）
import fs from 'node:fs';
const H = {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/',Origin:'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const base = {LeagueID:'00',SeasonType:'Regular Season',PerMode:'Totals',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',
  PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',Conference:'',Division:'',GameSegment:'',Location:'',Outcome:'',PORound:'',
  PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',ShotClockRange:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',
  Country:'',DraftPick:'',DraftYear:'',Height:'',Weight:'',Season:'2026-27',TeamID:'0'};
const jobs = {rim:['leaguedashptdefend',{MeasureType:'Base',DefenseCategory:'Less Than 6Ft'}], three:['leaguedashptdefend',{MeasureType:'Base',DefenseCategory:'3 Pointers'}],
  hustle:['leaguehustlestatsplayer',{MeasureType:'Base'}], advanced:['leaguedashplayerstats',{MeasureType:'Advanced'}]};
const dates = [...new Set(JSON.parse(fs.readFileSync('work/games.json','utf8')).map(g => g.date))].sort();
for (const d of dates) {
  const prev = new Date(d + 'T12:00:00Z'); prev.setUTCDate(prev.getUTCDate() - 1);
  const to = `${String(prev.getUTCMonth()+1).padStart(2,'0')}/${String(prev.getUTCDate()).padStart(2,'0')}/${prev.getUTCFullYear()}`;
  fs.mkdirSync(`snap/${d}`, {recursive:true});
  for (const [kind, [ep, q]] of Object.entries(jobs)) {
    const f = `snap/${d}/${kind}.json`;
    if (fs.existsSync(f)) continue;
    const url = `https://stats.nba.com/stats/${ep}?` + new URLSearchParams({...base, ...q, DateTo:to});
    for (let t = 1; ; t++) {
      try {
        const r = await fetch(url, {...H, signal:AbortSignal.timeout(60000)}); if (!r.ok) throw Error('HTTP ' + r.status);
        const data = await r.json(); const s = Array.isArray(data.resultSets) ? data.resultSets[0] : data.resultSets;
        fs.writeFileSync(f, JSON.stringify({url, dateTo:to, fetchedAt:new Date().toISOString(), data}) + '\n');
        console.log(d, kind, 'DateTo', to, 'rows', s.rowSet.length); break;
      } catch (e) { if (t >= 3) { console.log(d, kind, 'FAIL', String(e)); break; } await sleep(4000 * t); }
    }
    await sleep(800);
  }
}
