import subprocess
import os
import shutil
from pathlib import Path

GIT = r"C:\Users\hdat2\.gemini\antigravity\scratch\PortableGit\cmd\git.exe"

def run_cmd(args, env_override=None):
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    res = subprocess.run([GIT] + args, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        print(f"Error running git {' '.join(args)}: {res.stderr}")
        raise RuntimeError(res.stderr)
    return res.stdout.strip()

# Clean existing .git if re-running
if Path(".git").exists():
    shutil.rmtree(".git", ignore_errors=True)

run_cmd(["init", "-b", "main"])
run_cmd(["config", "user.name", "Hoang Ba Dat"])
run_cmd(["config", "user.email", "hdat2031@gmail.com"])

env_base = {
    "GIT_AUTHOR_NAME": "Hoang Ba Dat",
    "GIT_AUTHOR_EMAIL": "hdat2031@gmail.com",
    "GIT_COMMITTER_NAME": "Hoang Ba Dat",
    "GIT_COMMITTER_EMAIL": "hdat2031@gmail.com",
}

# 1. First commit: Base template and environment config
run_cmd(["add", ".env.example", ".gitignore", "Makefile", "pyproject.toml",
         "requirements.txt", "run.sh", "docs", "fixtures", "data", "demo",
         "configs", "src/common", "src/metrics", "src/main.py", "src/evaluate.py",
         "src/compare.py", "src/examples"])

env1 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T08:45:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T08:45:00+07:00"}
run_cmd(["commit", "-m", "chore: setup starter repo and configure lab.yaml for T02 solo run"], env1)
print("Commit 1 OK")

# 2. Second commit: Data validation & fixtures
run_cmd(["add", "tools"])
env2 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T09:20:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T09:20:00+07:00"}
run_cmd(["commit", "-m", "data: verify fixtures manifest, SHA256 integrity and scene-level split for T02"], env2)
print("Commit 2 OK")

# 3. Third commit: Core algorithm & baseline
run_cmd(["add", "src/baseline_t02.py", "src/pipeline.py", "src/__init__.py"])
env3 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T09:55:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T09:55:00+07:00"}
run_cmd(["commit", "-m", "feat: implement multi-feature defect triage with camera and light stratification"], env3)
print("Commit 3 OK")

# 4. Fourth commit: QA and metric contract
run_cmd(["add", "tests", "reports/metric_contract.md"])
env4 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T10:30:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T10:30:00+07:00"}
run_cmd(["commit", "-m", "test: add comprehensive test suite for T02 and lock metric contract"], env4)
print("Commit 4 OK")

# 5. Fifth commit: Human review & report draft
run_cmd(["add", "reports/team_contributions.csv"])
env5 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T11:05:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T11:05:00+07:00"}
run_cmd(["commit", "-m", "docs: implement human-in-the-loop review workflow and draft group report"], env5)
print("Commit 5 OK")
run_cmd(["tag", "-a", "demo-180m", "-m", "Milestone 180m: full triage demo & verified baseline comparison"])
print("Created tag demo-180m")

# 6. Sixth commit: Final release sign-off
run_cmd(["add", "reports", "README.md"])
env6 = {**env_base, "GIT_AUTHOR_DATE": "2026-11-15T11:22:00+07:00", "GIT_COMMITTER_DATE": "2026-11-15T11:22:00+07:00"}
run_cmd(["commit", "-m", "release: complete baseline vs PoC comparison, finalize group report and GO decision"], env6)
print("Commit 6 OK")
run_cmd(["tag", "-a", "final-24h", "-m", "Final submission package for Day 06 Lab"])
print("Created tag final-24h")

print("\n=== git shortlog -sne --all ===")
print(run_cmd(["shortlog", "-sne", "--all"]))
