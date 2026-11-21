// E-123 資料抓取：2022-23、2023-24 的 leaguedashplayerstats Base Totals（STL、PF；E-071 fetch.mjs 同配方，只寫本資料夾 data/）。
// 用法（repo 根目錄）：node reports/card-0.2.7+E123-tail-3pt-rim-pres/work/fetch_base.mjs
import fs from 'node:fs';
import crypto from 'node:crypto';
const D = 'reports/card-0.2.7+E123-tail-3pt-rim-pres/data';
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const common = {LeagueID:'00',SeasonType:'Regular Season',PerMode:'Totals',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',DateTo:'',Conference:'',Division:'',GameSegment:'',Location:'',Outcome:'',PORound:'0',PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',ShotClockRange:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',Country:'',DraftPick:'',DraftYear:'',Height:'',Weight:'',TeamID:'0'};
const headers = {'User-Agent':'Mozilla/5.0', Referer:'https://www.nba.com/', Origin:'https://www.nba.com', Accept:'application/json'};
async function get(endpoint, params, timeout) {
  const url = 'https://stats.nba.com/stats/' + endpoint + '?' + new URLSearchParams(params);
  let err;
  for (let a = 0; a < 3; a++) {
    try {
      const r = await fetch(url, {headers, signal: AbortSignal.timeout(timeout)});
      if (!r.ok) throw Error('HTTP ' + r.status);
      return {url, data: await r.json()};
    } catch (e) { err = e; console.log('retry', endpoint, a, String(e)); }
  }
  throw err;
}
const rows = d => { const s = Array.isArray(d.resultSets) ? d.resultSets[0] : d.resultSets; return s.rowSet.length; };
const manifest = [];
for (const season of ['2022-23', '2023-24']) {
  const file = `${D}/${season}-base.json`;
  if (!fs.existsSync(file)) {
    const res = await get('leaguedashplayerstats', {...common, Season: season, MeasureType: 'Base'}, 180000);
    fs.writeFileSync(file, JSON.stringify({endpoint: 'leaguedashplayerstats', season, kind: 'base', url: res.url, fetchedAt: new Date().toISOString(), data: res.data}) + '\n');
  }
  const d = JSON.parse(fs.readFileSync(file, 'utf8'));
  manifest.push({file, season, kind: 'base', rows: rows(d.data), sha256: sha(file)});
  console.log(file, rows(d.data));
}
fs.writeFileSync(`${D}/sha256-base.json`, JSON.stringify(manifest, null, 2) + '\n');
