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
        for name in ("vm-source", "experiments", "dashboard"):
            shutil.copytree(source / name, folder / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("run.sh", "README.md"):
            shutil.copyfile(source / "ubuntu" / name, folder / name)
        c1 = folder / "c1"
        c1.mkdir()
        controller = home / "sdn-lab/first_controller.py"
        if not controller.is_file():
            controller = source / "sdn-python-source-20261117-190113/first_controller.py"
        shutil.copyfile(controller, c1 / "first_controller.py")
        shutil.copyfile(source / "c1-linear-rerun.pcapng", c1 / "c1-linear-rerun.pcapng")
        folder.rename(target)
    print(f"Ready: {target}")


if __name__ == "__main__":
    main()
