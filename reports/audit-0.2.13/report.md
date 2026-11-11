# 稽核 card／inseason 0.2.13（commit f0dc684）

稽核人：role-audit（獨立 session）。腳本：同夾 a4_pnr.py、a45.py、a5.py、a7.py（皆 `python -I -X utf8`）。

## 判定表
| # | 項目 | 判定 | 證據 |
|---|---|---|---|
| 1 | 預註冊／選臂 | 成立 | prereg sha256 與 .sha256 檔相符；mtime prereg 23:04:47、訓練輸出 23:14:22、results 23:14:29（凍結早於結果）。results.json：G50_W04 M1 最高 .24278 但 low_p90=71.2>70，依預註冊「#1 不過改取過 #1 者 M1 最高」→ G50_W05（.24236）；其餘過 #1 的臂 M1 都更低（G50_W06 .24111、REL 全 >72 或更低）。pnr_live.py 定義與 e258_prep.py 對得上：量＝POSS/MIN×36、率＝(PTS+kμ)/(POSS+k) 收縮、G50＝率只在 POSS≥50 排、w=0.5、ρ 用 corrcoef。 |
| 2 | 樣本內外 | 成立（有保留） | E-258 的 M1 R² 是「留一季預測下季進攻 RAPM」（E-255 prereg 第 14 行），三折 +.019/+.031/+.006，bootstrap 90% CI [+.0023,+.0335]，是跨季樣本外。保留：(a) 12 臂取最大有選擇樂觀偏差（報告已寫）；(b) 上卡時另做的選擇——Mapper 頂端尾巴開／底端關、窗口 246、k／μ 取 2025-26——不在 E-258 預註冊內，但都沒用結果挑參數（k、μ 是 E-255 est_k 公式，我重算逐位相同）；(c) 上卡後的卡片層沒有新的樣本外量測。 |
| 3 | 窗口 L-117 | 成立 | 四季滑動窗口：weights_c0＝{2025-26 .417, 2024-25 .25, 2023-24 .083, 2022-23 1e-12}；`window(c, past, cur)` 在 c>0 加 CUR 季（u＝w·c/82）；pnr_live.live 在 run_c4_live_rookie.vet_pnr 被呼叫（PNL.live(c, …)），老將 attrs['pnr'] 被覆寫、新秀用 live 值或 ROOKIE_P0。daily_inseason_update._run 第 579 行 step_fetch_pnr 在 c4 之前；fetch_synergy_pnr.mjs 失敗不覆寫舊檔。實檔 data/defense-seventh/2026-27/synergy-pnr.json fetchedAt 2026-11-07T16:57Z、135 列。_check0213/new/pnr.json 存在。 |
| 4 | 卡片數字重算 | 成立（一個小瑕疵） | a4_pnr.py 從原始 Synergy＋player-games 全部重算（不讀凍結池）：582 人 pnr 與 card-0.2.13/pnr-attr.csv 最大誤差 **0.0**（k=141.4619、μ=0.88114、ρ=0.047616 全相同）。官方卡 vs w246 擬合卡：max\|ΔOVR\| 0.90、mean 0.032、前 20 換 Butler/Murray 各 1；0.2.12c 官方 vs 0.2.12c-w246：max 1.00、mean 0.033、同樣 Butler/Murray——同級。瑕疵：窗口權重 2022-23＝1e-12 會讓只在 2022-23 有擋拆回合的 7 人（McDermott、Porziņģis、Carter Jr.、Tate、Livers、TyTy Washington Jr.、Chandler）vol 變成 ~1e-11 而非 0，名次高過 214 個真 0 回合者，pnr 約 51 而非 43.3（+7.7）；OVR 影響 <0.5，無名次後果，但屬洩漏。 |
| 5 | R-109 | 成立 | 卡片 0.2.12c→0.2.13：前 20 進出 0；前 100 移動 ≥10 名 3 人（Knueppel 81→71、Alexander-Walker 66→78、McDaniels 89→79）；max\|ΔOVR\| 1.5。賽中 c0→new（492 人）：前 20 進出 0；舊前 100 移動 ≥10 名 2 人（Edgecombe 78→93、Dybantsa 97→112），任一邊在前 100 為 3 人（多 Josh Hart 106→96）。皆遠低於 ≤2／≤25 門檻。 |
| 5b | PATCH 是否妥當 | 有疑慮（版號層級，非數字） | README：影響小（前 20 ≤2、前 100 ≤25）＝字母版（R-064）；PATCH 定義是「沒有變準、影響大」。本次影響按數字屬「小」。R-173 選 PATCH 的依據只有 R-137（gravity 由使用者升 PATCH）先例，R-173 的使用者原話是「做進卡片」，沒指定位數。不影響數字，交使用者確認。 |
| 6 | 回退 | 成立 | `sha256sum _check0213/{ref,c0,c0b}/ranking.csv` 三份同為 952e941e…bf24；new 為 a71cd2c3…。meta 版號 ref/c0/c0b＝inseason 0.2.12e、new＝0.2.13，dataCutoff 同為 2026-11-06、132 場。保留：我沒重跑，ref 是否真由 f0dc684 之前的程式產出只能信 check_inseason_0213.py 的敘述與 ref.log 版號字串。 |
| 7 | G5 | 見下表 | 前十長人名次與 0.2.12c 完全相同（pnr 對頂級長人幾乎不動）。 |
| G1 | npm test | 過 | 本機跑 43＋23 tests OK。 |

