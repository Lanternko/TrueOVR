// defense-update-speed：歷史季「截至某日」防守追蹤表。輕量網路抓取（本機）。
// 1) leaguegamelog（球隊逐場：日期、得失分、回合估算用欄位）→ data/gamelog-<季>.json
// 2) 每隊第 10、20 場的日期 D → rim/three/hustle/advanced 以 DateTo=D（快照）與 DateFrom=D+1（剩餘賽季，次要指標）各抓一次
// 3) 窗口最舊兩季（2020-21、2021-22）的季總計 5 表（格式同 reports/defense-tenth/step4-t2/raw）
// 4) matchups：leagueseasonmatchups 不吃 DateTo（第 0 步實測），改逐場 boxscorematchupsv3 → data/games-<季>.jsonl.gz
// 用法：node fetch_hist.mjs   （可重跑；已存在的檔跳過）
import fs from 'node:fs'; import zlib from 'node:zlib';
const OUT = new URL('../data/', import.meta.url); fs.mkdirSync(OUT, {recursive:true});
const H = {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/',Origin:'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const SEASONS = ['2024-25', '2025-26'], OLD = ['2020-21', '2021-22'], NS = [10, 20];
const common = (season, from, to) => ({LeagueID:'00',SeasonType:'Regular Season',PerMode:'Totals',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',
  PlusMinus:'N',Rank:'N',Period:'0',DateFrom:from,DateTo:to,Conference:'',Division:'',GameSegment:'',Location:'',Outcome:'',PORound:'',
  PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',ShotClockRange:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',
  Country:'',DraftPick:'',DraftYear:'',Height:'',Weight:'',Season:season,TeamID:'0'});
const jobs = (season, from='', to='') => ({
  rim: ['leaguedashptdefend', {...common(season, from, to), MeasureType:'Base', DefenseCategory:'Less Than 6Ft'}],
  three: ['leaguedashptdefend', {...common(season, from, to), MeasureType:'Base', DefenseCategory:'3 Pointers'}],
  hustle: ['leaguehustlestatsplayer', {...common(season, from, to), MeasureType:'Base'}],
  advanced: ['leaguedashplayerstats', {...common(season, from, to), MeasureType:'Advanced'}],
  matchups: ['leagueseasonmatchups', {LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',DefPlayerID:'',DefTeamID:'',OffPlayerID:'',OffTeamID:''}],
});
async function get(url, needRows=true) {
  for (let t = 1; ; t++) {
    try {
      const r = await fetch(url, {...H, signal:AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      if (needRows) { const s = Array.isArray(d.resultSets) ? d.resultSets[0] : d.resultSets; if (!s?.rowSet?.length) throw new Error('Empty dataset'); }
      return d;
    } catch (e) { if (t >= 4) throw e; await sleep(4000 * t); }
  }
}
const save = (f, o) => { const p = new URL(f, OUT); fs.mkdirSync(new URL('.', p), {recursive:true}); fs.writeFileSync(p, JSON.stringify(o) + '\n'); };
const has = f => fs.existsSync(new URL(f, OUT));
const mdY = d => `${d.slice(5,7)}/${d.slice(8,10)}/${d.slice(0,4)}`;
const next = d => { const x = new Date(d + 'T12:00:00Z'); x.setUTCDate(x.getUTCDate() + 1); return x.toISOString().slice(0, 10); };
const log = m => console.log(new Date().toISOString(), m);
async function table(file, kind, ep, params, season, extra={}) {
  if (has(file)) return;
  const url = `https://stats.nba.com/stats/${ep}?` + new URLSearchParams(params);
  const data = await get(url);
  save(file, {season, team:0, kind, endpoint:ep, url, ...extra, fetchedAt:new Date().toISOString(), data});
  await sleep(800);
}
for (const s of SEASONS) {
  const f = `gamelog-${s}.json`;
  if (!has(f)) { const url = 'https://stats.nba.com/stats/leaguegamelog?' + new URLSearchParams({Counter:'0',Direction:'ASC',LeagueID:'00',PlayerOrTeam:'T',Season:s,SeasonType:'Regular Season',Sorter:'DATE',DateFrom:'',DateTo:''});
    save(f, {season:s, url, fetchedAt:new Date().toISOString(), data:await get(url)}); await sleep(800); }
  const d = JSON.parse(fs.readFileSync(new URL(f, OUT))).data.resultSets[0];
  const I = k => d.headers.indexOf(k), byTeam = {};
  for (const r of d.rowSet) (byTeam[r[I('TEAM_ID')]] ??= []).push([r[I('GAME_DATE')], r[I('GAME_ID')]]);
  const dates = new Set();
  for (const g of Object.values(byTeam)) { g.sort(); for (const n of NS) dates.add(g[n - 1][0]); }
  log(`${s}: ${d.rowSet.length / 2} games, snapshot dates ${[...dates].sort().join(' ')}`);
  for (const D of [...dates].sort()) for (const [k, [ep, p]] of Object.entries(jobs(s, '', mdY(D)))) if (k !== 'matchups') {
    await table(`cut/${s}/to-${D}-${k}.json`, k, ep, p, s, {dateTo:D});
    const p2 = jobs(s, mdY(next(D)), '')[k][1];
    await table(`cut/${s}/from-${next(D)}-${k}.json`, k, ep, p2, s, {dateFrom:next(D)});
  }
  log(`${s}: cut tables done`);
}
for (const s of OLD) for (const [k, [ep, p]] of Object.entries(jobs(s))) await table(`raw/${s}/0-${k}.json`, k, ep, p, s);
log('old season totals done');
for (const s of SEASONS) {
  const f = new URL(`games-${s}.jsonl`, OUT), fz = new URL(`games-${s}.jsonl.gz`, OUT);
  if (fs.existsSync(fz)) continue;
  const done = new Set(fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l).gid) : []);
  const d = JSON.parse(fs.readFileSync(new URL(`gamelog-${s}.json`, OUT))).data.resultSets[0];
  const gids = [...new Set(d.rowSet.map(r => r[d.headers.indexOf('GAME_ID')]))].sort();
  const fails = [];
  for (const gid of gids) { if (done.has(gid)) continue;
    try {
      const j = await get(`https://stats.nba.com/stats/boxscorematchupsv3?GameID=${gid}&LeagueID=00`, false);
      const b = j.boxScoreMatchups, rows = [];
      for (const side of ['homeTeam', 'awayTeam']) for (const p of b[side].players) for (const m of p.matchups || [])
        rows.push([b[side].teamId, p.personId, m.personId, m.statistics.partialPossessions, m.statistics.matchupFieldGoalsAttempted]);
      fs.appendFileSync(f, JSON.stringify({gid, rows}) + '\n');
    } catch (e) { fails.push([gid, String(e)]); }
    await sleep(600);
  }
  if (!fails.length) { fs.writeFileSync(fz, zlib.gzipSync(fs.readFileSync(f))); fs.unlinkSync(f); }
  log(`${s}: games ${gids.length}, fails ${fails.length} ${JSON.stringify(fails.slice(0, 5))}`);
}
fs.writeFileSync(new URL('FETCH_DONE', OUT), new Date().toISOString() + '\n');
log('ALL DONE');
