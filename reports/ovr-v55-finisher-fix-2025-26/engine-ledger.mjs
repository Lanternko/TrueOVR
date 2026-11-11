// v53 引擎 + 一個額外的 origin ledger：逐禁區出手記下「出手者 / 這球用的是接球投機率還是自主機率 / 是不是補籃」。
// 只用來校正 B1 的聯盟水準常數 c；評估跑用的是原封不動的 reports/player-impact-v53/engine.mjs。
//
// 為什麼要另開一支檔：v41/v45/v47/v53 這條字串補丁鍊沒有「外加補丁」的通用介面，而這些檔案是
// 凍結產物（改它們會動到 v53/v54 的可重現性）。所以這裡重跑 v53 engine.mjs 的patch 流程，在它
// 注入 src/timed_game.js 的 changes 清單尾端多塞一組 [from,to]。
//
// 兩個必須踩對的點（第一版都踩錯了）：
//  1. reports/player-impact-v53/engine.mjs 是 **CRLF**，錨點字串不能用 '\n'。
//  2. 「這球算不算被餵」的正確旗標是 **usedAssist**，不是 assist!==null。src/timed_game.js 的
//     best() 會比較 own=probability(i,null) 與 caught=probability(i,assist) 的 EV 取高者，
//     所以傳過球（assist!==null）不代表這球真的吃了接球投的機率。shotOriginAdjustment 收到的
//     是被選中那一支的 a，等價於 usedAssist?assist:null。
import fs from 'node:fs';
const cache = new Map();

export async function ledgerEngine(version, options = {}) {
  const key = JSON.stringify([version, options]);
  if (cache.has(key)) return cache.get(key);
  let s = fs.readFileSync('reports/player-impact-v53/engine.mjs', 'utf8');
  // v53 的 luck 陣列字面值結尾（CRLF），把我們的 pair 接在它後面，順序：
  // v41 自己的補丁 → v53 的 luck → 本檔 → v47 的 FT。
  const eol = s.includes('\r\n') ? '\r\n' : '\n';
  const tail = `'],${eol}  ];`;
  const at = s.indexOf(tail);
  if (at < 0 || s.indexOf(tail, at + 1) >= 0) throw Error('ledger: v53 luck list tail anchor drift');
  const from = "const points=zone==='long'?3:2;";
  const to = from + "if(opt.originLedger&&zone==='short'){const k=ls[off][hi].playerId*4+(usedAssist?1:0)+(putback!==null?2:0);opt.originLedger.set(k,(opt.originLedger.get(k)??0)+1);}";
  // 錨點唯一性由 v41 的 replace() 在跑的時候保證（不是剛好 1 份就丟 anchor drift）。
  const inject = `'],${eol}    [${JSON.stringify(from)},${JSON.stringify(to)}],${eol}  ];`;
  s = s.slice(0, at) + inject + s.slice(at + tail.length);
  const mod = await import('data:text/javascript;base64,' + Buffer.from(s).toString('base64'));
  const run = await mod.impactEngine(version, options);
  cache.set(key, run);
  return run;
}

// ledger key -> {playerId, assisted, putback}
export function decode(k) {
  return { playerId: Math.floor(k / 4), assisted: (k % 4) % 2 === 1, putback: k % 4 >= 2 };
}
