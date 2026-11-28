// teams.js — 測試卡表（自動產生，勿手改；改 gen_teams.mjs）
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
  GSW: {
    name: '勇士 2016-17',
    season: '2016-17',
    roster: [
      P('Stephen Curry', 'PG',  98,  93,  87,  58,  69,  93,  98,  63,  58,  44,  88,  46,  88,  83,  98,  92),
      P('Klay Thompson', 'SG',  97,  94,  89,  45,  92,  61,  90,  52,  85,  66,  90,  68,  99,  73,  62,  45),
      P('Kevin Durant', 'SF',  86,  97,  99,  84,  83,  86,  96,  88,  95,  90,  88,  83,  48,  80,  82,  52, '無球下修：定點投射威脅頂級，但跑動不是他得分的方式（要球單打型）'),
      P('Draymond Green', 'PF',  56,  42,  61,  85,  47,  91,  52,  87,  95,  97,  85,  73,  94,  90,  45,  90, '無球下修：跑動與掩護一流，但定點投射威脅由 SPACING_W 另外算'),
      P('Andre Iguodala', 'SF',  73,  87,  98,  69,  91,  79,  53,  69,  84,  65,  65,  65,  54,  78,  51,  68, '近射樣本小(175 次)'),
    ],
  },
  CLE: {
    name: '騎士 2015-16',
    season: '2015-16',
    roster: [
      P('Kyrie Irving', 'PG',  64,  99,  61,  62,  81,  90,  96,  46,  71,  53,  81,  49,  75,  45,  99,  90, '擋拆手調'),
      P('JR Smith', 'SG',  96,  70,  56,  40,  99,  54,  48,  46,  66,  64,  78,  68,  81,  45,  50,  40, '擋拆手調'),
      P('LeBron James', 'SF',  60,  71,  99,  85,  68,  96,  57,  82,  84,  94,  95,  83,  62,  60,  96,  95, '擋拆手調'),
      P('Kevin Love', 'PF',  82,  85,  50,  71,  74,  71,  85,  95,  61,  64,  81,  90,  79,  68,  50,  50, '擋拆手調'),
      P('Tristan Thompson', 'C',  40,  44,  92,  98,  79,  41,  43,  95,  90,  82,  68,  80,  35,  86,  35,  30, '整季 0 次三分出手；擋拆手調'),
    ],
  },
  OKC: {
    name: '雷霆 2025-26',
    season: '2025-26',
    roster: [
      P('Shai Gilgeous-Alexander', 'PG',  86,  99,  93,  90,  94,  96,  97,  57,  86,  92,  90,  57,  35,  56,  90,  88),
      P('Jalen Williams', 'SF',  48,  68,  68,  85,  82,  91,  83,  72,  65,  85,  74,  62,  69,  63,  82,  68, 'GP 33，樣本小'),
      P('Chet Holmgren', 'C',  74,  93,  97,  88,  72,  46,  73,  95,  90,  98,  76,  86,  65,  89,  65,  50),
      P('Luguentz Dort', 'SG',  66,  63,  52,  42,  87,  41,  58,  59,  65,  87,  69,  63,  97,  86,  48,  40),
      P('Isaiah Hartenstein', 'C',  42,  63,  94,  96,  42,  80,  42,  99,  55,  98,  57,  96,  63,  97,  40,  62),
    ],
  },
  NYK: {
    name: '尼克 2025-26',
    season: '2025-26',
    roster: [
      P('Jalen Brunson', 'PG',  81,  99,  53,  70,  89,  95,  89,  43,  73,  45,  95,  45,  68,  70,  92,  92),
      P('Mikal Bridges', 'SG',  81,  94,  92,  47,  97,  72,  78,  53,  90,  66,  88,  66,  60,  59,  50,  55),
      P('OG Anunoby', 'SF',  89,  63,  88,  69,  62,  49,  84,  72,  78,  63,  90,  84,  90,  63,  59,  48),
      P('Karl-Anthony Towns', 'C',  78,  57,  77,  91,  50,  68,  93,  99,  51,  78,  83,  96,  94,  92,  68,  52),
      P('Josh Hart', 'SG',  94,  75,  84,  65,  48,  84,  52,  90,  70,  54,  80,  65,  88,  85,  58,  56),
    ],
  },
  LAL: {
    name: '湖人 2001-02',
    season: '2001-02',
    roster: [
      P("Shaquille O'Neal", 'C',  44,  43,  99,  99,  86,  78,  40,  96,  50,  93,  86,  99,  40,  92,  88,  68, '無球/擋拆/盯防/護框手調'),
      P('Kobe Bryant', 'SG',  64,  85,  95,  79,  86,  89,  90,  65,  80,  55,  91,  61,  48,  40,  94,  80, '無球/擋拆/盯防/護框手調'),
      P('Derek Fisher', 'PG',  96,  88,  40,  41,  99,  73,  87,  40,  55,  35,  66,  50,  68,  35,  45,  45, '近射 84 次 .357；無球/擋拆/盯防/護框手調'),
      P('Rick Fox', 'SF',  75,  56,  95,  45,  51,  80,  78,  72,  70,  55,  65,  77,  85,  60,  48,  55, '無球/擋拆/盯防/護框手調'),
      P('Robert Horry', 'PF',  87,  47,  56,  64,  73,  78,  71,  82,  68,  72,  60,  79,  65,  62,  55,  55, '無球/擋拆/盯防/護框手調'),
    ],
  },
};

/** 全 PR50 的基準隊，用於校準與固定情境逆推。 */
export const BASELINE = {
  name: 'PR50 基準隊',
  season: 'calibration',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(`PR50-${i + 1}`, ['PG', 'SG', 'SF', 'PF', 'C'][i],
      70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70)),
};

/** 五小陣容：其他屬性都好，只有肉體低。用來驗證大個子的克制關係。 */
export const SMALLBALL = {
  name: '五小測試隊',
  season: 'synthetic',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(`Small-${i + 1}`, 'G', 80, 75, 62, 70, 72, 70, 78, 55, 75, 60, 75, 42, 80, 50, 72, 70)),
};

/** 大陣容：肉體高，三分差。SMALLBALL 的對照組。 */
export const BIGBALL = {
  name: '雙塔測試隊',
  season: 'synthetic',
  roster: Array.from({ length: 5 }, (_, i) =>
    P(`Big-${i + 1}`, 'C', 50, 62, 85, 78, 68, 45, 55, 88, 65, 82, 75, 95, 45, 88, 55, 55)),
};
