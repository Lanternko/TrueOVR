"""Claude Code PostToolUse hook（matcher mcp__ccd_turn__wrap_up）：本回合碰過實驗結果時，在寫收尾訊息之前提醒回報格式。

wrap_up 之後才寫給使用者的收尾訊息，所以在這裡注入提醒，第一版回報就照格式，不用事後擋下重寫。
「碰過實驗結果」＝本回合（最後一個使用者訊息之後）有：呼叫 dispatch_result、寫入 experiments.md／findings.md、
或指令讀 results.json／evaluation.json。只看工具呼叫本身，不看結果文字：這個專案的 git log、handoff、檔名到處是 E-xxx，
看結果文字會幾乎每回合誤觸發。格式本身寫在專案 CLAUDE.md「回報實驗結果」。
派工子 session（CLAUDE_DISPATCH_CHILD=1）不提醒。任何錯誤都放行。
"""
import json
import os
import re
import sys

RESULT_FILES = re.compile(r'\b(results|evaluation)\.json\b', re.I)
LEDGERS = re.compile(r'memory[\\/](experiments|findings)\.md$')
WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')

REMINDER = (
    "本回合碰過實驗結果。接下來的收尾訊息是固定三段式模板，不是參考（L-051、R-145）："
    "第一行就是「# 總評」，前面不放其他段落；三個標題照字面照順序："
    "① `# 總評`（一級標題，## 在 App 裡和粗體一樣大）：第一行寫「**4/5 大致達成 有部分退步（建議採用／不採用）**」"
    "（五級：5 重大達成／4 大致達成 有部分退步／3 一半一半／2 主目標達成 但是有副作用／1 失敗；有實質退步就不給 5），"
    "第二行直接寫「**核心結論**：一句話講清楚這次要驗證的問題成不成立、為什麼」（不要把結論藏在後面）。"
    "② `**關鍵數據與例子**`：一張代表性球員／球隊小表或名次變化（「誰從第幾名到第幾名」「幾成變好」），"
    "加最多 2–3 點說明哪裡變好、哪裡變差或副作用；禁止把同一個指標拆成正反兩段重複講。"
    "③ `**要你決定的事**`：approve 與否、2–3 個下一步方向選項（標明建議哪個、為什麼）。"
    "一則回覆只寫一份三段；稽核也用這三段（核心結論＝原結論站不站得住，關鍵數據＝核對成立與有疑慮處）。"
    "禁止回報工程基本功（資料抓齊、加總吻合、事前 commit、修掉過程腳本 bug、雜湊、Δρ、區間、閘門代號），一律只寫進報告檔；"
    "回覆在第 3 段結束，不加「細節」段（R-081、R-145）。這回合不是在回報實驗結果就忽略這段。"
)


def current_turn(entries):
    """最後一個使用者文字訊息之後的 entries。"""
    start = 0
    for i, e in enumerate(entries):
        content = (e.get('message') or {}).get('content')
        if e.get('type') == 'user' and (isinstance(content, str) or (isinstance(content, list) and any(
                isinstance(b, dict) and b.get('type') == 'text' for b in content))):
            start = i
    return entries[start + 1:]


def touched_experiment(entries):
    for e in current_turn(entries):
        content = (e.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for b in content:
            if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
                continue
            name, inp = b.get('name') or '', b.get('input') or {}
            if 'dispatch_result' in name:
                return True
            if name in WRITE_TOOLS and LEDGERS.search(str(inp.get('file_path', ''))):
                return True
            if name in ('Bash', 'PowerShell') and RESULT_FILES.search(str(inp.get('command', ''))):
                return True
    return False


def emit(obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    if sys.stdout is not None:
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
    else:
        os.write(1, data)


def main():
    if os.environ.get('CLAUDE_DISPATCH_CHILD') == '1':
        return
    raw = sys.stdin.buffer.read() if sys.stdin is not None else os.read(0, 1 << 20)
    payload = json.loads(raw.decode('utf-8') or '{}')
    path = payload.get('transcript_path')
    if not path or not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    if touched_experiment(entries):
        emit({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': REMINDER}})


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
