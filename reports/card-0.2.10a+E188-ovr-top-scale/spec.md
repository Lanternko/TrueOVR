# 派工任務：E-188 OVR 頂端錨點（用 role-card skill）

- cwd：`D:\Projects\CODING\basketball-autochess`
- 預註冊：`reports/card-0.2.10a+E188-ovr-top-scale/preregistration.md`（已凍結，sha256 見同目錄 `preregistration.sha256`；不准改，有錯寫 errata 回報）。
- 選定臂：S3（PR90→88、PR95→92；N＝19，a 區間 [17, 21]）。

## 要做
1. 寫 `ovr_map(g, anchors)`：照預註冊 §1（PR50 以上四節點分段直線，≥PR99 用舊斜率）。放在 `reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py`，`two_segment` 的呼叫端改走它。
2. 以 0.2.10a 為底產出 `reports/card-0.2.10b/`（frozen.json 加 PR90／PR95 錨，其餘照抄），ranking.csv 只有 ovr／ovr36 欄會變。
3. 賽中頁：**不准直接改 `reports/ovr-inseason-2026-27/live/`**（27 賽季 session 在做 0.2.12，有未 commit 的改動）。只產出 patch 檔 `live-patch.diff` 與說明，交 lead 轉給該 session。
4. 跑 §3 判定，寫 `report.md`。

## 不准
不改係數、能力值、用人層、池、分位數算法；不 commit、不 push、不部署。

## 回報
照 CLAUDE.md 六段（# 總評 …）；附 [90,99) 名單、直方圖、ΔOVR 前 30 人對照。

## 收工 memory
E-188 狀態、F-131 狀態；新發現寫 F；被抓到的錯寫 L。
