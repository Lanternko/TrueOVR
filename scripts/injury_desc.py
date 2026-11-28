"""傷病簡評（ESPN／官方 PDF 英文）→ 「左膝扭傷」這類短摘要。抽不到部位也抽不到類型就回空字串（不硬猜）。"""
from __future__ import annotations

import re

# (關鍵字 regex, 中文部位)；越具體越前面，通用字（leg／foot／hand）放最後。
_PARTS = [
    (r'acromioclavicular|\bac joint', '肩鎖關節'), (r'rotator cuff', '旋轉肌袖'), (r'labrum', '盂唇'),
    (r'patellar tendon|patella', '髕骨肌腱'), (r'achilles', '阿基里斯腱'), (r'plantar plate', '蹠板'),
    (r'soleus', '比目魚肌'), (r'fibula', '腓骨'), (r'tibia|shin', '脛骨'),
    (r'hamstring', '大腿後側'), (r'quadricep|\bquad\b', '大腿前側'), (r'groin|adductor', '鼠蹊'),
    (r'calf', '小腿'), (r'\bhip\b|glute', '髖'), (r'\bankle', '踝'), (r'\bknee', '膝'),
    (r'heel', '腳跟'), (r'toe\b', '腳趾'), (r'thumb', '拇指'), (r'finger', '手指'), (r'wrist', '手腕'),
    (r'elbow', '手肘'), (r'forearm', '前臂'), (r'shoulder', '肩'), (r'cervical|neck', '頸'),
    (r'\brib', '肋骨'), (r'\bback\b|lumbar', '背'), (r'abdom|\bcore\b', '核心'), (r'\bnose\b', '鼻'),
    (r'\bjaw\b', '下顎'), (r'\beye\b', '眼'), (r'thigh', '大腿'), (r'\bfoot\b', '腳'), (r'\bhand\b', '手'),
    (r'\bleg\b', '腿'),
]
# 韌帶／半月板本身就指明膝：直接給部位＋類型。
_KNEE = [(r'\bacl\b', '前十字韌帶'), (r'\bmcl\b', '內側副韌帶'), (r'\blcl\b', '外側副韌帶'),
         (r'\bpcl\b', '後十字韌帶'), (r'meniscus', '半月板')]
# 傷勢類型：先出現的規則優先。
_TYPES = [
    (r'torn|tear|ruptur', '撕裂'), (r'fractur|broken|\bbreak', '骨折'), (r'dislocat', '脫臼'),
    (r'concussion', '腦震盪'), (r'bone bruise', '骨挫傷'), (r'contusion|bruise', '挫傷'),
    (r'sprain', '扭傷'), (r'strain', '拉傷'), (r'tendin', '肌腱炎'), (r'sore|soreness', '痠痛'),
    (r'inflam', '發炎'), (r'spasm', '痙攣'), (r'mononucleosis', '單核球增多症'),
]
_NON_INJURY = [(r'\brested\b|\bresting\b|\(rest\)|load management', '休息'), (r'illness|\bsick\b|\bflu\b|virus', '生病'), (r'personal', '私人事由')]


def _side(t: str, word: str) -> str:
    m = re.search(r'\b(left|right)\s+(?:[\w-]+\s+)?(?:' + word + ')', t)
    if m:
        return {'left': '左', 'right': '右'}[m.group(1)]
    sides = set(re.findall(r'\b(left|right)\b', t))              # 部位字旁沒寫左右時，全文只出現一種就採用
    return {'left': '左', 'right': '右'}[sides.pop()] if len(sides) == 1 else ''


def injury_desc(comment: str | None) -> str:
    t = (comment or '').lower()
    if not t:
        return ''
    part = side = ''
    typ = ''
    for pat, name in _KNEE:                                   # ACL／MCL／半月板：部位固定是膝
        if re.search(pat, t):
            part, typ = '膝', name + '撕裂'
            side = _side(t, r'knee')
            break
    if not part:
        for pat, name in _PARTS:
            if re.search(pat, t):
                part, side = name, _side(t, pat)
                break
    if not typ:
        for pat, name in _TYPES:
            if re.search(pat, t):
                typ = name
                break
    if part or typ:
        return side + part + (typ or '傷') if part else typ
    for pat, name in _NON_INJURY:
        if re.search(pat, t):
            return name
    return ''
