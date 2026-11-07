// E-117 p0 loader hook (probe only): counts applyStamina calls and records max fatigue argument (= 1 - energy). Does not alter arithmetic.
const FROM='export function applyStamina(player, fatigue) {';
const TO=FROM+' globalThis.__P0.calls++; if(fatigue>globalThis.__P0.maxFatigue)globalThis.__P0.maxFatigue=fatigue;';
export async function load(url, context, nextLoad) {
  const r = await nextLoad(url, context);
  if (url.startsWith('file:') && url.endsWith('/src/probability_model.js')) {
    const s = Buffer.from(r.source).toString('utf8'); if (s.split(FROM).length !== 2) throw Error('applyStamina anchor drift');
    return {...r, source: s.replace(FROM, TO), shortCircuit: true};
  }
  return r;
}
