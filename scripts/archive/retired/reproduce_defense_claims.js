import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

// Read-only model audit: no simulation, calibration, or baseline overwrite.
const read=f=>JSON.parse(fs.readFileSync(new URL('../'+f,import.meta.url)));
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(new URL('../'+f,import.meta.url))).digest('hex');
const mean=x=>x.reduce((a,b)=>a+b,0)/x.length;
const variance=x=>mean(x.map(v=>(v-mean(x))**2));
const sd=x=>Math.sqrt(variance(x));
const covariance=(x,y)=>mean(x.map((v,i)=>(v-mean(x))*(y[i]-mean(y))));
const regression=(x,y)=>covariance(x,y)/variance(x);
const compare=(actual,simulated)=>({
  observedMean:mean(actual),simulatedMean:mean(simulated),bias:mean(simulated)-mean(actual),
  observedSD:sd(actual),simulatedSD:sd(simulated),sdRatio:sd(simulated)/sd(actual),
  correlation:covariance(actual,simulated)/sd(actual)/sd(simulated),slope:regression(actual,simulated),
  mae:mean(actual.map((v,i)=>Math.abs(simulated[i]-v))),
  centeredMAE:mean(actual.map((v,i)=>Math.abs(simulated[i]-mean(simulated)-(v-mean(actual))))),
  centeredRMSE:Math.sqrt(mean(actual.map((v,i)=>(simulated[i]-mean(simulated)-(v-mean(actual)))**2)))
});
const seeds=[20261012,20261013,20261014,20261015];
const stability=read('reports/defense-stability.json');
const sourceFiles=['reports/defense-stability.json','reports/defense-validation.json','data/season-league.json',
  'data/season-source/team-games.json','data/benchmark-source/teams.json'];
const reports=seeds.map(seed=>{
  const file='reports/nba-defense-v1-seed'+seed+'.json';sourceFiles.push(file);
  const saved=stability.runs.find(r=>r.id==='corrected'&&r.seed===seed);
  assert.equal(hash(file),saved.artifact.sha256);
  const result=read(file);
  assert.equal(result.options.minuteMode,'heuristic');assert.equal(result.options.foulConditioning,true);
  assert.equal(result.matches.length,1230);assert.equal(result.summary.teams.length,30);
  assert.deepEqual(result.summary,saved.summary);
  return result;
});
const teams=reports[0].summary.teams.map(t=>({id:t.id,name:t.name,observed:{...t.observed},
  simulated:Object.fromEntries(Object.keys(t).filter(k=>Number.isFinite(t[k])).map(k=>[k,
    mean(reports.map(report=>report.summary.teams.find(row=>row.id===t.id)[k]))]))
}));
for(const t of teams){
  t.simulated.net=t.simulated.ppg-t.simulated.opponentPPG;
  t.observed.net=t.observed.ppg-t.observed.opponentPPG;
}
const keys=['wins','net','offensiveRatingProxy','defensiveRatingProxy','opponentTwo','opponentThree',
  'forcedTOVRate','defensiveReboundPct','opponentFTR','possessionsProxy'];
const metrics=Object.fromEntries(keys.map(k=>[k,compare(teams.map(t=>t.observed[k]),teams.map(t=>t.simulated[k]))]));
const rawGames=read('data/season-source/team-games.json').data.resultSets[0];
const gameRows=rawGames.rowSet.map(row=>Object.fromEntries(rawGames.headers.map((k,i)=>[k,row[i]])));
const rowMap=new Map(gameRows.map(row=>[row.GAME_ID+':'+row.TEAM_ID,row]));
const schedule=read('data/season-league.json').schedule;
const actualGames=schedule.map(g=>{
  const a=rowMap.get(g.id+':'+g.homeId),b=rowMap.get(g.id+':'+g.awayId);
  assert.equal(a.PTS,g.observed.homeScore);assert.equal(b.PTS,g.observed.awayScore);
  assert.equal(a.PLUS_MINUS,a.PTS-b.PTS);assert.equal(b.PLUS_MINUS,b.PTS-a.PTS);
  return {homeId:g.homeId,awayId:g.awayId,margin:a.PTS-b.PTS};
});
const gameMetrics=(games,net)=>({
  marginSD:sd(games.map(g=>g.margin)),
  residualSD:sd(games.map(g=>g.margin-(net.get(g.homeId)-net.get(g.awayId)))),
  closeShare:mean(games.map(g=>Number(Math.abs(g.margin)<=5))),
  blowoutShare:mean(games.map(g=>Number(Math.abs(g.margin)>=20)))
});
const actualGameMetrics=gameMetrics(actualGames,new Map(teams.map(t=>[t.id,t.observed.net])));
const simulatedGameMetrics=reports.map(r=>({seed:r.seed,...gameMetrics(r.matches.map(g=>({...g,margin:g.scoreA-g.scoreB})),
  new Map(r.summary.teams.map(t=>[t.id,t.ppg-t.opponentPPG])))}));
