// 抓 gravityleaders 全欄位（含有球／無球 × 外線／禁區分項），存 gravity-<季>.json
import fs from 'node:fs'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
for (const season of ['2025-26', '2026-27']) {
  const r = await fetch(`https://stats.nba.com/stats/gravityleaders?LeagueID=00&Season=${season}&SeasonType=Regular+Season`,
    {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}, signal: AbortSignal.timeout(30000)});
  const j = await r.json(); const L = j.leaders || [];
  console.log(season, r.status, L.length, L[0] ? Object.keys(L[0]).join(',') : '');
  fs.writeFileSync(path.join(here, `gravity-${season}.json`), JSON.stringify(L));
}
