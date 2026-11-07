// sim 0.1.1 gate p1: doubleThreat physique term removed (R-089, E-135 ch1 made permanent).
// ref = pre-edit 0.1.1 src + E-086 ch1 loader hook (flag on); new = edited src, no hook. Both must be bit-identical.
// usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/p1.mjs <out.json> ref|new   (cwd = tree root)
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const mode = process.argv[3];
if (mode === 'ref') { const {registerE086} = await import('../sim-0.1.0+E086-param-screen/boot.mjs'); registerE086(); globalThis.__E086 = Object.freeze({ch1: true}); }
else if (mode !== 'new') throw Error('mode ref|new');
const {engine} = await import('./common.mjs');
const {loadX, playSeed, allPairs} = await import('../sim-0.1.0+E117-fatigue-off/rr-core.mjs');
const {source} = await import('../player-impact-v29/benchmark.mjs');
const M = await import('../../src/probability_model.js');
const run = await engine('new'), src = source(), {x} = await loadX();
const dt = x.players.map(p => [p.playerId, M.doubleThreat(p)]);
const recs = [];
for (const seed of [20261031, 20261032]) recs.push(...playSeed({run, src}, x, seed, allPairs(x.opponents.length).slice(0, 30)));
// WinImp (avg variant) for 3 of the E-065 g0 players, 2 samples x 30 opponents: ch1 moves the league-average teammate profiles here.
const W = await import('../card-0.1.2+E065-inout-wins/winimp-core.mjs');
const X = await W.loadX(), seeds = JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json', 'utf8'));
const ids = fs.readFileSync('reports/sim-0.1.0+E117-fatigue-off/g0-on.jsonl', 'utf8').trim().split('\n').slice(0, 3).map(l => JSON.parse(l).id);
const wi = ids.map(id => W.computeDraws({src, run}, X, {id, seed: seeds.baseSeed, samples: 2}, 'avg'));
const h = o => createHash('sha256').update(JSON.stringify(o)).digest('hex');
const out = {mode, players: dt.length, doubleThreatSha: h(dt), games: recs.length, gamesSha: h(recs), perGame: recs.map(h), winimpSha: h(wi), winimpCells: wi.map(a => a.draws.map(h))};
fs.writeFileSync(process.argv[2], JSON.stringify(out));
console.log(JSON.stringify({mode, players: out.players, doubleThreatSha: out.doubleThreatSha, games: out.games, gamesSha: out.gamesSha, winimpSha: out.winimpSha}));
