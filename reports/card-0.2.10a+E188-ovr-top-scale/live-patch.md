# E-188 新賽季頁 patch（交 27 賽季 session，lead 未改 live/）

card 0.2.12 的 `frozen.json` 錨與 0.2.10a 相同（0.2.9a 凍結值），所以 PR90／PR95 直接沿用 card 0.2.10b：
`PR90 = 2.0559`、`PR95 = 2.4527`（0.2.9a capture 池 gRepl、MIN ≥ 500、qf 最近名次；`reports/card-0.2.10b/frozen.json`）。

## 要改的兩處（`reports/ovr-inseason-2026-27/live/run_c4_live.py`）

1. `e064_anchors()`（約 :771）回傳改帶 PR90／PR95：
   ```python
   return [a['PR1'], a['PR50'], a['PR99'], a.get('PR90'), a.get('PR95')], d['rRepl']
   ```
   錨點來源 usage 檔（`build_usage_*.py` 寫的 `anchors`）要多存 PR90／PR95；沒有時退回舊兩段式。

2. `e064_map(g, anc)`（約 :777）換成 E-188 映射（同 `reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py`）：
   ```python
   def e064_map(g, anc):
       p1, p50, p99 = anc[:3]
       if g <= p50:
           return 40 + 30 * (g - p1) / (p50 - p1)
       if g >= p99 or len(anc) < 5 or anc[3] is None:
           return 70 + 29 * (g - p50) / (p99 - p50)
       return float(np.interp(g, [p50, anc[3], anc[4], p99], [70.0, 88.0, 92.0, 99.0]))
   ```

`build_usage_0212.py:152` 的 `M.two_segment` 只拿來核對卡片 ovr，換成 `ovr_map` 後要對 `reports/card-0.2.10b/ranking.csv`。
ΔOVR 會跟著換尺（見 report.md「ΔOVR 斜率」）。版本號由該 session 決定（例如 inseason 0.2.12b），`CURRENT.json` 照 L-090 更新。
