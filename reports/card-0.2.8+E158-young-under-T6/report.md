# E-158 報告：目標換 T6 後的年輕修正（預註冊 preregistration.md，未改動）

c0：K 臂（pipe 重跑）三個歷史原點與 E-153 K6、2025-26 與 card-0.2.8 ranking 逐位元相同（sha 見 results.json）。
解讀備註：Y1 的 rapm1 換成「各原點該季整季 T6 值」，同時套 A、B 兩半（poss 不動，T6 候選沒有的人被丟掉，約 40 人／半），沿用 errata-1 對 fitA／fitB 的做法。y·d·L 是設計矩陣最後一欄，可單獨刪除，停止條件未觸發。

## 判定（判定季 2022-23～2024-25，人數加權，對 K）
| 項目 | Y1 | Y0 |
|---|---|---|
| (a) 年輕子群 C 差（門檻 ≥ +0.01） | +0.090 | +0.106 |
| (a) 年輕 bootstrap 90% 下界（門檻 > −0.02） | +0.024 | +0.035 |
| (b) 全體 C 差（門檻 ≥ −0.005） | +0.029 | +0.001 |
| (c) 薪水／2K／RAPM／EPM 差 | +0.034／+0.026／+0.006／+0.023 | −0.005／+0.001／−0.003／+0.017 |
| 全過 | 是 | 是 |

兩個都過，年輕 C 差相差 0.016 ≥ 0.005 → 依預註冊取較大者 **Y0**。最終由使用者裁定。

## 只報告
- 2025-26（n=379，年輕 102）C：K 0.692／Y1 0.702／Y0 0.714；年輕 C：0.444／0.568／0.662；M_sal 全體 0.596／0.636／0.592；M_2k 全體 0.742／0.744／0.769。
- 前 300 名移動 ≥10 名：Y1 148 人、Y0 160 人。
- 前 20 名：Y0 進 Kevin Durant、出 Amen Thompson；Y1 進 Durant、LeBron James、Anthony Davis、Joel Embiid，出 Amen Thompson、Chet Holmgren、Michael Porter Jr.、Jalen Williams。
- y·d·L 係數：K −0.585（Y1 −0.194；Y0 無此欄）。折扣最大 5 人：Keyonte George、Kyshawn George、Bub Carrington、Ace Bailey、Alex Sarr。
- 關鍵球員與其餘變動：results.json（key_players、young_top30_*）。
