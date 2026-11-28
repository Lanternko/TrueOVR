# live/_retired

已淘汰。重現請 checkout 當時 commit。

本夾是 inseason 0.2.9a 以前各版（0.2.10i 的 build_usage_0210i.py、usage-2025-26-card0210i.json、build_prior_0210i.py、prior-2025-26-card0210i.json、rookie-prior-2026-0210i.json 於 2026-11-02 換 0.2.10j（加引力 gravity）時搬入，run_c4_live.GRAVITY=0 重現 0.2.10i 時讀這裡；0.2.10g／0.2.10h 的 build_usage_0210g.py、usage-2025-26-card0210g.json、build_prior_0210d.py、prior-2025-26-card0210d.json 於 2026-11-01 換 0.2.10i（切入／自主拆開）時搬入，run_c4_live.SPLIT_DC=0 重現 0.2.10h 時讀這裡的 usage／prior；0.2.9a 的 build_usage_029a.py、usage-2025-26-card029a.json 於 2026-11-01 換 0.2.10 時搬入；0.2.10d 的 build_usage_0210d.py、usage-2025-26-card0210d.json 於 2026-11-01 換 0.2.10e 時搬入；0.2.10e 的 build_usage_0210e.py、usage-2025-26-card0210e.json 於 2026-11-01 換 0.2.10f 時搬入；0.2.10f 的 build_usage_0210f.py、usage-2025-26-card0210f.json 於 2026-11-01 換 0.2.10g 時搬入，`run_c4_live.USAGE_WIN=0` 仍讀其中的 usage 檔）的建構腳本與凍結檔（build_prior_*、build_usage_*、prior-*.json、usage-*.json、pool-*.json）。
.py 檔頂端有 `raise SystemExit` 守門，不能直接執行；run_c4_live.py 也已不再讀這些檔。
現行版本與檔案清單見上一層 `CURRENT.json`；換版時把舊版檔案搬進本夾、更新 CURRENT.json（test/live_current_gate.py 會擋）。
