"""Review snapshot: personal accuracy, team accuracy, card OVR top 20 (2025-26).

  python reports/status/status_snapshot.py

Writes status.json (everything), personal.json, team.json, top20.json, v55fix.json, trend.json, team_card.json (dashboard datasets) and status.md
next to this file, and the same four datasets (+ kpi.json) into dashboard_payload/ for direct upload.
Re-run after any model, board or card change; it only reads existing outputs.
Holdout ρ: E2/F2/G3/H1 come from reports/ovr-v58-holdout-2025-26/holdout.json; every other layer (sim boards, legacy, v53, blend,
B12/C1/D1) and the rho2k column come from reports/ovr-metrics-backfill-2025-26/backfill.json (run backfill.py first). If a file
is missing the cell shows 「未量測」. Also writes trend.json and team_card.json (+ team_card_teams.json) next to the other datasets.
"""
import csv, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
PAYLOAD = OUT / 'dashboard_payload'
HOLDOUT = 'reports/ovr-v58-holdout-2025-26/holdout.json'
BACKFILL = 'reports/ovr-metrics-backfill-2025-26/backfill.json'
NA = '未量測'  # 缺值一律顯示這個，不留空白
CIRC = 'ρRAPM 樣本內（align/封頂用 RAPM）'
BLEND_NOTE = 'RAPM 混合目標（α=0.5）→ ρRAPM 部分樣本內'
TEAM_NOTE = '卡片版本（v55–v58）只改顯示用 OVR，不影響模擬 winsMAE；卡片的球隊指標另列於 team_card.json'
EVAL_POSS = 5000
LOW_MIN, RAPM_FAR, BIGS = 1000, 100, {'C', 'PF'}
LATEST_SIM = 'v54'  # latest sim board measured
OFFICIAL_CARD = 'reports/card-0.2.10g/ranking.csv'  # 2026-11-01 起正式卡片 = card 0.2.10g（0.2.10f 的用人層 L、a 改四季滑動窗口：E-192，使用者核准；前 20 名不變）；card 0.2.10f（0.2.10e 只換 3PT 欄對照池：E-191b P1m，ranking.csv 與 0.2.10e 逐位元組相同）；card 0.2.10e（0.2.10d 只換 OVR 映射：PR90→88、PR95→92，E-188 S3，R-124）；card 0.2.10d（0.2.10c 的 long、creation、threeValue、MPG 再改四季滑動窗口，E-185）；card 0.2.10c（0.2.10a 的修正後 T6 重擬合＋傳球全位置共用斜率，E-187 KAU，修 JW 偏高 F-125）；0.2.10a（0.2.10 只換 2025-26 T6：L-102 BPM 解析補回 Jokić／Wembanyama；0.2.10 = card 0.2.9a 係數全凍結，8 項屬性改 E-175 四季滑動窗口；R-111／R-114）。0.2.9a 以前見 reports/card-0.2.9a、card-0.2.9
C028_CARD = 'reports/card-0.2.8/ranking.csv'  # card 0.2.8（= card 0.2.7d 的 OVR 迴歸目標整個換成 T6；E-153 K6、R-102），2026-11-01 由 0.2.9 取代
C027D_CARD = 'reports/card-0.2.7d/ranking.csv'  # card 0.2.7d（= card 0.2.7c + E-147 連續 d），2026-10-30 起正式，2026-11-01 由 0.2.8 取代
C027C_CARD = 'reports/card-0.2.7c/ranking.csv'  # card 0.2.7c（= card 0.2.7b + E-131 OVR 迴歸拿掉 physique；R-084），由 0.2.7d 取代
C027C_EVAL = 'reports/card-0.2.7b+E131-no-physique/evaluation.json'  # E-131 evaluation：候選 K1 對 2K27 每場 ρ
C027B_CARD = 'reports/card-0.2.7b/ranking.csv'  # card 0.2.7b（= card 0.2.7a + E-123 3PT／RIM／PRES 頂端開尾；R-072、R-078），2026-10-30 由 0.2.7c 取代
C027B_EVAL = 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/evaluation.json'  # E-123 疊在 0.2.7a 上的 evaluation：候選 e123a 對 2K27 每場 ρ
C027A_CARD = 'reports/card-0.2.7a/ranking.csv'  # card 0.2.7a（= card 0.2.7 + E-125 pass 量率各半；R-074、R-077），2026-10-30 由 0.2.7b 取代
C027A_EVAL = 'reports/card-0.2.7+E125-pass-volume/evaluation.json'  # E-125 evaluation：候選 E125-P50 對 2K27 每場 ρ
C027_CARD = 'reports/card-0.2.7/ranking.csv'  # card 0.2.7（= card 0.2.6 + E-107 防守 UL：加成不打折、D 逐場線性遞減；R-061、R-065），2026-10-30 由 0.2.7a 取代
C027_EVAL = 'reports/card-0.2.6+E107-defense-UL/evaluation.json'  # E-107 evaluation：候選 E107-UL6 對 2K27 每場 ρ
C026_CARD = 'reports/card-0.2.6/ranking.csv'  # card 0.2.6（= card 0.2.5 + E-101 補籃改歸近距離、四季合併錨點、頂端只壓縮；R-055、R-056），2026-10-30 由 0.2.7 取代
C026_EVAL = 'reports/card-0.2.5+E101-crossera/evaluation.json'  # E-101 evaluation：候選 E101 對 2K27 每場 ρ
C025_CARD = 'reports/card-0.2.5/ranking.csv'  # card 0.2.5（= card 0.2.4 + E-089 分鐘權重改飽和 W(m)；R-047、R-048），2026-10-30 由 0.2.6 取代
C025_EVAL = 'reports/card-0.2.4+E089-minutes-saturation/evaluation.json'  # E-089 evaluation：候選 E089 對 2K27 每場 ρ
C024_CARD = 'reports/card-0.2.4/ranking.csv'  # card 0.2.4（= card 0.2.3 + E-084 用人回歸目標改單季 RAPM；R-042、R-044），2026-10-29 由 0.2.5 取代
C023_CARD = 'reports/card-0.2.3/ranking.csv'  # card 0.2.3（= card 0.2.2 + E-075 用人當能力證據；R-040），2026-10-29 由 0.2.4 取代
C024_EVAL = 'reports/card-0.2.3+E084-current-target/evaluation.json'  # E-084 evaluation：候選 E084 對 2K27 每場 ρ
C022_CARD = 'reports/card-0.2.2/ranking.csv'  # card 0.2.2（= card 0.2.0 + E-070 foulDraw 以量為主 + E-071 P1 pressure 改逼失誤；R-034、R-037、R-039），2026-10-29 由 0.2.3 取代
C023_EVAL = 'reports/card-0.2.2+E073-usage-evidence/evaluation.json'  # E-075 evaluation：候選 E075 對 2K27 每場 ρ
C021_CARD = 'reports/card-0.2.1/ranking.csv'  # 已發佈的 card 0.2.1：標成 E-070，實際內容是 card 0.2.0 + E-071 P1（L-040、R-037 勘誤）
C022_GATES = 'reports/card-0.2.2/gates.json'  # card 0.2.2 合併關卡：c2 對 card 0.2.0 Δρ、2K27 ρ
C020_CARD = 'reports/card-0.2.0/ranking.csv'  # card 0.2.0（= 0.1.2 能力值，OVR 改每場含上場時間、相對替補水準；R-028／E-064 副版），2026-10-29 正式卡片
E070_VERDICT = 'reports/card-0.2.0+E070-foul-volume/verdict.json'  # E-070 結果：對 2K27 ρ、A/B 半 RAPM 每場 Δρ
C012_CARD = 'reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv'  # card 0.1.2（= 0.1.1 + E-060 onBall；每 36 分鐘 OVR），2026-10-28 ~ 10-29 正式卡片
E064_VERDICT = 'reports/card-0.1.2+E064-pergame/verdict.json'  # E-064 結果：副版（repl）對 2K27 ρ、A/B 半樣本外 ρ
C011_CARD = 'reports/ovr-v61-shrink-history-2025-26/ranking.csv'  # card 0.1.1（E-054+E-055），未曾正式發版
V58_CARD = 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv'  # 2026-10-21 ~ 10-28 正式卡片 = v58 H1-m0
THREE_VALUE = 'reports/card-0.2.8/three-value.csv' if (ROOT / 'reports/card-0.2.8/three-value.csv').exists() else 'reports/card-0.2.7c/three-value.csv'  # E-057 threeValue＋E-123 頂端開尾（R-024：3PT 顯示欄；OVR 與模擬仍用 long）
CARD_EVAL = 'reports/card-0.1.1+E060-onball-targeting/evaluation.json'  # 0.1.1（label v61-shrink）與 0.1.2（label E060）的對 2K27 ρ
E2_CARD = 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv'  # 2026-10-20 ~ 10-21 正式卡片
V53_CARD = 'reports/ovr-calibrated-2025-26/ranking.csv'
F2_CARD = 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv'  # v56
G3_CARD = 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv'  # v57
V55_CARDS = {'B12': 'reports/ovr-v55-finisher-fix-2025-26/card/B12/ranking.csv',
             'C1': 'reports/ovr-v55-card-origin-attr-2025-26/card-C1/ranking.csv',
             'D1': 'reports/ovr-v55-attr-deflate-2025-26/card/D1/ranking.csv',
             'E2': 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
             'v58': V58_CARD}
