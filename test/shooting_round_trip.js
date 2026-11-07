import assert from 'node:assert/strict';
import * as M from '../src/probability_model.js';
import * as C from '../src/constants.js';
import {roundTripMake} from '../reports/player-impact-v9/model.mjs';
const applyStamina=(p,f)=>{const eff=1.00-(1.00-0.70)*Math.max(0,Math.min(1,f));return {...p,long:p.long*eff,mid:p.mid*eff,short:p.short*eff,drive:p.drive*eff,_eff:eff};};// local copy: engine fatigue removed in sim 0.1.1
const source={long:80,mid:99,short:90},curves={long:C.CURVE_3PT,mid:C.CURVE_MID,short:C.CURVE_SHORT};
const measurement={rates:{long:.39,mid:.54,short:.65},sourceBase:Object.fromEntries(Object.keys(source).map(z=>[z,M.interpolate(source[z],curves[z])]))};
const p={...source,shootingMeasurement:measurement},base={make:{...measurement.sourceBase}},copy=structuredClone(p);
for(const z of Object.keys(source))assert.ok(Math.abs(roundTripMake(base,p)[z]-measurement.rates[z])<1e-12);
assert.deepEqual(p,copy);
const tired=applyStamina(p,.7),q={make:Object.fromEntries(Object.keys(source).map(z=>[z,M.interpolate(tired[z],curves[z])]))};
for(const z of Object.keys(source))assert.ok(Math.abs(roundTripMake(q,tired)[z]-measurement.rates[z])<1e-12);
const better={...p,long:90},prob={make:{...base.make,long:M.interpolate(90,C.CURVE_3PT)}};
assert.ok(roundTripMake(prob,better).long>roundTripMake(base,p).long,'Source centering must not cancel a shooting improvement');
assert.ok(roundTripMake(base,p).mid>M.interpolate(99,C.CURVE_MID),'Rates above attr99 must survive');
assert.throws(()=>roundTripMake(base,{...p,_eff:0}),/stamina/);
console.log('shooting empirical round trip, fatigue centering, monotonic ability and immutable source checks passed');
