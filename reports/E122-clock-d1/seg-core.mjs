// E-122: measure full-clock first-segment durations of side-B (off===1) possessions from the event stream.
// segObserver(slotA,candSide): measures the offense opposing side candSide (default side 0 => off===1).
// Segment = POSSESSION event -> first terminal event (FGM/FGX/TOV/STEAL/FOUL/SHOT_CLOCK/NO_SHOT) or next POSSESSION/PERIOD_END.
// Full-clock = in-period clock at POSSESSION >= 30 s. Optionally restricted to periods when roster index `slotA` of side A is on floor.
const TERM=new Set(['FGM','FGX','TOV','STEAL','FOUL','SHOT_CLOCK','NO_SHOT','PERIOD_END','GAME_END']);
export function segObserver(slotA=null,candSide=0){
  const lineup=[[0,1,2,3,4],[0,1,2,3,4]];
  const st={n:0,sum:0,nOn:0,sumOn:0,nAll:0,sumAll:0};let open=null;
  const close=(clock)=>{if(!open)return;const d=open.start-clock;
    if(open.start>=30){st.nAll++;st.sumAll+=d;if(slotA!==null&&open.on){st.nOn++;st.sumOn+=d;}}
    open=null;};
  const f=e=>{
    if(e.type==='SUBSTITUTION'){const L=lineup[e.off];const k=L.indexOf(e.out);if(k>=0)L[k]=e.player;return;}
    if(e.type==='POSSESSION'){close(e.clock);if(e.off===1-candSide)open={start:e.clock,on:slotA!==null&&lineup[candSide].includes(slotA)};return;}
    if(open&&TERM.has(e.type))close(e.clock);
  };
  f.stats=st;return f;
}