## G5：0.2.13 卡片前十長人（C／PF）
2K27 名次＝reports/ovr-v55-2k27-compare/merged.csv 的 overall2k 排序（575 人，同分依檔序）；RAPM＝reports/impact-rapm/rapm.csv pooledNet、pooledPoss≥5000 的排名（478 人，樣本內性質，僅對照）。

| 卡片名次（0.2.12c） | 球員 | 位置 | OVR | 2K27 名次 | RAPM 名次 | pnr（POSS_eff） |
|---|---|---|---|---|---|---|
| 2（2） | Nikola Jokić | C | 104.4 | 3 | 1 | 74（124） |
| 4（4） | Victor Wembanyama | C | 101.3 | 2 | 5 | 66（85） |
| 5（5） | Giannis Antetokounmpo | PF | 99.0 | 5 | 3 | 92（134） |
| 8（8） | Jayson Tatum | PF | 95.4 | 14 | 44 | 96（287） |
| 15（15） | Chet Holmgren | PF | 93.5 | 36 | 8 | 57（21） |
| 17（17） | Evan Mobley | PF | 92.8 | 26 | 51 | 80（86） |
| 19（19） | Jalen Williams | PF | 92.4 | 48 | 213 | 93（316） |
| 23（23） | Joel Embiid | C | 90.7 | 16 | 10 | 51（2） |
| 29（29） | Karl-Anthony Towns | C | 89.7 | 13 | 106 | 61（37） |
| 31（31） | Jalen Johnson | PF | 89.5 | 27 | 152 | 59（251） |

組成與 0.2.12c 同；落差大者（Jalen Williams RAPM 213、Towns RAPM 106、Johnson 152）是既有現象，不是 pnr 造成。全體對 2K27 ρ 0.7656→0.7698（575 人，僅參考，非樣本外判定）。

pnr 副作用最大的人（前 150 名移動）：
| 球員 | 名次 | pnr（回合） | 2K27／RAPM | 判斷 |
|---|---|---|---|---|
| Nickeil Alexander-Walker | 66→78 | 56（218） | 70／101 | 合理（E-258 已預告的副作用：擋拆多但效率低，名次本來偏高於 2K／RAPM） |
| Scotty Pippen Jr. | 48→56 | 51（68） | 259／339 | 合理（原名次遠高於兩個基準） |
| Donte DiVincenzo | 82→90 | 67（119） | 174／131 | 合理 |
| Stephon Castle | 132→147 | 59（304） | 32／115 | 有疑慮：2K 名次 32 遠高，下掉方向與 2K 相反，量大但效率低 |
| Kon Knueppel | 81→71 | 88（199） | 58／46 | 合理（上升向 2K／RAPM 靠近） |
| Jaden McDaniels | 89→79 | 79（97） | 50／156 | 與 RAPM 相反，與 2K 同向 |
名次掉最多前 8 名全是 400 名以後 pnr＝43 的板凳（Trey Alexander 等），名次變動無意義。pnr 與 ΔOVR 相關 0.44。

## 給主 session 的結論
數字層面全部可重現；問題只有：(1) 1e-12 權重洩漏 7 人（+7.7 pnr）；(2) PATCH vs 字母版（R-064 影響小）；(3) Mapper 底端關／頂端開是上卡時的選擇，不在 E-258 預註冊；(4) 工作樹裡 pres_drive.py、run_c4_live_rookie.py、window8.py 有未 commit 修改，本稽核對的是 f0dc684 前後的產物，沒檢查這些未 commit 修改。
