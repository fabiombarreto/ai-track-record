"""Remove the containers and networks left behind by a killed Harbor job.

Usage: python -m atr.ops.cleanup <job directory> [--all] [--dry-run]

When Harbor or Docker dies mid-trial, the trial's Compose projects keep their
containers and networks, and a resumed job starts the trial again beside them.
Harbor names each project after the trial (`<trial>__env`, `<trial>__verifier...`),
so this removes the projects of every trial in the job that has no result.json,
or of every trial with --all. Run it before `harbor job resume`.
"""

import argparse
import subprocess
from pathlib import Path


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout


def project_resources(kind: str) -> list[tuple[str, str]]:
    """(Compose project, id) of every container or network that belongs to a project."""
    listed = docker(
        kind,
        "ls" if kind == "network" else "ps",
        *(["-a"] if kind == "container" else []),
        "--filter",
        "label=com.docker.compose.project",
        "--format",
        '{{.Label "com.docker.compose.project"}} {{.ID}}',
    )
    return [tuple(line.split(" ", 1)) for line in listed.splitlines() if line.strip()]


def unfinished_trials(job_dir: Path, include_finished: bool) -> list[str]:
    return sorted(
        trial.name
        for trial in job_dir.iterdir()
        if trial.is_dir()
        and (trial / "config.json").exists()
        and (include_finished or not (trial / "result.json").exists())
    )


def cleanup(job_dir: Path, include_finished: bool = False, dry_run: bool = False) -> list[str]:
    prefixes = [f"{trial.lower()}__" for trial in unfinished_trials(job_dir, include_finished)]
    if not prefixes:
        return []
    removed = []
    for kind in ("container", "network"):
        for project, resource_id in project_resources(kind):
            if any(project.startswith(prefix) for prefix in prefixes):
                if not dry_run:
                    docker(kind, "rm", *(["-f"] if kind == "container" else []), resource_id)
                removed.append(f"{kind} {resource_id} ({project})")
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--all", action="store_true", help="also clean up finished trials")
    parser.add_argument("--dry-run", action="store_true", help="list without removing")
    args = parser.parse_args()
    removed = cleanup(args.job_dir, include_finished=args.all, dry_run=args.dry_run)
    verb = "would remove" if args.dry_run else "removed"
    print(f"{verb} {len(removed)} resource(s)")
    for line in removed:
        print(f"  {line}")


if __name__ == "__main__":
    main()
