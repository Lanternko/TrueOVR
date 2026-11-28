# E-069 預註冊補充 1：subType 對應到資料編碼

- 日期：2026-10-29。lead 裁定，主預註冊（sha256 fc6e375e…）不改。
- 觸發：role-card 依 §2.1 停下，回報 subType 次數表。此時只看過次數，沒有看過任何率、回測或屬性值。
- 性質：只把 §2.1 列出的名稱對應到 PBP 實際編碼，歸類本身不變。

## 對應

lead 抽查 2024-25 前 150 場，看了 description 與相鄰的 foul 動作。

1. **`out-of-bounds`**（subType）依 description 拆開：
   - 含 `bad pass out-of-bounds`：歸 passTov，對應 §2.1 的「out of bounds bad pass」。
   - 含 `lost ball out-of-bounds`：歸 ctlTov，對應「out of bounds lost ball」。
   - 含 `step out-of-bounds`：歸 ctlTov，對應「step out of bounds」。
   - 其他：歸「其他」。
   - 抽查次數：492／257／116，沒有第四種。
2. **`offensive foul`**（subType）照 §2.1「只算 charge」判定：
   - 同一 period、同一 clock、同一 personId 的 `actionType == 'foul'` 動作，若 `descriptor == 'charge'`，歸 ctlTov。
   - 其餘全歸「其他」，包括：descriptor 空白（多為推人或掩護犯規，資料分不出來）、`off-the-ball`、找不到相鄰 foul 的情況。
   - 抽查次數：charge 137、空白 330、off-the-ball 58、其他 30。
3. 每季都要報告兩類比例：「out-of-bounds 拆不出來」和「offensive foul 找不到相鄰 foul」。任一季超過該類 5% 時，在報告中標記。只標記，不停下。
4. 場數不足 1230（2020-21 是縮水季；2024-25、2025-26 少 1–3 場）照實寫進報告，不補抓。
