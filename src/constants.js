// constants.js — 錨點表、夾值、校準目標
//
// 所有錨點來自 NBA 真實分布，rotation player 母體（G>=30, MPG>=20），
// 各球員在「自己那個賽季」的母體內取百分位，pr1->40 / pr50->70 / pr99->99。
//
// 出手區域取自 leaguedashplayershotlocations（DistanceRange=By Zone）：
//   近射 = Restricted Area + In The Paint (Non-RA)
//   中投 = Mid-Range
//   三分 = Corner 3 + Above the Break 3

export const ATTR_MIDPOINT = 70;
export const ATTR_SOFT_CAP = 150;

// --- 命中率曲線 ---------------------------------------------------------
// attr 70 錨在 2025-26 的「出手數加權聯盟平均」（不是中位數球員——中位數球員
// 比聯盟平均差，因為好射手出手多）。上下展幅取四個賽季百分位展幅的平均。
//
// 2025-26 聯盟平均：近射 .5782  中投 .4216  三分 .3639
// 四季平均展幅：    近射 -.068/+.088  中投 -.078/+.086  三分 -.065/+.069

export const CURVE_3PT = [
  [0, 0.235], [40, 0.2988], [55, 0.3313], [70, 0.3639],
  [85, 0.3985], [99, 0.4330], [120, 0.460], [150, 0.480],
];
export const CURVE_MID = [
  [0, 0.270], [40, 0.3439], [55, 0.3828], [70, 0.4216],
  [85, 0.4645], [99, 0.5073], [120, 0.540], [150, 0.565],
];
export const CURVE_SHORT = [
  [0, 0.430], [40, 0.5099], [55, 0.5441], [70, 0.5782],
  [85, 0.6223], [99, 0.6664], [120, 0.705], [150, 0.735],
];

// --- 防守：對手命中率的絕對增減量 ---------------------------------------
// leaguedashptdefend 的 PLUSMINUS。分類別的原始展幅（±.19 / ±.21）是樣本
// 雜訊灌水，以 Overall 類別（±.08）反推收縮後使用。
export const CURVE_DEF_3PT = [
  [0, 0.120], [40, 0.085], [55, 0.040], [70, 0.003],
  [85, -0.038], [99, -0.076], [120, -0.100], [150, -0.120],
];
export const CURVE_DEF_RIM = [
  [0, 0.150], [40, 0.105], [55, 0.050], [70, 0.004],
  [85, -0.048], [99, -0.095], [120, -0.125], [150, -0.150],
];
/** 中投由盯防與協防各半負責，但整體效果打折——中距離是最難干擾的一區。 */
export const DEF_MID_SCALE = 0.60;

// --- 失誤 ---------------------------------------------------------------
// tovSkill 由真實 TOV/(FGA+0.44*FTA+TOV) 百分位逆推（越低越好 -> 屬性越高）。
// 曲線是「每次進攻機會」而非每 possession：一個 possession 平均 ~1.18 次機會。
export const CURVE_TOV = [
  [0, 0.239], [40, 0.1826], [55, 0.1429], [70, 0.1032],
  [85, 0.0800], [99, 0.0567], [150, 0.047],
];

