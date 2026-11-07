"""Claude Code Stop hook：這個 session 做了實際工作、之後卻沒更新 memory/handoff.md，就提醒一次收工寫 memory。

「實際工作」＝本 session transcript 裡：
  - Edit／Write／NotebookEdit 改到 repo 內 memory/ 以外的檔案；
  - Bash／PowerShell 執行 scripts/ 或 reports/ 下的 .py／.js（--dry-run 不算）；
  - 派工（dispatch_submit／dispatch_continue）。
「更新 handoff」＝之後有 Edit／Write 寫 memory/handoff.md；或之後有 Bash／PowerShell 指令提到 handoff.md、
而且 handoff.md 的修改時間晚於最後一筆工作（用 shell／腳本寫入；只看修改時間會把共用 checkout 裡別的 session 寫的也算進來）。

什麼時候檢查：transcript 裡用過 mcp__ccd_turn__wrap_up（App）時，只在本回合有 wrap_up（工作告一段落）才檢查；
沒用過 wrap_up（CLI）時每回合結束都檢查。同一份未記錄的工作只提醒一次（狀態存在 %TEMP%）。
派工子 session（CLAUDE_DISPATCH_CHILD=1）不檢查。任何錯誤都放行。
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2].as_posix().lower()
STATE_DIR = Path(tempfile.gettempdir()) / 'claude-handoff-reminder'
EDIT_TOOLS = {'Edit', 'Write', 'NotebookEdit'}
SHELL_TOOLS = {'Bash', 'PowerShell'}
DISPATCH_TOOLS = {'mcp__claude-dispatch__dispatch_submit', 'mcp__claude-dispatch__dispatch_continue'}
WRAP_UP = 'mcp__ccd_turn__wrap_up'
RUN_SCRIPT = re.compile(r'\b(?:python[w3]?(?:\.exe)?|node(?:\.exe)?)\b[^\n|;&]*?\b(?:scripts|reports)[\\/][^\s"\']+\.(?:py|js)\b', re.I)

REASON = (
    "這個 session 做了實際工作（{what}），但之後沒有更新 memory/handoff.md。"
    "如果這段工作已告一段落：照 memory/README.md 收工規則，把新發現、實驗、裁決、教訓寫進對應檔，並更新 handoff.md"
    "（共用 checkout 時只 stage 自己的段落，L-047）。"
    "如果還在進行中（背景任務沒回來、等使用者決定），或這次改動確實不需要記錄，用一句繁體中文說明即可，不要呼叫工具。"
)


def norm(p):
    return str(p or '').replace('\\', '/').lower()


def in_repo(p):
    p = norm(p)
    return p.startswith(ROOT + '/') or not re.match(r'^[a-z]:/|^/', p)


def is_memory(p, name=''):
    rel = norm(p)[len(ROOT) + 1:] if norm(p).startswith(ROOT + '/') else norm(p)
    return rel.startswith('memory/' + name)


def tool_uses(entries):
    """依序產生 (index, 是否為使用者回合開頭, tool name, input, timestamp)。"""
    i = 0
    for e in entries:
        msg = e.get('message') or {}
        content = msg.get('content')
        if e.get('type') == 'user':
            if isinstance(content, str) or (isinstance(content, list) and any(
                    isinstance(b, dict) and b.get('type') == 'text' for b in content)):
                yield i, True, None, None, None
                i += 1
            continue
        if e.get('type') != 'assistant' or not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                yield i, False, b.get('name') or '', b.get('input') or {}, e.get('timestamp')
                i += 1


def scan(entries):
    last_work, what, work_ts, last_handoff, last_handoff_cmd, turn_start, wrap_turns, used_wrap = -1, '', None, -1, -1, -1, set(), False
    for i, user_turn, name, inp, ts in tool_uses(entries):
        if user_turn:
            turn_start = i
            continue
        if name == WRAP_UP:
            used_wrap = True
            wrap_turns.add(turn_start)
        elif name in EDIT_TOOLS:
            p = inp.get('file_path') or inp.get('notebook_path')
            if not in_repo(p):
                continue
            if is_memory(p, 'handoff.md'):
                last_handoff = i
            elif not is_memory(p):
                last_work, what, work_ts = i, '改了 ' + norm(p).rsplit('/', 1)[-1], ts
        elif name in SHELL_TOOLS:
            cmd = str(inp.get('command') or '')
            if 'handoff.md' in cmd:
                last_handoff_cmd = i
            m = RUN_SCRIPT.search(cmd)
            if m and '--dry-run' not in cmd and not re.search(r'[\\/]test[\\/]', m.group(0)):
                last_work, what, work_ts = i, '跑了 ' + m.group(0).rsplit('/', 1)[-1].rsplit('\\', 1)[-1], ts
        elif name in DISPATCH_TOOLS:
            last_work, what, work_ts = i, '派工', ts
    shell_handoff = last_handoff_cmd > last_work and handoff_touched_after(work_ts)
    if shell_handoff:
        last_handoff = max(last_handoff, last_handoff_cmd)
    return last_work, what, last_handoff, (turn_start in wrap_turns) if used_wrap else True


def handoff_touched_after(ts):
    """handoff.md 的修改時間是否晚於 transcript 時間戳 ts（ISO，UTC）。"""
    try:
        when = datetime.fromisoformat(str(ts).replace('Z', '+00:00')).timestamp()
        return (Path(ROOT) / 'memory/handoff.md').stat().st_mtime > when
    except (OSError, ValueError, TypeError):
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
    if payload.get('stop_hook_active'):
        return
    path = payload.get('transcript_path')
    if not path or not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    last_work, what, last_handoff, check_now = scan(entries)
    if not check_now or last_work < 0 or last_handoff > last_work:
        return
    state = STATE_DIR / (re.sub(r'[^\w.-]', '_', str(payload.get('session_id') or Path(path).stem)) + '.json')
    try:
        reminded = json.loads(state.read_text(encoding='utf-8')).get('lastWork', -1)
    except (OSError, ValueError):
        reminded = -1
    if reminded >= last_work:
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({'lastWork': last_work}), encoding='utf-8')
    emit({'decision': 'block', 'reason': REASON.format(what=what)})


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
