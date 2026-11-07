import assert from 'node:assert/strict';
import * as M from '../src/probability_model.js';
import * as C from '../src/constants.js';
import {centeredMake} from '../reports/player-impact-v14/model.mjs';
const applyStamina=(p,f)=>{const eff=1.00-(1.00-0.70)*Math.max(0,Math.min(1,f));return {...p,long:p.long*eff,mid:p.mid*eff,short:p.short*eff,drive:p.drive*eff,_eff:eff};};// local copy: engine fatigue removed in sim 0.1.1

const curves={long:C.CURVE_3PT,mid:C.CURVE_MID,short:C.CURVE_SHORT};
const source={long:80,mid:88,short:90};
const sourceBase=Object.fromEntries(Object.keys(curves).map(z=>[z,M.interpolate(source[z],curves[z])]));
const rates={long:.39,mid:.49,short:.65};
const sourcePlayer=applyStamina(source,.35);
const environment={long:.018,mid:-.007,short:.024};
const prediction=p=>({make:Object.fromEntries(Object.keys(curves).map(z=>[z,M.interpolate(p[z],curves[z])+environment[z]]))});
const sourceProbability=prediction(sourcePlayer);
const context=Object.fromEntries(Object.keys(curves).map(z=>[z,sourceProbability.make[z]-sourceBase[z]]));
const measurement={rates,sourceBase,contexts:{test:context}};
const card=p=>({...p,shootingMeasurement:measurement});
const reconstructed=centeredMake(sourceProbability,card(sourcePlayer),'test');
const rested=centeredMake(prediction(source),card(source),'test');
const exhausted=applyStamina(source,.7);
const tired=centeredMake(prediction(exhausted),card(exhausted),'test');
for(const z of Object.keys(curves)){
 assert.ok(Math.abs(reconstructed[z]-rates[z])<1e-12,'Observed source rotation must reconstruct empirical FG');
 assert.ok(rested[z]>reconstructed[z],'Rest above source rotation must retain value');
 assert.ok(tired[z]<reconstructed[z],'Additional fatigue must reduce FG');
}
const better={...sourcePlayer,long:sourcePlayer.long+5};
assert.ok(centeredMake(prediction(better),card(better),'test').long>rates.long);
const easier={make:{...sourceProbability.make,short:sourceProbability.make.short+.02}};
assert.ok(Math.abs(centeredMake(easier,card(sourcePlayer),'test').short-rates.short-.02)<1e-12);
assert.throws(()=>centeredMake(sourceProbability,card(sourcePlayer),'missing'),/context/);
console.log('Observed-rotation reconstruction, extra fatigue, rest, ability and changed-context response passed');
