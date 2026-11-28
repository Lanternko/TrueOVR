# E-207 spec 修訂（2026-11-02，取代 spec.md 中衝突處）

E-204 W246 已 commit（4401062、826eeb9、7c588dc），正式版現為 card 0.2.12b／inseason 0.2.12b（窗口 246）。E-207 疊在其上：
- 版號：兩頁都 **0.2.12c**（card 0.2.12c／inseason 0.2.12c）。PATCH_NOTES 把字母版併進 0.2.12 格（R-064）。
- 建構基底：card-0.2.12b（W246，`live/win_len.py`）。KC（觸球分母）原本在 328 窗口建，**不能與 KC final 逐位元組比**；驗收改為：
  1. `TOV_TOUCH=0` 時卡片與賽中 ranking.csv 與 0.2.12b 逐位元組相同。
  2. 打開時：重擬合全部係數（R-115），池與 prior 依 W246 重算；TO 榜前 30 持球時間低於中位數人數、Reaves／KPJ／Brunson／Hauser 等 TO 與 OVR 名次與 E-206 KC 方向一致，附 0.2.12b→0.2.12c 表；前 100 名移動 ≥10 名人數。
- 其餘（fetch TOUCHES、tov_live 觸球分母、ATTR_TIPS／tov_rows／OD_OFF、新池檔、CURRENT.json、_retired、gh-pages 發布、curl 驗版號、npm test）照 spec.md。
- 先確認工作樹 live/、scripts/ 沒有別人未 commit 的改動（見 git status）；commit 只放自己的 hunks（暫時 GIT_INDEX_FILE＋commit-tree）。