// --- 進攻端修正因子（tanh 乘數）-----------------------------------------
export const OFFBALL_SCALE = 40.0;      // 隊友定點投射威脅 -> 拉開空間 -> 三分命中
export const OFFBALL_MAX_IMPACT = 0.10;
export const SCREEN_SCALE = 40.0;       // 隊友擋拆 -> 切入空間 -> 近射命中
export const SCREEN_MAX_IMPACT = 0.12;
// 隊友無球跑動 -> 空切接球上籃。這跟擋拆是兩種不同的禁區機會：
// 擋拆是幫持球者鑿開一條路，空切是隊友自己跑到籃下等球。
// 真實的切入（cut）命中率約 .65-.70，遠高於禁區平均 .578——
// 接球在移動中直接放，防守來不及落位。
// 沒有這條通道的話無球只剩「傳得出去」與「誰接到球」，後者是純重分配
// （實測全隊無球 40->99 只值 +0.001 分/回合，等於這個屬性不存在）。
export const OFFBALL_CUT_SCALE = 40.0;
export const OFFBALL_CUT_IMPACT = 0.09;
// 隊友傳球 -> 出手品質。接球投的命中率就是比自己運球拔起來高，
// 空切被餵到的球也比自己硬鑽好。這跟無球（拉開空間）是兩件事：
// 無球是「我跑出空檔」，傳球是「有人把球準時送到」。
export const PASS_SCALE = 40.0;
export const PASS_MAX_IMPACT = 0.10;
// 引力：身邊有超級得分手，防守必須分心，隊友的出手就變好。
//
// 這是進攻端唯一能「全隊放大」的機制，補的是一個結構不對稱：
// 護框（協防）用 top-2 合成，一個人就能改善對手全部五個回合；
// 而無球是「其他四人平均」，一個超級得分手會被四個隊友稀釋。
// 沒有引力的話，模型會系統性低估後衛——實測 Curry 的 OVR 會掉到 Tristan Thompson 之下。
export const GRAVITY_SCALE = 40.0;
export const GRAVITY_MAX_IMPACT = 0.075;
export const GRAVITY_W = { long: 0.60, short: 0.40 };
/**
 * 引力取「外線拉扯」與「包夾威脅」的**大者**，不是只看三分。
 *
 * 兩個人困在禁區守 Shaq，外線就是空的——那是不折不扣的引力，而且比任何
 * 三分射手都強。防守的注意力是一份，被拉出去或被吸進來都是同一份被用掉。
 * 取 max 而非加權：一支球隊只需要一種讓對手分心的方式。
 * 兩項在 PR50 都等於 70，所以基準校準不受影響。
 */

// 創造依賴：吃餅型球員拿到的出手是別人創造的，不該是免費的。
//
// 這是引力的鏡像。引力補「強得分手讓隊友變好」，這一項補「弱創造者需要有人餵」。
// 沒有這一項，五個吃餅中鋒的陣容跟有 PG 的一樣強（實測 75.4% vs 77.3%，
// 屬性總量相同），創造力等於不存在——evaluateLineup 無條件替每個人算一個
// 期望得分，等於預設球永遠送得到最好的位置。
//
// 依賴度由持球者自己的 drive/pass 決定：吃餅型 -> 1，創造型 -> 0，PR50 -> 0.5。
// PR50 全隊時 ctx.create = 70 -> tanh = 0 -> boost = 1，所以基準校準完全不受影響。
export const CREATE_SCALE = 40.0;
export const CREATE_MAX_IMPACT = 0.14;
/** 隊友創造力的成分。切入權重高於傳球，因為傳球另有 passBoost 一條路，
 *  而切入原本只有 Z_DRIVE_RIM_W 一條弱通道（單卡邊際價值僅 +0.004）。 */
export const CREATE_CTX_W = { drive: 0.65, pass: 0.35 };
export const CREATE_DEP_BASE = 0.50;
export const CREATE_DEP_SCALE = 60.0;
/** 沒人能創造機會時，禁區與三分都拿不到，被擠去中距離——跟防守否決同構。 */
export const Z_CREATE_RIM_W = 0.30;
export const Z_CREATE_LONG_W = 0.20;

export const Z_PASS_RIM_W = 0.20;       // 好的傳球也讓禁區機會變多
export const PHYS_SCALE = 45.0;         // 肉體差 -> 禁區優勢
export const PHYS_MAX_IMPACT = 0.18;
export const PHYS_SHOT_PULL = 12.0;     // 肉體優勢把出手選擇往禁區拉（分數單位）
export const PHYS_REB_WEIGHT = 0.30;    // 隊伍籃板中肉體的權重
export const PHYS_HELP_BONUS = 0.25;    // 大個子墊高協防

