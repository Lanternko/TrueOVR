# E-194 診斷計畫（F-133；跑 diag.py 之前寫定，跑完不改定義，L-026）

來源 spec：`spec.md`。全部用 KJ 卡（`reports/card-0.2.10c+E190-creation-jumper/work/KJ-<季>/out/ranking.csv`），三歷史原點 2022-23／2023-24／2024-25，MIN≥500，人群＝E-190 a2 的 `s_data('KJ')`（下季 poss≥1000 且有下季 mpg）。預期每季 n＝262／286／319（`results-final.json` 的 a2.n_eval），不同就停。
bootstrap：球員層、季內重抽、2000 次、seed 20261101，報 90% 區間（5%、95%）；跨季合併＝人數加權平均（同 E-190）。只讀 E-190 的 work/，不寫它。

## 記號
- `net`＝下季 RAPM net×wfun(下季 mpg)（`s_data` 的 `net`）；`ovr`＝KJ 卡 ovr；`t6net`＝`work/base-KJ-<季>/<季>/rapm-R.csv` 的 pooledNet（卡片擬合的目標）。
- `pct(x)`＝rank(x)/n（`E173.pct`）；`sp`＝Spearman（`E173.sp`）。
- 殘差 e_net＝pct(net) − pct(ovr)，pct 在整個 a2 人群（n 人）上算＝E-190 a2 口徑；用它重現 E-190 的 S(drive)（合併 −0.2435）當閘門。

## D1 目標 vs 擬合
- t6net 缺的人（約 8 人，T6 池沒有）：D1 只算有 t6net 的子群（n_t6）；pct(t6net) 在子群上算（rank/n_t6）。
- e_target＝pct(net) − pct(t6net)；e_fit＝pct(t6net) − pct(ovr)；恆等式：max|e_target + e_fit − e_net| < 1e-9（子群上逐人檢查）。
- 報：Spearman(drive, e_target)、Spearman(drive, e_fit)、Spearman(drive, e_net，子群)，三季各自＋合併，bootstrap 區間。
- 各占幾成：Spearman 不可加，改用 drive 名次與各殘差的共變異：share_target＝cov(rank(drive), e_target) / cov(rank(drive), e_net)，share_fit 同理（兩者和＝1）。同樣 bootstrap（每季算份額再人數加權前先對共變異加權合併：合併共變異＝Σ n_t·cov_t / Σ n_t，再取比值）。

## D2 哪一欄多給分
- 卡的線性部分：`summary.json`（`work/base-KJ-<季>/<季>/cards/K0/primary/`）`formula` 的 14 欄（long mid short ft drive foulDraw tovSkill pass rebound onBall help heightInches creation pressure）標準化係數 b[0:14]，加位置交互（PG／SG／SF／PF 各 4 個：long short rebound help，順序 b[14+4k : 18+4k]；C 為基準；pass 交互已被 E-180 拿掉）。z_j＝(x_j − attributeMean_j)/attributeSD_j，x 用 ranking.csv 的屬性欄（小數 1 位）。
- 核對：重建 pred0 與 ranking.csv 的 pred0 欄，最大絕對差應 <0.02（四捨五入造成）；超過就停。
- 逐人貢獻（per36）：c_j＝(b_j + 該人位置的交互係數 if j∈{long,short,rebound,help}) × z_j。對應 spec 的 β_j×(x_j − 人群平均)，人群平均＝擬合池平均（formula.attributeMean）；β 讀卡建置輸出，非重算。
- 換成 OVR 分：c_j × 29/(PR99 − PR50)（`scaleAnchorsPer36`，OVR 映射在 PR50 以上的斜率；全部人用同一個斜率，下半段實際斜率更大，這裡不分段）。per36 值也存。
- 報（OVR 分）：每欄 Spearman(drive, c_j)；「drive 前 25%（每季內 drive ≥ 第 75 百分位）」c_j 平均 − 其他人平均；這群人 e_fit 平均 − 其他人 e_fit 平均（子群）；Σc_j 的同樣差、ovr 的同樣差。三季人數加權合併＋bootstrap 區間。
- 前 3 欄＝合併差最大的 3 欄（正向，給切入型球員多給分最多）。
- 注意 c_j 只含屬性線性部分；防守加成、align、H1 封頂、OVR 非線性映射不在內（差額另列 `ovr diff − Σc_j diff`）。

## D3 切入在現實值多少
- 欄：同上 14 欄（KJ 擬合用的 13 項＋help、heightInches；stamina、physique 擬合時已拿掉），標準化用該季 KJ `formula` 的 mean／SD。
- 形式：位置交互（4 位置×4 欄，同卡）＋ridge λ=1（只罰斜率）。權重：單位權重（下季 RAPM 沒有卡擬合用的 1/(mc+s²) 量測方差，故兩條迴歸都用同一組單位權重，才能互比；與卡片本身的 drive 係數另列對照）。
- 三個回應變數（都轉成 pct，單位＝百分位×100）：pct(net)（下季 RAPM，整個 a2 人群）、pct(t6net)（子群）、pct(ovr)（整個 a2 人群，參考）。
- 報 drive 每 10 點係數（＝β_drive/SD_drive×10×100，百分位分），±bootstrap SE（2000 次標準差）與 90% 區間，三季各自＋合併；並排：對 t6net 的同口徑係數、兩者差（net − t6net，同一組重抽）、KJ 卡本身 valuePer10AttributePoints.drive（per36，三季人數加權，只供對照單位不同）。
- 獨立資訊：回應＝pct(net)，比較含 drive 與拿掉 drive 的迴歸，Spearman(預測, net) 的變化 Δρ＝ρ(拿掉)−ρ(含)：(i) 樣本內；(ii) 10 折交叉驗證（折按球員固定指派，seed 20261101；bootstrap 時同一球員的重複列同折，避免洩漏）。三季人數加權合併＋bootstrap 區間。同表列卡片 ovr 對 net 的 ρ 當參考。樣本內結果不算證據（R-007），以交叉驗證為準。

## 球員表
E-190 預註冊 §2 的 15 人（Jordan Miller、Trendon Watford、Aaron Holiday、Michael Porter Jr.、Lauri Markkanen、Kristaps Porziņģis、Stephen Curry、Shai Gilgeous-Alexander、Giannis Antetokounmpo、Ja Morant、Zion Williamson、Jalen Williams、LeBron James、Nikola Jokić、Anthony Edwards）在三季中出現者的逐季列，加三季合併 drive 前 10 名（以 drive 值排，同值照季序）。欄：季、drive、e_net、e_target、e_fit、前 3 欄的 c_j（OVR 分）。不在 a2 人群的人註明。

## 不做
不改卡、不提採用、不調參。結果檔 `results.json`、報告 `report.md`；重跑 `python -I -B -X utf8 reports/F133-drive-scoring/diag.py` 需逐位一致（固定 seed）。
