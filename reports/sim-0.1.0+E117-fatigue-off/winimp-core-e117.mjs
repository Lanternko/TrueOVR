// E-117 WinImp core: identical to E-065 winimp-core.mjs (imported unchanged) except the engine run() can stamp fatigue:false.
import {loadX, computeDraws, averageProfiles} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
import {impactEngine} from './engine-e117.mjs';
export {loadX, computeDraws, averageProfiles};
export async function makeRunner(fatigue = true) {
  const run = await impactEngine('rotation-space', {game: true, fatigue}), src = source();
  return {src, run};
}