// --- 出手區域選擇 -------------------------------------------------------
// p(zone) ∝ leagueShare(zone) × exp(ΔEV / EV_TEMP + 可及性 / ZONE_TEMP)
//
// 兩個乘數是兩件不同的事：
//   ΔEV    這種出手值不值得（命中率 × 分數，相對 PR50 基準）
//   可及性  拿不拿得到這種出手（無球/擋拆/切入/肉體，減去防守否決）
//
// 只用可及性會讓中投變成死屬性：中投練高只是讓你多投一種期望值較低的球，
// 淨值為零。加進 ΔEV 之後，中投高的人投中投時「每球更值錢」，才有邊際價值。
// PR50 全隊時兩項皆為 0，機率恰好等於聯盟佔比——bias 自動校準，不必手調。
export const LEAGUE_ZONE_SHARE = { short: 0.483, mid: 0.110, long: 0.407 };
/**
 * 陣地戰的區域先驗。跟 LEAGUE_ZONE_SHARE 不同的是它**扣掉補籃**——
 * 真實的 .483 禁區佔比裡有約 2.5 個百分點是進攻籃板後直接放回去的，
 * 而補籃在模型裡是另外生成的（putbackRate），不走這個 softmax。
 * 兩者混用的話禁區佔比會被算兩次（實測 +3.2%）。
 */
export const HALFCOURT_ZONE_SHARE = { short: 0.458, mid: 0.115, long: 0.427 };
export const ZONE_TEMP = 30.0;
export const EV_TEMP = 0.60;
// EV_TEMP 不能再小。混合期望值對某區 EV 的偏導是 w_z × (1 + (ev_z - 混合均值)/T)，
// 當 T 小於「最差區與均值的差距」時會變負——中投練高反而變弱。實測 0.55 是臨界值。
/** PR50 對 PR50 時各區的每次出手期望得分，ΔEV 的基準點。 */
export const EV_REF = { long: 1.1007, mid: 0.8474, short: 1.1644 };

// 防守「否決」：好的盯防讓你投不到三分、好的協防讓你切不進去。
// 兩條路都被斷 -> 只剩中距離。這是中投屬性存在的理由。
export const DENY_LONG = 0.45;
export const DENY_SHORT = 0.55;

// 區域分數中隊友情境與創造力的權重（分數單位，直接加減）
export const Z_OFFBALL_W = 0.35;   // 空間（定點投射威脅）-> 三分機會
/** 無球跑動 -> 禁區機會。空切與後門就是這一條。
 *  無球把三分那條通道讓給「空間」之後，如果不給它自己的出口，
 *  它就只剩「傳得出去」與「誰接到球」——後者是純重分配，等於這個屬性不存在
 *  （實測全隊無球 40->99 只值 +0.001 分/回合）。 */
export const Z_OFFBALL_RIM_W = 0.26;
export const Z_SCREEN_W = 0.30;    // 擋拆 -> 禁區機會
export const Z_DRIVE_RIM_W = 0.55; // 切入 -> 禁區機會
export const Z_DRIVE_MID_W = 0.15; // 切入 -> 中距離機會（急停跳投）

// --- 持球者選擇：出手品質搜尋 -------------------------------------------
// 舊版是靜態 usage 權重（(投射+切入)/2 的指數），跟實際出手品質脫鉤。
// 現在每次進攻機會都算五個人的期望得分，再依 softmax 抽。
//
// 純比期望得分會把球權給效率最高的人（通常是吃餅中鋒），而不是給創造力最強的人。
// 真實的 usage 同時吃「效率」與「能不能自己製造出手」，所以加一個創造項：
// 三項投籃的最高值——能自己得分的人才會被交付球權，即使他失誤多。
export const USAGE_TEMP = 0.22;
export const USAGE_CREATE_W = 1.10;
export const USAGE_FLOOR_MIX = 0.10;
/** 創造力的成分權重。傳球（AST%）是分開持球創造者與定點射手的主力訊號。 */
export const CREATE_W = { long: 0.30, mid: 0.20, short: 0.05, drive: 0.15, pass: 0.50 };
/** 球權上下限。NBA 真實範圍：頭號球星 28-35%，第五人 10-14%。 */
export const USAGE_CLAMP = [0.085, 0.345];
/** 無球屬性高 = 接球就投型，球權會被扣；持球創造者的無球通常偏低。 */
export const CREATE_OFFBALL_PENALTY = 0.15;

