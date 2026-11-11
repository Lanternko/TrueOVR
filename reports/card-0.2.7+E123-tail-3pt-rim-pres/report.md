# 總評
**4/5 大致達成 有部分退步**

預註冊（sha256 bbaace39…2374）的判定關卡全部通過，T 和 H＋P 都可以交 G5。扣一分的原因：338 人的 OVR 小幅變動，Mobley 從第 22 名掉到第 29 名；T 和 PRES 的底端沒過 h1，維持在 40；a0T 第一次沒過，修了重現的 bug 才過（見「細節」的 lead 審查）。

**這次目標**
把 E-101 的四季合併池加開尾巴的做法，套到 3PT（threeValue，只顯示）、RIM（help）、PRES（pressure／presDisplay），讓剛好 99 的並列散開。

**進步了什麼**
- **3PT**：剛好 99 的從 4 人變 0 人。Curry 105.0、Murray 104.4、Knueppel 102.0、Isaiah Joe 100.4。threeValue 不進 OVR。
- **RIM**：剛好 99 的從 4 人變 0 人。Stewart 113.5、Holmgren 112.5、Wembanyama 108.7、Kalkbrenner 99.3。沒有人超過 120。照 R-072 只看護框實績，不含位置。
- **PRES**：卡片 pressure 剛好 99 的從 7 人變 0 人。Thybulle 127.0、Dru Smith 123.7、Ausar Thompson 112.1、Goodwin 108.3、Caruso 103.8、Paul Reed 103.4、Cason Wallace 102.7。網站的 presDisplay 剛好 99 的從 6 人變 0 人，Thybulle 129.3。
- 全卡沒有任何值超過 140。Wembanyama 維持第 2、Wagner 維持第 7（R-061），前十名的長人沒有變動。
- 準確度沒有變差：三個樣本外量尺的差都在 ±0.001 左右，evaluate 維持 18/19。

**退步了什麼**
- 338 人的 OVR 有小幅變動，最多 1.8 分。
  - Mobley 從第 22 名到第 29 名（85.1 → 84.2），Gobert 從第 46 名到第 50 名。原因是 help 頂端打開後重新擬合，RIM 頂尖那幾個人的分數拉開了。
  - Stewart 從第 177 名升到第 151 名，Dru Smith 從第 275 名升到第 258 名。
  - 前 20 名：Knueppel 第 21 名進榜（第 19 名），Anunoby 出榜。
- 3PT 和 PRES 的底端沒通過跨季穩定檢驗，維持在 40。RIM 底端雖然打開了，但沒有人低於 40（最低 49.4）。
- 卡片上 99 以上的值，模擬引擎還沒用到。引擎讀的是自己的 help 來源，所以這些人在模擬裡的強度不變。
- 有幾個人網站上會顯示 99，但其實是 98.9x 四捨五入上來的，不是被卡在頂端：Harkless 的 PRES，Konchar 和 Javonte Green 的 presDisplay。

**直觀證據**

| 球員 | 欄位 | card 0.2.7 | E-123 |
|---|---|---|---|
| Curry | 3PT | 99 | 105.0 |
| Knueppel | 3PT | 99 | 102.0 |
| Stewart | RIM | 99 | 113.5 |
| Wembanyama | RIM | 99 | 108.7 |
| Thybulle | PRES | 99 | 127.0 |
| Dru Smith | PRES | 99 | 123.7 |

| 欄位 | 剛好 99 | > 99 | > 120 | > 140 |
|---|---|---|---|---|
| 3PT | 4 → 0 | 4 | 0 | 0 |
| RIM | 4 → 0 | 4 | 0 | 0 |
| PRES（卡片） | 7 → 0 | 7 | 2（Thybulle、Dru Smith） | 0 |
| presDisplay（網站） | 6 → 0 | 6 | 2 | 0 |

| 球員 | 名次 | OVR |
|---|---|---|
| Wembanyama | 2 → 2 | 103.7 → 103.9 |
| Wagner | 7 → 7 | 97.2 → 97.6 |
| Mobley | 22 → 29 | 85.1 → 84.2 |
| Knueppel | 21 → 19 | 85.5 → 85.7 |
| Stewart | 177 → 151 | 71.1 → 72.9 |

**要你決定的事**
1. 3PT（threeValue 顯示值）要不要採用？這只改網站顯示，不影響 OVR。
2. RIM＋PRES 要不要採用？會動 OVR，建議先抽查 Mobley 從第 22 名到第 29 名、Knueppel 進前 20、Stewart 升到第 151 名。
3. a0T 修了 bug 才通過，這樣能不能接受？lead 建議接受，理由見「細節」。
4. 採用後，新賽季頁要另開 inseason 實驗才會跟上（R-050）。

---

## 細節

