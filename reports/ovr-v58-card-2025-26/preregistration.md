# v58 卡片修正預先註冊：前十「過譽升幅上限」

本檔案在跑任何 v58 候選之前寫成，鎖定診斷、公式、固定先驗候選值、沿用 v57 的 19 項硬門檻與
選版規則。寫完後候選集合不得再改；若之後發現預註冊外問題，只能在 `report.md` 另加
「預註冊外探索」段落並明確標示。

- 基準資料 SHA256（`data/season-league.json`）：`497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6`（本輪不碰）。
- 診斷：`reports/ovr-v58-card-2025-26/diagnose.py` → `diagnosis.json`（唯讀既有產物）。
- 本輪只新增 `reports/ovr-v58-card-2025-26/` 下的檔案。v57 及更早的 reports、`scripts/`、`src/`、
  `data/`、`reports/player-impact-v53/calibrate-spread.mjs`、`reports/status/status.json` 全部唯讀。

---

## 一、量化診斷（v57 G3-δ0.25 為什麼差 #18）

v57 最佳候選 G3-δ0.25（γ=1.0、δ=0.25、taper PR 90/96）的 19 項硬門檻過了 18 項，唯一失敗是
#18「Wembanyama／Giannis／Jokić／Chet 四人留前十」。實際前十末段為：

| 名次 | 球員 | pos | pred | pred0 | defenseBonus | align | lift=bonus+align | RAPM pooledNet 名次 | 2K27 名次 |
|---|---|---|---|---|---|---|---|---|---|
| 10 | **Draymond Green** | PF | 3.423 | 0.827 | **2.356** | 0.239 | 2.595 | 46 | 142 |
| 11 | Luka Dončić | PG | 3.353 | 3.377 | 0 | −0.025 | −0.025 | 16 | 5 |
| 12 | Jalen Suggs | PG | 3.351 | 0.803 | 2.443 | 0.105 | 2.548 | 85 | 110.5 |
| 13 | Ausar Thompson | SF | 3.279 | 0.070 | 2.474 | 0.735 | 3.209 | 28 | 47.5 |
| 14 | **Giannis Antetokounmpo** | PF | 3.254 | 2.690 | 0 | 0.564 | 0.564 | 3 | 5 |

診斷要點（全部由 `diagnose.py` 產生）：

1. **Draymond 不是被 align 拉進前十，是被 defenseBonus 拉進去的。** 他的 pred0 排第 72；
   只加 align（δ=0.25）排第 49；只加 defenseBonus（γ=1.0，PR 82.8 使 taper=1.0，centeredD=2.356）
   就排第 12；兩者相加排第 10。lift 的 **90.8% 來自 bonus**。
2. **Giannis 差第 10 名 0.169 分。** 他的 align=0.564（r−pred0=2.256），若只調 δ，需要
   δ≈0.325 才能追平第 10；但 v57 的 G3-δ0.4 實測會讓 Chet 掉到第 13（其他被 align 拉升的人
   漲得更多），所以「只把 δ 調大」不是可行解。
3. **擋在 Giannis 前面的 13 人裡，有 8 人（White、Wagner、Caruso、Gobert、Holiday、Draymond、
   Suggs、Ausar）的 lift 主要來自 bonus，且卡片名次都優於自己的 RAPM 名次。** 其中 Draymond
   （RAPM 46）、Suggs（85）、Ausar（28）、Gobert（29）、Holiday（27）在 RAPM 眼中都不是前十，
   卻被 bonus 推進前十或前十邊緣。這正是「向上修正沒有上限」造成的過譽（over-rating）。
4. v57 的門檻體系只有「不誤傷」上界 `rank ≤ max(2K27, RAPM)`，**沒有對稱的下界**；因此一個
   被 bonus 大幅拉升、但兩個外部基準都不支持的球員（Draymond）不會被任何既有門檻擋住，
   只能靠 #18 間接抓到。v58 要補的就是這個對稱面。
5. 保護組盤點：側翼三人 Caruso（rank 5／RAPM 9）、Herbert Jones（22／14）、Marcus Smart（36／30）
   中，只有 Caruso 在 RAPM 眼中是前十邊緣；Jones/Smart 的卡片名次本來就比 RAPM 差，不會被
   「不得優於 RAPM 名次」的上限碰到。長人組 Gobert（6／29）、Draymond（10／46）、Mobley（16／47）
   會被碰到；Queta（20／13）、Wembanyama（7／5）、Embiid（24／10）、Jaren Jackson Jr.（34／?）
   不會。七人名單中只有 Gobert 會被碰到（6→最多 29，門檻是 ≤60.5，安全）。

