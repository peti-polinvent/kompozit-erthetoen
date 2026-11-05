"""autosync.py – a projekt automatikus szinkronizálása GitHubbal (Windows és Mac).

    python .claude/hooks/autosync.py pull   # munkamenet elején: friss állapot letöltése
    python .claude/hooks/autosync.py push   # minden kör végén: commit + push, ha van változás

A git-et a PATH-ból vagy a GitHub Desktop beépített gitjéből veszi. Hibánál nem áll meg
a munkamenet: csak kiírja, mi történt.
"""
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAX_MB = 90  # GitHub 100 MB-os fájllimitje alatt


def find_git():
    g = shutil.which("git")
    if g:
        return g
    pats = [os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe"),
            "/Applications/GitHub Desktop.app/Contents/Resources/app/git/bin/git"]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    sys.exit("autosync: git nem található")


GIT = find_git()


def git(*a, check=False):
    r = subprocess.run([GIT, *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        print(f"autosync: git {' '.join(a)} hiba:\n{r.stderr.strip()}", file=sys.stderr)
    return r


def pull():
    r = git("pull", "--rebase", "--autostash", check=True)
    print("autosync pull:", (r.stdout or r.stderr).strip().splitlines()[-1:] or "ok")


def push():
    if not git("status", "--porcelain").stdout.strip():
        return
    git("add", "-A")
    # túl nagy fájlok kivétele (GitHub-limit)
    for f in git("diff", "--cached", "--name-only").stdout.splitlines():
        p = os.path.join(ROOT, f)
        if os.path.isfile(p) and os.path.getsize(p) > MAX_MB * 1e6:
            git("reset", "-q", "--", f)
            print(f"autosync: kihagyva (> {MAX_MB} MB): {f}", file=sys.stderr)
    if not git("diff", "--cached", "--name-only").stdout.strip():
        return
    host = os.environ.get("COMPUTERNAME") or os.uname().nodename
    git("commit", "-q", "-m", f"auto: {time.strftime('%Y-%m-%d %H:%M')} ({host})", check=True)
    git("pull", "--rebase", "--autostash", check=True)
    r = git("push", check=True)
    print("autosync push:", "ok" if r.returncode == 0 else "HIBA")


if __name__ == "__main__":
    {"pull": pull, "push": push}[sys.argv[1] if len(sys.argv) > 1 else "push"]()
