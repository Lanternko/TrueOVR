# E-198 進度（每步一行；接手從最後一行往下）
- c0（2026-11-02）：build_kg.py cards KAU（E185_TAIL_U=card-0.2.10i/tail-U.csv，E185_WORK=work/A）→ run_i.py KAU → finalize.py KAU；部件卡 sha 同 0.2.10i A-real（primary d6a50c35…），pre ranking 00585c3a…，work/KAU-final/out/ranking.csv sha 8b3e99d6… ＝ card-0.2.10i/ranking.csv 逐位元（過）。
- gravity_raw.py：gravity-raw.csv（582 人，234 有值／348 補值，OLS R² 0.725）、gravity-attr.csv（池 GP≥30&MPG≥20 252 人，PctMapper 兩端尾巴開）；work/gravity-impute.json。
- rapm_split.py：全季重算 c0 max|Δnet| 0（過）；work/rapm-2025-26-odd.json（86ba7115…，607 場）、-even.json（5165e371…，613 場），λ 皆 3000。
- phase0（KG 前）：e198_eval.py phase0 → phase0.md／phase0.json（sha a60055fffef6…）；379 人、S 組 29 人；h 0.0580、MDE_rank 8.26、MDE_value 0.2335；無假象 → A 主口徑名次殘差。
- KG：build_kg.py cards KG（部件卡 primary gravity +0.186±0.040 per36/10 點）→ run_i.py KG（pre 0c7a9e48…）→ finalize.py KG → work/KG-final/out/ranking.csv sha 4519d615…
- eval：e198_eval.py eval → results.json（sha d053efc2749c…）；A 不過（名次殘差縮小 −0.005 < 8.26）；沒弄壞 Δρ +0.003 ≥ −0.116 過；gravity +0.186±0.040 per36/10 點（≈ +1.6±0.35 OVR）。npm test 跑中。
- report.md 寫好（npm test 結果待補）。
- npm test exit 0（52 passed）；report.md 補上。完成。
