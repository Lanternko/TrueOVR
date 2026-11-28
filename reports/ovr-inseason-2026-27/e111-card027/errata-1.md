# E-111 errata 1：RAPM 同分排序

狀態：已凍結（2026-10-30，使用者「1」）。sha256 存在 `errata-1.sha256`。補充 `preregistration.md`（f20f34a4…739e），其餘不變。

## 發生什麼
前置 (L1) 只有 Toumani Camara 不過（−0.180）。H1 封頂的名次用 RAPM pooledNet；Camara 與 Sam Hauser 同分 3.501。card 0.2.7 的產生器（`reports/card-0.2.6+E107-defense-UL/calibrate-wing.py` 的 `attach_external_ranks`）同分時照 rapm.csv 列序，賽中 `OVRPipeline` 照 playerId，名次相反（L-067）。

## 修改
- 027 模式下，賽中管線算 RAPM 名次（以及任何用來比卡片名次的排序）時，同分規則照卡片產生器：與 `attach_external_ranks` 相同的去重與 rapm.csv 列序。實作只在 027 分支覆寫，不改 `tools/` 共用程式，025 輸出逐位元不變。
- 回測（backtest_e111.py）的先驗卡、答案卡若也用到 RAPM 名次，同樣照產生器規則。

## 判定
- 前置 (c0)(c1)(u)(z)(L1)(s) 全部重跑，門檻不變。
- 前置全過才跑 (1)(2)，規則同 `preregistration.md`。
- 前置仍不過：停下回報，不再自行修。

## 已看過
只有 E-111 前置結果與 L1 診斷（`s-worker-027.json` 的 `L1diag`）；沒看過回測 (1)(2)。
