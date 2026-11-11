// v55 修正 B：從快取 play-by-play 抽出「分區 × 被助攻」的出手帳。
//   node reports/ovr-v55-finisher-fix-2025-26/extract-assist-zones.mjs
// 輸出 assist-zones.json：每季每名球員每分區的 {A, M, Ma}
//   A  = 出手數（Made + Missed 都算）
//   M  = 命中數
//   Ma = 被助攻的命中數（action 上有 assistPersonId）
// 注意：NBA play-by-play 只在**命中**的球上標助攻，所以「被助攻的出手數」本身不可觀測。
// 這裡只抽可觀測量，分攤留給 build-finisher-card.mjs（用來源角色的 receivedShare 補上缺的那一式）。
//
// 分區定義與 scripts/build_season_league.js 的卡片分區一致（leaguedashplayershotlocations By Zone）：
//   short = Restricted Area + In The Paint (Non-RA)
//   mid   = Mid-Range
//   long  = 任何 3pt
// 分區用 xLegacy/yLegacy 幾何判定，不用 play-by-play 的 area 字串。實測 2025-26：
//   幾何法禁區出手 106285，官方 leaguedashplayershotlocations 106161（差 0.12%）；
//   area 字串法只有 103349（差 -2.65%），因為 2404 球官方算禁區、live feed 標成 Mid-Range。
import fs from 'node:fs';
import path from 'node:path';

const SEASONS = {
  '2025-26': 'data/defense-a-source/pbp',
  '2024-25': 'data/defense-seventh/2024-25/pbp',
  '2023-24': 'data/defense-seventh/2023-24/pbp',
  '2022-23': 'data/defense-seventh/2022-23/pbp',
};
// 傳統座標，單位是 0.1 英尺，籃框在 (0, 0)。
// Restricted Area = 距籃框 4 英尺內；In The Paint (Non-RA) = 禁區內但在 RA 外（禁區寬 16 英尺、深到罰球線）。
function zoneOf(a) {
  if (a.actionType === '3pt') return 'long';
  if (a.actionType !== '2pt') return null;
  const x = a.xLegacy, y = a.yLegacy;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  if (Math.hypot(x, y) <= 40) return 'short';                        // Restricted Area
  if (Math.abs(x) <= 80 && y <= 142.5 && y >= -47.5) return 'short'; // In The Paint (Non-RA)
  return 'mid';
}

const out = {};
for (const [season, dir] of Object.entries(SEASONS)) {
  if (!fs.existsSync(dir)) { console.error('missing ' + dir); continue; }
  const files = fs.readdirSync(dir).filter(f => /^\d+\.json$/.test(f)).sort();
  const players = new Map();
  let games = 0, shots = 0, skipped = 0, noArea = 0;
  for (const f of files) {
    let j;
    try { j = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); } catch { skipped++; continue; }
    const actions = j?.data?.game?.actions ?? j?.game?.actions;
    if (!Array.isArray(actions)) { skipped++; continue; }
    games++;
    for (const a of actions) {
      if (a.isFieldGoal !== 1) continue;
      const z = zoneOf(a);
      if (!z) { if (a.actionType === '2pt') noArea++; continue; }
      const id = a.personId;
      if (!id) continue;
      let rec = players.get(id);
      if (!rec) players.set(id, rec = { name: a.playerNameI || a.playerName || String(id),
        short: [0, 0, 0], mid: [0, 0, 0], long: [0, 0, 0] });
      const t = rec[z];
      t[0]++; shots++;
      if (a.shotResult === 'Made') { t[1]++; if (a.assistPersonId) t[2]++; }
    }
  }
  out[season] = { games, shots, skippedFiles: skipped, unclassified2pt: noArea,
    players: Object.fromEntries([...players].map(([id, r]) => [id, r])) };
  console.log(JSON.stringify({ season, games, shots, players: players.size, skipped, unclassified2pt: noArea }));
}
const dest = 'reports/ovr-v55-finisher-fix-2025-26/assist-zones.json';
fs.writeFileSync(dest, JSON.stringify(out));
console.log('wrote ' + dest + ' ' + (fs.statSync(dest).size / 1e6).toFixed(2) + ' MB');