// --- 進攻機會：最多五次傳球 ---------------------------------------------
//
// 一次進攻機會 = 最多 MAX_PASSES 次傳球。持球者有「夠好」的出手機會就投，
// 不夠好就找人傳；沒有傳球機會（或傳球次數用完）就只能勉強出手。
//
// 這取代了舊版的「一次算五個人的期望得分、softmax 抽一個出手」——
// 舊版沒有時間維度，等於預設球永遠送得到最好的位置。
//
// 時限的簡化：不算秒數，只算傳球次數。門檻隨剩餘次數遞減——
// 越接近沒得傳，越願意將就。這就是「進攻時限壓力」的離散版。
export const MAX_PASSES = 5;
/** 出手門檻（每回合得分單位）。PR50 自主出手的期望得分是 1.031。 */
export const SHOT_THRESHOLD = 1.16;
export const SHOT_THRESHOLD_STEP = 0.030;
/** 門檻不是硬切——真實球員沒有一個精確的閾值，用 logistic 過渡。 */
export const SHOT_TEMP = 0.24;

/**
 * 接球投加成：不必自己創造，出手品質天生較好。
 * 這是整個傳球鏈的價值來源——沒有這一項，傳球只是換人拿球，賺不到東西。
 *
 * 但它**不是憑空加在命中率上**，而是「防守被傳球調動了」：球轉得快，
 * 對位者來不及回位，等於他的盯防與協防暫時下降。這一點很重要——
 * 走防守這條路的話，好傳球不只讓你投得準，還會讓你**投得到**
 * （denyLong / denyShort 一起變小），三分與禁區同時打開；
 * 直接加在命中率上則只有前者。
 *
 * 幅度取自真實的接球投 vs 持球投差距，不是調出來的：
 *   三分 C&S .375 / pull-up .335 -> +.040
 *   CURVE_DEF_3PT 斜率 (.085-(-.076))/59 = .0027 /點 -> .040/.0027 ≈ 15 點
 *   CURVE_DEF_RIM 斜率 (.105-(-.095))/59 = .0034 /點 -> .040/.0034 ≈ 12 點
 * 傳球者的傳球屬性再上下調節 ±ASSIST_DROP_SPAN。
 */
export const ASSIST_DEF_DROP = 15.0;
export const ASSIST_DEF_DROP_HELP = 12.0;
export const ASSIST_DROP_SCALE = 40.0;
export const ASSIST_DROP_SPAN = 0.40;
/** 一樣要以聯盟接球投率為中心零和：命中率曲線錨在聯盟平均，那個平均本來就
 *  包含 60% 的接球投。只加不扣的話整體命中率會被整條推高
 *  （實測會讓近射從 .578 跑到 .597）。 */
export const LEAGUE_ASSISTED_RATE = 0.541;

/**
 * 放空稅：不能投的人站在場上，他的防守者可以直接沉進禁區。
 *
 * 這是無球屬性的第二條路，也是「球權低本身不是問題、不能投才是問題」的來源。
 * 第一條路（OFFBALL_MAX_IMPACT）是拉開空間讓隊友命中率上升；
 * 這一條是**不拉開空間讓對手協防上升**——作用在對手的有效協防值上，
 * 所以會連帶收緊禁區可及性，跟真實比賽裡的沉退防守同構。
 *
 * 中心點就是 ATTR_MIDPOINT，所以 PR50 全隊時稅為零，基準校準完全不受影響。
 * 幅度：一個完全不能投的陣容（無球 40）讓對手協防 +13.5 點，
 * 換算近射命中約 -.046——跟真實的「放空一個非射手」量級相符。
 */
