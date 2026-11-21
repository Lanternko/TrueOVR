const A = pr => pr<=1?40 : pr<50 ? Math.round(40+(pr-1)/49*30) : pr<99 ? Math.round(70+(pr-50)/49*29) : 99;
// name, [longPR, midPR, shortPR, drivePR, tovSkillPR, passPR, ftPR], [reb,onBall,help,stamina,phys,offBall,screen,handle,breakDbl], pos, note
const D = {
GSW: ['勇士 2016-17','2016-17',[
 ['Stephen Curry','PG',[96.9,89.3,78.2,30.2,48.0,88.4,96.9],[63,58,44,88,46,88,83,98,92],''],
 ['Klay Thompson','SG',[95.6,90.7,81.8,9.8,86.7,34.7,84.0],[52,85,66,90,68,99,73,62,45],''],
 ['Kevin Durant','SF',[77.3,95.6,98.7,72.9,72.0,76.4,93.8],[88,95,90,88,83,48,80,82,52],'無球下修：定點投射威脅頂級，但跑動不是他得分的方式（要球單打型）'],
 ['Draymond Green','PF',[27.6,3.6,36.0,76.0,12.4,85.3,20.0],[87,95,97,85,73,94,90,45,90],'無球下修：跑動與掩護一流，但定點投射威脅由 SPACING_W 另外算'],
 ['Andre Iguodala','SF',[54.7,78.2,96.9,47.6,84.9,65.8,21.8],[69,84,65,65,65,54,78,51,68],'近射樣本小(175 次)'],
]],
CLE: ['騎士 2015-16','2015-16',[
 ['Kyrie Irving','PG',[40.7,99.1,35.0,37.2,68.6,83.2,94.7],[46,71,53,81,49,75,45,99,90],'擋拆手調'],
 ['JR Smith','SG',[93.4,49.6,27.9,1.8,99.6,23.5,13.3],[46,66,64,78,68,81,45,50,40],'擋拆手調'],
 ['LeBron James','SF',[33.2,50.9,99.1,75.7,46.9,94.2,28.8],[82,84,94,95,83,62,60,96,95],'擋拆手調'],
 ['Kevin Love','PF',[69.9,74.8,17.3,50.9,57.1,50.9,75.7],[95,61,64,81,90,79,68,50,50],'擋拆手調'],
 ['Tristan Thompson','C',[0,7.1,87.2,96.9,65.5,2.7,5.8],[95,90,82,68,80,35,86,35,30],'整季 0 次三分出手；擋拆手調'],
]],
OKC: ['雷霆 2025-26','2025-26',[
 ['Shai Gilgeous-Alexander','PG',[77.4,99.6,88.9,83.7,90.5,94.4,95.2],[57,86,92,90,57,35,56,90,88],''],
 ['Jalen Williams','SF',[13.9,46.0,47.2,74.6,70.2,86.1,72.6],[72,65,85,74,62,69,63,82,68],'GP 33，樣本小'],
 ['Chet Holmgren','C',[56.0,89.3,96.4,80.2,54.0,11.1,54.4],[95,90,98,76,86,65,89,65,50],''],
 ['Luguentz Dort','SG',[44.0,38.1,21.4,3.6,78.6,2.4,31.0],[59,65,87,69,63,97,86,48,40],''],
 ['Isaiah Hartenstein','C',[4.8,39.3,90.9,93.7,4.0,66.3,4.4],[99,55,98,57,96,63,97,40,62],''],
]],
NYK: ['尼克 2025-26','2025-26',[
 ['Jalen Brunson','PG',[67.9,98.4,23.0,50.0,82.9,92.5,81.3],[43,73,45,95,45,68,70,92,92],''],
 ['Mikal Bridges','SG',[69.0,90.1,86.9,12.7,95.6,52.8,62.7],[53,90,66,88,66,60,59,50,55],''],
 ['OG Anunoby','SF',[82.1,38.9,81.0,47.6,36.9,16.3,73.4],[72,78,63,90,84,90,63,59,48],''],
 ['Karl-Anthony Towns','C',[63.1,29.0,61.9,85.3,16.7,46.8,88.9],[99,51,78,83,96,94,92,68,52],''],
 ['Josh Hart','SG',[90.9,58.7,73.4,42.5,14.3,73.8,19.8],[90,70,54,80,65,88,85,58,56],''],
]],
LAL: ['湖人 2001-02','2001-02',[
 ["Shaquille O'Neal",'C',[8.1,6.7,99.5,98.6,76.7,63.3,1.0],[96,50,93,86,99,40,92,88,68],'無球/擋拆/盯防/護框手調'],
 ['Kobe Bryant','SG',[40.5,75.2,91.9,65.2,77.6,81.9,84.3],[65,80,55,91,61,48,40,94,80],'無球/擋拆/盯防/護框手調'],
 ['Derek Fisher','PG',[94.3,80.0,0,2.4,98.6,55.2,79.0],[40,55,35,66,50,68,35,45,45],'近射 84 次 .357；無球/擋拆/盯防/護框手調'],
 ['Rick Fox','SF',[58.1,26.7,92.9,8.6,19.5,67.6,62.9],[72,70,55,65,77,85,60,48,55],'無球/擋拆/盯防/護框手調'],
 ['Robert Horry','PF',[79.0,12.9,26.7,41.0,54.3,64.3,51.9],[82,68,72,60,79,65,62,55,55],'無球/擋拆/盯防/護框手調'],
]],
};
let out = `// teams.js — 測試卡表（自動產生，勿手改；改 gen_teams.mjs）
// 屬性由真實 NBA 資料逆推，各球員在「自己那個賽季」的 rotation 母體內取百分位
// （G>=30, MPG>=20），再依 pr1->40 / pr50->70 / pr99->99 映射。
// 詳見 vault：遊戲/basketball-autochess-隊伍卡表
//
// 十六屬性：
//   long 三分  mid 中投  short 近射   （leaguedashplayershotlocations By Zone）
//   drive 切入  （FTA/FGA + 禁區出手佔比的合成百分位 = 創造出手，不是終結）
//   tovSkill 失誤（TOV/(FGA+0.44FTA+**AST**+TOV) 反轉——分母含助攻，否則傳球者被系統性懲罰）
//   pass 傳球（AST%）  ft 罰球（FT%，低出手量用 log(FTA) 迴歸當先驗）
//   rebound 籃板（REB_PCT）  stamina 體力（MPG）  physique 肉體（身高+體重）
//   onBall 盯防 / help 護框（leaguedashptdefend 的 PLUSMINUS，分類別收縮）
//   screen 擋拆（SCREEN_ASSISTS）
//
// 手填三欄（無球 / 持球 / 破包夾）——沒有 box score 欄位對應得上：
//   offBall 無球（跑動：繞掩護、空切、補位。**不含定點投射威脅**，
//     那個由 SPACING_W 從三分/中投另外算，兩件事綁在一起就只能弄錯一邊：
//     Draymond 跑動一流但站在三分線外沒人理他）
//   handle 持球（自主拔投——不靠人餵也能製造出手並投進）。
//     Curry 98 / Klay 62 是這一欄存在的理由：兩人投籃數字幾乎相同，
//     但一個是聯盟最強的自主拔投，一個是純接球投。
//   breakDbl 破包夾（被兩個人夾住還能運出來或把球送出去）。
//     原本用 切入/傳球/無球/失誤 合成，但那組數字算不出 Durant——
//     他的切入 84 / 傳球 86 / 失誤 83 都不低，實際上被夾住就出不了球。
//
//   這三欄的對齊目標是**真實 USG%**（stats.nba.com Advanced，各自賽季，
//   先發五人正規化到 100）。25 人平均絕對誤差 1.70pp，見 test/run_tests.js §6。
//   逼近方式是有界座標下降 + 正則化，但擬合器跑出沒有籃球意義的值時
//   （SGA 持球 67、KD 持球 56、Hartenstein 持球 63）一律不採用——
//   那是把答案寫進輸入。代價是 Draymond 差 7.1pp，那是刻意留的。

const P = (name, pos, long, mid, short, drive, tovSkill, pass, ft,
           rebound, onBall, help, stamina, physique, offBall, screen, handle,
           breakDbl, note = '') =>
  ({ name, pos, long, mid, short, drive, tovSkill, pass, ft,
     rebound, onBall, help, stamina, physique, offBall, screen, handle,
     breakDbl, note });

export const TEAMS = {
`;
for (const [k,[name,season,roster]] of Object.entries(D)) {
  out += `  ${k}: {\n    name: '${name}',\n    season: '${season}',\n    roster: [\n`;
  for (const [n,pos,prs,rest,note] of roster) {
    const q = n.includes("'") ? '"' : "'";
    const a = prs.map(A);
    out += `      P(${q}${n}${q}, '${pos}', ${a.map(x=>String(x).padStart(3)).join(', ')}, ${rest.map(x=>String(x).padStart(3)).join(', ')}${note?`, '${note}'`:''}),
`;
  }
  out += `    ],\n  },\n`;
}
out += `};

/** 全 PR50 的基準隊，用於校準與固定情境逆推。 */
export const BASELINE = {
  name: 'PR50 基準隊',
  season: 'calibration',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(\`PR50-\${i + 1}\`, ['PG', 'SG', 'SF', 'PF', 'C'][i],
      70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70)),
};

/** 五小陣容：其他屬性都好，只有肉體低。用來驗證大個子的克制關係。 */
export const SMALLBALL = {
  name: '五小測試隊',
  season: 'synthetic',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(\`Small-\${i + 1}\`, 'G', 80, 75, 62, 70, 72, 70, 78, 55, 75, 60, 75, 42, 80, 50, 72, 70)),
};

/** 大陣容：肉體高，三分差。SMALLBALL 的對照組。 */
export const BIGBALL = {
  name: '雙塔測試隊',
  season: 'synthetic',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(\`Big-\${i + 1}\`, 'C', 50, 62, 85, 78, 68, 45, 55, 88, 65, 82, 75, 95, 45, 88, 55, 55)),
};
`;
import('fs').then(fs=>fs.writeFileSync('src/teams.js', out));