> 診斷檔另含 `staticCapSensitivity`：直接對 v57 G3 既有 pred 做的**靜態固定點敏感度**（不重跑
> 回歸、不重算 OVR、不產生 ranking.csv），只用來檢查上限值不會明顯自相矛盾。真正候選一律由
> 本輪 `calibrate-wing.py` 從 E2 league 重新計算。

### 被否決的方向（不佔候選名額）

- **只調大 δ（v57 G3-δ0.4 已測）**：Giannis 進前十但 Chet 掉到 13，且 ρ(2K27) 從 0.5299 降到
  0.5175；#18 只是換一個人失敗。
- **純 2K27 名次衰減／封頂（任務方向 1 的字面版）**：擋住 Giannis 的人 2K27 名次橫跨 47.5–142
  （Ausar 47.5、Gobert 60.5、Holiday 81、Suggs 110.5、Draymond 142）。任何能抓到 Draymond 的
  2K 門檻（例如 >100）都抓不到 Gobert/Holiday/Ausar；把門檻降到 40 又會同時打到側翼三人
  （Jones/Smart 2K=142、Caruso 94）與 Wagner（47.5），無法乾淨分開。因此改以 RAPM 名次作上限
  參考（見 H1），並把「2K∪RAPM 共識版」列為 H3 對照。
- **固定分數上限 C（任務方向 3 的字面版）**：診斷顯示要讓 Draymond 掉出前十，C 需低於
  ≈2.43；但 C=2.0 會把 Marcus Smart 的 lift 從 2.995 砍到 2.0（pred 0.257），有掉出 #13 的風險；
  C 在 2.4 附近才能同時滿足，數值過於貼線、像事後調參，故不列為候選。改以「名次上限」表達，
  讓 caps 由外部基準決定，而不是由 pred 尺度決定。

---

## 二、共同基線（與 v57 G3-δ0.25 完全相同）

全部候選都疊在 **E2-λ0.4 的卡片 league**（`reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json`）
之上，不碰吃餅折扣、不改回歸目標／設計矩陣／ridge。共用定義：

```
alpha = 0.5 ; BLEND_PER36 = 0.75 ; BLEND_POSS = 1000 ; BONUS_MIN_POSS = 5000
PR_LO, PR_HI = 90, 96                          # v57 已鎖定的 taper 錨點，本輪不改
posMeanD(pos) = MIN 加權平均 0.75*pooledD，池 = 同 pos 且 pooledPoss >= 1000
centeredD(i)  = 0.75*pooledD(i) - posMeanD(pos(i))
r(i)          = 0.75*pooledNet(i) - MIN 加權位置均值（池 pooledPoss >= 1000）
pred0(i)      = 回歸預測值（與 E2-λ0.4 的 predictedPer36 相同）
PR(i)         = pred0(i) 在縮放參考池（MIN >= 500, n=379）的百分位
taper(PR)     = clip((96-PR)/(96-90), 0, 1)
bonus(i)      = 1.0 * max(0, centeredD(i)) * taper(PR(i))   若 pooledPoss >= 5000，否則 0
align(i)      = 0.25 * (r(i) - pred0(i))                     若 pooledPoss >= 5000，否則 0
pred_base(i)  = pred0(i) + bonus(i) + align(i)
```

外部名次（全部用既有 `reports/impact-rapm/rapm.csv` 與 `reports/ovr-v55-2k27-compare/merged.csv`，
口徑與 v57 `evaluate.mjs` 完全一致）：

```
RAPM_rank(i) = pooledNet 由高到低的名次；rapm.csv 先以 name 去重（同名最後一列覆蓋，
               與 evaluate.mjs 的 Map 行為一致），池 = pooledPoss >= 5000
rank2k(i)    = merged.csv 的 rank2k（非空；可能為 .5）
```

---

## 三、候選方向與固定值（跑結果前鎖定，共 8 個）

全部由 `calibrate-wing.py` 以 `--direction H1|H2|H3|H4` 實作。上限一律作用在 `pred` 後處理、
OVR percentile 映射之前。

### H1：RAPM 升幅上限（總 lift，2 值）

