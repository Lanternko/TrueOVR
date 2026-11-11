import fs from 'fs';
import { TEAMS, BASELINE } from './src/teams.js';
import { monteCarlo, simulateGame } from './src/simulation_engine.js';
const A=['long','mid','short','ft','drive','pass','tovSkill','rebound','onBall','help','stamina','physique','offBall','screen','handle','breakDbl'];
const H=['三分','中投','近射','罰球','切入','傳球','失誤','籃板','盯防','護框','體力','肉體','無球','擋拆','持球','破包夾'];
const OPTS={mode:'race',targetScore:21,winBy:1};
let o=[];
for(const [k,T] of Object.entries(TEAMS)){
  o.push(`## ${T.name}`,'');
  o.push('| 球員 | '+H.join(' | ')+' |','|---|'+H.map(()=>'---').join('|')+'|');
  for(const p of T.roster) o.push(`| ${p.note?'**'+p.name+'**':p.name} | `+A.map(a=>p[a]).join(' | ')+' |');
  const n=T.roster.filter(p=>p.note);
  if(n.length){o.push('');for(const p of n)o.push(`- **${p.name}**：${p.note}`);}
  o.push('');
}
o.push('## 模擬結果（先到 21 分，n=4000）','','### 對 PR50 基準隊','');
o.push('| 隊伍 | 勝率 | 平均比分 | eFG% | 近射 | 中投 | 三分 |','|---|---|---|---|---|---|---|');
for(const k of Object.keys(TEAMS)){const r=monteCarlo(TEAMS[k],BASELINE,4000,OPTS),s=r.statA,w=r.winRateA+r.tieRate/2;
 o.push(`| ${TEAMS[k].name} | ${(w*100).toFixed(1)}% | ${r.avgScoreA.toFixed(1)} - ${r.avgScoreB.toFixed(1)} | ${s.efg.toFixed(3)} | ${s.shortRate.toFixed(3)} | ${s.midRate.toFixed(3)} | ${s.longRate.toFixed(3)} |`);}
o.push('');
const tab={},keys=Object.keys(TEAMS); for(const k of keys)tab[k]=0;
for(let i=0;i<keys.length;i++)for(let j=i+1;j<keys.length;j++){
 const r=monteCarlo(TEAMS[keys[i]],TEAMS[keys[j]],4000,OPTS),w=r.winRateA+r.tieRate/2;
 tab[keys[i]]+=w; tab[keys[j]]+=1-w;}
o.push('### 五隊循環賽','','| 排名 | 隊伍 | 期望勝場 / 4 |','|---|---|---|');
keys.slice().sort((a,b)=>tab[b]-tab[a]).forEach((k,i)=>o.push(`| ${i+1} | ${TEAMS[k].name} | ${tab[k].toFixed(2)} |`));
o.push('','### 球權分布（對 PR50 基準隊）','','| 隊伍 | 球員（球權%） |','|---|---|');
for(const k of keys){const c=new Map(TEAMS[k].roster.map(p=>[p.name,0]));let t=0;
 for(let i=0;i<1200;i++){const g=simulateGame(TEAMS[k],BASELINE,{...OPTS,seed:i*7919});
  for(const e of g.log) if(e.off===0){c.set(e.handler,c.get(e.handler)+1);t++;}}
 o.push(`| ${TEAMS[k].name} | `+[...c.entries()].sort((a,b)=>b[1]-a[1]).map(([n,v])=>`${n.split(' ').slice(-1)[0]} ${(100*v/t).toFixed(0)}%`).join('、')+' |');}
o.push('');
const DOC='docs/隊伍卡表.md';
const B='<!-- BEGIN GENERATED', E='<!-- END GENERATED -->';
const doc=fs.readFileSync(DOC,'utf8').split(/\r?\n/);
const bi=doc.findIndex(l=>l.startsWith(B)), ei=doc.findIndex(l=>l.startsWith(E));
if(bi<0||ei<0) throw new Error(DOC+' 找不到 BEGIN/END GENERATED 標記');
fs.writeFileSync(DOC,[...doc.slice(0,bi+1),...o,...doc.slice(ei)].join('\n'));
console.log(DOC+' 已更新（生成 '+o.length+' 行）');
