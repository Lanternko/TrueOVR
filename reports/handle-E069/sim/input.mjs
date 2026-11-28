// E-069 input wrapper: v41 input plus (when cfg given) handle / passSec / creation fields. Defaults 70 when missing.
import fs from 'node:fs';
import {loadInput as v41Input} from '../../player-impact-v41/input.mjs';
import {interpolate} from '../../../src/probability_model.js';
import {CURVE_TOV} from '../../../src/constants.js';
const M=70,csv=f=>{const [h,...r]=fs.readFileSync(f,'utf8').replace(/^﻿/,'').trim().split(/\r?\n/);const k=h.split(',');return r.map(l=>Object.fromEntries(l.split(',').map((v,i)=>[k[i],v])));};
const rel=a=>interpolate(a,CURVE_TOV)/interpolate(M,CURVE_TOV);
export function loadInput(season,e069){
 const x=v41Input(season);if(!e069)return x;
 const hand=new Map(csv('reports/handle-E069/handle.csv').filter(r=>r.season===season).map(r=>[r.playerId,r]));
 // card 0.2.0 creation (CRT) matched by name; the ranking has no playerId.
 const card=new Map(csv('reports/card-0.2.0/ranking.csv').map(r=>[r.name,Number(r.creation)]));
 const miss={handle:0,pass:0,creation:0};
 for(const p of x.league.teams.flatMap(t=>t.roster)){
  const h=hand.get(String(p.playerId));
  const handle=h&&Number.isFinite(Number(h.handle))?Number(h.handle):(miss.handle++,M);
  const passSec=h&&Number.isFinite(Number(h.passSec))?Number(h.passSec):(miss.pass++,M);
  const cr=card.get(p.name);const creation=Number.isFinite(cr)?cr:(miss.creation++,M);
  p.handle=handle;p.e069Handle=handle;p.e069Creation=creation;
  p.e069HandleRel=rel(handle);p.e069PassRel=rel(passSec);
 }
 x.e069Missing=miss;return x;
}
