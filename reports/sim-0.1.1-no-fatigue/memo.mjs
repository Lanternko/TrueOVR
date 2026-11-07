// sim 0.1.1: does the memoized:true chain still build? (expected: old OK, new throws anchor drift)
import {impactEngine} from '../player-impact-v53/engine.mjs';
try { await impactEngine('rotation-space', {game: true, memoized: true}); console.log('memoized OK'); }
catch (e) { console.log('memoized THROWS:', String(e.message).slice(0, 160)); }
