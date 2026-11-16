# Databricks notebook source
# DBTITLE 1,Configure Git hooks path
import os
import stat
import subprocess
import sys
from pathlib import Path


HOOKS_DIR = ".github/hooks"
HOOK_NAMES = ["pre-commit", "pre-push"]


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def main() -> int:
    try:
        repo_root = Path(
            run_git("rev-parse", "--show-toplevel")
        ).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: This script must be run inside a Git repository.")
        return 1

    hooks_dir = repo_root / HOOKS_DIR

    if not hooks_dir.is_dir():
        print(f"ERROR: Hooks directory does not exist: {hooks_dir}")
        return 1

    try:
        # Use --local so this only affects the current repository.
        run_git("config", "--local", "core.hooksPath", HOOKS_DIR)

        configured_path = run_git(
            "config", "--local", "--get", "core.hooksPath"
        )

        if configured_path != HOOKS_DIR:
            print(
                f"ERROR: core.hooksPath was set to unexpected value: "
                f"{configured_path}"
            )
            return 1

    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Failed to configure Git hooks: {exc}")
        return 1

    # Git silently skips hooks that are not executable, so set the
    # executable bit on disk and in the Git index (mode 100755).
    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        if not hook_path.is_file():
            continue

        mode = hook_path.stat().st_mode
        os.chmod(hook_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if not os.access(hook_path, os.X_OK):
            print(f"ERROR: Could not make hook executable: {hook_path}")
            return 1

        rel_path = f"{HOOKS_DIR}/{hook_name}"
        try:
            root = str(repo_root)
            if run_git("-C", root, "ls-files", "--", rel_path):
                run_git("-C", root, "update-index", "--chmod=+x", "--", rel_path)
            index_entry = run_git("-C", root, "ls-files", "-s", "--", rel_path)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR: Failed to update index mode for {rel_path}: {exc}")
            return 1

        print(f"Executable: {rel_path} (index: {index_entry or 'untracked'})")

    print(f"Git hooks configured successfully.")
    print(f"core.hooksPath = {configured_path}")
    print(f"Hooks directory: {hooks_dir}")

    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        sys.exit(exit_code)

# COMMAND ----------

# Pre-provision the PHI scanner venv exactly where .github/hooks/pre-commit
# expects it, so the hook finds it installed and skips its own bootstrap.
# The hook's bootstrap fails on Databricks because /usr/bin/python3 has no
# ensurepip and no virtualenv; /databricks/python3 ships virtualenv.
# On serverless, $HOME is per-session: re-run this cell in each new session.
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PHI_REPO_URL = os.environ.get(
    "PHI_REPO_URL", "https://github.com/Intermountain-Health/data-mlops-github-hooks.git"
)
PHI_HOME = Path(os.environ.get("PHI_HOME", Path.home() / ".cache" / "mlops-phi"))
VENV = PHI_HOME / "venv"
STAMP = PHI_HOME / "last_check"
INSTALLED_TAG = PHI_HOME / "installed_tag"

# Run child Pythons from a neutral directory with a clean environment so
# workspace folders (e.g. one named 'email') cannot shadow stdlib modules.
SAFE_CWD = tempfile.gettempdir()
CLEAN_ENV = {
    k: v for k, v in os.environ.items()
    if k not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")
}
CLEAN_ENV["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
CLEAN_ENV["GIT_TERMINAL_PROMPT"] = "0"


def run(cmd, check=True, **kw):
    return subprocess.run(
        [str(c) for c in cmd], check=check, text=True, capture_output=True,
        cwd=kw.pop("cwd", SAFE_CWD), env=kw.pop("env", CLEAN_ENV), **kw,
    )


def venv_python():
    for p in (VENV / "Scripts" / "python.exe", VENV / "bin" / "python"):
        if p.exists() and os.access(p, os.X_OK):
            return p
    return None


def ok(cmd) -> bool:
    return run(cmd, check=False).returncode == 0


def latest_tag() -> str:
    out = run([
        "git", "ls-remote", "--heads", "--refs", "--sort=-v:refname",
        PHI_REPO_URL, "refs/heads/release/v*",
    ]).stdout.split()
    if len(out) < 2:
        raise RuntimeError(f"No release/v* branch found at {PHI_REPO_URL}")
    sha, ref = out[0], out[1]
    return f"{ref.removeprefix('refs/heads/')}@{sha}"


def create_venv() -> Path:
    candidates = [
        os.environ.get("PHI_BOOTSTRAP_PYTHON"),
        "/databricks/python3/bin/python3",
        sys.executable,
        shutil.which("python3"),
        "/usr/bin/python3",
    ]
    tried = []
    for boot in dict.fromkeys(c for c in candidates if c):
        if not Path(boot).exists():
            continue
        for method in (["-m", "venv"], ["-m", "virtualenv", "-q"]):
            shutil.rmtree(VENV, ignore_errors=True)
            res = run([boot, *method, VENV], check=False)
            py = venv_python()
            if res.returncode == 0 and py and ok([py, "-m", "pip", "--version"]):
                print(f"Created venv with: {boot} {' '.join(method)}")
                return py
            tried.append(f"{boot} {' '.join(method)}")
    shutil.rmtree(VENV, ignore_errors=True)
    raise RuntimeError("Could not create a venv with pip. Tried:\n  " + "\n  ".join(tried))


def bootstrap_phi_scanner(force: bool = False) -> Path:
    PHI_HOME.mkdir(parents=True, exist_ok=True)
    tag = latest_tag()
    current = INSTALLED_TAG.read_text().strip() if INSTALLED_TAG.exists() else ""
    py = venv_python()
    installed = bool(py) and ok([py, "-c", "import mlops_phi"])

    if installed and current == tag and not force:
        print(f"PHI scanner already installed: {tag}")
    else:
        if not py or not ok([py, "-m", "pip", "--version"]):
            py = create_venv()
        print(f"Installing PHI scanner {tag} ...")
        res = run([
            py, "-m", "pip", "install", "--quiet", "--force-reinstall", "--no-deps",
            f"git+{PHI_REPO_URL}@{tag.split('@')[-1]}",
        ], check=False)
        if res.returncode != 0:
            raise RuntimeError(f"pip install failed:\n{res.stdout}\n{res.stderr}")
        INSTALLED_TAG.write_text(tag + "\n")

    if not ok([py, "-c", "import mlops_phi"]):
        raise RuntimeError("mlops_phi is not importable from the venv.")
    STAMP.write_text(f"{int(time.time())}\n")

    version = run([py, "-m", "pip", "show", "mlops-phi-hooks"]).stdout
    version = next((l for l in version.splitlines() if l.startswith("Version:")), "")
    print(f"PHI_HOME:      {PHI_HOME}")
    print(f"Venv python:   {py}")
    print(f"Installed tag: {tag} ({version})")
    return py


PHI_PY = bootstrap_phi_scanner()

# COMMAND ----------

# Scan every file in the repo (tracked + untracked, excluding .gitignore'd)
# with the same scanners and blocking policy the pre-commit hook uses.
repo_root = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
)

files = [
    f for f in subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z",
         "--cached", "--others", "--exclude-standard"],
        check=True, capture_output=True,
    ).stdout.decode().split("\0")
    if f and (repo_root / f).is_file()
]
print(f"Repo: {repo_root}")
print(f"Files found: {len(files)}\n")

scan = run([PHI_PY, "-m", "mlops_phi.pre_commit", *files], check=False, cwd=repo_root)
print(scan.stdout)
if scan.stderr:
    print(scan.stderr)

if scan.returncode == 0:
    print("FULL SCAN RESULT: PASSED")
else:
    print(f"FULL SCAN RESULT: FAILED (exit code {scan.returncode}) - a commit with these files would be blocked.")

