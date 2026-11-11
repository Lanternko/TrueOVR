# 薪水 vs 各評分的相關（2026-10-30）

只是探索分析，沒有預註冊、不進任何版本。數字都是 Spearman 排名相關。

## 資料
- 薪水：Basketball-Reference 合約頁（2021-22～2025-26 用 Wayback 存檔，2026-27 用現頁），URL 與 sha256 在 `sources.json`。原始 HTML 在 `source/`（本機，不進 git，約 19 MB）。
- 被裁球員：合約頁 `y1` 是該季所有球隊的總額（含舊隊死錢）；一人兩列時改取保障額較小那列的 `remain_gtd`（新隊），上限 `y1`。
- 簽約事件：bref 交易頁 `NBA_<年>_transactions.html`，排除 two-way／10-day／Exhibit／hardship；選秀當年簽的新秀約排除（draft 2021–2025）；延長合約若下一季薪水只比本季多 0–8.5%，視為還沒開始生效、排除。
- 真 EPM：dunksandthrees 付費牆後只有前 5 名，不用；改用自製 EPM 式（`impact-epm-2026-27/epm-live.csv` 的 careerO+careerD）。
- 薪水跨季比較時除以當季薪資上限。

## 1. 2025-26 全部合約（`corr.py` → `corr-output.txt`）
| 指標 | 全部 435 人 | ≥1000 分鐘 266 人 |
|---|---|---|
| 2K27 | 0.71 | 0.70 |
| card 0.2.7c OVR | 0.58 | 0.51 |
| 自製 EPM 式 | 0.47 | 0.45 |
| RAPM 多季 | 0.44 | 0.41 |
| RAPM 2025-26 | 0.26 | 0.19 |

## 2. 只看 2024-07～2026-06 簽的非新秀合約（`window.py` → `window-output.txt`）
141 人：2K26 0.87、2K27 0.77、OVR 0.63、自製 EPM 式 0.51、RAPM 多季 0.46、RAPM 2025-26 0.29。去掉 ≤$5M：OVR 0.67、2K26 0.84。

## 3. 歷年簽約前後一年（`proxy.py`、`hist.py` → `signings.csv`）
- 以前的賽季沒有 card OVR，所以用「替代 OVR」：拿 bref 進階數據（BPM、VORP、WS、使用率、分鐘等 25 欄）用 GBM 去學 2025-26 的 card 0.2.7c OVR，再套到 2020-21～2025-26。10 折樣本外和真 OVR：ρ 0.86（全部）、0.80（≥1000 分鐘），前 50 名重疊 31 人。2025-26 簽約那批人：真 OVR 對薪水 0.59、替代 OVR 0.60。
- 754 份合約，2021-22～2025-26 簽約季；四個指標都有的 397 人：

| 和簽約首年薪水（÷上限） | 全部 397 | 前一季 ≥1000 分鐘 264 | 薪水 >4% 上限 227 |
|---|---|---|---|
| 替代 OVR，簽約前一季 | 0.72 | 0.59 | 0.62 |
| 替代 OVR，合約首季 | 0.67 | 0.65 | 0.62 |
| 2K，簽約當年夏天之後推出的版本 | 0.79 | 0.75 | 0.82 |
| 2K，合約首季之後推出的版本 | 0.77 | 0.78 | 0.77 |

## 限制
- 替代 OVR 不是 card 0.2.7c；要確定得用真流程重建以前賽季（約 8 層實驗檔都只做了 2025-26）。
- 2K 歷年檔只收還在 2K27 的球員：倖存者偏誤。
- 774 筆簽約對不上薪水（2020-21 沒有薪水頁、季中底薪、名字寫法）。
- 2K 會參考名氣與合約，和薪水有一點互相影響。

## 重跑
```bash
python reports/salary-corr/corr.py reports/salary-corr/source
python reports/salary-corr/window.py reports/salary-corr/source
python reports/salary-corr/hist.py reports/salary-corr/source
```
