// sim 0.1.1 verification helper. mode 'old' = start-HEAD engine, every game's options get fatigue:false stamped LAST (same trick as E-117 engine-e117.mjs);
// mode 'new' = fatigue-removed engine, options pass through unchanged (no fatigue key). Run with cwd = a tree root and node --preserve-symlinks --preserve-symlinks-main.
import {impactEngine as v53} from '../player-impact-v53/engine.mjs';
export async function engine(mode) {
  if (mode !== 'old' && mode !== 'new') throw Error('mode old|new');
  const inner = await v53('rotation-space', {game: true});
  if (mode === 'new') return inner;
  const run = (...a) => { const o = a[a.length - 1]; a[a.length - 1] = {...o, fatigue: false}; return inner(...a); };
  return Object.assign(run, inner);
}
