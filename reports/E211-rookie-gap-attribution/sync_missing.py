"""把主 repo 中 worktree 缺的檔案（gitignored）複製進 worktree；只讀主 repo。用法: sync_missing.py <相對目錄>... """
import sys, os, shutil, time
MAIN = r'D:\Projects\CODING\basketball-autochess'
WT = __import__('os').environ.get('E211_ROOT', r'D:\Projects\CODING\_wt\e141-env')
CUT = time.mktime(time.strptime(os.environ.get('E211_CUTOFF','2026-10-31 12:36'),'%Y-%m-%d %H:%M'))
SKIP_DIRS = {'cards', '__pycache__'}
MAXSZ = 60e6
n = 0; skipped_new = []
for rel in sys.argv[1:]:
    for dp, dns, fns in os.walk(os.path.join(MAIN, rel)):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            s = os.path.join(dp, f)
            r = os.path.relpath(s, MAIN)
            d = os.path.join(WT, r)
            if os.path.exists(d): continue
            if os.path.getsize(s) > MAXSZ: print('big skip', r); continue
            if os.path.getmtime(s) > CUT: skipped_new.append(r); continue
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d); n += 1
print('copied', n, 'skipped newer-than-run', len(skipped_new))
for r in skipped_new[:40]: print(' newer', r)
