# E-162 報告：卡片目標進攻分量混入部分 PER

- 預註冊 `preregistration.md`（sha 5b3d6323…1025，commit 8147f57），照做無偏離。執行：子代理（role-card），lead 核對 c0 sha 與 results.json。
- 結論：**P15、P30 都不過，維持 card 0.2.9。**

## c0
四原點 K 和 card-0.2.9／E-158 Y0 ranking 逐位元相同（2025-26 sha 03288908…c334eae）。PER 對不到：各季 3/5/3/2 人（≤1%），保留 T6 原值。

## 判定（三季依人數加權；bootstrap 2000 次，seed 20261103，子群聯集 76 人）
| 條件 | 門檻 | P15 | P30 |
|---|---|---|---|
| (a) 子群 C 差 | ≥ +0.01 | −0.0034 ✗ | −0.0033 ✗ |
| (a) 90% 下界 | > −0.02 | −0.0150 ✓ | −0.0208 ✗ |
| (b) 全體 C 差 | ≥ −0.005 | +0.0014 ✓ | +0.0012 ✓ |
| (c) 薪水 | ≥ −0.02 | −0.0044 ✓ | −0.0115 ✓ |
| (c) 2K | ≥ −0.02 | +0.0037 ✓ | +0.0066 ✓ |
| (c) 下季 RAPM | ≥ −0.05 | +0.0007 ✓ | −0.0006 ✓ |
| (c) 下季 EPM | ≥ −0.05 | +0.0011 ✓ | +0.0004 ✓ |

子群（USG% ≥ P75、TS% 在 P25–P75）人數 41/271、46/303、54/346、64/379（2022-23～2025-26）。

## 2025-26 只報告
| 臂 | C 全體；子群 | 薪水 | 2K |
|---|---|---|---|
| K | 0.714；0.693 | 0.592；0.660 | 0.768；0.739 |
| P15 | 0.713；0.688 | 0.586；0.642 | 0.768；0.737 |
| P30 | 0.718；0.696 | 0.590；0.661 | 0.774；0.742 |

關鍵球員名次（K／P15／P30）：Flagg 75/78/77、Banchero 141/147/147、Knueppel 82/84/86、Edwards 9/9/9、Jalen Green 168/167/158、LaVine 189/197/197、DeRozan 84/82/85、Poole 358/357/355、SGA 1/1/1、Jokić 6/6/6、Wembanyama 2/2/2。Trae Young 卡 MIN 384 < 500 不列。

子群 K→P30 升最多：RJ Barrett 121→100、Jerami Grant 299→281、Brandon Williams 269→251、Mathurin 206→193、Sharpe 175→164。降最多：Hunter 205→216、Vukcevic 231→242、Brandon Miller 130→140、Sensabaugh 233→243、Portis 182→191。

G5 預查（K 前十 C／PF，K／P15／P30）：Wembanyama 2/2/2、Giannis 4/4/4、Jokić 6/6/6、Tatum 8/8/8、Barnes 12/12/11、Mobley 15/13/18、Holmgren 16/14/12、Jalen Williams 17/17/13、Jalen Johnson 21/20/21、Davis 22/22/22。

前 20 進出：P15 進 Jalen Johnson 出 Durant；P30 進 Austin Reaves 出 Durant。前 300 移動 ≥ 10 名：P15 19 人、P30 87 人。

## 解讀
目標裡混 30% PER，卡片排名幾乎不動（Flagg、Banchero 反而小降）。OVR 是能力值對目標的迴歸，目標改一點，係數的變化被能力值組成吸收；「高產量被低估」的落差不在目標本身。

## 子代理自選的讀法（lead 確認可接受）
- 分位數用 `np.percentile` 線性內插，在該季評估人群內算；USG%／TS% 缺值者（各季 2～4 人）不進子群。
- 子群 bootstrap 照 `eval_v2.boot` 改遮罩。前十長人＝ranking pos 為 C 或 PF 者按 K 名次取前 10。2025-26 無下季 RAPM／EPM，不報。
- `work/` 含 PER 原始欄位，不進 git（R-062、R-093）。

## npm test
52 passed, 0 failed。