```
ref(i)      = RAPM_rank(i)
allowed(i,m)= max(1, ceil(ref(i) - m))
lift(i)     = bonus(i) + align(i)
T(A)        = 候選自己 pred 分布中第 A 高的值（固定點迭代，見下）
pred(i)     = min( pred(i), max(pred0(i), T(allowed(i,m))) )   若 lift(i) > 0 且有 ref
            = pred(i)                                         其餘
```

- **候選值：`m ∈ {0, 10}`**。`m=0` 是「卡片不得比 RAPM 名次更好」的嚴格對稱版（v57 的
  `rank ≤ max(2K,RAPM)` 是上界，這是下界）；`m=10` 允許 RAPM 名次有 10 名的估計誤差，
  是較小干預。兩個值在診斷的靜態敏感度都能讓四人留在前十（見 diagnosis.json），
  但實際結果仍以本輪候選輸出為準。
- **只砍向上的 lift**：`max(pred0, T)` 保證不會把球員壓到 pred0 以下；pred0 本身已優於
  allowed 名次時，等於把該球員的 lift 全部歸零、保留原 pred0。
- 預期副作用：Draymond（RAPM 46）→ 名次 ≥36/46；Gobert（29）、Holiday（27）、Suggs（85）、
  Ausar（28）一併被壓回 RAPM 名次附近；White（6）、Wagner（7）、Caruso（9）在 m=10 不受影響、
  m=0 只被壓到各自 RAPM 名次（仍遠優於其門檻上限 70.5/47.5/94）。Giannis（RAPM 3）與
  Chet（8）、Jokić（1）、Wembanyama（5）不受上限影響，靠其他人下移進入/留在前十。
- 主要風險：ρ(RAPM) 可能因上限使用 RAPM 而**機械性上升**（與 v57 G3/G4 相同的自我實現問題），
  因此 ρ(RAPM) 只當下限、不當排序依據；ρ(2K27) 完全不在 H1 的機制裡，仍可作為外部判準。

### H2：RAPM 升幅上限（只砍 defenseBonus，2 值）

```
ref(i), allowed(i,m), T(A) 同 H1
bonus'(i) = min( bonus(i), max(0, T(allowed(i,m)) - pred0(i)) )   若 bonus(i) > 0 且有 ref
          = bonus(i)                                              其餘
pred(i)   = pred0(i) + bonus'(i) + align(i)
```

- **候選值：`m ∈ {0, 10}`**。理由：診斷顯示 Draymond lift 的 90.8% 來自 bonus，align 只佔 9.2%；
  若只砍 bonus 就能修好 #18，代表不需要動 align（align 本來就是往 RAPM 拉，與上限使用 RAPM
  有部分重疊）。這是比 H1 更窄的干預，若表現不輸 H1，依選版規則的「較小干預」應優先。
- 注意：H2 的上限只保證 `pred0+bonus` 不超過 T；align 仍可再把 pred 推高，所以它不是嚴格的
  名次上限，而是「bonus 不得單獨把人推過頭」。若 align 很大（例如 Ausar 0.735），仍可能留在
  前十邊緣；#18 是否過仍以實際 ranking 為準。

### H3：2K27∪RAPM 共識升幅上限（總 lift，2 值）

```
ref(i)      = min( rank2k(i), RAPM_rank(i) )   兩者都有時；只有一個時用該值；都沒有則不設限
allowed(i,m)= max(1, ceil(ref(i) - m))
其餘公式與固定點同 H1
```

- **候選值：`m ∈ {0, 10}`**。這是任務方向 1「對 2K 名次很差的球員封頂」與 RAPM 版的合併：
  只有當**兩個外部基準都認為**某球員不該那麼高時，才用兩者中較寬的名次封頂。
- 與 H1 的差別：對「2K 比 RAPM 更寬容」的球員（例如 Luka 2K 5／RAPM 16）H3 用 5，H1 用 16；
  但診斷顯示擋在 Giannis 前的 13 人裡，會被上限碰到的幾位（Draymond/Suggs/Ausar/Gobert/
  Holiday/White/Wagner/Caruso）都是 RAPM 名次 ≤ 2K 名次，所以 H3 與 H1 在**實際會 bind 的
  球員**上幾乎相同。列為對照是為了確認「加入 2K 參考」是否會改變結果。
- **必須揭露的偏誤**：H3 的 ref 使用 2K27，會讓 ρ(2K27) 部分機械性上升（自我實現）。
  因此若 H1 與 H3 都全過，選版時**優先 H1**（ρ(2K27) 對 H1 仍是完全外部信號）。

### H4：不對稱 align（2 值，對照組）