export const SPACING_HELP_W = 0.45;
export const SPACING_HELP_CAP = 18.0;
/** 定點投射威脅的成分。三分為主、中投為輔——中投多半是持球急停，
 *  被放空時的懲罰能力遠不如三分。這把尺只量「不看他行不行」，
 *  不量他跑不跑得動（那是無球屬性）。 */
export const SPACING_W = { long: 0.75, mid: 0.25 };

/**
 * 誰把球帶起來。第一手由持球能力決定，不是由期望得分決定。
 *
 * 用期望得分挑第一手會讓終結能力最強的人變成控球後衛——實測 Durant 拿到
 * 38% 球權，但他真實 USG 只有 27.4%，而且勇士的持球核心是 Curry 與 Draymond。
 * 出手多跟持球多是兩件事：終結者靠傳球鏈餵，持球者自己把球帶過來。
 *
 * 持球佔最大權重——這一欄的定義就是球在誰手上。切入權重同時下修：那是
 * 「FTA/FGA + 禁區出手佔比」逆推的，量的是終結方式，不是誰把球帶過半場。
 */
export const HANDLING_W = { handle: 0.40, pass: 0.30, drive: 0.15, tovSkill: 0.15 };
export const HANDLING_TEMP = 9.0;
export const HANDLING_FLOOR_MIX = 0.18;
export const HANDLING_CLAMP = [0.08, 0.36];

/**
 * 進攻籃板 -> 補籃。
 *
 * 真實 NBA 約 40-45% 的進攻籃板會直接轉成一次補籃出手，其餘拉出來重新組織。
 * 沒有這一條的話進攻籃板會回到傳球鏈起點，搶板的人要重新競爭球權——
 * 但補籃本來就是搶板的人自己放，這是籃板型球員出手的主要來源。
 */
export const PUTBACK_BASE = 0.42;
export const PUTBACK_SCALE = 45.0;
export const PUTBACK_PHYS_IMPACT = 0.30;   // 自己的肉體：卡得住位就放得進去
export const PUTBACK_RIM_IMPACT = 0.55;    // 對手護框：協防強就放不進去
export const PUTBACK_CLAMP = [0.10, 0.70];
/** 進攻籃板落到誰手上的 softmax 溫度（籃板屬性單位）。 */
export const OREB_PICK_TEMP = 9.0;

/**
 * 自主出手的品質取決於**他自己的創造力**，不是一個固定懲罰。
 *
 * 這一條很關鍵：給自主出手固定懲罰的話，球會流向「接球投期望值最高的人」，
 * 也就是定點射手——實測 Fisher 拿到 44.7% 球權、Draymond 只有 2.2%，
 * 而真實值約 13% 與 15%。創造者拿到球會自己弄出一個好機會，模型必須讓他做得到。
 */
export const SELF_CREATE_SCALE = 40.0;
export const SELF_CREATE_IMPACT = 0.130;

/**
 * 持球投：不靠人餵，自己拉起來就投得進。
 *
 * 這是第 15 個屬性，開它的理由很具體：Curry 與 Klay 的三分 97/98、中投 93/94
 * 幾乎相同，但一個是聯盟最強的自主拔投、一個是純接球投。現有 14 個屬性分不開
 * ——切入是 FTA 率逆推的，而 Curry 本來就不切入（58）。
 * 少了它，自主出手品質只能用切入+傳球代打，Curry 被判成弱自主出手者，
 * 球權全流向 Durant（實測 40.1%，真實 USG 27.4%）。
 */
export const HANDLE_SCALE = 40.0;
export const HANDLE_IMPACT = 0.145;

