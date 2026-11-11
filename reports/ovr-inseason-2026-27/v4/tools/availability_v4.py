"""P7/G6：2026-27 資料層可用清單（本輪不讀、不抓任何 2026-27 資料）。

派工限制：本輪不得讀取 2026-27 資料，所以這份檔只記錄「預期/規劃」的層與缺層標記，
實際檔名與 SHA 由 L0 補（status 會從 expected 改成 present，並附逐場 SHA 清單）。
creation 依 preregistration-v4 §10.1 標為缺失（沒有 tracking／dependence），值將沿用 c_2025-26。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C


def main():
    doc = {
        'season': '2026-27',
        'stage': 'P7（凍結前；L0 尚未執行）',
        'noDataRead': True,
        'note': ('本輪不讀、不抓任何 2026-27 資料（派工限制，也避免凍結前看到結果）。'
                 '下列 status 一律是 expected/planned，observed=false；L0 執行後才填實際檔名與 SHA。'),
        'layers': {
            'player_games': {'status': 'expected', 'observed': False,
                             'path': 'data/defense-seventh/2026-27/box/player-games',
                             'feeds': ['box 統計', '窗口 N=3/5/10/20'], 'required': True},
            'team_games': {'status': 'expected', 'observed': False,
                           'path': 'data/defense-seventh/2026-27/box/team-games',
                           'feeds': ['u_proxy', 'teamGames'], 'required': True},
            'pbp': {'status': 'expected', 'observed': False,
                    'path': 'data/defense-seventh/2026-27/pbp',
                    'feeds': ['逐場視窗的 15 項能力值'], 'required': True},
            'v3_league': {'status': 'expected', 'observed': False,
                          'path': 'data/defense-seventh/2026-27/v3-league',
                          'feeds': ['onBall/help'], 'required': True},
            'dependence (creation)': {'status': 'missing', 'observed': False,
                                      'reason': '2026-27 沒有 tracking 錨點，dependence-audit 建不起來',
                                      'policy': 'carried（沿用 c_2025-26，manifest 標 carried；§10.1）',
                                      'required': False},
            'four_factors (pressure)': {'status': 'expected_unverified', 'observed': False,
                                        'reason': '需逐季 four-factors（tovNonSteal_defense）',
                                        'policy': '季中若無 → carried（沿用 c_2025-26）；有 → 照正式流程',
                                        'required': False},
            'shot_origin (sTilde)': {'status': 'expected_unverified', 'observed': False,
                                     'reason': '需 shot-origin 產物（prepare-origin.mjs 吃 pbp）',
                                     'policy': '缺 → short=shortBase（同 2021-22 降級）',
                                     'required': False},
            'season_cards': {'status': 'end_of_season', 'observed': False,
                             'reason': '答案卡用的同季 season-cards 於季末建（A0）', 'required': False},
            'rapm': {'status': 'end_of_season', 'observed': False,
                     'reason': '季末 RAPM 於 A0 建，檔名即最大季', 'required': False},
        },
        'creationMissing': True,
        'g6Recorded': True,
    }
    C.V4_LIVE.mkdir(parents=True, exist_ok=True)
    C.write_json(C.V4_LIVE / 'availability.json', doc)
    print(json.dumps({'layers': {k: v['status'] for k, v in doc['layers'].items()},
                      'creationMissing': doc['creationMissing']}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
