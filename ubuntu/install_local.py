"""Copy the presentation and experiment files into a new, user-owned Ubuntu directory."""
from pathlib import Path
import shutil
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    home = Path.home()
    target = home / "sdn-project"
    if target.exists() or target.is_symlink():
        raise SystemExit(f"Already exists: {target}. Existing files were preserved.")
    manager = home / "sdn-lab/.venv/bin/osken-manager"
    if not manager.is_file():
        raise SystemExit(f"Existing OS-Ken installation missing: {manager}")
    with tempfile.TemporaryDirectory(dir=home) as temp:
        folder = Path(temp) / target.name
        folder.mkdir()
        for name in ("vm-source", "experiments", "dashboard", "c1", "output", "media", "ubuntu"):
            shutil.copytree(source / name, folder / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("run.sh", "README.md"):
            shutil.copyfile(source / "ubuntu" / name, folder / name)
        for name in ("requirements.txt", "AGENTS.md", "HANDOFF.md", "PLAN.md", "ISSUES_AND_RISKS.md", "WORK_LOG.md"):
            shutil.copyfile(source / name, folder / name)
        folder.rename(target)
    print(f"Ready: {target}")


if __name__ == "__main__":
    main()