V55_DESC = {'B12': '方向 B：吃餅長人禁區出手來源修正（模擬層）後重校卡片',
            'C1': '方向 1：自創禁區比例 s̃ 映成第 16 屬性 originShare 加進卡片回歸',
            'D1': '方向 2：屬性建構層 long 去膨脹（--attr-deflate）後重校卡片',
            'E2': '方向 E2：吃餅折扣 λ=0.4（禁區出手按非自創比例打折，PF/C 自創 ≥65 吸引包夾者豁免）'}
# 驗收：下修類看方向；不誤傷類只要卡片名次不低於 2K27 或 RAPM 其中一個的名次（兩者擇一准即可）
V55_CHECKS = [('Karlo Matković', '下修 ≥ 10 名', lambda a, b, ref: b - a >= 10),
              ('John Collins', '下修', lambda a, b, ref: b > a),
              ('Isaiah Stewart', '下修', lambda a, b, ref: b > a),
              ('Luka Garza', '下修', lambda a, b, ref: b > a),
              ('Neemias Queta', '名次 ≤ 2K27 或 RAPM 名次', lambda a, b, ref: b <= ref),
              ('Rudy Gobert', '名次 ≤ 2K27 或 RAPM 名次', lambda a, b, ref: b <= ref),
              ('Jalen Smith', '名次 ≤ 2K27 或 RAPM 名次', lambda a, b, ref: b <= ref)]


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def rows(path):
    return list(csv.DictReader(open(ROOT / path, encoding='utf-8-sig')))


