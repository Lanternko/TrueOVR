"""球隊戰力排行檢視（使用者 2026-11-02「直接合併單頁」）：嵌進名單頁當第二個檢視，和球員分頁共用同一個眉頭，切換不重載。
用 Shadow DOM 隔離樣式（名單頁的 .pn／.av／.seg／table 規則不會污染排行表；色票與字型變數從名單頁繼承）；
資料放獨立的 teams-data.json（build_teams_page.py 產生），第一次進排行（或閒置時預載）才 fetch，每日只更新傷病時不用重建 2.3 MB 的名單頁。
網址：/rank/＝排行；/rank/LAL/＝展開某隊。對外 API：window.PureRank = {ensure(), open(abbr)}，檢視切換由 site_header.JS 負責。"""

STYLE = """@import url("https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@1,700;1,800&family=Barlow+Condensed:wght@600;700&display=swap");
*{box-sizing:border-box}
:host{--nf:"Barlow Condensed","Arial Narrow",Impact,sans-serif}
:host{display:block}
.rkroot{color:var(--fg);font-family:var(--f-body);font-size:14px}
.rkw{max-width:1360px;margin:0 auto;padding-block:16px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:12px}
@media (min-width:641px){.rkw{max-width:min(1360px,calc(var(--tw,1328px) + 32px))}}
.hd{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;border-bottom:3px solid var(--fg);padding-bottom:10px}
h1{font:italic 800 4.2rem/.85 var(--nf);text-transform:uppercase;margin:0;letter-spacing:-.01em}
h1 span{display:block;font:600 1rem var(--f-body);font-style:normal;letter-spacing:.3em;color:var(--muted);margin-top:8px;text-transform:none}
.stamp{white-space:nowrap;font:700 1.15rem/1.2 var(--nf);text-transform:uppercase;letter-spacing:.06em;text-align:right;color:var(--muted)}
.stamp b{display:block;color:var(--fg);font-size:1.9rem;font-style:italic;font-weight:800}
.meta{color:var(--muted);font-size:.82rem;line-height:1.5}
.meta b{color:var(--fg);font-weight:600}
.warn{color:var(--gold)}
.vctl{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.seg{display:flex;border:1px solid var(--line);border-radius:3px;overflow:hidden}
.seg button{background:var(--panel);color:var(--muted);border:0;border-right:1px solid var(--line);font:600 .95rem var(--f-disp);letter-spacing:.04em;padding:7px 14px;cursor:pointer}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--gold);color:var(--gold-ink)}
.hint{color:var(--muted);font-size:.78rem}
button:focus-visible,th:focus-visible,tr.row:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.tbox{overflow:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
thead th{background:var(--bg,#0d1014);color:var(--muted);font:700 1.3rem var(--nf);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;text-align:right;cursor:pointer;user-select:none;white-space:nowrap;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
thead th.l,td.l{text-align:left}
thead th .zh{display:block;font:500 .85rem var(--f-body);opacity:.8}
thead th[aria-sort]{color:#fff;font-weight:700;box-shadow:inset 0 0 0 999px rgba(255,255,255,.05)}
thead th[aria-sort] .zh{color:#fff;font-weight:700;opacity:1}
td.sorted{box-shadow:inset 0 0 0 999px rgba(255,255,255,.05)}
td{padding:5px 8px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap;font:600 1.05rem var(--nf);letter-spacing:.02em}
tr.row{cursor:pointer}
tr.row:hover td{background:#1a2128}
tr.row.open td{background:#1d252d}
td.rk{width:72px;text-align:right;padding-right:14px;font:italic 800 1.7rem/1 var(--nf);letter-spacing:-.02em}
td.tm{font:italic 800 1.3rem/1 var(--nf);text-transform:uppercase;letter-spacing:.01em}
td.tm .tmw{display:flex;align-items:center;gap:9px}
td.tm .lg{width:32px;height:32px;flex:none;object-fit:contain}
td.tm .tt{min-width:0}
td.tm small{display:block;font:500 .7rem var(--f-body);font-style:normal;text-transform:none;color:var(--muted);letter-spacing:.04em;margin-top:2px}
td.net{font:italic 800 1.7rem/1 var(--nf);letter-spacing:-.01em}
.pos{color:var(--g-a)}.neg{color:var(--g-f)}
.inj{color:var(--g-f)}
tbody tr.row td:not(.rk):not(.net):not(.tm){color:var(--muted)}
.det td{padding:0;background:#10151a;white-space:normal;text-align:left}
.dg{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:14px;padding:14px 16px 18px;align-items:start}
.dg>div{background:var(--panel);border:1px solid var(--line);border-radius:4px;overflow:hidden}
.dg h3{margin:0;padding:10px 12px;border-bottom:1px solid var(--line);font:700 .95rem var(--f-body);letter-spacing:.02em;color:var(--fg);display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.dg h3 small{font:500 .74rem var(--f-body);color:var(--muted)}
.dg table{font-size:.88rem}
.dg thead th{position:static;background:transparent;font:600 .74rem var(--f-body);letter-spacing:.04em;text-transform:none;color:var(--muted);padding:6px 12px;cursor:default;border-bottom:1px solid var(--line);text-align:right;box-shadow:none}
.dg thead th.l{text-align:left}
.dg td{padding:7px 12px;border-bottom:1px solid #1a2128;white-space:normal;font:500 .9rem var(--f-body);letter-spacing:0;vertical-align:middle}
.dg tbody tr:last-child td{border-bottom:0}
.dg td.n{min-width:9.5em;overflow-wrap:break-word;text-align:left;font-weight:600}
.dg td.num{font:700 1rem var(--nf);text-align:right;white-space:nowrap;width:1%}
.mn{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.mn i{display:block;width:64px;height:5px;border-radius:3px;background:#1d252d;overflow:hidden}
.mn i b{display:block;height:100%;background:var(--muted);opacity:.75}
.pill{display:inline-block;padding:2px 9px;border-radius:99px;font:700 .74rem var(--f-body);letter-spacing:.02em;white-space:nowrap;border:1px solid transparent}
.s-out{color:var(--g-f);background:color-mix(in srgb,var(--g-f) 16%,transparent);border-color:color-mix(in srgb,var(--g-f) 40%,transparent)}
.s-dbt,.s-q{color:var(--gold);background:color-mix(in srgb,var(--gold) 14%,transparent);border-color:color-mix(in srgb,var(--gold) 38%,transparent)}
.s-q{opacity:.85}
.s-p{color:var(--g-a);background:color-mix(in srgb,var(--g-a) 14%,transparent);border-color:color-mix(in srgb,var(--g-a) 38%,transparent)}
.rb b{display:block;color:var(--gold);font:700 .9rem var(--f-body)}
.rb b.far{color:var(--g-f)}
.rb small{display:block;color:var(--muted);font:500 .72rem var(--f-body);margin-top:1px}
.chips{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:3px 10px;font:500 .8rem var(--f-body);color:var(--muted);white-space:nowrap}
.chip b{font:700 1rem var(--nf);margin-left:5px;color:var(--fg)}
.chip b.pos{color:var(--g-a)}.chip b.neg{color:var(--g-f)}
.tname{font:italic 800 1.25rem var(--nf);text-transform:uppercase;margin-right:6px}
.pn{display:flex;align-items:center;gap:9px;min-width:0}
.av{flex:none;width:34px;height:34px;border-radius:50%;background:var(--panel-2);border:1px solid var(--line);overflow:hidden;display:block}
.av img{display:block;width:100%;height:100%;object-fit:cover;object-position:50% 12%}
.pn>span:last-child{min-width:0}
.sum{grid-column:1/-1;color:var(--muted);font-size:.8rem}
.cm{color:var(--muted);font-size:.74rem;display:block;white-space:normal;max-width:46ch}
.cm.rt{color:var(--gold)}
.note{color:var(--muted);font-size:.8rem;line-height:1.7;border-top:1px solid var(--line);padding-top:10px}
.note b,.meta b{color:var(--fg);font-weight:600}
.note em,.meta em{color:var(--gold);font-style:normal;font-weight:600}
.meta .nb{margin:0;padding-left:1.2em;color:var(--muted)}
.meta .warn{display:block}
@media (max-width:900px){.hide-m{display:none}}
@media (max-width:760px){.dg{grid-template-columns:minmax(0,1fr)}.cm{max-width:none}}
@media (max-width:640px){
  .rkroot{font-size:13px}
  h1{font-size:2.6rem}
  .stamp{font-size:.9rem}.stamp b{font-size:1.1rem}
  td.rk{width:40px;font-size:1.4rem;padding-right:8px}
  td.tm{font-size:1.1rem}
  td.net{font-size:1.5rem}
  .hide-m,thead th .zh{display:none}
  .dg{padding:10px 10px 14px}
  .dg td{padding:7px 8px}.dg thead th{padding:6px 8px}
  .dg td:not(:first-child){white-space:nowrap;font-size:.8rem}
  .dg>div:last-child .av{display:none}
  .dg td.n{min-width:8em}.pill{padding:2px 7px;font-size:.7rem}.mn i{width:44px}
  .rkw{gap:10px}
  td{padding:5px 4px}
  thead th{padding:7px 4px;font-size:1rem;letter-spacing:.02em}
  td.tm small{display:none}
  td.tm .tmw{gap:6px}
  td.tm .lg{width:26px;height:26px}
  .av{width:30px;height:30px}
  .pn{gap:7px}
  td.net{font-size:1.6rem}
  .seg button{padding:9px 16px}
  .vctl{gap:6px}
}
.msg{color:var(--muted);padding:40px 16px;text-align:center}
tr[data-pid]{cursor:pointer}
tr[data-pid]:hover td{background:#18202a}
tr[data-pid]:focus-visible{outline:2px solid var(--gold);outline-offset:-2px}"""

