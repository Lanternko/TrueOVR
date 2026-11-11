// v55 修正 B 的 OVR 板 input：v54 input（v53 engine + v54 卡片）再加上
//   B1 = 禁區出手來源修正（src/source_shot_origin.js）
//   B2 = shootingMeasurement.rates 的可靠度收縮（./rates-reliability.mjs，K=200）
// mode: 'v54'（原樣，平行性檢查用）| 'B1' | 'B2' | 'B12' | 'B12_oos'
import fs from 'node:fs';
import {ovrInput as v54Input, pressureCoefficients, spreadScale} from '../ovr-v54-2025-26/input.mjs';
import {shotOriginTables, attachShotOrigin} from '../../src/source_shot_origin.js';
import {applyRatesReliability} from './rates-reliability.mjs';
export {pressureCoefficients, spreadScale};
const DIR='reports/ovr-v55-finisher-fix-2025-26';
export const RELIABILITY_K=200;                       // 預先登錄主值
export const OOS_SEASONS=['2022-23','2023-24','2024-25'];
const read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
let originCache=null;
export function originTablesFor(mode){
 originCache??=read(`${DIR}/shot-origin.json`);
 return shotOriginTables(originCache,mode==='B12_oos'?OOS_SEASONS:['2025-26']);
}
/** 校正跑算出來的聯盟水準常數 c；還沒校正時回 0。
 *  預先登錄：c 是**單一個**聯盟水準常數，四季、四個變體共用同一個值（calibrate-center.mjs
 *  在 2025-26 球隊層跑一顆種子定出來後凍結）。所以這裡只讀 center.json 的 `center` 欄位，
 *  不分 mode。 */
export function centerFor(mode){
 const f=`${DIR}/center.json`;
 if(!fs.existsSync(f))return 0;
 const j=read(f);
 if(!Number.isFinite(j.center))throw Error('center.json has no frozen center');
 return j.center;
}
export const MODES={
 v54:{origin:false,rates:false},
 B1:{origin:true,rates:false},
 B2:{origin:false,rates:true},
 B12:{origin:true,rates:true},
 B12_oos:{origin:true,rates:true},
};
export function applyV55(players,mode,opts={}){
 const m=MODES[mode];
 if(!m)throw Error('Unknown v55 mode '+mode);
 const info={mode};
 if(m.rates)info.rates=applyRatesReliability(players,'2025-26',opts.K??RELIABILITY_K);
 if(m.origin){
  const tables=opts.tables??originTablesFor(mode);
  info.origin=attachShotOrigin(players,tables,{center:opts.center??centerFor(mode)});
  info.tables={seasons:tables.seasons,league:tables.league,eb:tables.eb};
 }
 return info;
}
export async function ovrInput(variant,mode=process.env.V55_MODE??'B12',opts={}){
 const x=await v54Input(variant);
 const all=[...x.players,...x.opponents.flatMap(t=>t.roster)];
 x.v55=applyV55(all,mode,opts);
 return x;
}
