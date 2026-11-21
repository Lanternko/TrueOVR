# F-126 diag1 預註冊：半季卡乾淨複查（2026-11-01，凍結後不改）

目的：diag0 的殘差用 card 0.2.10 OVR（整季命中率，含 A 半運氣，和 SM_A 共用），會機械性把斜率往負推。diag1 改用只看半季資料建的卡（E-081 的 E-075 半季卡）消掉洩漏。診斷，不改卡，不佔 F-126 實驗額度。

## 修正紀錄（跑任何統計量之前）
原 spec 的 k1 寫錯：寫成 `ans ≈ rapm1 net × mpg_ev`。第 1 輪自檢發現最大差 158.0／183.4（AB／BA），查出 `cards.json` 的 `ans` 來自 `reports/ovr-v58-holdout-2025-26/rapm-{A,B}.csv` 的 `pooledNet`（多季合併，E-081 稱 Q）× `mpg_ev`（`e081_cards.py:381`），不是 `rapm1-*.csv`（2025-26 單季分半 λ=3000，E-081 稱 N）。App 於 2026-11-01 裁定：k1 改為下面的寫法；(r4) 目標就是 Q，另加 (r5)＝N 版。此修正在跑主統計量之前做，修正過程沒有看任何結果（第 1 輪只做了 k1 唯讀核對與人數預檢，沒有算任何 SM 斜率）。主統計量與 (r1)–(r3) 不受影響。

## 資料
- 半季卡：`reports/card-0.2.3+E081-age-residual/cards.json`。`dirs.AB.cand`＝用 A 半特徵建的卡，評估對 B 半；`dirs.BA` 反之。以 `pid` 對人。`cand` 照原樣使用（不重新縮放）。
- SM：`reports/F126-shot-difficulty/diag0/player_game.csv`（以 `playerId`、`half` 聚合 FGA、FGM、sumXFG），SM＝(FGM−ΣxFG)/(FGA+k)，k 從 `diag0/result.json` 的 `k` 讀（243.2327…），不重估。不設 FGA 下限。
- 目標：`reports/card-0.2.3+E081-age-residual/rapm1-A.csv`、`rapm1-B.csv` 的 `net`（同 diag0）。
- 人群：方向 AB＝cards.json `dirs.AB` 的人 ∩ 兩半都有 SM 資料 ∩ 兩半 rapm1 都有；BA 同理用 `dirs.BA`。

## 自檢（任一失敗就停下回報，不出結論）
- k0：`cards.json` 的 `k0.pass` 為 true。
- k1（修正後）：對 cards.json 每個方向每個人，`ans` ≈ `reports/ovr-v58-holdout-2025-26/rapm-{ev}.csv` 的 `pooledNet` × `mpg_ev`，最大差 < 1e-6（AB 的 ev＝B，BA 的 ev＝A）。
- k2：重跑 diag0.py 前後 `diag0/result.json` 的 `slope_mean` 逐位元一致（約 −0.228）。diag1.py 在暫存資料夾重跑 diag0 程式碼，不覆寫 diag0 任何檔案。

## 主統計量
方向 AB：無權重 OLS，`net_B ~ 1 + card_A + z(SM_A)`，取 z(SM_A) 係數。BA 對稱：`net_A ~ 1 + card_B + z(SM_B)`。z 在該方向人群內標準化（母體標準差 ddof=0，同 diag0）。兩方向平均＝主統計量。單位：RAPM／100 回合 每 1 SD SM。

## 不確定性
master＝兩方向人群的聯集。球員 bootstrap 2000 次，`numpy.random.default_rng(20261101)`，每次 `rng.integers(0, M, M)` 抽 master index（M＝master 大小），兩方向用同一組抽樣，各方向取有在抽樣裡的人（含重複）；z 在每次抽樣內重新標準化。90% 區間＝平均的 5、95 百分位；SE＝bootstrap 平均的 std(ddof=1)；MDE＝2.49×SE。

## 判讀（照抄 diag0 規則，寫死）
- 下界 > 0 →「卡片低估難球命中者」
- 上界 < 0 →「卡片高估難球命中者」
- 其他 →「未偵測到（MDE＝…）」
判讀只看主統計量。

## 只報告（不影響判讀；每項同樣給 AB／BA／平均與同一組 bootstrap 的 90% 區間）
- (r1) diag0 式「先殘差化再回歸」：`resid(net_t ~ 1 + card_s)` 對 z(SM_s) 的斜率（含截距）。
- (r2) 主統計量流程，把 card_s 換成 card 0.2.10 OVR（`reports/card-0.2.10/ranking.csv` 的 `ovr`，以 `diag0/pool.csv` 的 name→playerId 對人），同一人群 → 應接近 diag0 的負斜率；這是洩漏的大小。人群內若有人沒有 0.2.10 OVR，列出並從 r2 剔除，註明 n。
- (r3) 不放卡：`net_t ~ 1 + z(SM_s)` 的斜率。
- (r4) 目標換成 cards.json 的 `ans`（Q：V58 多季合併 pooledNet × mpg_ev），主統計量流程（卡＝cand）。標明與主統計量不同口徑。
- (r5) 目標換成 rapm1 net × `mpg_ev`（N 版；AB 用 dirs.AB.mpg_ev 乘 rapm1-B net，BA 用 dirs.BA.mpg_ev 乘 rapm1-A net），主統計量流程。
- (r6) 尺度核對：`cand` 是 (卡 −替補)×出場分鐘／36（乘了分鐘的量），目標 net 是每百回合的率；r6＝主統計量流程把卡換成 `cand / mpg_ev`（率尺度）。純核對，事前列入，不影響判讀。

## 限制（寫進報告）
- 半季卡是 card 0.2.3 架構（E-075/E-081），不是 0.2.10。
- 係數 coef[AB] 用 B 半特徵 → RAPM_A 訓練（群體係數，對個別球員洩漏極小）。
- 人群因 diag0 逐球資料只涵蓋 303 人而小於 cards.json 的 389／388 人。
- 本診斷只有 2025-26 一季分半；樣本內分半診斷（R-007）。

## 流程
1. 本檔＋ sha256 先 commit（單獨一個 commit）。
2. 再寫並跑 `diag1.py` → `result.json`、`report.md`、`inputs.sha256`。
3. 發現設計有錯：照原設計跑完，另列「事後」段。
