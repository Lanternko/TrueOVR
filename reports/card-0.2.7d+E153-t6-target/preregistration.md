# E-153 預註冊：card 0.2.7d 的迴歸目標整個換成 T6

- 日期：2026-11-01。來源：使用者看完 E-142 稽核與關鍵球員表後，對「一定要把另一半的 B12 目標表也換成 T6；而且要在現行的 0.2.7d 上重做」回「GO」。
- 基準：card 0.2.7d（`reports/card-0.2.7d/ranking.csv`，sha 見該目錄 summary.json `ranking_csv_sha256`）。

## 0. 已揭露（lead 看過）
- E-142 全部結果（0.2.7c 底）：T6 三折判 adopt；稽核指出改回單季訓練會判不過、舊 2K 下界貼 0。
- E-142 的 0.2.7c 底 T6 卡關鍵球員名次（2024-25 全換：Banchero 153→65、Herb Jones 8→145、Dillon Brooks 14→183 等；2025-26 只換 RAPM 半：Flagg 264→292）。
- 0.2.7d 的 Flagg 等人名次。
- **沒看過任何 0.2.7d 底換目標卡的數字。**本實驗沒有可調參數：T6 定義、評估規則全部照 E-142（含 errata-1～3）。
- 本實驗用的三季在 E-142 已經用來選 T6，**不是**新的樣本外證據；它回答的是「換到 0.2.7d 底、目標整個換掉後，E-142 的結論還在不在」。真正樣本外是 2026-27（另案）。

## 1. 改動
- **T6**：照 E-142（`reports/E142-card-target/phase1_build.py` 的 t6），t 季 DARKO、BPM 的 O、D 季內 z 平均後轉回每百回合，net＝O＋D。
- **整個目標換成 T6**：卡片迴歸（OVR 擬合）讀到的每一個「影響力目標」輸入，包括 2025-26 的 B12 目標表那一半、RAPM 那一半，以及 primary／fitA／fitB 各 part，全部換成 T6 對應季的值。和目標無關的輸入（mpg、dnp、def-L、能力值、league）不動。
- 歷史原點（2022-23、2023-24、2024-25）：照 E-142 hist 建卡，加上 E-147 的連續 d（`e147.py` 的 scope_feats 替換方式），作為「0.2.7d 底」。

## 2. 臂
| 臂 | 內容 |
|---|---|
| K0 | 0.2.7d 原樣。c0：2025-26 ranking 和 `reports/card-0.2.7d/ranking.csv` 逐位元相同，不同就停 |
| K0h | 歷史三原點的 0.2.7d 底（E-142 hist＋連續 d），目標不換。c0h：關掉連續 d 時要和 E-142 `phase1-work/T0/<季>` 的 ranking 逐位元相同，不同就停 |
| K6 | K0／K0h 的目標整個換成 T6（第 1 節），四原點 |

## 3. 第 0 階段（不產生任何換目標的卡）
先列出 0.2.7d 2025-26 建卡讀「影響力目標」的每一個檔案與欄位（含 B12 目標表的來源與組合方式），和 E-142 c0 實際換掉的部分對照，寫進 `phase0.md`。若找不到能把「B12 目標表那一半」換成 T6 的明確對應（例如 B12 表欄位不是每百回合影響力），**停下回報 lead**，不要自行決定。c0、c0h 也在這一階段做。

## 4. 指標與判定（照 E-142 errata-1～3 的口徑）
- 人群：卡 MIN ≥ 500、K0 與 K6 都有、逐人參考分有項目者。
- 逐人參考分：薪水（errata-1 合約年次權重）0.4、2K（合併檔 `data/external-impact/2k/2k-merged-e142.csv`，sha cb40f9a0…dab4）0.3、下季 RAPM × W(mpg) 0.15；沒有模擬項（E-142 c0s 不過）。缺項按比例重分配。C＝Spearman(OVR, ref)。
- 判定季：2022-23、2023-24、2024-25，三季依人數加權。不做選擇（T6 已定），所以沒有折。
- ①：C(K6)−C(K0) 的球員層 bootstrap（三季球員聯集重抽，2000 次，seed 20261101）90% 下界 > 0。
- ② 薪水不差超過 0.02；②之二 2K 不差超過 0.02；③ 下季 RAPM 不差超過 0.05。
- 全過＝採用候選；①過其他不過＝有副作用；①不過＝沒有改善。採用與否最後由使用者裁定。
- **只報告**：2025-26 的 C、M_sal、M_2k；≤23 歲子組的 M_2k；關鍵球員表（Flagg、Knueppel、Banchero、Simons、Podziemski、Anthony Edwards、Kuminga、Wembanyama、SGA、Jokić、Brunson、Herb Jones、Dillon Brooks、Castle、Harper），K0 對 K6 的 OVR 與名次（MIN ≥ 500）；前 20 名進出。

## 5. 限制
- 只寫 `reports/card-0.2.7d+E153-t6-target/`；E-142、0.2.7d、E-147 目錄唯讀；不改 `src/`。
- 外部數據不轉載進 commit 的檔，只放彙總。