/**
 * 包夾。
 *
 * 這是引力的代價，也是模型裡唯一能自動壓住「最強的人吃掉全部球權」的東西。
 * 沒有它就只能靠溫度與夾值硬壓——那是把答案寫進參數，不是機制。
 *
 * 決定被包夾多寡的不是絕對威脅，而是**你比隊友強多少**：
 * 五個人都要顧的時候誰都包夾不了，一個人扛的時候他每次持球都被兩個人夾。
 * 這正是「Curry 引力高，吸走 Durant 的包夾」——兩人威脅相當，誰都夾不動。
 *
 * 破包夾有三條路，對應三種不同的球員：
 *   持球  自己運出來（Curry、Kyrie）
 *   切入  用身體撞出來（LeBron、SGA）
 *   無球  一開始就不在會被夾的位置（Klay、Dort）
 * 三條都沒有的人（引力高但控球普通的終結者）被夾就死。
 *
 * 作用取期望值而不是逐次擲骰：一個吸引 30% 包夾的人，平均就承受 30% 的效果。
 * 這樣 EV 評估是精確的，接球者選擇不必對包夾狀態再展開一層。
 */
export const DOUBLE_BASE = 0.16;
/** 中心化用的聯盟平均包夾率。跟接球投、強迫出手同一套紀律：
 *  命中率錨點本來就含真實比賽裡的包夾，只扣不補會扣兩次。 */
export const LEAGUE_DOUBLE_RATE = 0.16;
/**
 * 包夾威脅的尺，跟引力不同。
 *
 * 引力量的是「會不會被拉出三分線」（三分為主）；包夾量的是「不夾住他就會得分」
 * ——低位與禁區才是包夾的主場，而且**必須自己製造得分**：接球才會投的人
 * 沒有人會去包夾（Klay 從來不被包夾，Shaq 每一球都被包夾）。
 * sim 0.1.1 拿掉原本的體格項（phys 0.25，R-089）：真實球員的包夾威脅被量測錨點抵銷，
 * 體格項只動到平均隊友，E-135 量不出效果。三項在 doubleThreat 裡除以權重和。
 */
export const DOUBLE_THREAT_W = { long: 0.20, mid: 0.10, short: 0.45 };
export const DOUBLE_CREATE_W = { handle: 0.50, drive: 0.50 };
export const DOUBLE_THREAT_MIX = 0.50;   // 得分能力與自主製造能力各半
/**
 * 包夾對象不能只跟隊友比。
 *
 * 只用相對值的話，兩個怪物同隊會互相抵消成「誰都不用夾」——但 2001-02 湖人
 * 是 Shaq 和 Kobe **都**被夾，剩下三個人被放空。所以基準線是隊友最強威脅
 * 與聯盟平均的混合：隊友能吸走一部分注意力，吸不走全部。
 */
export const DOUBLE_PEER_MIX = 0.65;
export const DOUBLE_REL_SCALE = 16.0;
export const DOUBLE_REL_SPAN = 0.90;
export const DOUBLE_BREAK_SCALE = 40.0;
export const DOUBLE_BREAK_SPAN = 0.55;
/**
 * 破包夾是**獨立的手填屬性**，不是 切入/傳球/無球/失誤 的合成。
 *
 * 合成版算不出 Durant：他切入 84、傳球 86、失誤 83 四項都不低，公式給他
 * 破包夾 78，但真實情況是被夾住就出不了球。拉起來就投（持球投）跟被兩個人
 * 夾住還能運出來是兩回事，而後者沒有任何 box score 欄位對應得上。
 * 手填的三欄（無球/持球/破包夾）以真實 USG%、TOV%、命中率為對齊目標。
 */
export const DOUBLE_CLAMP = [0.02, 0.45];
/** 被包夾時對手協防的有效增量。真正的包夾是兩個人守一個人，
 *  CURVE_DEF_RIM 斜率 .0034/點，45 點 ≈ 命中率 -.15——那才是包夾的量級。
 *  這個值乘上「包夾率 − 聯盟平均」，所以呈現的是期望效果而非單次效果。 */
