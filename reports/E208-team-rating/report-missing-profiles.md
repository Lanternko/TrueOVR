# E-216 球隊頁：上季缺陣球員補底卡

2026-11-02。spec：`spec-missing-profiles.md`。不改 src／引擎係數／正式卡片／凍結檔。

## 底卡選擇（寫死在 `team_ratings_daily.py` 的 `BASE_CARDS`，不看結果挑）
候選：repo 內有 12 項能力值＋OVR＋身高＋位置、且包含這些人的卡，只有 `reports/ovr-inseason-2026-27/v{3,4,5}/cards/<季>.csv` 系列（card 0.2.x 正式卡、live 排名、E-208 的 `players-attrs.json`／`pprime-day0-2425.json` 都沒有他們：卡片門檻要有本季分鐘，他們上季整季缺陣）。
規則：依賽季由近到遠，取「有這個人的最近一張」：2024-25 卡（v5 `-min` 主答案卡，README §R.7）→ 2023-24 卡（v5 `-min`）→ 都沒有就維持聯盟平均並留在 `missingProfiles`。v3/v4/v5 卡的能力值欄位相同（只有 OVR 不同），所以只放主答案卡。不做年齡衰退。
profile：聯盟平均 profile ＋（底卡能力值 − 該卡自己的分鐘加權聯盟平均）；位置、身高取自底卡。有 live 列的人「底卡 + (live − 底卡)」＝原本的 live 算法，所以沒變（今天補卡的 6 人都沒有 live 列）。新秀照舊。

## 補卡名單（今天 6 人，`missingProfiles` 33 → 27）
| 人 | 隊 | 來源 | OVR（該卡） |
|---|---|---|---|
| Kyrie Irving | DAL | 24-25 卡 | 90 |
| Damian Lillard | POR | 24-25 卡 | 86 |
| Tyrese Haliburton | IND | 24-25 卡 | 85 |
| Fred VanVleet | HOU | 24-25 卡 | 90 |
| Trey Lyles | MIN | 24-25 卡 | 64 |
| Georges Niang | GSW | 24-25 卡 | 60 |

仍是平均球員（任何歷史卡都沒有）：Mario Hezonja（CLE，17.9 分）、Graham Ike、Josh Dix、Alpha Diallo 等；其中 Hezonja 是有輪替分鐘的非新秀，要補得另找資料源。2026 新秀本來就有 live OVR，沒動。
OVR 提醒：v5 答案卡的 OVR 尺度和現行卡不同（Kyrie、VanVleet 同為 90.26，頂端有併值），只能當「上季水準」參考。

## Net 變動（同一份傷病／賽程快取、200 場、同種子；其餘 24 隊變動 < 0.04）
今日陣容版（主表）前 5：
| 隊 | Net 舊→新 | 預測勝場 舊→新 |
|---|---|---|
| POR | +4.1 → +1.4（−2.7） | 41.9 → 39.8 |
| DAL | −5.8 → −7.6（−1.8） | 28.9 → 25.5 |
| GSW | −6.0 → −4.5（+1.6） | 35.8 → 37.2 |
| HOU | +1.6 → +0.4（−1.2） | 46.9 → 44.3 |
| MIN | +3.0 → +3.9（+0.9） | 48.0 → 49.0 |

指定四隊（今日陣容版／近況版 Net；預測勝場）：
| 隊 | 今日 Net | 近況 Net | 今日 預測勝場 | 近況 預測勝場 |
|---|---|---|---|---|
| DAL | −5.8→−7.6 | −5.8→−7.6 | 28.9→25.5 | 28.8→25.3 |
| POR | +4.1→+1.4 | −1.2→−1.6 | 41.9→39.8 | 38.9→37.9 |
| IND | −6.9→−6.9（Haliburton 今日缺陣） | −7.8→−5.7 | 23.1→26.8 | 22.6→26.5 |
| HOU | +1.6→+0.4 | +1.6→+0.4 | 46.9→44.3 | 46.5→43.9 |
IND 今日 Net 沒變是因為 Haliburton 在缺陣名單；預測勝場上升是他回歸日之後的場次補進來。

**意外**：Kyrie、VanVleet 的卡 OVR 90，補進去後 DAL、HOU 反而下降，表示引擎看他們的能力組（Kyrie 籃板 −12、體格 −25、協防 −11；VanVleet 籃板 −23、體格 −28、短距 −15，皆相對 24-25 聯盟平均）比「平均球員」差。這是引擎對小個子高 OVR 後衛的長期偏向，不是補卡的 bug；留給 lead 判斷。

## POR 調查（只調查，不修）
工具：`por_probe.py`（每人換成聯盟平均球員、同分鐘，600 場；`probe-POR.json`）。數字是「他比平均球員多讓全隊每場贏幾分」（近況名單）：
Clingan +5.7、Robert Williams +4.6、Holiday +2.0、Camara +0.9、Krejčí +0.3、Lillard +0.1、Avdija −0.6、Henderson −1.1、Cissoko −1.1、**Morant −4.3**。
- 補卡後現象仍在：近況版（有 Morant）7.2 → 今日版（Morant、Sharpe 缺陣）8.5（對平均隊每場分差），拿掉 Morant 反而變好。Net 差從舊的 5.3 縮到 3.0（+1.4 對 −1.6）：補 Lillard 讓今日版下降，但沒消除。
- 原因不是 Lillard：Morant 自己的能力組（長 45、短 51、籃板 54、體格 41、協防 66，只有 drive 99／pass 99 好）在 27 分鐘下，防守端扣分大於進攻端加分，單人邊際 −4.3。
- 重疊只解釋一部分：Morant 的邊際值在沒有 Lillard 時 −3.0、沒有 Avdija 時 −2.1、沒有 Holiday 時 −3.8，沒有 Henderson 時 −5.3、沒有 Clingan 時 −5.0。也就是少一個同類控球／後場，他不那麼負，少一個大個子則更負；但就算少了這些人他仍然是負的，所以主因是引擎對「高 drive／pass、低防守／籃板」這類球員的整體估值。
- 交給 lead 的描述：POR「加人反而變差」仍成立，成因是引擎對 Morant 這類球員單人邊際為負（−2 到 −5），其次是控球後場重疊（約 1–2 分）；Lillard 同類（+0.1）。這和 `star-overlap/` 的球星重疊遞減不同層次，建議先查引擎防守端對這類球員的權重，再看重疊。

## 驗證
- `npm test` 通過（含新測試 `BaseCards` 3 項：最近底卡優先／舊卡／無卡；新秀、有 live 列、有引擎 profile 的人不用底卡；實跑 sim：有底卡的人用底卡、沒有的人退回平均）。
- 重算 154 秒（≤5 分鐘）；`team-ratings.json` 新增 `baseProfiles`，rotation 內補卡的人帶 `ovrSrc`。
- 截圖 `site-shots/teams-v4-dal.png`（展開 DAL，Kyrie OVR 90 附「24-25 卡」小標）。
