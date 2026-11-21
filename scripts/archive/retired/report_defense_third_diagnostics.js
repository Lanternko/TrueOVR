import fs from 'node:fs';
import readline from 'node:readline';
import {read,hash} from './defense_io.js';
import {varianceAnalysis} from '../src/defense_variance_sources.js';
import {variance} from '../src/statistical_summary.js';
const root='reports/defense-third';
const load=async f=>{const a=[];for await(const l of readline.createInterface({input:fs.createReadStream(f),crlfDelay:Infinity}))if(l)a.push(JSON.parse(l));return a;};
const real=await load('reports/defense-b1/real-games.jsonl'),ids=new Set(real.map(g=>g.id));
for(const g of real){const e=read('data/defense-a-source/pbp/'+g.id+'.json').data.game.actions.find(e=>e.actionType==='period'&&e.subType==='end'&&e.period===4);g.regulationScore=[+e.scoreHome,+e.scoreAway];}
const actual=varianceAnalysis(real),results=[];
for(const replay of read(root+'/replay-diagnostics.json')){
  const games=(await load(replay.file)).filter(g=>ids.has(g.id)),m=varianceAnalysis(games),pts=games.flatMap(g=>g.possessions.filter(p=>p.period<=4).map(p=>p.points));
  const distribution=Object.fromEntries([0,1,2,3,4].map(k=>[k,pts.filter(x=>x===k).length/pts.length]));
  const perPossession=m.meanCombinedPossessions*(m.teamCenteredPointVariance-actual.teamCenteredPointVariance),countIID=(m.meanCombinedPossessions-actual.meanCombinedPossessions)*actual.teamCenteredPointVariance;
  const paceNet=(m.decomposition.individualPaceVariance+m.decomposition.paceCovarianceReduction)-(actual.decomposition.individualPaceVariance+actual.decomposition.paceCovarianceReduction);
  const coupling=m.decomposition.remainingCovarianceReduction-actual.decomposition.remainingCovarianceReduction;
  const serial=m.decomposition.withinTeamSerialAndHeterogeneityVariance-actual.decomposition.withinTeamSerialAndHeterogeneityVariance;
  const gap=m.decomposition.total-actual.decomposition.total;
  if(Math.abs(perPossession+countIID+paceNet+coupling+serial-gap)>1e-7)throw Error('Variance identity');
  const budget=Object.fromEntries(['Setup','Pass','Release','Flight','Inbound','Violation','Other'].map(k=>[k,replay.totals['time'+k]/1230]));
  const sum=Object.values(budget).reduce((a,b)=>a+b,0);if(Math.abs(sum-replay.totals.seconds/10/1230)>1e-7)throw Error('Time identity');
  results.push({label:replay.file.split('/').at(-1),variance:{...m,records:undefined},pointsVariance:variance(pts),distribution,
    gap:{total:gap,components:{singlePossessionVariance:perPossession,meanPossessionCount:countIID,sharedPaceNet:paceNet,remainingSameGameCovariance:coupling,withinTeamSerialAndHeterogeneity:serial},fractionOfPreviousComponents:{singlePossessionVariance:perPossession/31.2960216635,remainingSameGameCovariance:coupling/35.805783833,withinTeamSerialAndHeterogeneity:serial/48.321617764}},timeBudgetSecondsPerGame:budget,
    countsPerTeamGame:Object.fromEntries(['tov','stl','passSteals','touchSteals','clockTov','offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov','fta','fga','madeFoul','missFoul'].map(k=>[k,replay.totals[k]/2460])),provenance:{file:replay.file,sha256:hash(replay.file)}});
}
fs.writeFileSync(root+'/diagnostics.json',JSON.stringify({actual:{...actual,records:undefined},results,scope:'Same 1227 fixtures, regulation variance/distributions; event counts and time budget full1230 including OT. One paired seed20261012; not twenty-seed uncertainty.'},null,2)+'\n');
console.log(results.map(r=>({label:r.label,var:r.pointsVariance,points:r.distribution,residual:r.variance.marginResidualSD,budget:r.timeBudgetSecondsPerGame})));