# 球員卡彈窗（使用者 2026-11-05「點球員會出現球員卡，依 OVR 五種等級，雙面」）：樣式照 docs/card-design/demo-frost-tiers.html（霧鑽五階），
# 類別名改掉和排行表撞名的 .hd／.sum；五階門檻沿用名單表 OVR 色框的 70／80／90／100（110+ 併進 100+）。
CARD_CSS = """
.pcov{position:fixed;inset:0;z-index:100;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;
  background:rgba(4,6,10,.72);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);padding:16px}
.pcov[hidden]{display:none}
.pcov *{margin:0}
.pcov .pcx{position:absolute;top:max(12px,env(safe-area-inset-top,0px));right:max(12px,env(safe-area-inset-right,0px));width:40px;height:40px;border-radius:50%;border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.08);color:#fff;font:400 22px/1 system-ui;cursor:pointer}
.pcov .pcx:hover{background:rgba(255,255,255,.16)}
.pcov .pch{color:rgba(255,255,255,.6);font:500 12px/1 var(--f-body);letter-spacing:.12em}
.pcs{--pcz:1;scale:var(--pcz);transform-origin:50% 50%}
@media (min-width:700px) and (min-height:720px){.pcs{--pcz:1.25}.pcov{gap:72px}}
@media (min-width:700px) and (min-height:900px){.pcs{--pcz:1.4}.pcov{gap:110px}}
.stage{perspective:900px}
.flip{--rx:0deg;--ry:0deg;--fl:0deg;position:relative;width:300px;height:430px;transform-style:preserve-3d;cursor:pointer;
  transform:rotateX(var(--rx)) rotateY(calc(var(--fl) + var(--ry)));transition:transform .6s cubic-bezier(.3,.7,.2,1)}
.flip.live{transition:transform .04s linear}
.flip.fb{--fl:180deg}
.pcov .card{--nf2:'Bebas Neue',Impact,'Arial Narrow',sans-serif;--sport:'Barlow Condensed','Arial Narrow',sans-serif;--tc:var(--f-body),'Noto Sans TC','Microsoft JhengHei',sans-serif;
  position:absolute;inset:0;width:300px;height:430px;border-radius:18px;overflow:hidden;isolation:isolate;font-family:var(--tc);user-select:none;
  -webkit-backface-visibility:hidden;backface-visibility:hidden}
.pcov .card.back{transform:rotateY(180deg)}
.card>*{position:absolute}
.card .bg,.card .fx,.card .fx2{inset:0;pointer-events:none}
.portrait{left:0;right:0;top:0;height:300px;overflow:hidden;z-index:2}
.portrait img{position:absolute;left:50%;transform:translateX(-50%);bottom:-8px;height:274px;width:auto;max-width:none;filter:drop-shadow(0 8px 14px rgba(0,0,0,.45))}
.portrait svg{position:absolute;left:50%;transform:translateX(-50%);bottom:0;height:80%;opacity:0}
.noimg .portrait img{display:none}
.noimg .portrait svg{opacity:.55}
.ovr{left:16px;top:8px;z-index:4;line-height:.8}
.ovr b{display:block;font:400 112px/0.86 var(--nf2);letter-spacing:-.01em}
.plate{left:0;right:0;top:282px;z-index:5;height:50px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:1px}
.plate .name{font:400 30px/1 var(--nf2);letter-spacing:.09em;white-space:nowrap}
.plate .zh{font:500 11px/1 var(--tc);letter-spacing:.3em;opacity:.8;margin-top:3px}
.mt{position:absolute;width:var(--len,110px);height:2px;border-radius:2px;transform-origin:100% 50%;opacity:0;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.8) 60%,#fff);filter:drop-shadow(0 0 3px var(--glow)) drop-shadow(0 0 1px rgba(60,30,60,.35))}
.mt::after{content:"";position:absolute;right:-1px;top:50%;width:4px;height:4px;margin-top:-2px;border-radius:50%;background:#fff;box-shadow:0 0 6px 2px #fff,0 0 12px 4px var(--glow)}
.mist{--fs:46px;--fa:.12;color:#fff;box-shadow:0 18px 48px -14px var(--glow),0 0 40px -8px var(--glow)}
.mist::after{content:"";position:absolute;inset:0;border-radius:inherit;z-index:7;pointer-events:none;box-shadow:0 0 0 1px rgba(255,255,255,.85) inset,0 0 0 5px rgba(255,255,255,.14) inset,0 0 0 6px var(--rim) inset}
.mist .bg{background:
  repeating-linear-gradient(0deg,rgba(255,255,255,0) 0 calc(var(--fs) + 8px),rgba(255,255,255,calc(var(--fa) * .55)) calc(var(--fs) + 8px) calc(var(--fs) + 9px)),
  repeating-linear-gradient(60deg,rgba(255,255,255,0) 0 var(--fs),rgba(255,255,255,var(--fa)) var(--fs) calc(var(--fs) + 1px)),
  repeating-linear-gradient(-60deg,rgba(255,255,255,0) 0 var(--fs),rgba(255,255,255,calc(var(--fa) * .7)) var(--fs) calc(var(--fs) + 1px)),
  conic-gradient(from 200deg at 62% 34%,var(--k0) 0deg,var(--k1) 40deg,var(--k2) 95deg,var(--k3) 150deg,var(--k4) 200deg,var(--k5) 255deg,var(--k6) 310deg,var(--k0) 360deg)}
.mist .bg::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.18),rgba(255,255,255,0) 40%)}
.mist .portrait{height:310px;-webkit-mask-image:linear-gradient(180deg,#000 74%,transparent 96%);mask-image:linear-gradient(180deg,#000 74%,transparent 96%)}
.mist .portrait img{bottom:-22px;height:302px;filter:drop-shadow(0 0 1px #fff) drop-shadow(0 0 12px var(--glow)) drop-shadow(0 8px 12px rgba(20,20,30,.4))}
.mist .ovr b{background:linear-gradient(180deg,#fff 5%,#fff 40%,var(--num1) 100%);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 1px 0 #fff) drop-shadow(0 3px 0 var(--num2)) drop-shadow(0 7px 10px var(--glow))}
.fade{left:0;right:0;bottom:0;top:262px;z-index:4;background:linear-gradient(180deg,transparent 0,var(--plate) 22%,var(--plate2) 100%);pointer-events:none}
.mist .plate .name{text-shadow:0 2px 8px var(--stdk)}
.stats{z-index:5;display:grid}
.st{position:relative;display:flex;flex-direction:column;align-items:center;gap:4px}
.st b{font:400 38px/.9 var(--nf2);letter-spacing:.02em;text-shadow:0 1px 6px var(--stdk)}
.st em{font:italic 700 11px/1 var(--sport);letter-spacing:.16em;text-transform:uppercase;text-shadow:0 1px 4px var(--stdk)}
.st.free b,.st.free em{opacity:.58}
.stats.m-row{grid-template-columns:1fr 1fr 1.05fr;left:14px;right:14px;bottom:16px;align-items:center}
.m-row .st.core{padding:0 6px;gap:6px}
.m-row .st.core+.st.core::before{content:"";position:absolute;left:0;top:10%;bottom:6%;width:1px;background:rgba(255,255,255,.26)}
.m-row .st.core b{font-size:56px}
.m-row .st.core em{font-size:13px}
.stk{position:relative;display:flex;flex-direction:column;justify-content:center;gap:0;padding-left:14px}
.stk::before{content:"";position:absolute;left:0;top:10%;bottom:6%;width:1px;background:rgba(255,255,255,.26)}
.stk .st{flex-direction:row;justify-content:space-between;align-items:baseline;gap:8px;padding:5px 2px}
.stk .st+.st{border-top:1px solid rgba(255,255,255,.2)}
.stk .st b{font-size:24px}
.stk .st em{font-size:9.5px;letter-spacing:.12em}
.c-pink{--k0:#f8f3f6;--k1:#efd9e6;--k2:#e3c0d4;--k3:#f4e6ee;--k4:#fffafd;--k5:#ebd0df;--k6:#d4a9c2;
  --glow:#ffb8dc88;--rim:rgba(255,255,255,.45);--plate:rgba(122,66,102,.5);--plate2:rgba(98,44,80,.88);--stdk:#5e2f4c;--num1:#f0cfe1;--num2:#b07a98}
.c-ice{--k0:#f1f6fb;--k1:#d6e6f4;--k2:#b8d2ea;--k3:#e6f0f9;--k4:#fafdff;--k5:#c4dcf0;--k6:#94b9d9;
  --glow:#8fc8ff88;--rim:rgba(255,255,255,.45);--plate:rgba(52,96,140,.5);--plate2:rgba(24,60,104,.88);--stdk:#1c426f;--num1:#cfe4f6;--num2:#5f8fba}
.c-gold{--k0:#fbf6ec;--k1:#f1e2c2;--k2:#e3cc9c;--k3:#f6ecd4;--k4:#fffdf6;--k5:#ead7ab;--k6:#c7a768;
  --glow:#ffd57a88;--rim:rgba(255,246,214,.7);--plate:rgba(122,90,30,.5);--plate2:rgba(92,64,14,.88);--stdk:#5c4010;--num1:#f3e2b8;--num2:#a98438}
.c-violet{--k0:#f6f2fb;--k1:#e2d6f2;--k2:#cbb8e6;--k3:#eee6f8;--k4:#fcfaff;--k5:#d6c6ec;--k6:#a68cce;
  --glow:#b99aff88;--rim:rgba(255,255,255,.45);--plate:rgba(84,54,128,.5);--plate2:rgba(52,28,92,.88);--stdk:#3a2060;--num1:#e0d3f4;--num2:#8a6bb8}
.c-steel{--k0:#f3f4f6;--k1:#dcdfe4;--k2:#c3c8d0;--k3:#e8eaee;--k4:#fbfbfc;--k5:#ced2d9;--k6:#9aa1ac;
  --glow:#b4bccb88;--rim:rgba(255,255,255,.5);--plate:rgba(56,64,80,.5);--plate2:rgba(28,34,46,.9);--stdk:#202633;--num1:#dfe2e7;--num2:#7a828f}
.fx2{z-index:6;overflow:hidden;border-radius:inherit}
.t1{--fs:54px;--fa:.07;box-shadow:0 10px 24px -14px var(--glow)}
.t1::after{box-shadow:0 0 0 1px rgba(255,255,255,.6) inset !important}
.t2{--fs:42px;--fa:.11;box-shadow:0 14px 34px -14px var(--glow),0 0 26px -10px var(--glow)}
.t3{--fs:34px;--fa:.16}
.t3::after{box-shadow:0 0 0 1px #fff inset,0 0 0 4px rgba(190,160,255,.55) inset,0 0 0 5px rgba(255,255,255,.3) inset !important}
.t4{--fs:26px;--fa:.22;box-shadow:0 20px 56px -12px var(--glow),0 0 54px -4px var(--glow)}
.t4::after{box-shadow:0 0 0 1px #fff3c4 inset,0 0 0 4px rgba(255,214,120,.6) inset,0 0 0 6px rgba(255,255,255,.35) inset !important}
.t5{--fs:18px;--fa:.3;box-shadow:0 20px 60px -10px #ff7ac8aa,0 0 56px -2px #ffb8e0aa}
.t5::after{box-shadow:0 0 0 1px #fff inset !important}
.t3 .fx2::before,.t4 .fx2::before,.t5 .fx2::before{content:"";position:absolute;inset:0;mix-blend-mode:soft-light;background:linear-gradient(115deg,rgba(255,255,255,0) calc(var(--gp,50%) - 30%),rgba(255,255,255,.26) var(--gp,50%),rgba(255,255,255,0) calc(var(--gp,50%) + 30%))}
.t4 .fx2::before{background:linear-gradient(115deg,rgba(255,246,214,0) calc(var(--gp,50%) - 30%),rgba(255,246,214,.32) var(--gp,50%),rgba(255,246,214,0) calc(var(--gp,50%) + 30%))}
.t5 .fx2::before{background:linear-gradient(115deg,rgba(255,230,246,0) calc(var(--gp,50%) - 30%),rgba(255,230,246,.4) var(--gp,50%),rgba(255,230,246,0) calc(var(--gp,50%) + 30%))}
.t5 .fx2::after{content:"";position:absolute;inset:0;border-radius:18px;padding:4px;background:conic-gradient(from var(--ang,0deg),#ff8fd0,#fff,#ffc2e6,#ff5fb8,#fff,#ff8fd0);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#000 0 0) content-box exclude,linear-gradient(#000 0 0)}
.t5 .mt{background:linear-gradient(90deg,transparent,rgba(255,200,232,.7) 70%,#fff)}
.mist.back{--fa:.07}
.back{box-shadow:0 12px 30px -14px var(--glow)}
.back .tint{inset:0;z-index:1;background:var(--plate2);opacity:.8;pointer-events:none}
.back .bg::after{background:radial-gradient(90% 40% at 30% 0%,rgba(255,255,255,.2),rgba(255,255,255,0))}
.back .bk{inset:0;z-index:4;padding:20px 22px 0}
.bk .bhd{display:flex;justify-content:space-between;align-items:flex-end;gap:8px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,.28)}
.bk .bhd .n{font:400 27px/1 var(--nf2);letter-spacing:.09em;white-space:nowrap;text-shadow:0 1px 6px var(--stdk)}
.bk .bhd .z{font:500 10px/1 var(--tc);letter-spacing:.28em;opacity:.78;margin-top:5px}
.bk .bhd .o{font:400 56px/.8 var(--nf2);background:linear-gradient(180deg,#fff 20%,var(--num1));-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 2px 6px var(--stdk))}
.bk .cols{display:grid;grid-template-columns:1fr 1fr;column-gap:20px;margin-top:10px}
.bk .gh{font:700 11px/1 var(--tc);letter-spacing:.4em;color:#fff;display:flex;align-items:center;gap:8px;padding:5px 0 3px;margin:4px 0 0;text-shadow:0 1px 3px var(--stdk)}
.bk .gh::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,rgba(255,255,255,.6),rgba(255,255,255,0))}
.bk .gh:first-child{margin-top:0}
.ab{position:relative;display:grid;grid-template-columns:1fr auto;align-items:baseline;height:32px;padding-top:3px}
.ab .l{font:500 12px/1 var(--tc);letter-spacing:.06em;opacity:.88}
.ab .l i{font:italic 600 9.5px var(--sport);letter-spacing:.12em;opacity:.62;margin-left:5px}
.ab b{font:400 21px/1 var(--nf2);letter-spacing:.02em;opacity:.9}
.ab s{grid-column:1/3;align-self:end;margin-bottom:4px;height:4px;border-radius:2px;background:rgba(0,0,0,.4);box-shadow:0 0 0 1px rgba(255,255,255,.08);position:relative;overflow:hidden}
.ab s::after{content:"";position:absolute;left:0;top:0;bottom:0;width:var(--w);border-radius:2px;background:linear-gradient(90deg,rgba(255,255,255,.75),#fff);opacity:.7}
.ab.top b{opacity:1;color:#fff;text-shadow:0 0 8px var(--glow)}
.ab.top .l{opacity:1;font-weight:700}
.ab.top s::after{opacity:1;box-shadow:0 0 6px var(--glow)}
.bk .bsum{position:absolute;left:22px;bottom:50px;width:128px;display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid rgba(255,255,255,.28)}
.bk .bsum div{display:flex;flex-direction:column;gap:3px}
.bk .bsum b{font:400 44px/.85 var(--nf2);text-shadow:0 1px 6px var(--stdk)}
.bk .bsum em{font:italic 700 11px/1 var(--sport);letter-spacing:.16em;opacity:.78}
.bk .ft{position:absolute;left:22px;right:22px;bottom:14px;display:flex;justify-content:space-between;font:italic 600 9.5px/1 var(--sport);letter-spacing:.24em;opacity:.55;border-top:1px solid rgba(255,255,255,.2);padding-top:8px}
@media (prefers-reduced-motion:reduce){.flip{transition:none}.mt{display:none}}"""

