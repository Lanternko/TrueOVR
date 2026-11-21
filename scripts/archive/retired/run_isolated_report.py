"""Run a frozen report without adding its directory to Python's module search.

Some historical report basenames (e.g. select.py) collide with stdlib modules.
Keep their frozen bytes and give subprocess workers the same clean search path.
"""
import runpy,sys
from pathlib import Path
if __name__=='__main__':
 target=Path(sys.argv[1]).resolve();sys.argv=[str(target),*sys.argv[2:]]
 sys.path[:]=[str(Path.cwd()),*[p for p in sys.path if Path(p or '.').resolve()!=target.parent]]
 runpy.run_path(str(target),run_name='__main__')
