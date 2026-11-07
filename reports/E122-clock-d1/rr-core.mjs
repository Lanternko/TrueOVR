// E-122 30-team round robin (t1 + calibration). One game per team pair per seed, using E-065 opponentTeam() for both sides.
import {loadX, makeRunner} from './winimp-core-e122.mjs';
import {opponentTeam, options} from '../player-impact-v29/benchmark.mjs';
export {loadX, makeRunner};
// Returns per-game records. pair (a<b); orientation (who is team A) and rotation phase alternate by seed parity.
export function playSeed({run,src},x,seed,pairs){
  const out=[];
  for(const [a,b] of pairs){
    const phase=(seed+a+b)&1, swap=((seed>>>1)+a)&1;
    const ta=opponentTeam(x,x.opponents[a],src.capMinutes,phase), tb=opponentTeam(x,x.opponents[b],src.capMinutes,phase);
    const gseed=(seed+Math.imul(a*30+b,1000003))>>>0;
    const teams=swap?[tb.team,ta.team]:[ta.team,tb.team], schedules=swap?[tb.schedule,ta.schedule]:[ta.schedule,tb.schedule];
    // per side counters: oreb,dreb,sc (second-chance pts), rimA,rimM (shots taken by side), pts
    const c=[{oreb:0,dreb:0,toreb:0,tdreb:0,sc:0,rimA:0,rimM:0,poss:0},{oreb:0,dreb:0,toreb:0,tdreb:0,sc:0,rimA:0,rimM:0,poss:0}];let scFlag=[false,false];
    const eventObserver=e=>{
      const t=e.type,s=e.off;
      if(t==='POSSESSION'){scFlag=[false,false];c[s].poss++;}
      else if(t==='OREB'||t==='TEAM_OREB'){c[s].oreb++;if(t==='TEAM_OREB')c[s].toreb++;scFlag[s]=true;}
      else if(t==='DREB'||t==='TEAM_DREB'){c[s].dreb++;if(t==='TEAM_DREB')c[s].tdreb++;}
      else if(t==='FGM'||t==='FGX'){
        if(e.zone==='short'){c[s].rimA++;if(t==='FGM')c[s].rimM++;}
        if(t==='FGM'&&scFlag[s])c[s].sc+=e.points;
      }else if(t==='FTM'&&scFlag[s])c[s].sc+=1;
    };
    const g=run(...teams,{...options(x,gseed,schedules),eventObserver});
    if(g.gameSeconds!==2880||!g.complete)throw Error('Incomplete game');
    const ia=swap?1:0, ib=1-ia; // index of team a / b in the game
    const sc=[g.scoreA,g.scoreB];
    out.push({seed,a,b,ptsA:sc[ia],ptsB:sc[ib],
      orebA:c[ia].oreb,orebB:c[ib].oreb,torebA:c[ia].toreb,torebB:c[ib].toreb,tdrebA:c[ia].tdreb,tdrebB:c[ib].tdreb,drebA:c[ia].dreb,drebB:c[ib].dreb,
      possA:c[ia].poss,possB:c[ib].poss,scA:c[ia].sc,scB:c[ib].sc,rimAttA:c[ia].rimA,rimMadeA:c[ia].rimM,rimAttB:c[ib].rimA,rimMadeB:c[ib].rimM});
  }
  return out;
}
export const allPairs=n=>{const p=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)p.push([a,b]);return p;};