```
align_asym(i) = align(i)            若 align(i) <= 0
              = phi * align(i)      若 align(i) > 0
pred(i)       = pred0(i) + bonus(i) + align_asym(i)
```

- **候選值：`phi ∈ {0.0, 0.5}`**。任務方向 2「向上拉的幅度小於向下壓」；φ=0 是完全不對稱
  （只保留向下 align），φ=0.5 是一半。
- 預期：**不足以修 #18**。Draymond 的 align 只有 0.239（佔 lift 9.2%），把向上 align 全部
  拿掉只會讓他從 3.423 降到 3.184，而 Giannis 也會從 3.254 降到 2.690（他的 align 0.564
  是正的），差距反而擴大。列為最小干預對照，用來證明「問題不在 align 的方向不對稱」。

### 固定點與名次決定（全部候選共用）

- `T(A)` 用候選**自己**的 pred 分布（全部 582 列）計算；因為 cap 會改變分布，採固定點迭代：
  每次重算 `T`、只會把 pred 往下調，最多 100 次，直到最大變動 < 1e-10。收斂後才寫 ranking。
- `T(A)` 取第 A 高值再減 `1e-9`，確保被 cap 的球員嚴格排在該名次之後，不會因浮點相等
  而擠進前一名的位置。
- 最終名次排序：`pred` 由高到低；同值時 `pred0` 由高到低；再同值時 name 的 UTF-8 字典序。
  這個 tie-break 只影響精確同值的順序，不影響 OVR（同 pred 同 OVR）。
- 上限只作用於 `pooledPoss ≥ 5000` 且有外部名次的球員；沒有 RAPM/2K 名次者不設限。

---

## 四、驗收門檻（沿用 v57 第三節，數字不變）

量測口徑與 v57 完全相同：`pooledPoss ≥ 5000` 池；ρ(2K27) 只納入 merged.csv 中 `rank2k` 非空者；
名次用候選自己的 ranking.csv；比較基準 v53 用 `reports/ovr-calibrated-2025-26/ranking.csv`。

### A. 沿用 v56 的 9 項（硬門檻）

| # | 門檻 | 寫死的數字 |
|---|---|---|
| 1 | Karlo Matković 相對 v53（第 7）下修 ≥10 名 | `rank ≥ 17` |
| 2 | John Collins 相對 v53（第 29）下修 | `rank > 29` |
| 3 | Isaiah Stewart 相對 v53（第 32）下修 | `rank > 32` |
| 4 | Luka Garza 相對 v53（第 33）下修 | `rank > 33` |
| 5 | Neemias Queta ≤ max(2K27 110.5, RAPM 13) | `rank ≤ 110.5` |
| 6 | Rudy Gobert ≤ max(2K27 60.5, RAPM 29) | `rank ≤ 60.5` |
| 7 | Jalen Smith ≤ max(2K27 220, RAPM 65) | `rank ≤ 220` |
| 8 | ρ(2K27) 地板 | `≥ 0.4828`（= F2 0.4878 − 0.005） |
| 9 | ρ(RAPM pooledNet) 地板 | `≥ 0.5650`（= F2 0.5700 − 0.005） |

### B. 側翼／後衛防守門檻（硬門檻）

| # | 門檻 | 寫死的數字 |
|---|---|---|
| 10 | RAPM pooledD 前 30 的側翼＋後衛（14 人）滿足 `rank ≤ max(2K27,RAPM)` 的人數 | `≥ 10 / 14` |
| 11 | Herbert Jones ≤ max(2K27 142, RAPM 14) | `rank ≤ 142` |
| 12 | Alex Caruso ≤ max(2K27 94, RAPM 9) | `rank ≤ 94` |
| 13 | Marcus Smart ≤ max(2K27 142, RAPM 30) | `rank ≤ 142` |
| 14 | 長人組（RAPM pooledD 前 30 的 PF/C，16 人）滿足 `rank ≤ max(2K27,RAPM)` 的人數 | `≥ 14 / 16` |

### C. 前十長人門檻（硬門檻）

| # | 門檻 | 寫死的數字 |
|---|---|---|
| 15 | 前十名裡 `pos ∈ {PF,C}` 人數 | `≤ 5` |
| 16 | 前十名不得含 Evan Mobley | 硬門檻 |
| 17 | 前十名不得含 Aaron Gordon | 硬門檻 |
| 18 | Wembanyama／Giannis／Jokić／Chet 四人全部留前十 | 硬門檻 |

### D. 回報項

