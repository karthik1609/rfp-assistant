"""
Cross-platform launcher that bootstraps the Docker runtime for the RFP Assistant.

This script performs a few guard checks before delegating to `docker compose`:

- Verify that Docker (Desktop or Engine) is available and reachable.
- Ensure the working `.env` file exists, copying from `.env_example` if needed.
- Run the equivalent of `docker compose up -d`, with optional build/pull flags.
- Optionally perform teardown (`--down`) or status checks (`--status`).

The file is designed to be packaged with PyInstaller for macOS/Linux binaries
and a Windows `.exe`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    env: Path
    env_example: Path
    compose: Path


def resolve_project_paths() -> ProjectPaths:
    """
    Attempt to locate the repository root by searching for docker-compose.yml.

    When packaged by PyInstaller, the real project files will be alongside the executable,
    so we search the current working directory as well as the bundle's temporary path.
    """
    search_roots = []
    if getattr(sys, "_MEIPASS", None):
        search_roots.append(Path(sys._MEIPASS))
    script_dir = Path(__file__).resolve().parent
    search_roots.extend([Path.cwd(), script_dir])

    visited = set()
    for start in search_roots:
        for candidate in [start, *start.parents]:
            if candidate in visited:
                continue
            visited.add(candidate)
            compose = candidate / "docker-compose.yml"
            if compose.is_file():
                return ProjectPaths(
                    root=candidate,
                    env=candidate / ".env",
                    env_example=candidate / ".env_example",
                    compose=compose,
                )

    raise LauncherError(
        "Unable to locate docker-compose.yml. Run the launcher from the project "
        "directory or alongside the release bundle."
    )


class LauncherError(RuntimeError):
    """Raised when the launcher hits a guard failure."""


def log(message: str) -> None:
    """Write a message to stdout with a common prefix."""
    print(f"[rfp-launcher] {message}")


def copy_env_file(paths: ProjectPaths) -> None:
    """Create `.env` by copying `.env_example` if the former does not exist."""
    if paths.env.exists():
        return
    if not paths.env_example.exists():
        raise LauncherError(
            "Missing .env and .env_example. Please supply required environment "
            "variables manually."
        )
    shutil.copy(paths.env_example, paths.env)
    log("Created .env from .env_example. Review and populate secrets before continuing.")


def detect_empty_env_keys(paths: ProjectPaths) -> List[str]:
    """Return env keys that have empty assignments in `.env`."""
    if not paths.env.exists():
        return []
    empty: List[str] = []
    for raw_line in paths.env.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not value:
            empty.append(key)
    return empty


def ensure_runtime_directories(paths: ProjectPaths) -> None:
    """Create directories that docker volumes expect to exist."""
    required = [
        paths.root / "output",
        paths.root / "output" / "docx",
        paths.root / "output" / "pdfs",
        paths.root / "backend" / "memory" / "data",
    ]
    for directory in required:
        directory.mkdir(parents=True, exist_ok=True)


def ensure_docker_available() -> None:
    """Check that Docker CLI and daemon are available."""
    docker_path = shutil.which("docker")
    if not docker_path:
        raise LauncherError(
            "Docker CLI not found on PATH. Install Docker Desktop (Windows/macOS) "
            "or Docker Engine (Linux) and ensure the `docker` command is available."
        )

    version_cmd = ["docker", "version", "--format", "{{.Server.Version}}"]
    try:
        completed = subprocess.run(
            version_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        server_version = completed.stdout.strip()
        if not server_version:
            raise LauncherError(
                "Docker daemon is not reachable. Start Docker Desktop / service and retry."
            )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        raise LauncherError(
            "Unable to communicate with Docker daemon. "
            "Start Docker Desktop (Windows/macOS) or the docker service (Linux)."
        ) from exc

    compose_cmd = ["docker", "compose", "version"]
    try:
        subprocess.run(compose_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise LauncherError(
            "Docker Compose v2 is required. Upgrade Docker Desktop or install "
            "docker-compose-plugin."
        ) from exc


def run_subprocess(
    paths: ProjectPaths, cmd: Iterable[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Execute a subprocess command with logging."""
    cmd_list = list(cmd)
    log(f"Executing: {' '.join(cmd_list)}")
    return subprocess.run(
        cmd_list,
        cwd=paths.root,
        check=check,
        text=True,
        capture_output=True,
    )


