# E-190 errata-1（已核可 2026-11-01，使用者「跑」）

- 日期：2026-11-01。原因：c0 第 2 部分不過，預註冊 §0／§1 對舊 creation 的來源、換算、窗口三處寫錯（`report.md`、L-105）；使用者裁定出手歸類（R-126）。預註冊本文不改，本檔取代下列段落。
- 已揭露：c0 全部數字（`results.json`）；`work/creation-recompute.csv` 的 creationJ 欄（舊版定義）lead 沒看與 drive 的相關、也不再使用。

## 改動（取代 §1）
逐球載入、助攻加權（失手用類別未助攻比例）照 `build_drive.py`。分類只看 descriptor 與 qualifier，一筆出手只進一類：
| 類 | 規則 | 去哪 |
|---|---|---|
| 補籃／空接／空切 | descriptor 含 tip、putback、alley-oop、cutting | 都不計（R-126 先忽略） |
| 切入 D | 兩分、descriptor 含 driving、非 2ndchance／fastbreak | drive_D |
| 自主 J | 其餘所有非助攻出手（三分、pullup、step back、hook、turnaround、fadeaway、floating、running、無 descriptor…，不限距離） | creationJ |

| 臂 | 內容 |
|---|---|
| KAU | 現行 0.2.10c（c0 已過，沿用） |
| **KP**（對照） | drive 不變（tail-U 現值）；creation＝逐球「全部非助攻出手」（舊定義的逐球版） |
| **KJ** | drive＝drive_D；creation＝creationJ |

- 換算與窗口：creation 兩臂都用 attach_creation 的單季池（2025-26，GP≥30、MPG≥20，`to_attribute`），四原點共用同一值（同 0.2.10c 做法，L-091）。drive_D 用和 tail-U drive 欄同一條管線（量 0.5＋效率 0.5、同收縮與窗口），只換候選出手篩選；先用該管線重算舊 drive 欄，差 <1e-6 才往下（不過就停下回報）。
- KP、KJ 都全部係數重擬合，旗標同 KAU。

## 判定（取代 §2 的 a2 與比較基準；門檻數字不變）
- a1：KJ 的 r(drive_D, creationJ) ≤ 0.70，且 VIF(drive_D) ≤ 3.0。另報 KP 的同兩值。
- a2：三歷史原點合併 Spearman(drive, 下季 RAPM 殘差) **KJ − KP** ≥ +0.05。
- b：npm test；C 與下季 RAPM ρ 用 **KJ − KAU**（門檻同原文）；h_R 在 KAU 上算，phase0 寫檔後才跑 KP／KJ。
- 只報告：KP − KAU（換資料來源本身的影響）、原文所列項目；15 人表加 KP 欄與 drive→drive_D 欄，再加 Gobert、Embiid、Sengun、Mitchell Robinson。
