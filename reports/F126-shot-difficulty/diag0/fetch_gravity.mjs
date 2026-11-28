// 抓 2025-26 gravityleaders（整季，GP>=55）存 gravity.json（playerId、frames、avgGravity）
import fs from 'node:fs'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const r = await fetch('https://stats.nba.com/stats/gravityleaders?LeagueID=00&Season=2025-26&SeasonType=Regular+Season',
  {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}, signal: AbortSignal.timeout(30000)});
const j = await r.json(); const L = j.leaders || [];
console.log(r.status, L.length);
fs.writeFileSync(path.join(here, 'gravity.json'), JSON.stringify(L.map(x => ({playerId: x.PLAYERID, name: x.FIRSTNAME + ' ' + x.LASTNAME, frames: x.FRAMES, avgGravity: x.AVGGRAVITYSCORE}))));
