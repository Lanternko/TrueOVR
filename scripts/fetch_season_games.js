import fs from 'node:fs/promises';

// Separate snapshots: do not overwrite the fixed-five benchmark's sources.
// 用法：node scripts/fetch_season_games.js [季別]；預設 2025-26 寫 data/season-source/，其他季寫 data/season-source-<季別>/。
const season = process.argv[2] || '2025-26';
const directory = new URL(season==='2025-26' ? '../data/season-source/' : `../data/season-source-${season}/`, import.meta.url);
// 整季才檢查球隊列數（30 隊 × 82 場）；賽季進行中不檢查。
const fullTeamRows = season==='2025-26' ? 2460 : null;
await fs.mkdir(directory, {recursive:true});
let teamGames;
for (const [name, kind, expected] of [['team-games','T',fullTeamRows], ['player-games','P',null]]) {
  const query = new URLSearchParams({Counter:'1000',DateFrom:'',DateTo:'',Direction:'DESC',
    LeagueID:'00',Season:season,SeasonType:'Regular Season',Sorter:'DATE',PlayerOrTeam:kind});
  const url = `https://stats.nba.com/stats/leaguegamelog?${query}`;
  const response = await fetch(url, {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'},
    signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
  const data = await response.json();
  const set = data.resultSets?.[0];
  if (!set?.rowSet?.length || (expected && set.rowSet.length!==expected)) throw new Error(`Incomplete ${name}`);
  await fs.writeFile(new URL(`${name}.json`,directory), JSON.stringify({url,fetchedAt:new Date().toISOString(),season,data})+'\n');
  console.log(`${name}: ${set.rowSet.length} records`);
  if (kind==='T') teamGames=set.rowSet.map(row=>Object.fromEntries(set.headers.map((k,i)=>[k,row[i]])));
}
// Neutral-site rows may both say "@". Preserve the separate NBA summary.
for (const [id,rows] of Map.groupBy(teamGames,r=>r.GAME_ID)) {
  if (rows.filter(r=>r.MATCHUP.includes(' vs. ')).length===1) continue;
  const url='https://stats.nba.com/stats/boxscoresummaryv2?GameID='+id;
  const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'},signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
  const data=await response.json();
  if (!data.resultSets?.some(s=>s.name==='GameSummary'&&s.rowSet.length===1)) throw new Error('Missing game summary: '+id);
  await fs.writeFile(new URL(`game-summary-${id}.json`,directory),JSON.stringify({url,fetchedAt:new Date().toISOString(),season,data})+'\n');
  console.log('neutral summary: '+id);
}