def load_holdout():
    try:
        return json.loads((ROOT / HOLDOUT).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def load_backfill():
    try:
        return json.loads((ROOT / BACKFILL).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def holdout_cell(holdout, key):
    """樣本外 ρ（淨值 / 防守）顯示文字；E2/F2/G3/H1 沿用 holdout.json；讀不到 = 未量測。"""
    try:
        a = holdout['cards'][key]['holdout_scale0.5']['avg']
        return f"{a['net']:.3f} / {a['def']:.3f}"
    except (KeyError, TypeError):
        return NA


def backfill_layer(backfill, key):
    return backfill.get('layers', {}).get(key)


def card_eval_2k(label):
    """card 0.1.1 / 0.1.2 的對 2K27 ρ（evaluation.json 候選表，label v61-shrink / E060）；讀不到 = None。"""
    try:
        d = json.loads((ROOT / CARD_EVAL).read_text(encoding='utf-8'))
        return next(c['rho2k'] for c in d['candidates'] if c['label'] == label)
    except (OSError, ValueError, StopIteration, KeyError):
        return None


def e064_rho(path):
    """E-064 副版（repl）的對 2K27 ρ（full，n=575）與 A/B 半 RAPM 樣本外 ρ（新目標＝每場淨值；與其他卡片的 ρ 目標不同，只供參考）；讀不到 = None。"""
    try:
        d = json.loads((ROOT / E064_VERDICT).read_text(encoding='utf-8'))
        return d['rho2k']['full']['repl'], d['rho']['avg']['newTarget_perGame']['repl']
    except (OSError, ValueError, KeyError):
        return None, None


def e070_rho():
    """E-070（card 0.2.1）對 2K27 ρ（每場）與 A/B 半 RAPM 每場 ρ 差（對 card 0.2.0）；讀不到 = None。"""
    try:
        d = json.loads((ROOT / E070_VERDICT).read_text(encoding='utf-8'))
        return d['reportOnly']['rho2k']['E070']['perGame'], d['c2']['delta'], d['c2']['ci90']
    except (OSError, ValueError, KeyError):
        return None, None, None


def c022_rho():
    """card 0.2.2 對 2K27 ρ（每場）、A/B 半 RAPM 每場 ρ 差（對 card 0.2.0），以及 E-071 P1（＝已發佈 0.2.1 內容）的 2K27 ρ；讀不到 = None。"""
    try:
        d = json.loads((ROOT / C022_GATES).read_text(encoding='utf-8'))
        return d['rho2k']['M']['perGame_repl'], d['c2']['delta'], d['c2']['ci90'], d['rho2k']['E071P1']['perGame_repl']
    except (OSError, ValueError, KeyError):
        return None, None, None, None


def eval_2k(path, label):
    """evaluate.mjs 輸出中某候選對 2K27 ρ（每場，同人群）；讀不到 = None。"""
    try:
        d = json.loads((ROOT / path).read_text(encoding='utf-8'))
        return next(c['rho2k'] for c in d['candidates'] if c['label'] == label)
    except (OSError, ValueError, KeyError, StopIteration):
        return None


def personal(rapm_by_id, rapm_by_name, holdout, backfill):
    out = []

    def add(layer, desc, scores, note='', src='', hold=None, bk=None, k2=None):
        b = backfill_layer(backfill, bk or hold)
        keep = [(s, r) for s, r in scores if r and float(r['pooledPoss']) >= EVAL_POSS]
        s = [k[0] for k in keep]
        out.append({'layer': layer, 'description': desc, 'players': len(keep),
                    'rhoNet': round(spearman(s, [float(r['pooledNet']) for _, r in keep]), 3),
                    'rhoDefense': round(spearman(s, [float(r['pooledD']) for _, r in keep]), 3),
                    'holdoutRho': holdout_cell(holdout, hold) if hold and holdout_cell(holdout, hold) != NA else (b['holdoutRho'] if b else NA),
                    'rho2k': round(k2, 3) if k2 is not None else (round(b['rho2k'], 3) if b else NA),
                    'note': note or f'無額外備註；來源 {src}，對全量 RAPM 計算'})
    sim = rows('reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv')
    src = 'reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv'
    add('模擬板 v53（原始）', '8 種子期望分差，位置置中每 36 分鐘', [(float(r['rawPer36']), rapm_by_id.get(r['playerId'])) for r in sim],
        '不讀 RAPM，樣本內即樣本外：同一份分數直接對 A 半、B 半 RAPM 各算一次 ρ 再平均（reports/ovr-metrics-backfill-2025-26）', src=src, bk='sim_v53_raw')
    add('模擬板 v53（收縮修正版）', '先發不收縮、替補收縮（已採用）', [(float(r['v2Per36']), rapm_by_id.get(r['playerId'])) for r in sim],
        '不讀 RAPM，樣本內即樣本外：同一份分數直接對 A 半、B 半 RAPM 各算一次 ρ 再平均（reports/ovr-metrics-backfill-2025-26）', src=src, bk='sim_v53_v2')
    sim = rows('reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv')
    src = 'reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv'
    add('模擬板 v54（原始）', '三分／禁區命中率改用可靠度加權收縮', [(float(r['rawPer36']), rapm_by_id.get(r['playerId'])) for r in sim],
        '不讀 RAPM，樣本內即樣本外：同一份分數直接對 A 半、B 半 RAPM 各算一次 ρ 再平均（reports/ovr-metrics-backfill-2025-26）', src=src, bk='sim_v54_raw')
    add('模擬板 v54（收縮修正版）', '同 v53 收縮規則', [(float(r['v2Per36']), rapm_by_id.get(r['playerId'])) for r in sim],
        '已收束；球隊層 2025-26 勝場 MAE 變差，未切換對局資料，卡片板仍為 v53 校準；不讀 RAPM，樣本內即樣本外：同一份分數直接對 A 半、B 半 RAPM 各算一次 ρ 再平均（reports/ovr-metrics-backfill-2025-26）', src=src, bk='sim_v54_v2')
    e064_2k, e064_out = e064_rho(E064_VERDICT)
    c022_2k, c022_d, c022_ci, e071_2k = c022_rho()
    c023_k = eval_2k(C023_EVAL, 'E075')
    c024_k = eval_2k(C024_EVAL, 'E084')
    add('卡片 OVR（正式卡片板，card 0.2.10g）', '0.2.10g：用人層（L 上場強度、a 出賽率）改四季滑動窗口（E-192；前 20 名不變）；0.2.10f：3PT 欄對照池改近三季窗口值＋本季（E-191b P1m；OVR 與名次同 0.2.10e）；0.2.10e：OVR 映射頂端加 PR90→88、PR95→92 兩錨（名次不變，E-188）；0.2.10d：long／creation／threeValue／MPG 四季窗口；0.2.10c：傳球共用斜率；0.2.10a：2025-26 T6 補回 L-102 BPM 解析漏掉的聯盟第一（Jokić 7→3 名）；其餘同 0.2.10：card 0.2.9a 係數與錨全凍結，8 項屬性（drive、foulDraw、ft、mid、pass、rebound、short、tovSkill）改 E-175 四季滑動窗口（R-111／R-114，2026-11-01）；0.2.9 起拿掉年輕×爛隊×時間（y·d·L）折扣（E-158 Y0，R-104）（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(OFFICIAL_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.10g = 0.2.10f + 用人層 L、a 四季窗口（E-192，係數同 0.2.10d，r_repl、錨點重取）；card 0.2.10f = 0.2.10e + 3PT 欄新對照池（E-191b P1m，OVR 不變）；card 0.2.10e = 0.2.10d + OVR 頂端加 PR90／PR95 錨（E-188 S3，名次不變）；card 0.2.10d = 0.2.10c + long／creation／threeValue／MPG 四季窗口（E-185）；card 0.2.10c = E-175 滑動窗口屬性 + 修正後 T6（L-102）重擬合 + 傳球共用斜率（E-187）；0.2.9 的 E-158 預註冊判定通過（年輕子群 C +0.106、下界 +0.035；全體 +0.001）；此列 ρ vs RAPM 照舊用 RAPM 算；對 2K27 ρ 尚無 0.2.10 的 evaluation.json，不填；來源 card-0.2.10g（0.2.10f 的 ranking.csv 同 card-0.2.10e）', src=OFFICIAL_CARD, k2=None)
    add('卡片 OVRcard 0.2.8（前正式版）', 'card 0.2.7d 的 OVR 迴歸目標整個換成 T6（DARKO 與 BPM 攻守季內 z 平均）；2025-26 原點 alpha=1，usage 層 rapm1 不換（E-153 K6，2026-11-01 使用者裁定 R-102；同日由 card 0.2.9 取代）（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C028_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.8 = card 0.2.7d + 目標換 T6；E-153 預註冊四項檢查全過（bootstrap 90% 下界 +0.0033，邊際小）；npm test 52 過；此列 ρ vs RAPM 照舊用 RAPM 算（目標已不是 RAPM，樣本內意義不同）；對 2K27 ρ 尚無 0.2.8 的 evaluation.json，不填；來源 card-0.2.8', src=C028_CARD, k2=None)
    add('卡片 OVR card 0.2.7d（前正式版）', 'card 0.2.7c + E-147：usage 層 d 改連續 d＝clip((0.40−s)/0.10,0,1)；2026-10-30 起正式，2026-11-01 由 card 0.2.8 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C027D_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.7d = card 0.2.7c + E-147；對 2K27 ρ 未接 evaluation.json；來源 card-0.2.7d', src=C027D_CARD, k2=None)
    add('卡片 OVR（前正式版，card 0.2.7c）', 'card 0.2.7b + E-131：OVR 迴歸拿掉 physique（身高＋體重），身高 heightInches 保留，能力值不動（2026-10-30 使用者裁定 R-084）（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(OFFICIAL_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.7c = card 0.2.7b + E-131；對 card 0.2.7b 的 Δρ_{{N_W}} +0.0015 [-0.0014, +0.0044]、Δρ_{{Q_W}} -0.0014 [-0.0040, +0.0011]、線性量尺 +0.0013 [-0.0016, +0.0042]（預註冊 E-131，看過係數才選，不算盲測，只證明不變差；前 300 名 36 人移動 ≥ 10 名，使用者裁定字母小版本）；evaluate 18/19；對 2K27 ρ 取 card-0.2.7b+E131-no-physique/evaluation.json 的 K1 每場值；2026-10-30 起正式，由 card 0.2.7d 取代；來源 card-0.2.7c', src=C027C_CARD, k2=eval_2k(C027C_EVAL, 'K1'))
    add('卡片 OVR card 0.2.7b（前正式版）', 'card 0.2.7a + E-123：threeValue、help（只看護框實績，不看位置）、pressure／presDisplay 照 E-101 四季池開 99 以上的頂端，底端 h1 沒過的維持 40（2026-10-30 使用者裁定 R-072、R-078）；2026-10-30 由 card 0.2.7c 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C027B_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.7b = card 0.2.7a + E-123；對 card 0.2.7a 的 Δρ_{{N_W}} -0.0008 [-0.0025, +0.0007]、Δρ_{{Q_W}} +0.0001 [-0.0011, +0.0012]、線性量尺 -0.0007 [-0.0024, +0.0008]（預註冊 E-123，只證明不變差，字母小版本）；evaluate 18/19；對 2K27 ρ 取 card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/evaluation.json 的 e123a 每場值；來源 card-0.2.7b', src=C027B_CARD, k2=eval_2k(C027B_EVAL, 'e123a'))
    add('卡片 OVR card 0.2.7a（前正式版）', 'card 0.2.7 + E-125：傳球 pass 改成量率各半 0.5·z(AST/36)＋0.5·z(AST%)，四季池與錨點照 E-101 重算（2026-10-30 使用者裁定 R-074、R-077）；2026-10-30 由 card 0.2.7b 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C027A_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.7a = card 0.2.7 + E-125；對 card 0.2.7 的 Δρ_{{N_W}} +0.0004 [-0.0004, +0.0013]、Δρ_{{Q_W}} +0.0007 [-0.0002, +0.0017]、線性量尺 +0.0004 [-0.0005, +0.0013]（看過 Giannis 才選，不算盲測，只證明不變差，字母小版本）；evaluate 18/19；對 2K27 ρ 取 card-0.2.7+E125-pass-volume/evaluation.json 的 E125-P50 每場值；來源 card-0.2.7a', src=C027A_CARD, k2=eval_2k(C027A_EVAL, 'E125-P50'))
    add('卡片 OVR card 0.2.7（前正式版）', 'card 0.2.6 + E-107 防守 UL：防守加成不打折 max(0, centeredD)，防守 D 改用逐場線性遞減、回合門檻 × 1/2（2026-10-30 使用者裁定 R-061、R-065）；2026-10-30 由 card 0.2.7a 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C027_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.7 = card 0.2.6 + E-107；對 card 0.2.6 的 Δρ_{{N_W}} +0.0059 [+0.0009, +0.0111]、Δρ_{{Q_W}} +0.0016 [-0.0026, +0.0059]、線性量尺 +0.0063 [+0.0011, +0.0116]（看過 E-106 才選，不算盲測，PATCH）；evaluate 18/19；對 2K27 ρ 取 card-0.2.6+E107-defense-UL/evaluation.json 的 E107-UL6 每場值；來源 card-0.2.7', src=C027_CARD, k2=eval_2k(C027_EVAL, 'E107-UL6'))
    add('卡片 OVR card 0.2.6（前正式版）', 'card 0.2.5 + E-101：PBP 補籃、補扣改歸近距離，能力值百分位與 99 錨點改對 2022-23～2025-26 四季合併池，頂端差距尺只壓縮不放大（2026-10-30 使用者裁定 R-055、R-056，G5 通過）；2026-10-30 由 card 0.2.7 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C026_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.6 = card 0.2.5 + E-101；對 card 0.2.5 的樣本外 Δρ_N -0.0027 [-0.0069, +0.0015]、Δρ_Q -0.0032 [-0.0067, +0.0004]（只證明不變差，PATCH）；對 2K27 ρ 取 card-0.2.5+E101-crossera/evaluation.json 的 E101 每場值；來源 card-0.2.6', src=C026_CARD, k2=eval_2k(C026_EVAL, 'E101'))
    add('卡片 OVR card 0.2.5（前正式版）', 'card 0.2.4 + E-089：卡片 g 的分鐘權重由 mpg/36 改成飽和 W(m)=(1−e^(−m/15))/(1−e^(−36/15))，上場少但效率高的人不再被埋沒（2026-10-29 使用者裁定 R-047、R-048）；2026-10-30 由 card 0.2.6 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C025_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.5 = card 0.2.4 + E-089；對 card 0.2.4 的 Δρ_{{N_W}} +0.0096 [+0.0020, +0.0176]、線性量尺 +0.0087 [+0.0011, +0.0168]、四季量尺 +0.0066 [-0.0005, +0.0141]（樣本外只證明不變差）；對 2K27 ρ 取 card-0.2.4+E089-minutes-saturation/evaluation.json 的 E089 每場值；來源 card-0.2.5', src=C025_CARD, k2=eval_2k(C025_EVAL, 'E089'))
    add('卡片 OVR card 0.2.4（前正式版）', 'card 0.2.3 + E-084：用人回歸的訓練目標由四季合併 RAPM 改成 2025-26 單季 RAPM，修正年輕被低估、老將被高估（2026-10-29 使用者裁定 R-042、R-044）；2026-10-29 由 card 0.2.5 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C024_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.4 = card 0.2.3 + E-084；當季量尺（另一半 2025-26 單季 RAPM × MPG）ρ 對 card 0.2.3 差 +0.025 [+0.009, +0.039]；四季量尺差 -0.017 [-0.030, -0.004]；年齡偏差 S -0.202 → -0.075；對 2K27 ρ 取 card-0.2.3+E084-current-target/evaluation.json 的 E084 每場值；來源 card-0.2.4', src=C024_CARD, k2=c024_k)
    add('卡片 OVR card 0.2.3（前正式版）', 'card 0.2.2 + E-075：教練用人當能力證據（分鐘、出賽率、年齡、練兵隊；DNP 與輪休分開）進入 OVR 的能力估計（2026-10-29 使用者裁定 R-040）；2026-10-29 由 card 0.2.4 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C023_CARD)],
        f'{CIRC}；每場 OVR；card 0.2.3 = card 0.2.2 + E-075；A/B 半 RAPM 每場 ρ 對 card 0.2.2 差 -0.0005 [-0.0186, +0.0159]（不變差，不是變準）；c4 只報告（+0.0160 [-0.0002, +0.0321]）；對 2K27 ρ 取 card-0.2.2+E073-usage-evidence/evaluation.json 的 E075 每場值；來源 card-0.2.3', src=C023_CARD, k2=c023_k)
    add('卡片 OVR card 0.2.2（前正式版）', 'card 0.2.0 + E-070：foulDraw 改為池內百分位(0.75·z(FTA/36)+0.25·z(FTA/FGA)) + E-071 P1：pressure 改為事件式逼失誤 force（抄截、干擾傳球、對位失誤、製造進攻犯規）（2026-10-29 使用者裁定 R-034、R-037、R-039）；2026-10-29 由 card 0.2.3 取代（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C022_CARD)],
        f'{CIRC}；每場 OVR；A/B 半 RAPM 每場 ρ 對 card 0.2.0 差 '
        + (f'{c022_d:+.4f} [{c022_ci[0]:+.4f}, {c022_ci[1]:+.4f}]' if c022_d is not None else NA)
        + '；對 2K27 ρ 取 card-0.2.2/gates.json 每場值；來源 card-0.2.2', src=C022_CARD, k2=c022_2k)
    add('卡片 OVR card 0.2.1（前正式版，實際內容為 E-071 P1）', '標成 card 0.2.0 + E-070，但發佈的檔案其實是 card 0.2.0 + E-071 P1（pressure 改逼失誤，沒有 E-070）；2026-10-29 由 card 0.2.2 取代（L-040）（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C021_CARD)],
        f'{CIRC}；每場 OVR；對 2K27 ρ 取 card-0.2.2/gates.json 的 E071P1 每場值；來源 card-0.2.1', src=C021_CARD, k2=e071_2k)
    add('卡片 OVR card 0.2.0（前正式版）', 'card 0.1.2 的能力值不變，OVR 改為每場（含上場時間：g=(預測−替補水準)·MPG/36，替補水準＝PR10），兩段映射錨點取 MIN≥500 池 PR1/PR50/PR99（2026-10-29 使用者裁定 R-028，E-064 副版）（遊戲本體不讀取任何 OVR）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C020_CARD)],
        f'2026-10-29 由 card 0.2.1 取代（實際只換 pressure），再由 card 0.2.2 取代；{CIRC}；每場 OVR 含上場時間，與每 36 分鐘版不可直接比；E-064 預註冊樣本外 ρ（A/B 半場對調平均，目標＝每場淨值）'
        + (f'{e064_out:.3f}' if e064_out is not None else NA) + '，與其他卡片的樣本外目標不同、不併入下表樣本外欄；對 2K27 ρ 取 E-064 verdict.json 的 repl 值（2K27 評分本身含上場時間，故高於每 36 分鐘版）；來源 card-0.2.0', src=C020_CARD, k2=e064_2k)
    add('卡片 OVR card 0.1.2（前正式版，每 36 分鐘）', 'card 0.1.1（v61 收縮歷史，E-054+E-055）+ E-060 onBall 對位目標（2026-10-28 發版，2026-10-29 由 card 0.2.0 取代 OVR 單位）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C012_CARD)],
        f'2026-10-29 由 card 0.2.0 取代（能力值相同，只換 OVR 單位）；{CIRC}；樣本外 ρ（A/B 半 RAPM）尚未量測；對 2K27 ρ 取 evaluation.json 的 E060 值；來源 card-0.1.1+E060-onball-targeting/primary', src=C012_CARD, k2=card_eval_2k('E060'))
    add('卡片 OVR card 0.1.1（v61 收縮歷史）', 'v58 H1-m0 之後的 E-054+E-055（收縮歷史）卡片；未曾正式發版，直接併入 0.1.2（現 0.2.0）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(C011_CARD)],
        f'{CIRC}；未曾正式發版（2026-10-28 與 E-060 一併發為 card 0.1.2，10-29 起為 card 0.2.0 的能力值來源）；樣本外 ρ 未量測；對 2K27 ρ 取 evaluation.json 的 v61-shrink 值', src=C011_CARD, k2=card_eval_2k('v61-shrink'))
    add('卡片 OVR v58 H1-m0（前正式版）', 'v57 G3（γ=1.0、δ=0.25：防守加分 + 往 RAPM align）再加上限：單人總 lift 不得超過其 RAPM 名次（margin=0）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(V58_CARD)],
        f'2026-10-28 由 card 0.1.2 取代（10-29 起為 card 0.2.0）；{CIRC}；樣本外 ρ 為 A/B 半場對調平均（ovr-v58-holdout-2025-26/report.md）；19/19 硬門檻全過；對 2K27 ρ .537；前十長人僅 Wemby/Giannis/Jokić/Chet（皆為 v58 當時數字）', src=V58_CARD, hold='H1')
    add('卡片 OVR v57 G3（γ=1.0、δ=0.25）', 'E2 之上加防守加分（γ=1.0，全位置、PR 90–96 漸減）+ 往 RAPM align δ=0.25，無封頂（v58 的前身）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(G3_CARD)], f'{CIRC}；v58 加封頂後樣本外 ρ 幾乎不變；v58 已於 2026-10-28 由 card 0.1.2 取代（10-29 起 card 0.2.0）', src=G3_CARD, hold='G3')
    add('卡片 OVR v56 F2（PF/C 防守加分 γ=0.5）', 'E2 之上只對 PF/C 加防守加分，無 align、無封頂',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(F2_CARD)], 'ρRAPM 部分樣本內（防守加分用 RAPM pooledD，另有 RAPM 混合目標）', src=F2_CARD, hold='F2')
    add('卡片 OVR v55 E2（前正式版）', '吃餅折扣 λ=0.4（PF/C 自創 ≥65 豁免）後重校，目標同 v53：模擬與 RAPM 混合 α=0.5',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(E2_CARD)], f'2026-10-21 由 v58 H1-m0 取代（v58 於 10-28 由 card 0.1.2 取代，10-29 起 card 0.2.0）；{BLEND_NOTE}', src=E2_CARD, hold='E2')
    add('卡片 OVR v53（前正式版）', '能力值公式校準到模擬與 RAPM 混合目標，α=0.5，見 ovr-blended-2025-26/dataflow.md',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(V53_CARD)],
        f'2026-10-20 由 E2 取代（E2 再於 10-21 由 v58 H1-m0 取代，v58 於 10-28 由 card 0.1.2 取代，10-29 起 card 0.2.0）；{BLEND_NOTE}；樣本外為 backfill 以 A/B 半 RAPM 重擬合（calibrate.py 複本加 --rapm，全量重現 OVR 最大差 0.0）', src=V53_CARD, hold='v53')
    legacy = rows('reports/ovr-calibrated-2025-26/legacy-sim-only/ranking.csv')
    add('卡片 OVR（舊版，sim-only）', '能力值公式校準到 v53 模擬，α=0（已被正式卡片板取代）',
        [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in legacy], f'目標不含 RAPM，ρRAPM 為純樣本外（全量 RAPM）；不讀 RAPM，樣本內即樣本外：同一份分數直接對 A 半、B 半 RAPM 各算一次 ρ 再平均（reports/ovr-metrics-backfill-2025-26）',
        src='reports/ovr-calibrated-2025-26/legacy-sim-only/ranking.csv', bk='legacy')
    blend = rows('reports/ovr-blended-2025-26/ranking.csv')
    add('卡片 OVR（混合 α=0.5）', '校準目標 = 模擬與 RAPM 各半（與正式卡片板同一組數字，來源腳本不同）', [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in blend],
        '目標含 RAPM，樣本內 ρ 偏高；blend.py 與 calibrate.py --alpha 0.5 輸出逐名相同，樣本外沿用 v53 的 A/B 半重擬合（backfill）', src='reports/ovr-blended-2025-26/ranking.csv', bk='blend')
    for key, desc in V55_DESC.items():
        if key in ('E2', 'v58'):
            continue
        add(f'卡片 OVR 實驗 {key}（未採用）', desc, [(float(r['ovr']), rapm_by_name.get(r['name'])) for r in rows(V55_CARDS[key])],
            f'Karlo 未過，不採用；{BLEND_NOTE}；樣本外為 backfill 以 A/B 半 RAPM 重擬合', src=V55_CARDS[key], bk=key)
    return out


