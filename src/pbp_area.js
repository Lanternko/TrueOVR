// 2026-27 起 cdn liveData pbp 的投籃動作拿掉 area／areaDetail（2021-22 本機檔也沒有），
// defense_pbp_analysis.realFactorEvent 用 /Restricted Area|In The Paint/ 分近射，於是整季 shortA=0、全落到 midA。
// 只在「整場投籃都沒有 area」時補，有 area 的場次（2022-23～2025-26）一個位元都不動。
// 補法：二分球用官方 qualifier 'pointsinthepaint'（2025-26 有 area 的 11.6 萬球排除 (0,0) 座標後，
// 和 area 的近射／中距二分 0 誤差；(0,0) 座標的上籃灌籃官方 area 有四成標成 Mid-Range，是官方缺座標的預設值，
// qualifier 全標禁區，照 qualifier）。RA／非 RA 與三分角落只影響原始分區名稱，用座標（xLegacy/yLegacy，1/10 呎）。
const isFieldGoal=e=>['2pt','3pt'].includes(e.actionType)&&e.isFieldGoal;
export function deriveArea(e){
  const x=e.xLegacy??0,y=e.yLegacy??0;
  if(e.actionType==='3pt')return y>=470?'Backcourt':Math.abs(x)>=210&&y<=90?(x<0?'Left Corner 3':'Right Corner 3'):'Above the Break 3';
  if(!(e.qualifiers??[]).includes('pointsinthepaint'))return 'Mid-Range';
  return Math.hypot(x,y)<=40?'Restricted Area':'In The Paint (Non-RA)';
}
export function fillMissingAreas(actions){
  const shots=actions.filter(isFieldGoal);
  if(!shots.length||shots.some(e=>e.area))return actions;
  for(const e of shots){e.area=deriveArea(e);e.areaDerived=true;}
  return actions;
}
