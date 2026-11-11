# E-214 官方傷病報告 PDF 備援（E-213 追加）

2026-11-02。spec：`spec-pdf-fallback.md`。

## 做了什麼
- `load_injuries()` 順序：ESPN → 官方 PDF → 沿用前一份（標 stale）。ESPN 成功時完全不碰 PDF，每日耗時不變。
- 新參數 `--injury-source auto|espn|pdf`（預設 auto；`pdf` 強制只走官方 PDF）。
- PDF 來源 `source='nba-official-pdf'`，另存 `pdfUrl`、`reportTime`（ET 時段）、`reportHeader`（PDF 表頭）、`notSubmitted`（NOT YET SUBMITTED 的隊）。items 格式與 ESPN 版一致，走同一個 `attach_ids()`；Probable／Available 不算缺陣，Out／Doubtful 才移出輪替。
- `teams.html` 已會顯示 `source`（大寫），只改了日期優先順序（ESPN 時間戳 → 報告時間 → 抓取時間）。頁面沒重發（下次每日更新自然帶上）。

## PDF 檔名格式（實際探測）
`https://ak-static.cms.nba.com/referee/injury/Injury-Report_<YYYY-MM-DD>_<HH_MM><AM|PM>.pdf`，美東時間、12 小時制、**每 15 分鐘一份**（04_15AM、04_00AM、03_45AM、03_30AM 皆回 200，約 96 KB）。沒出報告的時段回 404。從現在往回每 15 分鐘試一個，最多 36 小時；連續 3 次非 404 的連線錯誤就放棄（不會試滿 145 個）。Windows 沒有 tzdata，美東時間（含夏令）自己算。

## 解析
- 用 `pdftotext -raw`（本機 `shutil.which` 找不到時退到 `C:\Program Files\Git\mingw64\bin\pdftotext.exe`），子程序 `CREATE_NO_WINDOW`。沒有裝 pypdf 等套件，不需要新依賴。
- **偏離 spec：不用 `-layout`**。-layout 因儲存格垂直置中，狀態／原因會跟球員名錯開一行以上，隊名也漂到區塊中間；`-raw` 依內容串流輸出，隊名固定在該隊第一列、後面列沿用，折行的原因單獨成列接回上一位。
- 「Last, First」→「First Last」，處理 `Udeh, Jr., Ernest`、`Murphy III, Trey`、`de Larrea, Sergio`。跨頁沿用隊名。

## 實測：`--injury-source pdf`（04:15 ET 報告，與同時間抓的 ESPN 比）
| | 官方 PDF | ESPN |
|---|---|---|
| 條目數 | 83 | 95 |
| 缺陣（Out／Doubtful）| 61 | 75 |
| 對不上球員 | 11 | 8（15:43 那次） |
| 同名球員隊伍不一致 | 0 | — |

- 跑完整流程 118 秒，30 隊評分正常。
- **PDF 有 8 隊 NOT YET SUBMITTED**（IND、BKN、ORL、BOS、LAL、GSW、TOR、LAC），這 8 隊在 PDF 版沒有任何缺陣；ESPN 列了其中 28 位缺陣者（如 Curry、Haliburton、Banchero、Kawhi）。這是 PDF 備援最大限制：深夜／比賽日前報告尚未交齊時，備援會比 ESPN 少很多。Milwaukee 在這份 PDF 裡完全沒出現（也不在 NOT YET SUBMITTED 清單），ESPN 對 MIL 也沒有缺陣者，所以對結果沒有差。
- 有出報告的隊，缺陣人數 PDF 比 ESPN 多：ATL 6 vs 4、CLE 4 vs 1、HOU 3 vs 1、NOP 4 vs 2、POR 4 vs 2、UTA 5 vs 3、MIA 2 vs 0、PHX 2 vs 1，多半是 G League／Two-Way 的名單（ESPN 不列）。
- **Doubtful：PDF 7 人（ATL Gilbert、Wilson；CHI Claxton；NOP Dia、Pierre Jr.；MEM Pippen Jr.；DAL Aldama），ESPN（含簡評升級）只有 MEM Pippen Jr.**。PDF 的 Doubtful 直接帶狀態，不用從簡評猜。
- 反向：ESPN 把 Alvarado、Joe、Cardwell、Diallo 標 Out，官方是 Questionable（ESPN 較悲觀，或較新）。
- 對不上的 11 人（Sorber、Diop、Veesaar、Onyenso、Dia、Pierre Jr.、Simmons、Biberovic、Copeland、Quaintance、Donaldson）都是本季還沒上場的人；與 ESPN 那次的 8 人重疊 5 人，其餘是 PDF 才有的 Two-Way 球員。

## 測試
`test/team_ratings_gate.py` 新增 `OfficialPdf`（8 個）：真實報告文字 fixture 解析（83 筆、8 隊 NOT YET SUBMITTED、Caruso/Udeh Jr./Claxton/Hardaway Jr./Murphy III 的隊伍與狀態、跨頁沿用隊名、折行原因、三個 Williams 各歸各隊）、姓名轉換、美東時間與夏令交界、檔名時段、往回找與連線失敗放棄、ESPN 成功不抓 PDF、ESPN 失敗（含空回應）走 PDF 並走 attach_ids、強制 pdf 不碰 ESPN、兩者都失敗沿用前一份。`npm test` 全過。

## 注意
- 實測會覆寫 `data/season-source-2026-27/injuries.json`／`team-ratings.json`；已用實測前的 ESPN 版還原，下次每日更新會自然重算。
- PDF 版名單只在 ESPN 失敗時才會進網站；網站顯示 `NBA-OFFICIAL-PDF`，日期顯示報告時段（ET，無時區標示）。
