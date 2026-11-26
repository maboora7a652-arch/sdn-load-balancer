"""Merge this release into Fouad's existing Ubuntu project without replacing results."""
import filecmp
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime


def copy_file(source, destination, project, owner=None, preserve_existing=False):
    source, destination, project = Path(source), Path(destination), Path(project)
    if not destination.resolve().is_relative_to(project.resolve()):
        raise ValueError("Destination leaves the local project: " + str(destination))
    if destination.is_symlink():
        raise ValueError("Refusing to replace a symlink: " + str(destination))
    if destination.exists():
        if filecmp.cmp(source, destination, shallow=False):
            return "unchanged"
        if preserve_existing:
            return "preserved"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if owner is not None:
        parent = destination.parent
        while parent != project.parent:
            os.chown(parent, *owner)
            if parent == project:
                break
            parent = parent.parent
    handle, temporary = tempfile.mkstemp(prefix=".sdn-update-", dir=destination.parent)
    try:
        with os.fdopen(handle, "wb") as stream, source.open("rb") as original:
            shutil.copyfileobj(original, stream)
        os.chmod(temporary, 0o755 if destination.name == "run.sh" else 0o644)
        if owner is not None:
            os.chown(temporary, *owner)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return "updated"


def backup_controller(source, current, backup_folder, owner=None):
    if not current.is_file() or filecmp.cmp(source, current, shallow=False):
        return None
    backup_folder.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("controller-before-sync-%Y%m%d-%H%M%S-%f.py")
    backup = backup_folder / name
    shutil.copy2(current, backup)
    os.chmod(backup, 0o644)
    if owner is not None:
        os.chown(backup_folder, *owner)
        os.chown(backup, *owner)
    # Retain only this updater's own backups; older manual checkpoints are untouched.
    for old in sorted(backup_folder.glob("controller-before-sync-*.py"), reverse=True)[3:]:
        if old.is_file() and not old.is_symlink():
            old.unlink()
    return backup


def main():
    if os.name != "posix":
        raise SystemExit("Run this updater on Ubuntu.")
    import pwd
    account = pwd.getpwnam(os.environ["SUDO_USER"]) if os.environ.get("SUDO_USER") else pwd.getpwuid(os.getuid())
    if account.pw_uid == 0:
        raise SystemExit("Use sudo from your normal Ubuntu account, not a root login.")
    home = Path(account.pw_dir)
    project = home / "sdn-project"
    if project.is_symlink() or not project.is_dir():
        raise SystemExit("Expected an existing regular directory: " + str(project))
    source = Path(__file__).resolve().parents[1]
    if source == project.resolve():
        raise SystemExit("Run the updater from the shared release, not the destination.")
    owner = (account.pw_uid, account.pw_gid) if os.geteuid() == 0 else None
    required = [source / "vm-source/rest_api_controller.py", source / "vm-source/custom_topology.py",
                source / "ubuntu/README.md", source / "ubuntu/run.sh"]
    if not all(p.is_file() for p in required):
        raise SystemExit("The shared release is missing a required source file.")
    backup = backup_controller(required[0], project / "vm-source/rest_api_controller.py", home / "sdn-backups", owner)
    if backup:
        print("Previous controller saved:", backup)
    counts = {"updated": 0, "unchanged": 0, "preserved": 0}
    mapping = [(source / "ubuntu/README.md", project / "README.md", False),
               (source / "ubuntu/run.sh", project / "run.sh", False)]
    for name in ("requirements.txt", "AGENTS.md", "HANDOFF.md", "PLAN.md", "ISSUES_AND_RISKS.md", "WORK_LOG.md"):
        if (source / name).is_file():
            mapping.append((source / name, project / name, False))
    for folder in ("vm-source", "experiments", "dashboard", "c1", "output", "media", "ubuntu"):
        root = source / folder
        if not root.is_dir():
            continue
        for item in root.rglob("*"):
            if not item.is_file() or item.is_symlink():
                continue
            relative = item.relative_to(source)
            if "__pycache__" in relative.parts or item.suffix == ".pyc":
                continue
            if "_success.py" in item.name or "_before_" in item.name:
                continue
            mapping.append((item, project / relative, relative.parts[:2] == ("experiments", "results")))
    for original, destination, preserve in mapping:
        outcome = copy_file(original, destination, project, owner, preserve)
        counts[outcome] += 1
        if outcome == "preserved":
            print("Kept differing local result:", destination.relative_to(project))
    print("Updated:", counts["updated"], "Unchanged:", counts["unchanged"], "Local results kept:", counts["preserved"])
    print("Ready:", project)
    print("README:", project / "README.md")
    print("The existing ~/sdn-lab/.venv and local results were preserved.")
    print("Restart the controller and Mininet before using changed Python code.")


if __name__ == "__main__":
    main()
