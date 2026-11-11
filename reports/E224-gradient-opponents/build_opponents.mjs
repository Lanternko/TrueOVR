// 把 B5／A5 的對手組成寫成記錄檔（work/opp-<key>.json）：球員三人組、位置、目標 OVR、備註。用法（repo 根）：node reports/E224-gradient-opponents/build_opponents.mjs
import fs from 'node:fs';
import {buildOpponents, readLadder} from './e224_opp.mjs';
for (const [key, variant, libf] of [['2425', 'Q', '../E208-team-rating/lib2425.mjs'], ['2526', 'P', '../E208-team-rating/lib.mjs']]) {
  const lib = await import(libf), L = await lib.setup(variant), lad = readLadder(key), out = {key, variant};
  for (const mode of ['B5', 'A5']) {
    const {teams, notes} = buildOpponents(L, lad, mode, key);
    out[mode] = {teams: teams.map(t => ({name: t.name, slots: t.slots})), notes};
    console.log(key, mode, 'short', notes.short.length, 'noProfile', notes.noProfile.length, 'posMismatch', notes.posMismatch.length);
  }
  fs.writeFileSync(new URL(`./work/opp-${key}.json`, import.meta.url), JSON.stringify(out, null, 1));
}
