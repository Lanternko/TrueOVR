// E-069：抓 tracking Possessions / Passing，每季 H1（<=D1）、H2（>=D1+1）、整季。參數同 reports/player-impact-v21/fetch-tracking.mjs。
// 用法（repo 根）：node reports/handle-E069/fetch-tracking.mjs
import fs from 'node:fs';
import crypto from 'node:crypto';
const here = 'reports/handle-E069';
const bnd = JSON.parse(fs.readFileSync(`${here}/boundaries.json`, 'utf8'));
const mdy = (iso) => { const [y, m, d] = iso.split('-'); return `${m}/${d}/${y}`; };
const jobs = [];
for (const season of Object.keys(bnd).sort()) for (const measure of ['Possessions', 'Passing']) {
  jobs.push({ season, measure, seg: 'H1', from: '', to: mdy(bnd[season].D1) });
  jobs.push({ season, measure, seg: 'H2', from: mdy(bnd[season].H2From), to: '' });
  jobs.push({ season, measure, seg: 'FULL', from: '', to: '' });
}
const results = [];
for (const j of jobs) {
  const file = `${here}/raw/${j.season}/${j.measure}-${j.seg}.json`;
  const params = { LeagueID: '00', Season: j.season, SeasonType: 'Regular Season', PerMode: 'Totals', PlayerOrTeam: 'Player', PtMeasureType: j.measure, TeamID: '0', LastNGames: '0', Month: '0', OpponentTeamID: '0', PaceAdjust: 'N', PlusMinus: 'N', Rank: 'N', Period: '0', DateFrom: j.from, DateTo: j.to, Conference: '', Division: '', GameSegment: '', Location: '', Outcome: '', PORound: '', PlayerExperience: '', PlayerPosition: '', SeasonSegment: '', StarterBench: '', VsConference: '', VsDivision: '', College: '', Country: '', DraftPick: '', DraftYear: '', Height: '', Weight: '' };
  const url = 'https://stats.nba.com/stats/leaguedashptstats?' + new URLSearchParams(params);
  try {
    if (!fs.existsSync(file)) {
      const r = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/' }, signal: AbortSignal.timeout(30000) });
      if (!r.ok) throw Error('HTTP ' + r.status);
      const data = await r.json();
      const rs = Array.isArray(data.resultSets) ? data.resultSets[0] : data.resultSets;
      if (!rs?.headers?.includes('PLAYER_ID') || !rs.rowSet.length) throw Error('Invalid player tracking table');
      fs.mkdirSync(`${here}/raw/${j.season}`, { recursive: true });
      fs.writeFileSync(file, JSON.stringify({ ...j, url, fetchedAt: new Date().toISOString(), data }) + '\n');
      await new Promise(r => setTimeout(r, 1500));
    }
    const d = JSON.parse(fs.readFileSync(file, 'utf8')); const rs = Array.isArray(d.data.resultSets) ? d.data.resultSets[0] : d.data.resultSets;
    results.push({ ...j, file, rows: rs.rowSet.length, sha256: crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') });
    console.log(j.season, j.measure, j.seg, rs.rowSet.length);
  } catch (e) { results.push({ ...j, url, error: String(e) }); console.log('FAIL', j.season, j.measure, j.seg, String(e)); }
}
fs.writeFileSync(`${here}/raw/fetch-manifest.json`, JSON.stringify({ jobs: results, failures: results.filter(r => r.error) }, null, 2) + '\n');
