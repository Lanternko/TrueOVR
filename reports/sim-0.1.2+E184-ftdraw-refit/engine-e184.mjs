// E-184 (amendment A1): v53 impactEngine + shooter foul-draw exponent a (harness only, src untouched). Copy of
// reports/player-impact-v53/engine.mjs with one extra game-source pair, wrapped like E-140 engine-e140.
// The harness draws shooting fouls from player-impact-v5 observedFoulInputs, which solves a per-player multiplier so expected
// FTA/FGA == r (input shotProfile.freeThrowsPerAttempt). With opt.foulDrawExponent = a that target becomes L*(r/L)^a,
// L = opt.leagueFTR, for the shot-level foul draw only (touch-level pFoul keeps r). No random numbers are read.
// a absent/1 stamps nothing -> identical to the E-140/E-166 harness.
import fs from 'node:fs';
const cache = new Map();
async function v53draw(version, options = {}) {
  const key = JSON.stringify([version, options]); if (cache.has(key)) return cache.get(key);
  let s = fs.readFileSync('reports/player-impact-v47/engine.mjs', 'utf8');
  const from = "url('reports/player-impact-v47/model.mjs')", to = "url('reports/player-impact-v53/model.mjs')";
  if (s.split(from).length !== 2) throw Error('v53 model anchor drift');
  s = s.replace(from, to);
  const luck = [
    ['made=rng()<foulInputs[zone].raw;', '{const drawP=foulInputs[zone].raw;made=rng()<drawP;if(opt.luckLedger)opt.luckLedger[off]+=((made?1:0)-drawP)*points;}'],
    ['made=rng()<(opt.foulConditioning?attemptMakeProbability(p.make[zone],shootingFoulChance):p.make[zone]);',
     '{const drawP=(opt.foulConditioning?attemptMakeProbability(p.make[zone],shootingFoulChance):p.make[zone]);made=rng()<drawP;if(opt.luckLedger)opt.luckLedger[off]+=((made?1:0)-drawP)*points;}'],
    ["record(off,shooter,'fta'); made=rng()<pct;", "record(off,shooter,'fta'); made=rng()<pct;if(opt.luckLedger)opt.luckLedger[off]+=(made?1:0)-pct;"],
    ['const made=rng()<pct;', 'const made=rng()<pct;if(opt.luckLedger)opt.luckLedger[off]+=(made?1:0)-pct;'],
    // E-184 A1: foul-draw exponent on the observedFoulInputs target.
    ['const foulInputs=observedFoulInputs(p,ls[off][hi],opt,attemptMakeProbability);',
     'const foulInputs=observedFoulInputs(p,opt.foulDrawExponent?{...ls[off][hi],shotProfile:{...ls[off][hi].shotProfile,freeThrowsPerAttempt:opt.leagueFTR*(ls[off][hi].shotProfile.freeThrowsPerAttempt/opt.leagueFTR)**opt.foulDrawExponent}}:ls[off][hi],opt,attemptMakeProbability);'],
  ];
  const listAnchor = ' const changes=[\n';
  if (s.split(listAnchor).length !== 2) throw Error('v53 luck anchor drift');
  s = s.replace(listAnchor, listAnchor + luck.map(([a, b]) => `  [${JSON.stringify(a)},${JSON.stringify(b)}],\n`).join(''));
  const mod = await import('data:text/javascript;base64,' + Buffer.from(s).toString('base64'));
  const run = await mod.impactEngine(version, options); cache.set(key, run); return run;
}
export async function impactEngine(version, options = {}) {
  const {foulBeta = null, c = 0, pace = 1, a: fd = 1, ...rest} = options;
  const inner = await v53draw(version, rest);
  const run = (...args) => {
    const o = args[args.length - 1], add = {fatigue: false};
    if (foulBeta) { add.defenderFoulBeta = foulBeta; add.foulBaseShift = c; add.pace = o.pace * pace; if (fd !== 1) add.foulDrawExponent = fd; }
    else if (c || pace !== 1 || fd !== 1) throw Error('c/pace/a only with beta on');
    args[args.length - 1] = {...o, ...add};
    return inner(...args);
  };
  return Object.assign(run, inner);
}
