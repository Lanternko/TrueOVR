import json, sys
def add(code, condition, value, passed, deviation=None):
    p = 'gates.json'
    d = json.load(open(p, encoding='utf-8'))
    g = dict(code=code, condition=condition, value=value, **{'pass': bool(passed)})
    if deviation: g['deviation'] = deviation
    d['gates'][code] = g
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