def v55fix(rapm_by_name):
    """7-player acceptance table for the v55 card experiments vs the official v53 card."""
    ranks = {k: {r['name']: int(r['rank']) for r in rows(p)} for k, p in {'v53': V53_CARD, **V55_CARDS}.items()}
    rank2k = {r['name']: float(r['rank2k']) for r in rows('reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    pool = sorted((r for r in rapm_by_name.values() if float(r['pooledPoss']) >= EVAL_POSS), key=lambda r: -float(r['pooledNet']))
    rapm_rank = {r['name']: i + 1 for i, r in enumerate(pool)}
    out = []
    for name, cond, ok in V55_CHECKS:
        base = ranks['v53'][name]; ref = max(rank2k[name], rapm_rank.get(name, 0))
        row = {'name': name, 'condition': cond, 'v53': base, 'rank2k': rank2k[name], 'rapmRank': rapm_rank.get(name, '—')}
        for k in V55_CARDS:
            row[k] = ranks[k][name]; row[k + 'Pass'] = ok(base, ranks[k][name], ref)
        out.append(row)
    return out


def team():
    chart = json.loads((ROOT / 'reports/model-evolution-20261016/chart-data.json').read_text(encoding='utf-8'))
    out = [{'version': f'v{v}', 'order': int(v), 'winsMAE': round(m['winsMAE'], 2), 'netRMSE': round(m['netRMSE'], 3),
            'ptsMAE': round(m['pts'], 2), 'source': 'model-evolution-20261016', 'measured': True}
           for v, m in chart['team'].items() if v != 'control']
    seen = {r['version'] for r in out}
    for v in (46, 47, 48, 49):
        d = json.loads((ROOT / f'reports/player-impact-v{v}/2025-26-scores.json').read_text(encoding='utf-8'))
        for c in d['cells']:
            if c['variant'] not in seen:
                m = c['teamMetrics']; seen.add(c['variant'])
                out.append({'version': c['variant'], 'order': int(c['variant'][1:]), 'winsMAE': round(m['winsMAE'], 2),
                            'netRMSE': round(m['netRMSE'], 3), 'ptsMAE': NA, 'source': f'player-impact-v{v}', 'measured': True})
    v53 = json.loads((ROOT / 'reports/player-impact-v53-team/scores.json').read_text(encoding='utf-8'))
    m = next(c['teamMetrics'] for c in v53['cells'] if c['season'] == '2025-26' and c['variant'] == 'v53')
    out.append({'version': 'v53', 'order': 53, 'winsMAE': round(m['winsMAE'], 2), 'netRMSE': round(m['netRMSE'], 3), 'ptsMAE': NA,
                'source': 'player-impact-v53-team（壓迫係數為樣本內）', 'measured': True})
    v54 = json.loads((ROOT / 'reports/player-impact-v54-team/scores.json').read_text(encoding='utf-8'))
    m = next(c['teamMetrics'] for c in v54['cells'] if c['season'] == '2025-26' and c['variant'] == 'v54')
    out.append({'version': 'v54', 'order': 54, 'winsMAE': round(m['winsMAE'], 2), 'netRMSE': round(m['netRMSE'], 3), 'ptsMAE': NA,
                'source': 'player-impact-v54-team（未採用）', 'measured': True})
    return sorted(out, key=lambda r: r['order'])


TREND = [('舊版 sim-only', 'legacy', 1, True), ('v53', 'v53', 2, True), ('E2 (v55)', 'E2', 3, True), ('F2 (v56)', 'F2', 4, True),
         ('G3 (v57)', 'G3', 5, True), ('H1 (v58)', 'H1', 6, True), ('card 0.1.1', 'c011', 7, False), ('card 0.1.2', 'c012', 8, True),
         ('card 0.2.0', 'c020', 9, True), ('card 0.2.1', 'c021', 10, True), ('card 0.2.2', 'c022', 11, True), ('card 0.2.3', 'c023', 12, True), ('card 0.2.4', 'c024', 13, True), ('card 0.2.5', 'c025', 14, True), ('card 0.2.6', 'c026', 15, True), ('card 0.2.7', 'c027', 16, True), ('card 0.2.7a', 'c027a', 17, True), ('card 0.2.7b', 'c027b', 18, True), ('card 0.2.7c', 'c027c', 19, True), ('card 0.2.7d', 'c027d', 20, True), ('card 0.2.8', 'c028', 21, True), ('card 0.2.9', 'c029', 22, True), ('B12', 'B12', 23, False), ('C1', 'C1', 24, False), ('D1', 'D1', 25, False)]
TREND_LAYER = {'legacy': '卡片 OVR（舊版，sim-only）', 'v53': '卡片 OVR v53（前正式版）', 'E2': '卡片 OVR v55 E2（前正式版）',
               'F2': '卡片 OVR v56 F2（PF/C 防守加分 γ=0.5）', 'G3': '卡片 OVR v57 G3（γ=1.0、δ=0.25）', 'H1': '卡片 OVR v58 H1-m0（前正式版）', 'c011': '卡片 OVR card 0.1.1（v61 收縮歷史）', 'c012': '卡片 OVR card 0.1.2（前正式版，每 36 分鐘）', 'c020': '卡片 OVR card 0.2.0（前正式版）', 'c021': '卡片 OVR card 0.2.1（前正式版', 'c022': '卡片 OVR card 0.2.2（前正式版）', 'c023': '卡片 OVR card 0.2.3（前正式版）', 'c024': '卡片 OVR card 0.2.4（前正式版）', 'c025': '卡片 OVR card 0.2.5（前正式版）', 'c026': '卡片 OVR card 0.2.6（前正式版）', 'c027': '卡片 OVR card 0.2.7（前正式版）', 'c027a': '卡片 OVR card 0.2.7a（前正式版）', 'c027b': '卡片 OVR card 0.2.7b（前正式版）', 'c027c': '卡片 OVR（前正式版，card 0.2.7c）', 'c027d': '卡片 OVR card 0.2.7d（前正式版）', 'c028': '卡片 OVR card 0.2.8（前正式版）', 'c029': '卡片 OVR（正式卡片板，card 0.2.9）',
               'B12': '卡片 OVR 實驗 B12（未採用）', 'C1': '卡片 OVR 實驗 C1（未採用）', 'D1': '卡片 OVR 實驗 D1（未採用）'}


def trend(personal_rows, backfill, holdout):
    """卡片版本趨勢：樣本內／樣本外／2K27 ρ。B12/C1/D1 是 v55 期間未採用的分支實驗，order 排在主線之後（adopted=false）。"""
    by_layer = {r['layer']: r for r in personal_rows}
    out = []
    for version, key, order, adopted in TREND:
        row = by_layer.get(TREND_LAYER[key]) or next((r for r in personal_rows if r['layer'].startswith(TREND_LAYER[key])), None)
        b = backfill_layer(backfill, key)
        try:
            h = holdout['cards'][key]['holdout_scale0.5']['avg']; net, df = h['net'], h['def']
        except (KeyError, TypeError):
            net, df = (b['out']['net'], b['out']['def']) if b else (None, None)
        out.append({'version': version, 'order': order, 'adopted': adopted, 'rhoNetIn': row['rhoNet'] if row else None,
                    'rhoNetOut': None if net is None else round(net, 3), 'rhoDefOut': None if df is None else round(df, 3),
                    'rho2k': round(b['rho2k'], 3) if b else (row['rho2k'] if row and row['rho2k'] != NA else None)})
    return out


def team_card(backfill):
    """卡片球隊指標：球隊名單依 2025-26 上場分鐘加權的平均卡片 OVR vs 實際每場分差（30 隊）。與模擬 winsMAE 分開。"""
    tc = backfill.get('teamCard')
    if not tc:
        return [], []
    names = {k: next((t for v, kk, o, a in TREND if kk == k for t in [v]), k) for k in {c['card'] for c in tc['cards']}}
    order = {kk: (o, a) for v, kk, o, a in TREND}
    rows_ = [{'version': names[c['card']], 'order': order[c['card']][0], 'adopted': order[c['card']][1], 'teams': c['teams'],
              'pearsonR': round(c['pearsonR'], 3), 'spearmanRho': round(c['spearmanRho'], 3), 'source': tc['source']} for c in tc['cards']]
    return sorted(rows_, key=lambda r: r['order']), tc['teams']


def three_value_by_name():
    # three-value.csv 以 playerId 為鍵；正式卡 ranking.csv 沒有 playerId，改用姓名對（兩邊 582 人姓名皆唯一且完全對上）。對不上的給 None。
    return {r['name']: float(r['tv_main']) for r in rows(THREE_VALUE)}


def top20(rapm_by_name):
    card = rows(OFFICIAL_CARD)
    tv = three_value_by_name()
    sim = {r['name']: int(r['rank']) for r in rows('reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv')}
    pool = sorted((r for r in rapm_by_name.values() if float(r['pooledPoss']) >= EVAL_POSS), key=lambda r: -float(r['pooledNet']))
    rapm_rank = {r['name']: i + 1 for i, r in enumerate(pool)}
    out = []
    for r in card[:20]:
        rr = rapm_rank.get(r['name']); flags = []
        if int(r['MIN']) < LOW_MIN: flags.append('低分鐘')
        if rr is None: flags.append('RAPM 樣本不足')
        elif rr > RAPM_FAR: flags.append('RAPM 差距大')
        if r['pos'] in BIGS: flags.append('長人')
        out.append({'rank': int(r['rank']), 'name': r['name'], 'pos': r['pos'], 'ovr': float(r['ovr']), 'minutes': int(r['MIN']),
                    'threeValue': round(tv[r['name']], 1) if r['name'] in tv else None,
                    'simRank': sim.get(r['name'], '—'), 'rapmRank': rr if rr is not None else '—', 'flags': '、'.join(flags) or '—'})
    return out, len(pool)


def kpi(holdout, personal_rows):
    """頂部 KPI；正式卡片 = card 0.2.10a。樣本外 ρ 尚未量測（顯示未量測，不拿 v58 代替）。遊戲本體不讀 OVR，所以標籤是「正式卡片」而非「遊戲現用」。"""
    def cell(key, field):
        try:
            return holdout['cards'][key]['holdout_scale0.5']['avg'][field]
        except (KeyError, TypeError):
            return None
    fmt = lambda v: NA if v is None else f'{v:.3f}'
    row = lambda name: next((r for r in personal_rows if name in r['layer']), {})
    inS = f"{row('正式卡片板，card 0.2.10a')['rhoNet']:.3f}" if row('正式卡片板，card 0.2.10a') else NA
    k2 = row('正式卡片板，card 0.2.10a').get('rho2k', NA)
    k2 = fmt(k2) if not isinstance(k2, str) else k2
    k2old = row('v58 H1-m0（前').get('rho2k', NA)
    return [{'label': '正式卡片 card 0.2.10a 樣本外 ρ（淨值）', 'value': NA,
             'sub': f'A/B 半 RAPM 樣本外尚未量測；樣本內 {inS}（循環）；前正式版 v58 H1-m0 為 {fmt(cell("H1", "net"))}（不同卡片，僅供參考）'},
            {'label': '正式卡片 card 0.2.10a 樣本外 ρ（防守）', 'value': NA, 'sub': f'尚未量測；v58 H1-m0 為 {fmt(cell("H1", "def"))}（僅供參考）'},
            {'label': '正式卡片 card 0.2.10a 對 2K27 ρ（外部基準）', 'value': k2,
             'sub': f"v58 H1-m0 {k2old if isinstance(k2old, str) else fmt(k2old)}；來源 {C027C_EVAL}（K1 候選，每場含上場時間）；card 0.2.7b 為 .738、card 0.2.7a 為 .737、card 0.2.7 為 .736、card 0.2.6 為 .737、card 0.2.5 為 .738、card 0.2.4 為 .748、card 0.2.3 為 .740、card 0.2.2 為 .681、card 0.2.0 為 .695、card 0.1.2（每 36 分鐘）為 .518；2K27 不參與擬合"}]


def md(snap):
    L = [f"# 審查表（{snap['generatedAt'][:10]}）", '', f"模擬版本 {LATEST_SIM}。由 `reports/status/status_snapshot.py` 產生。", '',
         '## 重點（KPI）', '', '| ' + ' | '.join(k['label'] for k in snap['kpi']) + ' |', '|' + '---:|' * len(snap['kpi']),
         '| ' + ' | '.join(f"**{k['value']}**" for k in snap['kpi']) + ' |', '', *[f"- {k['label']}：{k['sub']}" for k in snap['kpi']], '',
         f"## 個人準確度（RAPM，pooledPoss ≥ {EVAL_POSS}）", '',
         '樣本外 ρ = 只用 A 半（gameId 偶數）RAPM 擬合的卡片對 B 半 RAPM 的 ρ，再對調取平均（`reports/ovr-v58-holdout-2025-26/report.md`）；不讀 RAPM 的層（模擬板、舊版 sim-only）直接對 A／B 半 RAPM 各算一次再平均；讀 RAPM 的卡片層（v53／混合／B12／C1／D1）以 A／B 半重擬合（`reports/ovr-metrics-backfill-2025-26/`）；人群 = 評估半 pooledPoss ≥ 2500 的共同球員（約 408 人，各層共用）。對 2K27 ρ 的人群 = 所有層共有且有 2K 值的 575 人。', '',
         '| 層 | 人數 | 淨值 ρ（全量 RAPM） | 防守 ρ（全量 RAPM） | 樣本外 ρ（淨值 / 防守） | 對 2K27 ρ | 備註 |', '|---|---:|---:|---:|---:|---:|---|']
    L += [f"| {r['layer']} | {r['players']} | {r['rhoNet']:.3f} | {r['rhoDefense']:.3f} | {r['holdoutRho']} | {r['rho2k'] if isinstance(r['rho2k'], str) else format(r['rho2k'], '.3f')} | {r['note']} |" for r in snap['personal']]
    L += ['', '## 球隊準確度（30 隊、全季）', '', f"說明：{TEAM_NOTE}。球隊 winsMAE 只來自模擬模型版本（v53/v54 等）。", '',
          '| 版本 | 勝場 MAE | 淨分 RMSE | 得分 MAE | 來源 |', '|---|---:|---:|---:|---|']
    f = lambda v, p: v if isinstance(v, str) else f'{v:.{p}f}'
    L += [f"| {r['version']} | {f(r['winsMAE'], 2)} | {f(r['netRMSE'], 3)} | {f(r['ptsMAE'], 2)} | {r['source']} |" for r in snap['team']]
    L += ['', '## 卡片球隊指標（30 隊、2025-26）', '',
          '各隊名單依 2025-26 上場分鐘加權的平均卡片 OVR，對實際每場分差（`data/season-league.json` 的 PLUS_MINUS / GP）。與上表模擬 winsMAE 不同口徑；全量卡片、樣本內（卡片的 RAPM 目標含本季比賽），不可與模擬 winsMAE 比較。', '',
          '| 卡片 | 隊數 | Pearson r | Spearman ρ | 採用 |', '|---|---:|---:|---:|---|']
    L += [f"| {r['version']} | {r['teams']} | {r['pearsonR']:.3f} | {r['spearmanRho']:.3f} | {'是' if r['adopted'] else '否'} |" for r in snap['teamCard']]
    L += ['', '## 卡片版本趨勢', '', '| 版本 | 序 | 採用 | 樣本內 ρ 淨值 | 樣本外 ρ 淨值 | 樣本外 ρ 防守 | 對 2K27 ρ |', '|---|---:|---|---:|---:|---:|---:|']
    g = lambda v: '—' if v is None else f'{v:.3f}'
    L += [f"| {r['version']} | {r['order']} | {'是' if r['adopted'] else '否'} | {g(r['rhoNetIn'])} | {g(r['rhoNetOut'])} | {g(r['rhoDefOut'])} | {g(r['rho2k'])} |" for r in snap['trend']]
    L += ['', f"## 卡片 OVR 前 20（RAPM 名次在 {snap['rapmPool']} 人中）", '', '| # | 球員 | 位置 | OVR | 3PT | 分鐘 | 模擬名次 | RAPM 名次 | 旗標 |',
          '|---:|---|---|---:|---:|---:|---:|---:|---|']
    L += [f"| {r['rank']} | {r['name']} | {r['pos']} | {r['ovr']:.1f} | {'' if r['threeValue'] is None else format(r['threeValue'], '.1f')} | {r['minutes']} | {r['simRank']} | {r['rapmRank']} | {r['flags']} |" for r in snap['top20']]
    mark = lambda r, k: f"{r[k]}{'' if r[k + 'Pass'] else ' ✗'}"
    L += ['', '## v55 卡片修正各方向（7 人驗收，v53 名次 → 實驗名次，✗ = 未過；E2 曾為正式卡片，10-21 ~ 10-28 正式卡片為 v58 H1-m0，10-28 ~ 10-29 為 card 0.1.2，10-29 起為 card 0.2.0）', '',
          '| 球員 | 條件 | 2K27 | RAPM | v53 | ' + ' | '.join(V55_CARDS) + ' |', '|---|---|---:|---:|---:|' + '---:|' * len(V55_CARDS)]
    L += [f"| {r['name']} | {r['condition']} | {r['rank2k']:g} | {r['rapmRank']} | {r['v53']} | " + ' | '.join(mark(r, k) for k in V55_CARDS) + ' |' for r in snap['v55fix']]
    return '\n'.join(L) + '\n'


def main():
    rapm = rows('reports/impact-rapm/rapm.csv')
    by_id = {r['playerId']: r for r in rapm}; by_name = {r['name']: r for r in rapm}
    t20, pool = top20(by_name)
    holdout = load_holdout()
    backfill = load_backfill()
    personal_rows = personal(by_id, by_name, holdout, backfill)
    tcard, tcard_teams = team_card(backfill)
    snap = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'simVersion': LATEST_SIM, 'evalPoss': EVAL_POSS,
            'rapmPool': pool, 'kpi': kpi(holdout, personal_rows), 'teamNote': TEAM_NOTE, 'personal': personal_rows, 'team': team(),
            'top20': t20, 'v55fix': v55fix(by_name), 'trend': trend(personal_rows, backfill, holdout), 'teamCard': tcard, 'teamCardTeams': tcard_teams}
    PAYLOAD.mkdir(exist_ok=True)
    for k in ('personal', 'team', 'top20', 'v55fix', 'trend'):
        for d in (OUT, PAYLOAD):
            (d / f'{k}.json').write_text(json.dumps(snap[k], ensure_ascii=False, indent=1), encoding='utf-8')
    for d in (OUT, PAYLOAD):
        (d / 'team_card.json').write_text(json.dumps(snap['teamCard'], ensure_ascii=False, indent=1), encoding='utf-8')
        (d / 'team_card_teams.json').write_text(json.dumps(snap['teamCardTeams'], ensure_ascii=False, indent=1), encoding='utf-8')
    (PAYLOAD / 'kpi.json').write_text(json.dumps(snap['kpi'], ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'status.json').write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'status.md').write_text(md(snap), encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    print(md(snap))


if __name__ == '__main__':
    main()