const rawTeams=read('data/benchmark-source/teams.json').data.resultSets[0];
const countKeys=['oreb','dreb','fga','fgm','fta','ftm','pts','tov'];
const observedCounts=Object.fromEntries(countKeys.map(k=>[k,rawTeams.rowSet.reduce((n,row)=>n+row[rawTeams.headers.indexOf(k.toUpperCase())],0)/2460]));
const simulatedCounts=reports.map(r=>({seed:r.seed,...Object.fromEntries(countKeys.map(k=>[k,r.accounting.reduce((n,t)=>n+t.stats[k],0)/2460]))}));
const counts={observed:observedCounts,simulated:simulatedCounts,average:Object.fromEntries(countKeys.map(k=>[k,mean(simulatedCounts.map(r=>r[k]))]))};
for(const row of [counts.observed,counts.average,...simulatedCounts]){row.fgMiss=row.fga-row.fgm;row.ftMiss=row.fta-row.ftm;}
const ratio=row=>100*row.pts/(row.fga-row.oreb+row.tov+.44*row.fta);
const ratingAggregation={
  pooled:{observed:ratio(counts.observed),simulated:ratio(counts.average)},
  meanTeam:{observed:metrics.offensiveRatingProxy.observedMean,simulated:metrics.offensiveRatingProxy.simulatedMean}
};
const defense=metrics.defensiveRatingProxy;
const bestDefenseScale=defense.correlation*defense.observedSD/defense.simulatedSD;
const optimalCenteredRMSE=defense.observedSD*Math.sqrt(1-defense.correlation**2);
const legacy=read('reports/defense-validation.json').variants.find(v=>v.id==='legacy');
const singleSeedDefense=reports.map(r=>({seed:r.seed,...compare(r.summary.teams.map(t=>t.observed.defensiveRatingProxy),r.summary.teams.map(t=>t.defensiveRatingProxy))}));
const legacyDefense=compare(legacy.teams.map(t=>t.observed.defensiveRatingProxy),legacy.teams.map(t=>t.defensiveRatingProxy));
const result={schemaVersion:1,scope:'Reproduction gate only; A1-A4 implementation and A3/A4 causal diagnosis have not started.',
  definitions:{sd:'Population standard deviation (divide by N).',teamAggregation:'Average each team metric over four corrected normal-rotation seeds before cross-team calculations.',
    regression:'Simulated metric regressed on observed metric, with intercept. Wins per net point regress wins on own net points.',
    residual:'Game margin minus home team season PPG net minus away team season PPG net; fitted-season description, not held-out strength.',
    gameThresholds:'Absolute final margin <=5 or >=20, including overtime.',ratings:'Paired FGA-OREB+TOV+0.44FTA proxy; compare pooled league ratios separately from mean of team ratios.'},
  metrics,teams,winPerNet:{simulated:regression(teams.map(t=>t.simulated.net),teams.map(t=>t.simulated.wins)),
    observed:regression(teams.map(t=>t.observed.net),teams.map(t=>t.observed.wins))},
  games:{observed:actualGameMetrics,simulated:simulatedGameMetrics},counts,ratingAggregation,
  defenseScaleDiagnostic:{metric:'Centered RMSE, not MAE',before:defense.centeredRMSE,bestScale:bestDefenseScale,bestRMSE:optimalCenteredRMSE},
  legacyDefense,singleSeedDefense,
  discrepancies:[
    {claim:'Four-seed average OREB/G 13.07',reproduced:counts.average.oreb,explanation:'13.07073 occurs at seeds 20261012 and 20261015. Four-seed average is 13.04299.'},
    {claim:'League offensive proxy 115.13 versus 112.73',reproduced:ratingAggregation,explanation:'Pooled counts give 115.15599 versus 112.72815; unweighted mean of team ratings gives 115.14025 versus 112.75040. Neither reproduces the stated pair at two decimals.'}
  ],
  provenance:{sources:Object.fromEntries(sourceFiles.map(f=>[f,hash(f)])),code:{'scripts/reproduce_defense_claims.js':hash('scripts/reproduce_defense_claims.js')}}
};
const f=(n,d=3)=>n.toFixed(d);
const md=['# 防守第二批：數字重現檢查','',
  '只完成使用者指定的重現關卡。A1–A4實作與A3／A4原因驗證尚未開始；原版、v1及所有基準產物保持原樣。','',
  '30隊各項指標先逐隊取四seed平均，標準差使用母體定義（除以N）。迴歸斜率為模擬對真實、有截距。單場殘差扣除兩隊各自該季淨勝分差，仍屬同季描述。','',
  '| 指標 | 模擬均值 | 真實均值 | 偏差 | 模擬SD | 真實SD | SD比 | 相關 | 斜率 | 去均值MAE |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
  ...keys.map(k=>{const m=metrics[k];return `| ${k} | ${[m.simulatedMean,m.observedMean,m.bias,m.simulatedSD,m.observedSD,m.sdRatio,m.correlation,m.slope,m.centeredMAE].map(n=>f(n)).join(' | ')} |`;}),'',
  `四seed平均後勝場MAE：${f(metrics.wins.mae,2)}；單seed MAE範圍：${f(Math.min(...reports.map(r=>r.summary.winMAE)),2)}–${f(Math.max(...reports.map(r=>r.summary.winMAE)),2)}。`,
  `每分淨勝分的勝場斜率：模擬${f(result.winPerNet.simulated)}，真實${f(result.winPerNet.observed)}。`,'',
  '| seed | 分差SD | 扣實力殘差SD | ≤5分 | ≥20分 |','|---|---:|---:|---:|---:|',
  `| 真實 | ${f(actualGameMetrics.marginSD)} | ${f(actualGameMetrics.residualSD)} | ${f(100*actualGameMetrics.closeShare,2)}% | ${f(100*actualGameMetrics.blowoutShare,2)}% |`,
  ...simulatedGameMetrics.map(g=>`| ${g.seed} | ${f(g.marginSD)} | ${f(g.residualSD)} | ${f(100*g.closeShare,2)}% | ${f(100*g.blowoutShare,2)}% |`),'',
  '## 對不上的數字與需區分的口徑','',
  `- 四seed平均OREB／場為${f(counts.average.oreb,5)}，不是13.07；13.07073是seed 20261012／15的數字。DREB平均${f(counts.average.dreb,5)}，可重現36.45。`,
  `- 全聯盟合併計數的進攻／防守代理：模擬${f(ratingAggregation.pooled.simulated,5)}，真實${f(ratingAggregation.pooled.observed,5)}，偏差+${f(ratingAggregation.pooled.simulated-ratingAggregation.pooled.observed,5)}。若採30隊進攻代理算術平均，則為${f(ratingAggregation.meanTeam.simulated,5)}／${f(ratingAggregation.meanTeam.observed,5)}；115.13／112.73並非任一完整口徑。`,
  `- 防守「2.61→2.58」可重現為去均值RMSE：${f(defense.centeredRMSE,5)}→${f(optimalCenteredRMSE,5)}，最佳共同縮放${f(bestDefenseScale,5)}。去均值MAE為${f(defense.centeredMAE,5)}，不能與RMSE混用。`,
  `- 防守排序相關的同seed比較：原版${f(legacyDefense.correlation,5)}，v1 seed 20261012為${f(singleSeedDefense[0].correlation,5)}；四seed平均的v1為${f(defense.correlation,5)}。目前沒有四seed原版產物可作同等消噪的比較。`,'',
  '主要壓縮、五要素及變異數字均重現；上述差異不推翻偏差存在，但依「對不上先回報」的指示先停下。籃板／出界造成偏差仍是待驗證推測，不在本報告作因果結論。','',
  '`node scripts/reproduce_defense_claims.js` 重跑。[完整數據與來源／程式雜湊](defense-reproduction.json)。',''].join('\n');
fs.writeFileSync(new URL('../reports/defense-reproduction.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
fs.writeFileSync(new URL('../reports/defense-reproduction.md',import.meta.url),md);
console.log(JSON.stringify({expectedWinMAE:metrics.wins.mae,winSD:metrics.wins,winPerNet:result.winPerNet,
  defenseRMSE:result.defenseScaleDiagnostic,discrepancies:result.discrepancies},null,2));
console.log('Saved reproduction report. A-stage implementation has not started.');