| # | 內容 | 基準 |
|---|---|---|
| 19 | 觀察項：前十長人是否恰為該四人；若不是，列出多出的長人與其 2K27／RAPM 名次 | 不計入通過數 |
| 20 | ρ(RAPM pooledD) | 硬性下限 `≥ 0.2972`（E2 基準），計入 19 項硬門檻；另回報與 F2 的 0.3624 相比 |
| 21 | `data/season-league.json` SHA256 | 必須為 `497725ec…5a79bf6` |
| 22 | 候選 vs E2 vs F2 的前十、七人名次、側翼 14 人名次表 | — |
| 23 | Wembanyama 名次變化 | F2 第 1；E2 第 2 |

硬門檻合計 **19 項**（#1–18 ＋ #20 的 ρDef 下限）。

---

## 五、選版規則（沿用 v57 第四節，僅補充 v58 的「較小干預」定義）

1. **方向內選代表**：每個方向先取通過硬門檻數最多者；同分取 **ρ(2K27) 較高**者；仍同分取
   「前十長人數較少」者；再同分取**較小干預**者。v58 的較小干預定義：上限方向取 **margin 較大**
   （10 > 0），不對稱 align 取 **φ 較小**（0 < 0.5）。
2. **跨方向選最終建議**：在全部 19 項硬門檻都過的方向代表裡，取 **ρ(2K27) 最高**者。
   ρ(RAPM) 一律不得用作跨方向排序（G3/G4 與本輪 H1–H3 的 align/上限都含 RAPM，會機械性上升）。
3. **若沒有任何方向代表全過 19 項**：取通過數最多者；同分取 ρ(2K27) 較高者。若側翼門檻
   （#10–13）與前十長人門檻（#15–17）無法同時滿足，不自動升為正式卡片，報告並列兩者交由
   使用者裁決。
4. **正式卡片切換條件**：最終建議必須同時 (a) 19 項硬門檻全過，且 (b) ρ(2K27) ≥ 0.4878
   （F2-γ0.5 水準，不只是地板 0.4828）。否則只提出建議、不切換；正式卡片維持 E2-λ0.4，
   並說明 F2-γ0.5 與 v57 G3-δ0.25 何者仍是較佳備選。
5. **不做的事**：不放寬 E2 的吃餅折扣；不自由估計任何新係數；所有 margin/φ 都是本文件寫死的
   固定先驗；看到結果後不新增或修改門檻；不修改 `data/`、`scripts/`、`src/`、`runs/`、任何
   既有 reports 檔案。

---

## 六、產出清單

```
reports/ovr-v58-card-2025-26/
  diagnose.py                    # 已完成（唯讀診斷）
  diagnosis.json
  preregistration.md             # 本檔（候選鎖定）
  calibrate-wing.py              # 從 v57 複製後擴充 H1–H4（v57 原檔不動）
  card-H1-m0/ card-H1-m10/
  card-H2-m0/ card-H2-m10/
  card-H3-m0/ card-H3-m10/
  card-H4-phi0.0/ card-H4-phi0.5/
  evaluate.mjs                   # 沿用 19 項硬門檻，讀 H1–H4 與三個基準
  evaluation.json
  report.md
```

跑法（ preregistration 寫完後才執行）：

```bash
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H1 --capMargin 0  --out reports/ovr-v58-card-2025-26/card-H1-m0
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H1 --capMargin 10 --out reports/ovr-v58-card-2025-26/card-H1-m10
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H2 --capMargin 0  --out reports/ovr-v58-card-2025-26/card-H2-m0
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H2 --capMargin 10 --out reports/ovr-v58-card-2025-26/card-H2-m10
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H3 --capMargin 0  --out reports/ovr-v58-card-2025-26/card-H3-m0
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H3 --capMargin 10 --out reports/ovr-v58-card-2025-26/card-H3-m10
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H4 --phi 0.0 --out reports/ovr-v58-card-2025-26/card-H4-phi0.0
python reports/ovr-v58-card-2025-26/calibrate-wing.py --direction H4 --phi 0.5 --out reports/ovr-v58-card-2025-26/card-H4-phi0.5
node reports/ovr-v58-card-2025-26/evaluate.mjs
```

另會先跑一個 `sanity-G3-repro/`（`--direction G3 --gamma 1.0 --delta 0.25`，無任何 cap）確認
v58 管線與 v57 G3-δ0.25 逐列一致；此資料夾不是候選、不列入門檻矩陣。若不一致，先修管線再跑
候選，並在 report 說明。
