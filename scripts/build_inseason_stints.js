// 賽中 defenseBonus（2026-10-30 使用者）：把本季已賽場次做成 stints，供 live/rookie_defense.py 的 E-104 滑動窗口擬合。
// 沿用稽核過的整季程式，只在記憶體裡拿掉「必須 1230 場」的檢查：
//   fetch_defense_seventh_season.js → league.json、boxes/、game-exposure.json、manifest.json（box／pbp 已抓過的不重抓）
//   prepare_defense_b1.js（同 prepare_defense_seventh_season.js 的路徑替換）→ reports/defense-seventh/<季>/stints/stints.jsonl
// 不跑 validate_defense_stints（要求整季）和 stint-zones（擬合用不到）。
// 用法：node scripts/build_inseason_stints.js [2026-27]
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const season=process.argv[2]??'2026-27',data=`data/defense-seventh/${season}`,report=`reports/defense-seventh/${season}/stints`;
fs.mkdirSync(report,{recursive:true});
const run=(name,edits,must)=>{
  let source=fs.readFileSync('scripts/'+name+'.js','utf8');
  for(const[a,b]of edits){if(must.includes(a)&&!source.includes(a))throw Error(name+': anchor missing '+a);source=source.replaceAll(a,b);}
  const file='scripts/.inseason-'+season+'-'+name+'.js';fs.writeFileSync(file,source);
  try{execFileSync(process.execPath,[file,season],{stdio:'inherit',windowsHide:true});}finally{fs.rmSync(file,{force:true});}
};
run('fetch_defense_seventh_season',[["if(schedule.length!==1230)throw Error('Expected 1230 regular-season games');",'']],["if(schedule.length!==1230)throw Error('Expected 1230 regular-season games');"]);
run('prepare_defense_b1',Object.entries({'data/defense-a-source/pbp/':data+'/pbp/','data/defense-a-source/manifest.json':data+'/manifest.json',
  'data/defense-source/game-exposure.json':data+'/game-exposure.json','data/season-source/team-games.json':data+'/team-games.json',
  'data/season-league.json':data+'/league.json',"'reports/defense-b1'":`'${report}'`}),["'reports/defense-b1'"]);