def docker_compose_up(paths: ProjectPaths, build: bool, pull: bool) -> None:
    """Run `docker compose up -d` with optional `--build` and `--pull`."""
    cmd: List[str] = ["docker", "compose", "-f", str(paths.compose), "up", "-d"]
    if pull:
        cmd.append("--pull")
    if build:
        cmd.append("--build")
    result = run_subprocess(paths, cmd, check=False)
    if result.returncode != 0:
        raise LauncherError(
            f"`docker compose up` failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )
    if result.stderr.strip():
        log(result.stderr.strip())
    if result.stdout.strip():
        log(result.stdout.strip())


def docker_compose_down(paths: ProjectPaths, remove_volumes: bool) -> None:
    """Run `docker compose down` to stop the stack."""
    cmd: List[str] = ["docker", "compose", "-f", str(paths.compose), "down"]
    if remove_volumes:
        cmd.append("--volumes")
    result = run_subprocess(paths, cmd, check=False)
    if result.returncode != 0:
        raise LauncherError(
            f"`docker compose down` failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )
    log("Docker stack stopped.")


def fetch_compose_status(paths: ProjectPaths) -> List[Tuple[str, str]]:
    """
    Retrieve service statuses from `docker compose ps`.

    Returns:
        List of (service, status) tuples.
    """
    json_cmd = [
        "docker",
        "compose",
        "-f",
        str(paths.compose),
        "ps",
        "--format",
        "json",
    ]
    completed = run_subprocess(paths, json_cmd, check=False)
    if completed.returncode == 0 and completed.stdout.strip():
        try:
            entries = json.loads(completed.stdout)
            return [
                (entry.get("Service", entry.get("Name", "unknown")), entry.get("State", "unknown"))
                for entry in entries
            ]
        except json.JSONDecodeError:
            pass

    # Fallback to plain-text parsing
    text_cmd = [
        "docker",
        "compose",
        "-f",
        str(paths.compose),
        "ps",
    ]
    completed = run_subprocess(paths, text_cmd, check=False)
    statuses: List[Tuple[str, str]] = []
    if completed.returncode != 0:
        return statuses
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 3:
            service = parts[0]
            status = " ".join(parts[2:])
            statuses.append((service, status))
    return statuses


def wait_for_services(paths: ProjectPaths, timeout: int) -> None:
    """Poll docker compose until services are running or healthy."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = fetch_compose_status(paths)
        if statuses:
            pending = [
                (svc, status)
                for svc, status in statuses
                if not status.lower().startswith(("up", "running"))
                and "healthy" not in status.lower()
            ]
            if not pending:
                log("All services report running/healthy.")
                for svc, status in statuses:
                    log(f"{svc}: {status}")
                return
            log(
                "Waiting for services: "
                + ", ".join(f"{svc} ({status})" for svc, status in pending)
            )
        time.sleep(5)
    raise LauncherError(
        "Timed out waiting for services to enter a running state. "
        "Inspect `docker compose logs` for details."
    )


def print_status(paths: ProjectPaths) -> None:
    """Display current docker compose service status."""
    statuses = fetch_compose_status(paths)
    if not statuses:
        log("No active services found. Did you run `docker compose up -d`?")
        return
    for svc, status in statuses:
        log(f"{svc}: {status}")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the RFP Assistant Docker stack."
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Force build of container images before starting.",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Always attempt to pull newer images before starting.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Skip waiting for containers to report running/healthy.",
    )
    parser.add_argument(
        "--down",
        action="store_true",
        help="Stop the stack instead of starting it.",
    )
    parser.add_argument(
        "--remove-volumes",
        action="store_true",
        help="Remove volumes when used with --down.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show service status after the main action completes.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for services to become ready (default: 180).",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    try:
        paths = resolve_project_paths()

        copy_env_file(paths)
        ensure_runtime_directories(paths)
        empty_keys = detect_empty_env_keys(paths)
        if empty_keys:
            log(
                "The following environment variables are currently empty in .env: "
                + ", ".join(empty_keys)
            )
            log("Update them before using the application for full functionality.")

        ensure_docker_available()

        if args.down:
            docker_compose_down(paths, remove_volumes=args.remove_volumes)
        else:
            docker_compose_up(paths, build=args.build, pull=args.pull)
            if not args.no_wait:
                wait_for_services(paths, timeout=args.timeout)

        if args.status or args.down:
            print_status(paths)

        if not args.down:
            log("Stack is running. Access frontend at http://localhost:8000/")
            log("Backend API is available at http://localhost:8001/docs")
        return 0
    except LauncherError as exc:
        log(f"ERROR: {exc}")
        return 1
    except KeyboardInterrupt:
        log("Aborted by user.")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

