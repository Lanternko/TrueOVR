// v55 修正 B：從 play-by-play 建立「餵球 / 自主」出手分割。
//
// 為什麼要兩階段：NBA play-by-play 只在**命中**的球上記助攻，所以「被助攻的出手」本身
// 不可觀測。但 descriptor / subType（cutting、alley-oop、driving、pullup、step back…）
// 在命中與未命中兩邊都有，所以可以先用聯盟層級算出每一類的「命中球被助攻比例」q_k，
// 再把 q_k > 0.5 的類別整類判為「餵球」、其餘判為「自主」。這是出手層級的硬分割：
// 每一球的歸屬只看它自己的動作類型，不看它有沒有進，因此命中率可以直接觀測、無偏。
//
// 禁區的 putback / tip 另外計數並從分割中剔除：模擬器的補籃走的是 syntheticProbability
// 另一條路，不吃 centeredMake，也不會吃 v55 的原生分割調整。
//
//   node reports/ovr-v55-finisher-fix-2025-26/prepare-origin.mjs
// 輸出 reports/ovr-v55-finisher-fix-2025-26/shot-origin.json
import fs from 'node:fs';
const SEASONS={
 '2025-26':'data/defense-a-source/pbp',
 '2024-25':'data/defense-seventh/2024-25/pbp',
 '2023-24':'data/defense-seventh/2023-24/pbp',
 '2022-23':'data/defense-seventh/2022-23/pbp',
};
// 傳統座標，單位 0.1 英尺，籃框在 (0,0)。幾何分類比 live feed 的 area 字串準：
// 禁區出手數 106285 對官方 dashboard 的 106161（+0.12%），area 字串只有 103349（-2.65%）。
function zoneOf(a){
 if(a.actionType==='3pt')return 'long';
 if(a.actionType!=='2pt')return null;
 const x=a.xLegacy,y=a.yLegacy;
 if(!Number.isFinite(x)||!Number.isFinite(y))return null;
 if(Math.hypot(x,y)<=40)return 'short';
 if(Math.abs(x)<=80&&y<=142.5&&y>=-47.5)return 'short';
 return 'mid';
}
const PUTBACK=new Set(['putback','tip']);
const out={seasons:{},classTables:{}};
for(const [season,dir] of Object.entries(SEASONS)){
 const files=fs.readdirSync(dir).filter(f=>f.endsWith('.json'));
 const recs=[];let games=0;
 for(const f of files){
  const j=JSON.parse(fs.readFileSync(`${dir}/${f}`,'utf8'));
  const actions=j?.data?.game?.actions??j?.game?.actions;
  if(!Array.isArray(actions))continue;
  games++;
  for(const a of actions){
   if(a.isFieldGoal!==1)continue;
   const z=zoneOf(a);if(!z)continue;
   const d=(a.descriptor??'').trim().toLowerCase(),st=(a.subType??'').trim().toLowerCase();
   recs.push([a.personId,z,z==='short'&&PUTBACK.has(d)?'__putback__':d+'|'+st,a.shotResult==='Made'?1:0,a.assistPersonId?1:0]);
  }
 }
 // 第一階段：聯盟層級的類別助攻傾向 q_k（只看命中球）。
 const cls=new Map();
 for(const [,z,k,made,ast] of recs){
  if(k==='__putback__')continue;
  const key=z+'#'+k,c=cls.get(key)??[0,0,0];c[0]++;if(made){c[1]++;c[2]+=ast;}cls.set(key,c);
 }
 // 樣本太少（命中球 < 30）的類別不自行判定，退回同區聯盟平均傾向。
 const zoneAst={};
 for(const z of ['long','mid','short']){let m=0,a=0;for(const [key,c] of cls){if(key.startsWith(z+'#')){m+=c[1];a+=c[2];}}zoneAst[z]=m?a/m:0;}
 const fed=new Map(),table=[];
 for(const [key,c] of cls){
  const q=c[1]>=30?c[2]/c[1]:zoneAst[key.split('#')[0]];
  fed.set(key,q>0.5);
  table.push({key,attempts:c[0],makes:c[1],astOfMakes:+(c[1]?c[2]/c[1]:0).toFixed(4),q:+q.toFixed(4),fed:q>0.5});
 }
 table.sort((a,b)=>b.attempts-a.attempts);
 out.classTables[season]={zoneAstOfMakes:zoneAst,classes:table};
 // 第二階段：逐球員逐區的硬分割。
 const players=new Map();
 const blank=()=>({fedA:0,fedM:0,selfA:0,selfM:0,putA:0,putM:0});
 for(const [pid,z,k,made] of recs){
  let p=players.get(pid);if(!p){p={long:blank(),mid:blank(),short:blank()};players.set(pid,p);}
  const t=p[z];
  if(k==='__putback__'){t.putA++;if(made)t.putM++;continue;}
  if(fed.get(z+'#'+k)){t.fedA++;if(made)t.fedM++;}else{t.selfA++;if(made)t.selfM++;}
 }
 out.seasons[season]={games,shots:recs.length,players:Object.fromEntries(players)};
 const tot=['long','mid','short'].map(z=>{let f=0,s=0,fm=0,sm=0,pa=0;for(const p of players.values()){f+=p[z].fedA;fm+=p[z].fedM;s+=p[z].selfA;sm+=p[z].selfM;pa+=p[z].putA;}
  return {zone:z,fedA:f,fedPct:+(fm/f).toFixed(4),selfA:s,selfPct:+(sm/s).toFixed(4),gap:+(fm/f-sm/s).toFixed(4),fedShare:+(f/(f+s)).toFixed(4),putbackA:pa};});
 out.seasons[season].league=tot;
 console.log(season,games,'games',recs.length,'shots',players.size,'players');
 console.log(JSON.stringify(tot));
}
fs.writeFileSync('reports/ovr-v55-finisher-fix-2025-26/shot-origin.json',JSON.stringify(out));
console.log('wrote shot-origin.json',(fs.statSync('reports/ovr-v55-finisher-fix-2025-26/shot-origin.json').size/1048576).toFixed(2),'MB');
