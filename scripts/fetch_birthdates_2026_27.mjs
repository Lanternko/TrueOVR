// 抓卡片名單（Win11 D.pids 中 age_flags 讀得到的人）的出生日期 -> data/defense-seventh/2026-27/birthdates.json（凍結檔，E-193／R-129）。
// 來源：stats.nba.com commonplayerinfo 的 BIRTHDATE（Python urllib 會被擋，所以用 node，同 fetch_inseason_2026_27.js）；
// 逐人節流、可續抓（檔案已有的人不重抓）；抓不到的人不補（不用記憶或猜的）。
// 用法：node scripts/fetch_birthdates_2026_27.mjs <pids.json>   （pids.json＝pid 陣列）
import fs from 'node:fs';
const [,, pidFile] = process.argv;
const OUT = 'data/defense-seventh/2026-27/birthdates.json';
const URL = 'https://stats.nba.com/stats/commonplayerinfo?LeagueID=00&PlayerID=';
const headers = { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com' };
const pids = JSON.parse(fs.readFileSync(pidFile, 'utf8'));
const cur = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : {};
const dob = cur.birthdates || {};
const missing = new Set(cur.noBirthdate || []);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const save = () => fs.writeFileSync(OUT, JSON.stringify({
  source: URL + '<PLAYER_ID>', fetchedAt: new Date().toISOString(),
  note: '凍結檔；pid -> YYYY-MM-DD（commonplayerinfo BIRTHDATE）；noBirthdate＝端點無資料的 pid（不補）',
  birthdates: Object.fromEntries(Object.entries(dob).sort((a, b) => a[0] - b[0])), noBirthdate: [...missing].sort((a, b) => a - b),
}, null, 0).replace(/,"noBirthdate"/, ',\n"noBirthdate"') + '\n');
async function one(pid) {
  let last;
  for (let i = 0; i < 3; i++) {
    try {
      const r = await fetch(URL + pid, { headers, signal: AbortSignal.timeout(25000) });
      if (!r.ok) throw Error('HTTP ' + r.status);
      const s = (await r.json()).resultSets[0];
      const row = s.rowSet[0];
      return row ? (row[s.headers.indexOf('BIRTHDATE')] || '').slice(0, 10) || null : null;
    } catch (e) { last = e; await sleep(2000 * (i + 1)); }
  }
  throw last;
}
let fails = 0, n = 0;
for (const pid of pids) {
  if (dob[pid] || missing.has(pid)) continue;
  try { const v = await one(pid); fails = 0; if (v) dob[pid] = v; else missing.add(pid); }
  catch (e) { console.log('fail', pid, e.message); if (++fails >= 5) { console.log('連續失敗 5 次，停止'); break; } continue; }
  if (++n % 50 === 0) { save(); console.log(n, Object.keys(dob).length); }
  await sleep(600);
}
save();
console.log('done', Object.keys(dob).length, 'noBirthdate', missing.size);