export const DOUBLE_HELP = 45.0;
/** 被包夾就傳不出去（控球普通的終結者尤其），而且傳球容易被抄。 */
export const DOUBLE_PASS_PENALTY = 0.40;
export const DOUBLE_TOV_MULT = 1.60;

/** 自己的無球 -> 自己的三分接球機會（繞掩護、底角補位）。
 *  只在接球投時生效——自己運球起來的球跟跑不跑得動無關。 */
export const Z_OFFBALL_SELF_W = 0.30;

/**
 * 有沒有人可以傳。傳球者視野 + 隊友跑位/掩護 − 對位壓迫。
 * 傳不出去就只能自己出手——這是「壞持球員拿到球只能勉強出手」的來源。
 */
export const PASS_OPEN_BASE = 0.85;
export const PASS_OPEN_SCALE = 60.0;
export const PASS_OPEN_W = { pass: 0.35, offBall: 0.30, screen: 0.15, onBall: -0.30 };
export const PASS_OPEN_CLAMP = [0.25, 0.97];

/** 傳球被抄：傳球者的失誤傾向與傳球視野，對上對位者的盯防。 */
export const INTERCEPT_BASE = 0.030;
export const INTERCEPT_SCALE = 45.0;
export const INTERCEPT_MAX_IMPACT = 0.60;
export const INTERCEPT_CLAMP = [0.004, 0.150];

/** 持球者自己的失誤（運球被斷、走步、進攻犯規）。CURVE_TOV 是每次觸球的量表，
 *  但現在一個 possession 有多次觸球，所以要縮放。 */
export const HANDLER_TOV_SCALE = 0.73;

/**
 * 強迫出手：傳不出去或次數用完。防守已經站好，三分與禁區都被封，
 * 剩下的就是中距離——這是中投在模型裡真正的存在理由，
 * 比舊版繞道「防守否決」直接得多。
 */
// 跟 ASSIST 一樣要中心化：命中率曲線與區域佔比的錨點本來就包含真實比賽裡的
// 勉強出手，所以「強迫出手扣一層」而不補回來的話會扣兩次
// （實測中投佔比 +5.1%、中投命中 −3.2%）。
export const LEAGUE_FORCED_RATE = 0.185;
export const FORCED_DENY_LONG = 7.0;
export const FORCED_DENY_RIM = 6.0;
export const FORCED_MAKE_PENALTY = 0.035;

/** 接球者選擇：跑位拉開空檔的人先拿到球，再看他出手品質。 */
export const RECEIVER_TEMP = 0.20;
/** 保底與上下限，跟 usageFromEv 同一套理由：接球者選擇也要落在 NBA 真實範圍。
 *  少了這個，最好的定點射手會吃掉整條傳球鏈（Fisher 38.8%）。 */
export const RECEIVER_FLOOR_MIX = 0.12;
export const RECEIVER_CLAMP = [0.07, 0.50];
export const RECEIVER_OFFBALL_W = 0.010;
/**
 * 防守注意力：越強的得分點越難餵到球。
 *
 * 這是引力的對偶——引力給「隊友」加成（防守分心），注意力給「他自己」扣可及性
 * （防守優先切斷最強的那條線）。少了這一條，接球者選擇會退化成純期望值最大化，
 * 等於假設防守不會反應：實測 Fisher（三分 96）會吃到 40% 球權，真實值約 13%。
 */
export const RECEIVER_ATTENTION_W = 0.030;

