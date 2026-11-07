import assert from 'node:assert/strict';
import * as M from '../src/probability_model.js';
import * as C from '../src/constants.js';
import {centeredMake} from '../reports/player-impact-v12/model.mjs';
const applyStamina=(p,f)=>{const eff=1.00-(1.00-0.70)*Math.max(0,Math.min(1,f));return {...p,long:p.long*eff,mid:p.mid*eff,short:p.short*eff,drive:p.drive*eff,_eff:eff};};// local copy: engine fatigue removed in sim 0.1.1
const curves={long:C.CURVE_3PT,mid:C.CURVE_MID,short:C.CURVE_SHORT},source={long:80,mid:99,short:90};
const base=Object.fromEntries(Object.keys(source).map(z=>[z,M.interpolate(source[z],curves[z])])),context={long:-.014,mid:-.01,short:-.045};
const measurement={rates:{long:.39,mid:.54,short:.65},sourceBase:base,contexts:{test:context}};
const player={...source,shootingMeasurement:measurement},prob={make:Object.fromEntries(Object.keys(source).map(z=>[z,base[z]+context[z]]))};
for(const z of Object.keys(source))assert.ok(Math.abs(centeredMake(prob,player,'test')[z]-measurement.rates[z])<1e-12);
const tired=applyStamina(player,.7),tp={make:Object.fromEntries(Object.keys(source).map(z=>[z,M.interpolate(tired[z],curves[z])+context[z]]))};
for(const z of Object.keys(source))assert.ok(Math.abs(centeredMake(tp,tired,'test')[z]-measurement.rates[z])<1e-12);
const better={...player,long:90},bp={make:{...prob.make,long:prob.make.long+M.interpolate(90,C.CURVE_3PT)-base.long}};
assert.ok(centeredMake(bp,better,'test').long>measurement.rates.long);
const easier={make:{...prob.make,short:prob.make.short+.02}};assert.ok(Math.abs(centeredMake(easier,player,'test').short-measurement.rates.short-.02)<1e-12);
assert.throws(()=>centeredMake(prob,player,'missing'),/context/);
console.log('Source context reconstruction, fatigue centering, improved ability and changed-context response passed');
