// node reports/card-0.1.2+E065-inout-wins/analyze-demo.mjs -> demo.md
import fs from 'node:fs';
const dir='reports/card-0.1.2+E065-inout-wins',arms=JSON.parse(fs.readFileSync(dir+'/demo-arms.json','utf8'));
const rows=fs.readFileSync(dir+'/checkpoint-demo.jsonl','utf8').trim().split('\n').map(l=>JSON.parse(l));
const by=new Map();for(const r of rows){const k=r.armId;(by.get(k)||by.set(k,new Map()).get(k)).set(r.seed,r);}
const T=(r,id)=>r.teams.find(t=>t.id===id),mean=a=>a.reduce((s,v)=>s+v,0)/a.length,sd=a=>{const m=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-m)**2,0)/(a.length-1));};
const base=by.get('base'),seeds=arms.seeds,med=arms.medianTeam.id;
const name=id=>base.get(seeds[0]).teams.find(t=>t.id===id).name;
function delta(armId,teamId){const a=by.get(armId),w=[],m=[];for(const s of seeds){const x=T(a.get(s),teamId),y=T(base.get(s),teamId);w.push(x.wins-y.wins);m.push(((x.pts-x.opp)-(y.pts-y.opp))/x.games);}
 return {w:mean(w),wse:sd(w)/Math.sqrt(w.length),m:mean(m),mse:sd(m)/Math.sqrt(m.length),n:w.length};}
const f=(v,d=1)=>(v>=0?'+':'')+v.toFixed(d);
let md=`# E-065 示範（不作判準）：季模擬進出勝場差\n\n- 季模擬：2025-26 完整賽程 1230 場，v53 引擎（rotation-space，每名球員帶 tovNonSteal 係數，同 \`reports/player-impact-v53-team/worker.mjs\`），\`observedLineup\` 輪替。\n- 種子（所有組別共用，配對）：${seeds.join(', ')}（共 ${seeds.length} 個）。基準組 ${base.size} 次，其餘每組 ${seeds.length} 次，合計 ${rows.length} 次季模擬。\n- 中位勝場球隊：${name(med)}（基準組 ${seeds.length} 種子平均 ${arms.medianTeam.meanWins} 勝，30 隊排第 15；規則：平均勝場排名第 15、不得是示範球員的原隊）。\n- 差值＝該組 − 基準組（同種子），顯示平均 ± 標準誤（${seeds.length} 個種子間）。淨分差/場＝(得分−失分)/場數。\n\n## 移除（原隊少了他）\n\n| 球員 | 原隊 | 移除後勝場差 | 淨分差/場差 | 套用資訊 |\n|---|---|---|---|---|\n`;
const info={};
for(const p of arms.players){
 const d=delta('remove:'+p.name,p.teamId),ap=by.get('remove:'+p.name).get(seeds[0]).applied;
 md+=`| ${p.name} | ${p.teamName} | ${f(d.w)} ± ${d.wse.toFixed(1)} | ${f(d.m,2)} ± ${d.mse.toFixed(2)} | 移除 ${ap.games} 場（其中先發 ${ap.starts} 場） |\n`;
}
md+=`\n## 加入${name(med)}（中位勝場隊）\n\n| 球員 | 加入後 ${name(med)} 勝場差 | 淨分差/場差 | 原隊同時少他的勝場差 | 套用資訊 |\n|---|---|---|---|---|\n`;
for(const p of arms.players){
 const d=delta('add:'+p.name,med),h=delta('add:'+p.name,p.teamId),ap=by.get('add:'+p.name).get(seeds[0]).applied;
 md+=`| ${p.name} | ${f(d.w)} ± ${d.wse.toFixed(1)} | ${f(d.m,2)} ± ${d.mse.toFixed(2)} | ${f(h.w)} ± ${h.wse.toFixed(1)}（僅與${name(med)}對戰的場次受影響） | ${ap.games} 場；他在原隊平均 ${(ap.meanSeconds/60).toFixed(1)} 分（出賽 ${ap.appearances} 場）${ap.starter?'，先發':'，替補'} |\n`;
}
md+=`
## 方法與限制

- 移除：從該隊每場的 \`homePlayerIds/awayPlayerIds\` 與官方 box 拿掉他；若他是先發，該場出賽秒數最多的替補遞補先發並承接他的官方位置。其餘球員的觀測秒數由 \`observedLineup\` 依比例重標到 14400 秒（單人上限 2880 秒）——即現有輪替規則下的分鐘重分配，沒有手調。
- 加入：複製他的球員資料到中位隊，該隊每一場（82 場，等於全勤）都加入他；觀測秒數＝他在原隊出賽場次的平均秒數；若他原隊先發比例 ≥50%，則取代該場該隊秒數最少的先發，否則為替補（官方位置取他最常見者，替補多半無位置）。其餘人同樣由 \`observedLineup\` 比例重標。他留在原隊（複製），只有與中位隊的直接對戰場，他只算在中位隊那邊（原隊那場拿掉他）。
- 「全勤」與「全季平均分鐘」是示範的簡化，實際出賽場次（如 Caruso 56 場）被忽略；與移除組（只拿掉他實際出賽的場次）不對稱。
- 季模擬的隨機種子依「場次序號」配對，但輪替改變後亂數消耗不同，配對只在賽程層級有效；${seeds.length} 個種子的標準誤約 1 勝，只能看大方向，不是量測。
- 這是示範，不是判準；不拿來調任何參數。
`;
fs.writeFileSync(dir+'/demo.md',md);console.log(md);
