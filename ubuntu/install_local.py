"""Install this standalone folder into a new, user-owned Ubuntu project directory."""
from pathlib import Path
import shutil
import tempfile


def install_project(source, target):
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink():
        raise SystemExit(f"Already exists: {target}. Existing files were preserved.")
    required = ("run.sh", "setup.sh", "requirements.txt", "README.md", "install_local.py", "update_local.py",
                "vm-source/rest_api_controller.py", "vm-source/custom_topology.py",
                "experiments/grid_demo.py", "dashboard/serve.py")
    if not all((source / name).is_file() for name in required):
        raise SystemExit("Copy the complete ubuntu folder, not just the setup script.")
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        folder = Path(temp) / target.name
        folder.mkdir()
        for name in ("vm-source", "experiments", "dashboard", "c1"):
            shutil.copytree(source / name, folder / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", ".git"))
        for name in ("run.sh", "setup.sh", "requirements.txt", "README.md", "install_local.py", "update_local.py"):
            shutil.copyfile(source / name, folder / name)
        folder.rename(target)
    print(f"Ready: {target}")


def main():
    install_project(Path(__file__).resolve().parent, Path.home() / "sdn-project")


if __name__ == "__main__":
    main()