// --- 犯規與罰球 ---------------------------------------------------------
export const BASE_FOUL_RATE = 0.085;
export const FOUL_DRIVE_SCALE = 60.0;
export const FOUL_MAX_IMPACT = 0.55;
export const FT_ATTEMPTS = 2;
/** 沒有 ft 屬性時的退路（2025-26 聯盟平均）。 */
export const FT_PCT = 0.7935;
// 罰球是唯一不受防守影響的得分路徑——對超強防守陣容的解藥。
// FT% 分布左偏（一長串不會罰球的大個子），所以 40->70 的落差遠大於 70->99。
// 低出手量用 log(FTA) 迴歸當先驗；Shaq 2001-02 的 .555 是 pr 1.0。
export const CURVE_FT = [
  [0, 0.450], [40, 0.560], [55, 0.700], [70, 0.7935],
  [85, 0.850], [99, 0.900], [120, 0.925], [150, 0.940],
];

// --- 進攻籃板 -----------------------------------------------------------
export const LEAGUE_OREB_RATE = 0.28;
export const OREB_TEMP = 26.0;

// --- Composite 權重表 ---------------------------------------------------
// 基礎屬性（上卡面、可被玩家經營）與 composite（引擎實際使用）分成兩層。
// 這個結構抄自 zengm——它的常數不能抄（那是自己隨機生成的球員尺度），
// 但「基礎 -> composite」的分層本身是對的：把散落各處的加權集中成一張表，
// 調參才看得見、才測得動。
//
// 排序型權重：先由高到低排序再套用，所以 [0.6, 0.4] 意思是「最高的算 6 成」。
export const COMPOSITE = {
  /** 隊伍籃板：偏重最高者，肉體佔 PHYS_REB_WEIGHT */
  teamRebound: [0.35, 0.25, 0.18, 0.12, 0.10],
  /** 協防：對方前二名的加權，避免單點決定一切 */
  helpDefense: [0.60, 0.40],
  /** 隊友擋拆：掩護通常由一個大個子提供 */
  ctxScreen: [0.60, 0.40],
  /** 隊友傳球：球隊只需要一個會送球的人——所以 top-1 主導。
   *  舊值 [0.55, 0.45] 太平：pass 99+45 算出 74.7、pass 70+70 算出 70.0，
   *  只差 4.7 點，等於「隊上有沒有大腦」幾乎沒差別。 */
  ctxPass: [0.80, 0.20],
  /** 隊友創造力：同理，一個持球創造者就夠，但沒有就是真的沒有 */
  ctxCreate: [0.75, 0.25],
};

/** 把排序型權重套到一組值上（不足的權重平均分給其餘）。 */
export function weightedTop(values, weights) {
  const v = [...values].sort((a, b) => b - a);
  if (weights.length >= v.length) {
    return v.reduce((s, x, i) => s + x * (weights[i] ?? 0), 0);
  }
  const head = weights.slice(0, -1).reduce((s, w, i) => s + v[i] * w, 0);
  const restW = weights[weights.length - 1];
  const rest = v.slice(weights.length - 1);
  return head + (rest.reduce((s, x) => s + x, 0) / rest.length) * restW;
}

// --- 夾值 ---------------------------------------------------------------
export const CLAMP = {
  makeLong: [0.05, 0.62],
  makeMid: [0.10, 0.70],
  makeShort: [0.20, 0.88],
  tov: [0.02, 0.28],
  foul: [0.01, 0.25],
  oreb: [0.05, 0.60],
  // 各區佔比的上下限取自 NBA 球隊真實範圍。沒有任何球隊能把 72% 的出手
  // 塞進禁區——防守會塌陷，而 PR50 防守在模型裡不會自動塌陷，所以要夾。
  zoneShort: [0.30, 0.62],
  zoneMid: [0.02, 0.45],
  zoneLong: [0.15, 0.58],
};

// --- 校準目標（2025-26 聯盟）--------------------------------------------
export const LEAGUE_TARGETS = {
  efg: 0.548,
  tovPct: 0.117,
  longPct: 0.3639,
  midPct: 0.4216,
  shortPct: 0.5782,
  shortRate: 0.483,
  midRate: 0.110,
  longRate: 0.407,
  orebPct: 0.28,
  ppp: 1.15,
};
