"""SSH/SCP helpers for remote instance management."""

from __future__ import annotations

import io
import os
import stat
import subprocess
import time
from pathlib import Path


# Maximum retries waiting for SSH to become available after provisioning
SSH_READY_MAX_RETRIES = 30
SSH_READY_INTERVAL = 10  # seconds


def wait_for_ssh(host: str, port: int = 22, user: str = "ubuntu",
                 key_path: str = "~/.ssh/id_ed25519",
                 max_retries: int = SSH_READY_MAX_RETRIES) -> None:
    """Block until SSH is reachable on the remote host."""
    key = os.path.expanduser(key_path)
    for attempt in range(1, max_retries + 1):
        result = subprocess.run(
            [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                "-i", key,
                "-p", str(port),
                f"{user}@{host}",
                "echo ok",
            ],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"[ssh] Connected to {host} (attempt {attempt})")
            return
        print(f"[ssh] Waiting for {host}... ({attempt}/{max_retries})")
        time.sleep(SSH_READY_INTERVAL)
    raise TimeoutError(f"SSH not reachable on {host}:{port} after {max_retries * SSH_READY_INTERVAL}s")


def ssh_exec(host: str, command: str, port: int = 22, user: str = "ubuntu",
             key_path: str = "~/.ssh/id_ed25519", stream: bool = True) -> int:
    """Execute a command on a remote host via SSH. Returns exit code."""
    key = os.path.expanduser(key_path)
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", key,
        "-p", str(port),
        f"{user}@{host}",
        command,
    ]

    if stream:
        result = subprocess.run(ssh_cmd)
    else:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)

    return result.returncode


def scp_upload(host: str, local_path: Path, remote_path: str,
               port: int = 22, user: str = "ubuntu",
               key_path: str = "~/.ssh/id_ed25519") -> None:
    """Upload a file or directory to a remote host via SCP."""
    key = os.path.expanduser(key_path)
    cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", key,
        "-P", str(port),
        "-r",
        str(local_path),
        f"{user}@{host}:{remote_path}",
    ]
    print(f"[scp] Uploading {local_path} → {host}:{remote_path}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"SCP upload failed: {local_path} → {host}:{remote_path}")


def scp_download(host: str, remote_path: str, local_path: Path,
                 port: int = 22, user: str = "ubuntu",
                 key_path: str = "~/.ssh/id_ed25519") -> None:
    """Download a file or directory from a remote host via SCP."""
    key = os.path.expanduser(key_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", key,
        "-P", str(port),
        "-r",
        f"{user}@{host}:{remote_path}",
        str(local_path),
    ]
    print(f"[scp] Downloading {host}:{remote_path} → {local_path}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"SCP download failed: {host}:{remote_path} → {local_path}")


def rsync_upload(host: str, local_path: Path, remote_path: str,
                 port: int = 22, user: str = "ubuntu",
                 key_path: str = "~/.ssh/id_ed25519",
                 exclude: list[str] | None = None) -> None:
    """Upload via rsync (faster for large directories with .gitignore patterns)."""
    key = os.path.expanduser(key_path)
    cmd = [
        "rsync", "-avz", "--progress",
        "-e", f"ssh -o StrictHostKeyChecking=no -i {key} -p {port}",
    ]
    for pattern in (exclude or []):
        cmd += ["--exclude", pattern]
    # Default excludes for CEI project
    cmd += [
        "--exclude", ".git",
        "--exclude", "__pycache__",
        "--exclude", ".venv",
        "--exclude", "results/",
        "--exclude", "*.pyc",
    ]
    cmd += [f"{local_path}/", f"{user}@{host}:{remote_path}/"]
    print(f"[rsync] Uploading {local_path} → {host}:{remote_path}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"rsync upload failed: {local_path} → {host}:{remote_path}")
