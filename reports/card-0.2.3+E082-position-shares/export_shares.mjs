// 匯出 protocol.mjs 的 roles（先發秒數）。從 repo 根目錄執行：node reports/card-0.2.3+E082-position-shares/export_shares.mjs
import fs from 'node:fs';
import {positionalInputs} from '../ovr-2025-26-positional/protocol.mjs';
const x=positionalInputs();
const q=s=>/[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
const lines=['playerId,name,s_PG,s_SG,s_SF,s_PF,s_C,starts,lowConfidence'];
for(const r of x.roles)lines.push([r.playerId,q(r.name),...r.secondsBySlot,r.starts,r.lowConfidence?1:0].join(','));
fs.writeFileSync('reports/card-0.2.3+E082-position-shares/pos-shares.csv',lines.join('\n')+'\n');
console.log(x.roles.length,JSON.stringify(x.roleAudit));
