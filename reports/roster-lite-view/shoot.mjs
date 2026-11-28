// 名單頁精簡／詳細檢視截圖＋量測（headless Chrome 走 CDP，windowsHide；頁面只開本機暫存目錄）
// 用法：node shoot.mjs <輸出目錄> <頁面目錄絕對路徑>
import { spawn } from 'node:child_process';
import fs from 'node:fs';
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = process.argv[2], W = process.argv[3], port = 9334;
fs.mkdirSync(OUT, { recursive: true });
const ch = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, '--no-first-run', '--disable-gpu', '--user-data-dir=' + W + '/prof', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch (e) {} await sleep(200); }
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pend = new Map(); const logs = [];
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC ' + JSON.stringify(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 300));
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('ERR ' + JSON.stringify(m.params.args.map(a => a.value || a.description)).slice(0, 300)); };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const shot = async name => { const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(`${OUT}/${name}.png`, Buffer.from(r.result.data, 'base64')); };
await send('Runtime.enable'); await send('Page.enable');
async function load(file, w, h, mobile, view) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  await send('Page.navigate', { url: 'file:///' + W + '/' + file });
  await sleep(1500);
  if (view !== undefined) { await ev(view ? `localStorage.setItem('bbac.view','${view}')` : `localStorage.removeItem('bbac.view')`); await send('Page.navigate', { url: 'file:///' + W + '/' + file }); }
  await sleep(3500);
}
const vis = () => ev(`JSON.stringify([...document.querySelectorAll('#tbl thead tr:last-child th')].filter(t=>getComputedStyle(t).display!=='none').map(t=>t.dataset.k||'#'))`);
const grp = () => ev(`JSON.stringify([...document.querySelectorAll('#tbl thead tr.grp th')].filter(t=>getComputedStyle(t).display!=='none').map(t=>[t.textContent,t.colSpan,Math.round(t.getBoundingClientRect().left),Math.round(t.getBoundingClientRect().right)]))`);
const cellOf = (k, name) => `(()=>{const tr=document.querySelector('#tbl tbody tr[data-n="${encodeURIComponent(name)}"]');if(!tr)return null;return tr.querySelector('td[data-ck="${k}"]')})()`;
const hover = (k, name) => ev(`(()=>{const td=${cellOf(k, name)};if(!td)return 'nocell';td.scrollIntoView({block:'center'});td.dispatchEvent(new PointerEvent('pointerover',{bubbles:true,pointerType:'mouse'}));return 'ok'})()`);
const press = (k, name) => ev(`(()=>{const td=${cellOf(k, name)};if(!td)return 'nocell';td.scrollIntoView({block:'center'});const r=td.getBoundingClientRect();td.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerType:'touch',clientX:r.left+5,clientY:r.top+5}));return 'ok'})()`);
const res = { logs };
const pick = `(()=>{const pg=P.filter(p=>p.pos==='PG'&&p.min>=28&&p.tips&&p.tips.handle).sort((a,b)=>b.ovr-a.ovr)[0];return pg?pg.name:null})()`;
for (const [tag, w, h, mob] of [['desk', 1440, 900, false], ['mob', 390, 844, true]]) {
  await load('roster-viewer.html', w, h, mob, null);
  res[tag + '_default'] = await ev(`st.view`);
  const pgName = await ev(pick); res.pgName = pgName;
  await load('roster-viewer.html', w, h, mob, 'lite');
  res[tag + '_lite_cols'] = JSON.parse(await vis()); res[tag + '_lite_grp'] = JSON.parse(await grp());
  res[tag + '_lite_scrollW'] = await ev(`JSON.stringify({sw:document.querySelector('.tbox').scrollWidth,cw:document.querySelector('.tbox').clientWidth,pageSW:document.documentElement.scrollWidth,tbl:document.getElementById('tbl').getBoundingClientRect().width})`);
  if (mob) res.mob_first = JSON.parse(await ev(`JSON.stringify((()=>{const box=document.querySelector('.tbox'),br=box.getBoundingClientRect();const r={box:[br.left,br.right],vw:innerWidth};for(const th of document.querySelectorAll('#tbl thead tr:last-child th')){const k=th.dataset.k||'#';if(getComputedStyle(th).display==='none')continue;const q=th.getBoundingClientRect();r[k]=[Math.round(q.left*10)/10,Math.round(q.right*10)/10];}return r})())`));
  await shot(`${tag}-1-lite`);
  if (mob) { await ev(`document.querySelector('.tbox').scrollLeft=1e5`); await sleep(400); res.mob_scrolled = await ev(`document.querySelector('.tbox').scrollLeft`); await shot(`${tag}-2-lite-scrolled`); await ev(`document.querySelector('.tbox').scrollLeft=0`); }
  await ev(`st.q='Stephen Curry';render()`); await sleep(500);
  if (mob) { res[tag + '_press_outside'] = await press('outside', 'Stephen Curry'); await sleep(900); } else { res[tag + '_hover_outside'] = await hover('outside', 'Stephen Curry'); await sleep(500); }
  await shot(`${tag}-4-tip-outside`);
  await ev(`st.q=${JSON.stringify(pgName)};render()`); await sleep(500);
  if (mob) { await ev(`document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerType:'touch'}))`); await sleep(200); res[tag + '_press_handle'] = await press('handle', pgName); await sleep(900); } else { res[tag + '_hover_handle'] = await hover('handle', pgName); await sleep(500); }
  await shot(`${tag}-5-tip-handle`);
  await load('roster-viewer.html', w, h, mob, 'full');
  res[tag + '_full_cols'] = JSON.parse(await vis()); res[tag + '_full_grp'] = JSON.parse(await grp());
  res[tag + '_full_scrollW'] = await ev(`JSON.stringify({sw:document.querySelector('.tbox').scrollWidth,cw:document.querySelector('.tbox').clientWidth,tbl:document.getElementById('tbl').getBoundingClientRect().width})`);
  await shot(`${tag}-3-full`);
  await ev(`st.sort='spot';st.asc=false;render()`);
  await ev(`document.querySelector('#viewSeg button:not([aria-pressed="true"])').click()`); await sleep(1500);
  res[tag + '_sort_after_switch'] = await ev(`JSON.stringify([st.view,st.sort,st.asc])`);
  await ev(`document.querySelector('#tbl thead th[data-k=outside]').click()`); await sleep(500);
  res[tag + '_sort_outside_top3'] = await ev(`JSON.stringify([...document.querySelectorAll('#tbl tbody tr[data-n]')].slice(0,3).map(tr=>decodeURIComponent(tr.dataset.n)))`);
  await load('card-roster-viewer.html', w, h, mob, 'lite');
  res[tag + '_card_lite_cols'] = JSON.parse(await vis()); res[tag + '_card_grp'] = JSON.parse(await grp());
  await shot(`${tag}-6-2025-26-lite`);
  await load('card-roster-viewer.html', w, h, mob, 'full'); res[tag + '_card_full_cols'] = JSON.parse(await vis()); res[tag + '_card_full_grp'] = JSON.parse(await grp());
  await ev(`localStorage.removeItem('bbac.view')`);
  await ev(`document.querySelector('#mSettings summary').click()`); await sleep(300);
  res[tag + '_gear_season'] = await ev(`JSON.stringify([...document.querySelectorAll('#mSeasonLinks a')].map(a=>[a.textContent,a.getAttribute('href'),a.getAttribute('aria-current')]))`);
  await shot(`${tag}-7-gear-season`);
  res[tag + '_fseason'] = await ev(`JSON.stringify([...document.querySelectorAll('#fSeason a')].map(a=>[a.textContent,a.getAttribute('href'),a.getAttribute('aria-current')]))`);
}
await load('roster-viewer.html', 1440, 900, false, 'lite');
res.data = JSON.parse(await ev(`JSON.stringify((()=>{
  const keys=['offR','defR','play','outside','inside','handle','offball','perim','rebound','help'];
  const pool=P.filter(p=>p.min>=15), top=[...P].sort((a,b)=>b.ovr-a.ovr).slice(0,15).map(p=>p.name);
  const bench=P.filter(p=>p.min>=15&&p.min<24).sort((a,b)=>(b.outside??0)-(a.outside??0))[0]?.name;
  const names=[...top,'Stephen Curry','Nikola Jokić','Victor Wembanyama','Rudy Gobert',bench];
  const row=n=>{const p=P.find(x=>x.name===n);return p?{name:n,ovr:p.ovr,min:p.min,pos:p.pos,...Object.fromEntries(keys.map(k=>[k,p[k]==null?null:Math.round(p[k]*10)/10]))}:{name:n,missing:true}};
  const stats=Object.fromEntries(keys.map(k=>{const v=pool.map(p=>p[k]).filter(x=>x!=null),m=v.reduce((a,b)=>a+b,0)/v.length,s=Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/v.length);return [k,{n:v.length,mean:m,sd:s,min:Math.min(...v),max:Math.max(...v),ge99:v.filter(x=>x>=99).length}]}));
  const curry=P.find(p=>p.name==='Stephen Curry');
  return {rows:names.map(row),stats,poolN:pool.length,curryOutsideRows:curry?.tips?.outside?.rows.map(r=>r[0]),bench,
    pg:(n=>{const p=P.find(x=>x.name===n);return {name:n,pos:p?.pos,min:p?.min,rows:p?.tips?.handle?.rows.map(r=>r[0])}})(${JSON.stringify(res.pgName)}),
    tipCounts:Object.fromEntries(keys.map(k=>[k,P.filter(p=>p.tips&&p.tips[k]).length])),
    maxRows:Math.max(...P.flatMap(p=>Object.values(p.tips||{}).map(t=>t.rows.length))),
    atip:['offR','defR','play','outside','inside','handle','offball','perim'].map(k=>[k,!!ATIP[k]])}})())`));
fs.writeFileSync(OUT + '/res.json', JSON.stringify(res, null, 1));
console.log(JSON.stringify({ logs: res.logs, def: [res.desk_default, res.mob_default], pg: res.pgName, mobfirst: res.mob_first, sortAfter: [res.desk_sort_after_switch, res.mob_sort_after_switch] }));
ws.close(); ch.kill(); process.exit(0);