### 關卡
| 代號 | 結果 | 值 |
|---|---|---|
| f-eng | 過（第二分支） | 引擎軟上限 150，不截 99；活的 WinImp 鏈讀 `data/season-league.json` 自己的 help，不讀卡片 csv（D6） |
| a0T | 過 | 最大差 5e-7；第一次 0.31 沒過，用 D8 修正 |
| a0H | 過 | 0.0498（卡片四捨五入到 0.1） |
| a0P | 過 | force 差 0.0／0.0；pressure、presDisplay 0.0499 |
| a0P' | 過 | 欄名四季相同；2024-25 DEFL／CHG 逐列相同 |
| h1 T 頂／底 | 過／**沒過** | +0.730 [+0.362, +0.939]／+0.091 [−0.612, +0.645] |
| h1 H 頂／底 | 過／過 | +0.817 [+0.538, +1.070]／+0.647 [+0.407, +0.955] |
| h1 P 頂／底 | 過／**沒過** | +0.725 [+0.418, +0.924]／+0.202 [−0.150, +0.546] |
| c0 | 過 | 重建卡 sha256 aebcadf1…c6b6，和 card 0.2.7 逐位元相同 |
| c1 | 過 | `npm test` 57 過、0 敗 |
| m1／m2／m3 | 過 | −0.0003 [−0.0020, +0.0012]／+0.0005 [−0.0007, +0.0017]／−0.0002 [−0.0019, +0.0013] |
| c3 | 過 | 18/19（big14of16 和 card 0.2.7 一樣沒過） |
| c4 | 過 | > 140 共 0 個；threeValue 最大 105.0 |

只報告：e123h（只換 help）、e123p（只換 pressure）各自也全過，都是 18/19、c4 0。樣本內 ρ（R-007 不算證據）：ρ2K 0.7359 → 0.7362，ρRAPM 0.7793 → 0.7788，ρDef 0.5322 → 0.5316。

### 錨點
| 部分 | 池 n | r90 | r99 | (r99−r90)/1.044 ÷ SD |
|---|---|---|---|---|
| T | 1480 | 0.3707 | 0.6134 | 1.618 |
| help | 1480 | 0.0414 | 0.0937 | 1.569 |
| pressure | 958 | 0.9942 | 2.2497 | 1.614 |
| presDisplay | 958 | 1.0139 | 2.1317 | 1.499 |

「只壓縮」的保險都沒有生效（比值都 > 1）。

### 偏差 D1–D8（`deviations.json`）
- D1：help 用曲線型，x＝−收縮後的 rim 差，a99＝0.095（CURVE_DEF_RIM 的 99 點）。在看歷史季數值前決定，lead 轉達 R-072 後補記。
- D2→D3：P 池不加 MIN ≥ 500，用卡片現行的 GP ≥ 30 且 MPG ≥ 20（2025-26 是 252 人）。預註冊 §2.3 沒寫 MIN 門檻。
- D4→D7：T 池的 MIN 用 Base Totals 全季分鐘；修正了來源路徑。
- D5：2022-23 補抓成功，T 用四季，沒走三季的退路。
- D6：f-eng 走第二分支。
- D8：3PA＝0 的球員，acc 改用聯盟先驗（照 E-057 `new-long.json` 的實際行為）。

### lead 審查（2026-10-30）
- 自己重算核對成立：
  - 預註冊 sha256 沒有變；e123 卡片三欄剛好 99、> 99、> 140 的人數和子代理回報相同。
  - threeValue 前四名和 Sam Merrill 98.93、AJ Green 98.89 也相同。
  - Konchar、Javonte Green 的 presDisplay 未四捨五入前都是 98.974，不是被截在 99。
- **a0T 照字面不符預註冊 §3**：§3 寫「沒過就排除、不改規則重試」。第一次差 0.31 是重現程式漏了 E-057 的一個分支（3PA＝0 的人取聯盟先驗），不是改規則或改參數；修正發生在看任何歷史季數值之前，作用和 c0「停下修程式」一樣。lead 建議接受，但這是預註冊字面以外的處理，交使用者裁定。
- 子代理說 `find -newer` 逾時，沒查完資料夾外有沒有被寫入。`git status` 和開工時一致（`reports/` 被 gitignore，看不到本資料夾）。
- 本報告由 lead 依子代理的回報寫成，因為子代理的 Write 被工具擋下。

### 產出
`sources.json`、`h1-pairs.json`（sha256 8f3e25fa…d943，寫入時間早於 `h1-results.json`）、`h1-results.json`、`gates.json`、`deviations.json`、`tail-summary.json`、`three-value-e123.csv`、`e123/`、`e123h/`、`e123p/` 的 `ranking.csv`、`judge.json`、`evaluation.json`、`npm-test.log`、`cards/`、`work/`。
