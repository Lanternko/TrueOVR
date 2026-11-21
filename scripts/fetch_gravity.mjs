import fs from 'node:fs/promises';

// inseason 0.2.10j（R-134、E-200）：每天抓 NBA.com 引力榜（整季累計），供 live/gravity_live.py 算賽中 gravity（無球外線引力）。
// 端點與 headers 同 reports/F126-shot-difficulty/gravity-split/fetch_gravity_split.mjs（curl 會被擋，node fetch 可以）。
// 用法：node scripts/fetch_gravity.mjs [2026-27] → data/defense-seventh/<季>/gravity.json（{url, season, fetchedAt, leaders}）
// 失敗（HTTP 錯誤、空榜、缺欄位）exit 1，不覆寫上次成功的檔。
const season = process.argv[2] || '2026-27';
const dir = new URL(`../data/defense-seventh/${season}/`, import.meta.url);
await fs.mkdir(dir, {recursive: true});
const url = `https://stats.nba.com/stats/gravityleaders?LeagueID=00&Season=${season}&SeasonType=Regular+Season`;
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const NEED = ['PLAYERID', 'FRAMES', 'AVGOFFBALLPERIMETERGRAVITYSCORE'];
let leaders, err;
for (let t = 1; t <= 3; t++) {
  try {
    const r = await fetch(url, {...H, signal: AbortSignal.timeout(60000)});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    const L = j.leaders || [];
    if (!L.length) throw new Error('空榜');
    const miss = NEED.filter(k => !(k in L[0]));
    if (miss.length) throw new Error('缺欄位 ' + miss.join(','));
    leaders = L;
    break;
  } catch (e) {
    err = e;
    await sleep(5000 * t);
  }
}
if (!leaders) {
  console.log(JSON.stringify({season, ok: false, error: String(err)}));
  process.exit(1);
}
const tmp = new URL('gravity.json.tmp', dir);
await fs.writeFile(tmp, JSON.stringify({url, season, fetchedAt: new Date().toISOString(), leaders}) + '\n');
await fs.rename(tmp, new URL('gravity.json', dir));
console.log(JSON.stringify({season, ok: true, n: leaders.length}));
