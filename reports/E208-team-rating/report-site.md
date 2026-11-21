# E-208 第二階段：傷病名單＋球隊評分＋網站球隊頁（2026-11-02）

頁面：https://lanternko.github.io/PureOVR/teams.html（gh-pages commit 1b74bd0；header 每頁都有「球隊評分」連結）

## 做了什麼
- `scripts/fetch_schedule.mjs`：NBA CDN 賽程（node fetch；curl/python 會 403）→ `data/season-source-2026-27/schedule.json`（1200 場例行賽，每隊 80 場；其餘 2 場盃賽淘汰賽未定，用平均勝率補）。
- `scripts/team_ratings_daily.py`：傷病（ESPN JSON → 官方 PDF 未實作，失敗沿用上次檔並標資料日期）→ `injuries.json`；(c) 最近 10 場實際分鐘，今日版拿掉 Out／Doubtful／Suspension 後重新正規化（前 10 人、240、上限 48）；與 E-208 同一個引擎（sim 0.1.4、200 seeds、對聯盟平均隊）→ `team-ratings.json`；預測勝場＝已有勝場＋剩餘賽程逐場 Φ((Δmargin±2.5)/12)。
- `scripts/build_teams_page.py` → `teams.html`（共用 header、可排序、點列展開今日輪替＋傷病名單、「今日陣容／近況」切換、手機版）。
- `scripts/daily_inseason_update.py`：新步驟 `step_team_ratings`（失敗只記警告，不擋原頁；沒有新比賽時也會更新 teams.html，因為傷病每天變；`--shell` 只用存好的 JSON 重畫頁面）。

## 今日（資料日期 2026-11-02T07:43:07Z，ESPN；今日陣容版）
- 前五：LAL +13.8（Out/Doubtful 2）、OKC +9.7（Out/Doubtful 5）、MEM +7.9（Out/Doubtful 1）、CLE +7.1（Out/Doubtful 1）、SAS +6.2（Out/Doubtful 1）
- 後五：IND -9.0（Out/Doubtful 5）、SAC -8.8（Out/Doubtful 3）、DAL -7.7（Out/Doubtful 3）、UTA -6.4（Out/Doubtful 3）、LAC -6.0（Out/Doubtful 5）
- 近況版前五：OKC +11.6（Out/Doubtful 5）、LAL +10.9（Out/Doubtful 2）、CLE +8.7（Out/Doubtful 1）、BOS +6.9（Out/Doubtful 2）、MEM +6.8（Out/Doubtful 1）；後五：IND -10.3（Out/Doubtful 5）、SAC -9.6（Out/Doubtful 3）、DAL -7.7（Out/Doubtful 3）、WAS -6.7（Out/Doubtful 3）、LAC -6.0（Out/Doubtful 5）
- MEM 今日輪替（分鐘）：Cameron Boozer 35.8、Jaylen Wells 31.3、Ty Jerome 28.4、Jerami Grant 28.2、Cedric Coward 27.0、Cam Spencer 22.2、GG Jackson 19.5、Zach Edey 19.4、Isaiah Stewart 17.6、Quinten Post 10.6；Scotty Pippen Jr. Doubtful 已拿掉，Quinten Post（questionable）仍在。
- 每日耗時：計算 104 秒（200 seeds×48 份名單、8 workers），加畫頁面約 110 秒，遠低於 5 分鐘上限。

## 偏離 spec
1. 官方 PDF 後備沒有實作：ESPN 失敗時沿用上次 injuries.json 並在頁面標「資料日期」與過期警告。
2. ESPN 的 status 只有 Out／Day-To-Day／Suspension；簡評寫 doubtful 的 Day-To-Day 升成 Doubtful。
3. 傷病名單有 8 人對不上球員（本季未上場的新秀／長期傷兵：Henri Veesaar、Tyler Bilodeau、Tarik Biberovic、Thomas Sorber、Izaiyah Nelson、Ben Simmons、Jayden Quaintance、Nate Bittle），他們不在輪替裡，所以不影響評分。
4. 31 位球員沒有引擎檔案，用聯盟平均檔案＋（live−card）差值（沿用 E-208 前瞻作法）。
5. 今日版的預測勝場假設傷兵整季缺陣，頁尾已註明；評分為模擬值，回測僅與上季淨效率打平，僅供參考。

## 驗證
`npm test` 全過（含新增 `test/team_ratings_gate.py` 11 項：分鐘總和 240、單人 ≤48、Out／Doubtful／Suspension 不在輪替、姓名對應、預測勝場、表頭連結、成品不變量）；`test/daily_inseason_update.py` 12 項全過（含球隊步驟失敗不擋原頁）。

## 截圖
- 桌機：`D:/Projects/CODING/basketball-autochess/reports/E208-team-rating/site-shots/teams-desktop.png`（2880×3000，MEM 展開）
- 手機：`D:/Projects/CODING/basketball-autochess/reports/E208-team-rating/site-shots/teams-mobile.png`（780×3400，390px 寬）
