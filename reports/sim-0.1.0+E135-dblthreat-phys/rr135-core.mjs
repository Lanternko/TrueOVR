// E-135 m1: 30-team round robin (pattern of E-117 rr-core.mjs), engine/input from winimp-core-135.mjs (ch1 on/off).
// Records per game: team points, plus per-player on-court teammate FG (player-impact-v1 on-court.mjs collector, unchanged).
import {loadX, makeRunner} from './winimp-core-135.mjs';
import {opponentTeam, options} from '../player-impact-v29/benchmark.mjs';
import {onCourtCollector} from '../player-impact-v1/on-court.mjs';
export {loadX, makeRunner};
export const allPairs=n=>{const p=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)p.push([a,b]);return p;};
export function playSeed({run,src},x,seed,pairs){
  const games=[],col=onCourtCollector();
  for(const [a,b] of pairs){
    const phase=(seed+a+b)&1, swap=((seed>>>1)+a)&1;
    const ta=opponentTeam(x,x.opponents[a],src.capMinutes,phase), tb=opponentTeam(x,x.opponents[b],src.capMinutes,phase);
    const gseed=(seed+Math.imul(a*30+b,1000003))>>>0;
    const teams=swap?[tb.team,ta.team]:[ta.team,tb.team], schedules=swap?[tb.schedule,ta.schedule]:[ta.schedule,tb.schedule];
    let seen=0;
    const g=run(...teams,{...options(x,gseed,schedules),onCourtObserver:e=>{seen++;col.event(e);}});
    if(g.gameSeconds!==2880||!g.complete)throw Error('Incomplete game');
    if(!seen)throw Error('onCourtObserver never called');
    const ia=swap?1:0, ib=1-ia, sc=[g.scoreA,g.scoreB];
    games.push({a,b,ptsA:sc[ia],ptsB:sc[ib]});
  }
  const oc=col.finish();
  return {seed,games,onCourt:oc.players.map(p=>({id:p.playerId,teammates:p.teammates,own:p.own})),nGames:oc.games};
}
