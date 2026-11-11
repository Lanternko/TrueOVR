# role-audit：E-295 W1（card-0.2.14b-cand → 0.2.14b）

**4/5（建議採用）**：W1 結論站得住。獨立重寫重算與 bonus_pick.npz 差 4e-15、與候選卡 mixBonus 差 0.0005。W1 不讀位置標籤，隨機打亂標籤加分逐位元不變，PF／C 差 0。errata-1 度量失效成立，6 種替代定義 W1 都 0 人碰頂。前瞻台四折獨立重算逐位元一致：W1−A 加權 +0.0022（2022-23 +0.0002、2023-24 +0.0037、2024-25 +0.0026、2025-26 +0.0018），四折皆贏。

扣分：(1) BBRef 對名漏 3 人（Ron Holland、Tre Scott、Adama-Alpha Bal 名字寫法不同，被當無資料走身高推估；不影響前 30）；(2) 加分對 c 連續但不單調（227 位 PF+C>5% 中 99 人先升後降；每 1% C 最多動 0.08 分），屬設計性質：c 升高時扣掉的位置平均也升高（Naz Reid 全 PF +0.84、全 C +0.12）。

## 核對成立
- 前十 Wemby、Jokić、SGA、Luka、Giannis、Chet、Kawhi、Mobley、Mitchell、Tatum；Edwards 第 11。0.2.14a 前 30 無人掉 >5 名。
- 一致度 vs 0.2.14a：T ±0.000、EPM +0.001、2K +0.000，90% 區間含 0。純中鋒加分最多 ±0.20。
- BBRef 對名無錯配；72 位交易球員用 2TM 合併列，分鐘差 ≤150。報告公式與程式一致。
- 身高推估非回歸：MP≥200 的 463 人，取身高 ±1 吋內位置比例平均（80 吋 c 0.31、82 吋 0.68、≥85 吋 ~0.93），未用驗收指標，無洩漏。
- 報告小錯：Siakam 0.2.14a 加分應為 +0.15（報告寫 +0.19）。

## 上線前必修
1. 補 Holland、Scott、Bal 三人 BBRef 對名（手動對照表），重產 card-0.2.14b 與 mix-pool。
2. 賽中 `mix_live.bonus_h` 改讀凍結的 players π、mpos、scales；z 尺、λ、sd、ref 沿用 0214a 基底；拿掉「標籤不在 mpos 給 0」分支；不在表者用 heightPrior[身高]，超出 70–91 吋取端點。
3. 不在卡片但有較早季 BBRef 的老將（Lyles、Niang、Haliburton、Kyrie、Lillard、VanVleet）用最近一季比例。
4. 本季先整季凍結 2025-26 比例；混入 2026-27 比例另開實驗。
5. mix-pool 記 0214a 基底 sha256；`test/mix_day0_gate.py` 改對 card-0.2.14b。

## 關卡
G1 過；G2 過（缺 mix-pool 基底 sha，見必修 5）；G3 過（自有 seed 重抽區間相近）；G4 預註冊凍結早於結果、errata 事後但已揭露且替代定義結論不變；G5 前十合理。腳本：`recompute.py`、`recompute.json`、`bench_check.py`、`bench_check.json`（commit 9f4af2c）。
