// E-069 simulator helpers. State is shared with engine patches (module-level, one worker = one game at a time).
export const state={ctlShare:1,otherShare:0};
// Ball-handling hazard over `sec` seconds of holding: 1-exp(-kCtl*HandleRel*sec).
export const ctlProb=(p,sec,cfg)=>1-Math.exp(-cfg.kCtl*(p.e069HandleRel??1)*Math.max(0,sec));
// Pass segment: ball-handling hazard over the hold plus pass hazard min(.95,kPass*PassRel), combined.
export function passSegmentProb(p,sec,cfg){
 const pc=ctlProb(p,sec,cfg),pp=Math.min(.95,cfg.kPass*(p.e069PassRel??1));
 state.ctlShare=pc+pp>0?pc/(pc+pp):1;return 1-(1-pc)*(1-pp);
}
// Release (touch end) hazard: ball-handling TOV over the hold, plus a league-constant 'other' (offensive foul / violation) TOV per touch,
// kept at the baseline mechanism's role. cfg.pOther is fixed from data (actual other TOV total / baseline touches), not tuned.
export function releaseProb(p,sec,cfg){
 const pc=ctlProb(p,sec,cfg),po=cfg.pOther??0,tot=1-(1-pc)*(1-po);
 state.otherShare=tot>0?(1-pc)*po/tot:0;return Math.min(.95,tot);
}
