// E-065 demo (not a verdict): season replay (v53 flow = reports/player-impact-v53-team/worker.mjs) with a player
// removed from his own team, or cloned onto the median-wins team. Minutes are redistributed by the existing
// observedLineup rule (observed seconds of the remaining players rescaled proportionally to 14400 s, 2880 s cap).
import fs from 'node:fs';
import {loadInput} from '../player-impact-v47/input.mjs';
import {impactEngine} from '../player-impact-v53/engine.mjs';
import {pressureCoefficients} from '../ovr-v53-2025-26/input.mjs';
const SEASON='2025-26';
let run;
export async function prepare(){
 run??=await impactEngine('rotation-space');
 const b=loadInput(SEASON),coef=pressureCoefficients();
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;
 b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${SEASON}-center.json`)).fullCenter;
 for(const p of b.league.teams.flatMap(t=>t.roster)){const c=coef.get(p.playerId);if(c)p.pressureMeasurement={tovNonSteal:c.tovNonSteal};}
 return b;
}
const norm=s=>s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
export function findPlayer(b,name){
 const hits=[];for(const t of b.league.teams)for(const p of t.roster)if(norm(p.name)===norm(name))hits.push({team:t.id,teamName:t.name,player:p});
 if(hits.length!==1)throw Error('player match '+name+' -> '+hits.length);return hits[0];
}
// remove player from team's games: drop id from playerIds and from the official box; if he started, the
// highest-seconds reserve of that game takes his starter slot and official position.
function removeFrom(b,teamId,playerId,onlyGame=null){
 const games=new Map(b.exposure.games.map(g=>[g.id,g]));let n=0,starts=0;
 for(const f of b.league.schedule){
  const key=f.homeId===teamId?'homePlayerIds':f.awayId===teamId?'awayPlayerIds':null;if(!key||!f[key].includes(playerId)||(onlyGame&&f.id!==onlyGame))continue;
  f[key]=f[key].filter(i=>i!==playerId);n++;
  const box=games.get(f.id).teams.find(t=>t.teamId===teamId),k=box.players.findIndex(p=>p.playerId===playerId),me=box.players[k];
  box.players.splice(k,1);
  if(me.starter){starts++;const alt=box.players.filter(p=>!p.starter&&f[key].includes(p.playerId)).sort((a,c)=>c.seconds-a.seconds||a.playerId-c.playerId)[0];alt.starter=true;alt.position=me.position;}
 }
 return {games:n,starts};
}
// add a clone of the player to the target team for every game of that team (observed seconds = his own mean over
// the games he appeared; starter slot replaces the target's lowest-seconds starter if he started >=50% of his games).
function addTo(b,fromTeamId,player,toTeamId){
 const games=new Map(b.exposure.games.map(g=>[g.id,g]));let secs=0,app=0,st=0;const pos={};
 for(const g of b.exposure.games){const t=g.teams.find(t=>t.teamId===fromTeamId);const r=t?.players.find(p=>p.playerId===player.playerId);
  if(r&&r.seconds>0){secs+=r.seconds;app++;if(r.starter)st++;pos[r.position]=(pos[r.position]||0)+1;}}
 const mean=secs/app,starter=st/app>=.5,position=Object.entries(pos).sort((a,c)=>c[1]-a[1])[0][0];const posValue=position==='undefined'?undefined:position;
 const dest=b.league.teams.find(t=>t.id===toTeamId);dest.roster.push(structuredClone(player));
 let n=0;
 for(const f of b.league.schedule){
  const key=f.homeId===toTeamId?'homePlayerIds':f.awayId===toTeamId?'awayPlayerIds':null;if(!key)continue;
  const other=key==='homePlayerIds'?'awayPlayerIds':'homePlayerIds';
  if((f.homeId===fromTeamId||f.awayId===fromTeamId))removeFrom(b,fromTeamId,player.playerId,f.id); // cannot play both sides of one game
  f[key].push(player.playerId);n++;
  const box=games.get(f.id).teams.find(t=>t.teamId===toTeamId);
  if(starter){const low=box.players.filter(p=>p.starter).sort((a,c)=>a.seconds-c.seconds||a.playerId-c.playerId)[0];low.starter=false;}
  box.players.push({playerId:player.playerId,seconds:mean,starter,position:posValue});
 }
 return {games:n,meanSeconds:mean,starter,position,appearances:app};
}
export function applyArm(b,arm){
 if(arm.kind==='base')return {};
 if(arm.kind==='remove')return removeFrom(b,arm.teamId,arm.playerId);
 if(arm.kind==='add'){const p=b.league.teams.find(t=>t.id===arm.teamId).roster.find(r=>r.playerId===arm.playerId);return addTo(b,arm.teamId,p,arm.toTeamId);}
 throw Error('arm '+arm.kind);
}
export function runSeason(b,seed){
 const r=run(b.league,b.exposure,{seed,options:b.options,audit:false,replay:false,indices:null});
 return {seed,games:r.matches.length,teams:r.teams.map(t=>({id:t.id,name:t.name,games:t.games,wins:t.wins,pts:t.stats.pts,opp:t.opponent.pts}))};
}