STYLE += CARD_CSS

BODY = """<div class="rkroot"><div class="msg" id="msg">載入中…</div>
<div class="rkw" id="rkw" hidden>
<div class="hd"><h1>Power Ranking</h1><div class="stamp" id="stamp"></div></div>
<div class="meta" id="meta"></div>
<div class="vctl"><div class="seg" id="viewSeg" role="group" aria-label="名單版本"><button type="button" data-v="today" aria-pressed="true">可用</button><button type="button" data-v="c" aria-pressed="false">全員</button></div>
<span class="hint" id="viewHint"></span></div>
<div class="tbox"><table id="tbl"><thead><tr>
<th data-k="rank" class="rk">#</th><th data-k="name" class="l">球隊</th><th data-k="net" aria-sort="descending">NetRtg<span class="zh">淨效率</span></th>
<th data-k="ortg" class="hide-m">OffRtg<span class="zh">進攻</span></th><th data-k="drtg" class="hide-m">DefRtg<span class="zh">防守</span></th>
<th data-k="wpct">戰績<span class="zh">W-L</span></th><th data-k="pred">預測勝場<span class="zh">全季</span></th><th data-k="nOut">傷兵<span class="zh">不可用</span></th>
</tr></thead><tbody id="tb"></tbody></table></div>
<div class="note" id="note"></div>
</div>
<div class="pcov" id="pcov" hidden role="dialog" aria-modal="true" aria-label="球員卡"><button type="button" class="pcx" id="pcx" aria-label="關閉">×</button><div class="pcs" id="pcs"></div><div class="pch">點卡片翻面　·　點外面或 Esc 關閉</div></div>
</div>"""

JS = r"""<script>(()=>{
const host=document.getElementById('rankHost'),tpl=document.getElementById('rankTpl');if(!host||!tpl)return;
const root=host.attachShadow({mode:'open'});root.append(tpl.content.cloneNode(true));
let D=null,T=[],loading=null;
const $=s=>root.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let view=(()=>{try{return localStorage.getItem('bbac.teamsView')==='c'?'c':'today'}catch(e){return 'today'}})(),sk='net',sd=-1,open=null;
const CDN='https://cdn.nba.com/';
const logo=id=>id?'<img class="lg" alt="" loading="lazy" src="'+CDN+'logos/nba/'+id+'/global/D/logo.svg" onerror="this.style.visibility=\'hidden\'">':'<span class="lg"></span>';
const av=pid=>'<span class="av">'+(pid?'<img alt="" loading="lazy" src="'+CDN+'headshots/nba/latest/260x190/'+pid+'.png" onerror="this.remove()">':'')+'</span>';
const f1=v=>(v>=0?'+':'')+v.toFixed(1),f0=v=>v.toFixed(1);
const TC={ATL:'#E5384B',BOS:'#2EA66B',BKN:'#E6E6E6',CHA:'#1FA3CC',CHI:'#E3294F',CLE:'#C8305A',DAL:'#4A90D9',DEN:'#FEC524',DET:'#E5324B',GSW:'#FFC72C',HOU:'#E5324B',IND:'#FDBB30',LAC:'#E8365A',LAL:'#FDB927',MEM:'#7C9FE0',MIA:'#E5324B',MIL:'#3BAA6E',MIN:'#4F9FE0',NOP:'#D7B26A',NYK:'#F58426',OKC:'#3AA3E0',ORL:'#3A8FDC',PHI:'#3B8BDB',PHX:'#F27A28',POR:'#E5324B',SAC:'#9A7BE0',SAS:'#C4CED4',TOR:'#E5324B',UTA:'#A78BFA',WAS:'#E5324B'};     // 球隊主題色（深底可讀的亮度版）
const absO=v=>D.lgOrtg==null?f1(v.ortg):f0(v.ortg+D.lgOrtg),absD=v=>D.lgDrtg==null?f1(v.drtg):f0(v.drtg+D.lgDrtg);     // 官方寫法：每百回合得／失分；舊資料沒有聯盟平均時退回「相對聯盟」
const cls=v=>v>=0?'pos':'neg';
const d10=s=>s?String(s).slice(0,10):'';
const stc=st=>/^out/i.test(st)?'s-out':/^doubt/i.test(st)?'s-dbt':/^prob/i.test(st)?'s-p':'s-q';
const retCell=x=>{const out=x.missGames!=null,g=out?'缺 '+x.missGames+' 場':'',t=x.date?' title="資料日期 '+esc(d10(x.date))+'"':'';
 return x.returnDate?'<div class="rb"'+t+'><b'+(out&&x.missGames>=20?' class="far"':'')+'>'+esc(String(x.returnDate).slice(5,10))+(String(x.returnDate).slice(0,4)!==String(D.generatedAt||'').slice(0,4)?'<span style="font-weight:500;opacity:.7"> '+esc(String(x.returnDate).slice(0,4))+'</span>':'')+' 回歸</b>'+(g?'<small>'+g+'</small>':'')+'</div>'
  :'<div class="rb"'+t+'><b class="far">整季缺陣</b><small>無回歸日'+(g?'・'+g:'')+'</small></div>'};
function info(){
  const i=D.injuries||{};
  $('#stamp').innerHTML='<b title="資料截至 '+esc(D.dataCutoff)+' 已打完的比賽">'+esc(D.generatedAt.slice(0,10))+'</b>'+esc(D.generatedAt.slice(11,16))+' 更新';
  const isT=D.engineKind==='t';
  $('#meta').innerHTML='<ul class="nb"><li>'+(isT?'由<b>過去五季上場陣容得失分</b>訓練的<b>陣容模型（Transformer）</b>估計：依輪替分鐘抽出<b>五人陣容</b>，對<b>其他 29 隊各 '+D.opponent.drawsPerTeam+' 組陣容</b>對戰平均得出。'
     :'由模型<b>模擬比賽</b>（每隊對五支不同強度與位置配置的對手隊共打 <b>'+D.seeds+' 場</b>）得出。')+(isT&&D.actualBlend&&D.actualBlend.on?'再加上<b>本季實際戰果</b>：每隊已打的每場「實際得失分 − 用今天陣容強度重算的預期」累積後除以<b>（已打場數＋'+D.actualBlend.k+'）</b>加回，打越多場實際表現佔越重。':'')+'<em>目前還在 beta 版本</em>，僅供參考。</li>'
   +(isT?'':'<li><b>76 人被低估</b>：模型認為同隊持球單打手太多、彼此搶球，化學反應不佳。</li>')+'</ul>'
   +(i.stale&&(!i.fetchedAt||Date.now()-Date.parse(i.fetchedAt)>3*864e5)?'<span class="warn">傷病名單已超過三天沒更新。</span>':'')
   +(D.schedule&&D.schedule.remainingGames?'':'<span class="warn">抓不到賽程，剩餘場次以對全聯盟平均勝率計。</span>');
  $('#viewHint').textContent=view==='today'?'排除傷兵':'全員健康的版本';
  $('#note').innerHTML='<em>效率指標</em>：<b>OffRtg／DefRtg</b> 為每百回合得分／失分（<b>DefRtg 越低防守越好</b>），<b>NetRtg＝OffRtg−DefRtg</b>。主表顯示<b>今天的陣容</b>。'
   +'<br><em>上場時間</em>：取球員<b>近 '+D.lastN+' 場有出賽的平均分鐘</b>，依<b>焦灼比賽</b>（分差 5 分內或延長賽）主力縮輪替的比例調整並<b>湊滿 240 分鐘</b>，<b>單人上限 36 分鐘</b>（未滿 7 人時放寬至 40）。近期未出賽但<b>場均滿 '+(D.returnMin||15)+' 分鐘</b>者視為傷癒復出，照常排入輪替。'
   +'<br><em>可用／全員</em>：<b>「可用」</b>排除 <b>Out、Doubtful、Questionable、Day-To-Day 與停賽</b>球員（<b>Probable 照常上場</b>），「傷兵」欄為排除人數；<b>「全員」</b>假設全隊健康。'
   +((D.baseProfiles||[]).length?'<br><em>過往賽季卡</em>：<b>上季整季缺陣、本季尚無排名</b>的球員（'+D.baseProfiles.map(x=>esc(x.name)).join('、')+'），OVR 欄暫標<b>最近一張賽季卡</b>。':'')
   +'<br><em>預測勝場</em>：<b>目前勝場＋剩餘賽程逐場勝率</b>（計入主客場與對手強弱）。<b>「可用」版依 ESPN 預計回歸日逐場更換陣容</b>，回歸日前缺陣、之後歸隊；'
   +((D.injuries&&D.injuries.outNoReturnDate)?'<span class="warn">目前有 '+D.injuries.outNoReturnDate+' 位缺陣者沒有回歸日（官方 PDF 備援不提供），視為整季缺陣。</span>':'<b>無回歸日者視為整季缺陣</b>。')+'「全員」版全程以健康陣容計算。';
}
function rows(){
  const R=T.map(t=>({t,v:t[view]})).sort((a,b)=>b.v.net-a.v.net).map((o,i)=>({...o,rank:i+1}));
  const val={rank:o=>o.rank,name:o=>o.t.name,net:o=>o.v.net,ortg:o=>o.v.ortg,drtg:o=>-o.v.drtg,wpct:o=>(o.t.W+o.t.L)?o.t.W/(o.t.W+o.t.L):0,pred:o=>o.v.predWins,nOut:o=>o.t.nOut};
  R.sort((a,b)=>{const x=val[sk](a),y=val[sk](b);return (x<y?-1:x>y?1:0)*sd||a.rank-b.rank});
  return R;
}
function detail(o){
  const t=o.t,v=o.v,back=new Set((t.restored||[]).map(x=>x.pid)),
  rot=v.rotation.map(r=>'<tr'+pidAttr(r.pid,r.name,r.ovr)+'><td class="n"><div class="pn">'+av(r.pid)+'<span>'+esc(r.name)+(back.has(r.pid)?'<span class="cm">傷缺復出：最近 10 場沒出場，自己平均 ≥'+(D.returnMin||15)+' 分</span>':'')+'</span></div></td><td class="num"><div class="mn"><i><b style="width:'+Math.min(100,r.min/40*100).toFixed(0)+'%"></b></i>'+r.min.toFixed(1)+'</div></td><td class="num">'+(r.ovr==null?'—':Math.round(r.ovr)+(r.ovrSrc?'<span class="cm">'+esc(r.ovrSrc)+'</span>':''))+'</td></tr>').join(''),
  inj=t.injured.length?t.injured.map(x=>'<tr'+pidAttr(x.playerId,x.name)+'><td class="n"><div class="pn">'+av(x.playerId)+'<span>'+esc(x.name)+(x.injury?'<span class="cm">'+esc(x.injury)+'</span>':'')+'</span></div></td><td class="num"><span class="pill '+stc(x.status)+'">'+esc(x.status)+'</span></td><td class="num">'+retCell(x)+'</td></tr>').join(''):'<tr><td class="n" colspan="3">傷病名單沒有這隊的人</td></tr>',
  chip=(k,val,c)=>'<span class="chip">'+k+'<b'+(c?' class="'+c+'"':'')+'>'+val+'</b></span>';
  return '<div class="dg"><div class="sum chips"><span class="tname"'+(TC[t.abbr]?' style="color:'+TC[t.abbr]+'"':'')+'>'+esc(t.name)+'</span>'+chip('OffRtg',absO(v),cls(v.ortg))+chip('DefRtg',absD(v),cls(-v.drtg))+chip('NetRtg',f1(v.net),cls(v.net))
   +chip('剩餘賽程',v.schedGames+' 場'+(v.poolGames?'<span style="font-weight:500;font-size:.75rem;color:var(--muted)">（'+v.poolGames+' 場以平均勝率補）</span>':''))
   +(t.actual?chip('本季比預期','每場 '+f1(t.actual.net)+'（'+t.actual.n+' 場，計入 '+f1(t.actual.netShr)+'）',cls(t.actual.net)):'')
   +(view==='today'&&v.lineupStates>1?chip('傷兵回歸陣容狀態',v.lineupStates+' 種'):'')+'</div>'
   +'<div><h3>'+(view==='today'?'可用輪替':'全員輪替')+'<small>每場分鐘／OVR</small></h3><table><thead><tr><th class="l">球員</th><th>分鐘</th><th>OVR</th></tr></thead><tbody>'+rot+'</tbody></table></div>'
   +'<div><h3>傷病名單<small>Probable 照常上場</small></h3><table><thead><tr><th class="l">球員</th><th>狀態</th><th>預計回歸</th></tr></thead><tbody>'+inj+'</tbody></table></div></div>';
}
function render(){
  const R=rows();
  $('#tb').innerHTML=R.map(o=>{const t=o.t,v=o.v;
    return '<tr class="row'+(open===t.abbr?' open':'')+'" data-a="'+t.abbr+'" tabindex="0"><td class="rk">'+o.rank+'</td><td class="tm l"><div class="tmw">'+logo(t.id)+'<div class="tt">'+esc(t.abbr)+'<small>'+esc(t.name)+'</small></div></div></td>'
     +'<td class="net '+cls(v.net)+'">'+f1(v.net)+'</td>'
     +'<td class="hide-m">'+absO(v)+'</td><td class="hide-m">'+absD(v)+'</td><td>'+t.W+'-'+t.L+'</td><td>'+f0(v.predWins)+'</td><td class="'+(t.nOut?'inj':'')+'">'+(t.nOut||'')+'</td></tr>'
     +(open===t.abbr?'<tr class="det"><td colspan="8">'+detail(o)+'</td></tr>':'');}).join('');
  root.querySelectorAll('#viewSeg button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v===view)));
  let si=-1;
  root.querySelectorAll('thead th').forEach((h,i)=>{if(h.dataset.k===sk){si=i;h.setAttribute('aria-sort',sd<0?'descending':'ascending');}else h.removeAttribute('aria-sort');});
  root.querySelectorAll('#tb tr.row').forEach(r=>r.children[si]?.classList.add('sorted'));
  info();
}
$('#tb').addEventListener('click',e=>{const r=e.target.closest('tr.row');if(!r)return;toggle(r.dataset.a);});
$('#tb').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){const r=e.target.closest('tr.row');if(r){e.preventDefault();toggle(r.dataset.a);$('#tb tr[data-a="'+r.dataset.a+'"]')?.focus();}}});
$('thead').addEventListener('click',e=>{const h=e.target.closest('th');if(!h)return;const k=h.dataset.k;if(k===sk)sd=-sd;else{sk=k;sd=(k==='name'||k==='rank')?1:-1;}render();});
$('#viewSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;view=b.dataset.v;try{localStorage.setItem('bbac.teamsView',view)}catch(_){}render();});

function toggle(a){open=open===a?null:a;render();if(/^\/rank\//.test(location.pathname))history.replaceState(null,'','/rank/'+(open?open+'/':''));}
function ensure(){
  if(!loading)loading=fetch('/teams-data.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(d=>{
    D=d;T=Object.entries(D.teams).map(([id,t])=>({...t,id}));$('#msg').hidden=true;$('#rkw').hidden=false;render();
  }).catch(()=>{loading=null;$('#msg').textContent='戰力排行載入失敗，重新整理再試一次。';});
  return loading;
}
/* ===== 球員卡彈窗（霧鑽五階、雙面；樣式見 docs/card-design/demo-frost-tiers.html） =====
   資料直接讀名單頁的全域 P（能力值、off/def）與 REAL（NBA 球員 id）；找不到的人不給點 */
const PC_TIERS=[[100,5,'pink','粉鑽'],[90,4,'gold','霧金'],[80,3,'violet','霧紫'],[70,2,'ice','霧藍'],[-1e9,1,'steel','霧銀']];
const PC_GROUPS=[['進攻',[['threeValue','3PT','三分'],['mid','MID','中距離'],['short','INS','近框'],['ft','FT','罰球'],['gravity','GRV','引力'],['foulDraw','FD','製造犯規']]],
 ['組織',[['pass','PASS','傳球'],['creation','CRT','自主創造']]],
 ['球權',[['rebound','REB','籃板'],['tovSkill','TO','少失誤'],['pressure','PRES','壓迫']]],
 ['防守',[['onBall','PER D','單防'],['help','RIM','護框']]]];
const PC_SIL='<svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg"><circle cx="100" cy="78" r="42" fill="#fff"/><path d="M20 260c0-62 32-100 80-100s80 38 80 100z" fill="#fff"/></svg>';
let PC_BY=null,PC_PCT=null;
const PC_KN=[[50,70],[90,88],[95,92],[99,97]];
function pcDisp(v){if(v<70)return v;if(v>99)return v-2;const q=(v-70)*49/29+50;   // season_nav.display_scale
  for(let i=1;i<PC_KN.length;i++){const[a,b]=PC_KN[i-1],[c,d]=PC_KN[i];if(q<=c)return b+(q-a)*(d-b)/(c-a);}return 97;}
function pcIndex(){
  if(PC_BY)return PC_BY;
  PC_BY={id:new Map(),name:new Map()};
  let PP=[],RR={};
  try{PP=P;RR=REAL;}catch(e){}           // 名單頁頂層 const；不在名單頁就沒有卡
  for(const p of PP){const r=RR[p.name];if(r&&r.id)PC_BY.id.set(String(r.id),p);PC_BY.name.set(p.name,p);}
  // OFF／DEF：和能力值同一套轉換（照引力 PctMapper＋R-168 尾巴）：池＝MPG≥20、本季≥5 場；池內百分位 → attr()（PR1→40、PR50→70、PR99→99）；
  // PR≥99 以上：一個標準差＝(PR99 值−PR90 值)/1.044（常態 z99−z90），每多 1 個標準差 +10 分、不設上限；最後套網站顯示尺（方案 B，R-138）。
  const pool=PP.filter(p=>(p.min||0)>=20&&(p.gp||0)>=5),PL=pool.length>=50?pool:PP;
  const pct=k=>{const v=PL.map(p=>p[k]).filter(x=>x!=null).sort((a,b)=>a-b),n=v.length;
    const pr=x=>{let lo=0,hi=n;while(lo<hi){const m=(lo+hi)>>1;if(v[m]<x)lo=m+1;else hi=m;}let h=lo;while(h<n&&v[h]===x)h++;return 100*(lo+.5*(h-lo))/n;};
    const at=q=>Math.max(40,Math.min(99,q<50?40+(q-1)*30/49:70+(q-50)*29/49));
    const r90=v.find(x=>pr(x)>=90),r99=v.find(x=>pr(x)>=99),S=(r99-r90)/1.044;
    return x=>{if(x==null||n<2)return null;const q=pr(x);return Math.round(pcDisp(q>=99&&S>0?99+10*(x-r99)/S:at(q)));};};
  PC_PCT={off:pct('off'),def:pct('def')};
  return PC_BY;
}
const pcFind=(pid,name)=>{const I=pcIndex();return I.id.get(String(pid))||I.name.get(name)||null;};
const pidAttr=(pid,name,ovr)=>pcFind(pid,name)?' data-pid="'+esc(pid||'')+'" data-nm="'+esc(name)+'"'+(ovr!=null?' data-ovr="'+ovr+'"':'')+' tabindex="0" title="看球員卡"':'';
function pcFonts(){
  if(document.getElementById('pcFonts'))return;
  const l=document.createElement('link');l.id='pcFonts';l.rel='stylesheet';
  l.href='https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:ital,wght@1,600;1,700&display=swap';
  document.head.appendChild(l);
}
const pcHt=i=>i?Math.floor(i/12)+"'"+(i%12)+'"':'';
const pcFit=(name,px,room)=>Math.min(px,Math.floor(room/(name.length*.5)));   // Bebas 大寫約 0.5em／字（含字距），長名字縮小不換行
function pcHTML(p,pid,ovr){
  const O=Math.round(ovr!=null?ovr:p.ovr),T=PC_TIERS.find(t=>O>=t[0]),[,tn,col,tname]=T;
  const NAME=p.name.toUpperCase(),sub=esc([String(p.team||'').split('/').pop(),p.pos,pcHt(p.ht)].filter(Boolean).join(' · '));
  const all=PC_GROUPS.flatMap(g=>g[1]).map(([k,s,zh])=>({k,s,zh,v:p[k]==null?null:Math.round(p[k])}));
  const top=[...all].filter(a=>a.v!=null).sort((a,b)=>b.v-a.v).slice(0,2);
  const off=PC_PCT.off(p.off),def=PC_PCT.def(p.def),dv=v=>v==null?'—':v;
  const one=(k,v,c,tip)=>'<div class="st '+c+'"'+(tip?' title="'+tip+'"':'')+'><b>'+dv(v)+'</b><em>'+k+'</em></div>';
  const img=pid?'<img alt="" src="'+CDN+'headshots/nba/latest/1040x760/'+esc(pid)+'.png" onerror="this.closest(\'.card\').classList.add(\'noimg\')">':'';
  const front='<div class="card mist face c-'+col+' t'+tn+(pid?'':' noimg')+'"><div class="bg"></div><div class="fx"></div>'
   +'<div class="portrait">'+PC_SIL+img+'</div><div class="ovr"><b'+(O>=100?' style="font-size:94px"':'')+'>'+O+'</b></div><div class="fade"></div>'
   +'<div class="plate"><div class="name" style="font-size:'+pcFit(NAME,30,268)+'px">'+esc(NAME)+'</div><div class="zh">'+sub+'</div></div>'
   +'<div class="stats m-row">'+one('OFF',off,'core','進攻：每 36 分鐘淨分換成能力值尺（PR50＝70、PR99＝97，頂尖不封頂）')+one('DEF',def,'core','防守：每 36 分鐘淨分換成能力值尺（PR50＝70、PR99＝97，頂尖不封頂）')
   +'<div class="stk">'+top.map(a=>one(a.s,a.v,'free',a.zh)).join('')+'</div></div><div class="fx2"></div></div>';
  const topK=new Set(top.map(a=>a.k));let i=0;
  const grp=g=>'<div class="gh">'+g[0]+'</div>'+g[1].map(()=>{const a=all[i++];return '<div class="ab'+(topK.has(a.k)?' top':'')+'" style="--w:'+Math.max(0,Math.min(100,a.v||0))+'%"><span class="l">'+a.zh+'<i>'+a.s+'</i></span><b>'+dv(a.v)+'</b><s></s></div>'}).join('');
  const L=grp(PC_GROUPS[0]),R=grp(PC_GROUPS[1])+grp(PC_GROUPS[2])+grp(PC_GROUPS[3]);
  const back='<div class="card mist back c-'+col+' t'+tn+'"><div class="bg"></div><div class="tint"></div><div class="bk">'
   +'<div class="bhd"><div><div class="n" style="font-size:'+pcFit(NAME,27,180)+'px">'+esc(NAME)+'</div><div class="z">'+sub+'</div></div><div class="o">'+O+'</div></div>'
   +'<div class="cols"><div>'+L+'</div><div>'+R+'</div></div>'
   +'<div class="bsum"><div><b>'+dv(off)+'</b><em>OFF</em></div><div><b>'+dv(def)+'</b><em>DEF</em></div></div>'
   +'<div class="ft"><span>T'+tn+' '+tname+'</span><span>2026-27</span></div></div></div>';
  return {tn,html:'<div class="stage"><div class="flip" id="pcf">'+front+back+'</div></div>'};
}
/* 流星：只有 T5 粉鑽；大半徑圓弧由右上往左下，不進名牌與數字區 */
const pcR=(a,b)=>a+Math.random()*(b-a);
function pcMeteor(box){
  const W=300,YMAX=250,len=pcR(80,140),dur=pcR(500,2400),fromTop=Math.random()<.2;
  const hx=fromTop?pcR(230,W):W+pcR(6,24),hy=fromTop?-8:pcR(-6,200);
  const Cx=950,Cy=2500,r=Math.hypot(Cx-hx,Cy-hy),a0=Math.asin((Cx-hx)/r),maxL=pcR(380,520),N=24,fr=[];
  for(let i=0;i<=N;i++){const s=i/N,al=a0+s*maxL/r,x=Cx-r*Math.sin(al),y=Cy-r*Math.cos(al);if(y>YMAX&&i>0)break;
    const op=s<.12?s/.12:s>.7?.9*(1-(s-.7)/.3):1;
    fr.push({offset:s,opacity:op,transform:'translate('+(x-hx).toFixed(1)+'px,'+(y-hy).toFixed(1)+'px) rotate('+(180-al*180/Math.PI).toFixed(1)+'deg)'});}
  fr[fr.length-1]={...fr[fr.length-1],offset:1,opacity:0};
  const m=document.createElement('span');m.className='mt';m.style.cssText='left:'+(hx-len)+'px;top:'+hy+'px;--len:'+len+'px';
  box.appendChild(m);m.animate(fr,{duration:dur,easing:'linear'}).onfinish=()=>m.remove();
}
function pcMeteors(box){
  const next=()=>{if(!box.isConnected)return;if(!document.hidden&&box.querySelectorAll('.mt').length<2)pcMeteor(box);setTimeout(next,pcR(2500,7000));};
  setTimeout(next,pcR(300,1500));setTimeout(next,pcR(2000,4000));
}
let pcLast=null;
function openCard(tr){
  const p=pcFind(tr.dataset.pid,tr.dataset.nm);if(!p)return;
  pcFonts();pcLast=tr;
  const {tn,html}=pcHTML(p,tr.dataset.pid,tr.dataset.ovr!=null?+tr.dataset.ovr:null);
  $('#pcs').innerHTML=html;
  $('#pcov').hidden=false;
  if(tn===5)root.querySelectorAll('#pcs .face .fx2').forEach(pcMeteors);
  $('#pcx').focus({preventScroll:true});
}
function closeCard(){
  const ov=$('#pcov');if(ov.hidden)return;
  ov.hidden=true;$('#pcs').innerHTML='';
  if(pcLast&&pcLast.isConnected)pcLast.focus({preventScroll:true});
}
$('#tb').addEventListener('click',e=>{const r=e.target.closest('tr[data-pid]');if(r)openCard(r);});
$('#tb').addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;const r=e.target.closest('tr[data-pid]');if(r){e.preventDefault();openCard(r);}});
$('#pcx').addEventListener('click',closeCard);
$('#pcov').addEventListener('click',e=>{
  const f=e.target.closest('.flip');
  if(!f){closeCard();return;}
  f.classList.remove('live');f.classList.toggle('fb');f.dataset.busy=1;setTimeout(()=>{delete f.dataset.busy},600);
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#pcov').hidden)closeCard();});
/* 3D 傾斜＋反光：光源固定，傾斜時反光帶（--gp）在卡面上滑；翻到背面時左右傾斜方向反過來 */
$('#pcov').addEventListener('pointermove',e=>{
  const f=e.target.closest('.flip');if(!f||f.dataset.busy)return;
  const r=f.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height,sg=f.classList.contains('fb')?-1:1;
  f.classList.add('live');
  f.style.setProperty('--ang',(x*360)+'deg');
  f.style.setProperty('--ry',(sg*(x-.5)*14)+'deg');f.style.setProperty('--rx',((.5-y)*12)+'deg');
  f.style.setProperty('--gp',(50+(x-.5)*14*6+(y-.5)*12*3)+'%');
});
$('#pcov').addEventListener('pointerout',e=>{
  const f=e.target.closest('.flip');if(!f||f.contains(e.relatedTarget))return;
  f.classList.remove('live');['--rx','--ry','--ang','--gp'].forEach(k=>f.style.removeProperty(k));
});
window.PureRank={ensure,open(a){open=a||null;if(D)render();}};
})()</script>"""


def embed():
    """名單頁用：回傳 (宿主＋template 的 HTML, 腳本)。宿主放在 .wrap 前面，腳本放在眉頭腳本之前。"""
    tpl = '<template id="rankTpl"><style>' + STYLE + '</style>' + BODY + '</template>'
    return '<div id="rankHost"></div>' + tpl, JS
