"""Docker backend — build, push, and run GPU-enabled eval containers."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from src.infra.backend import Instance, JobHandle, JobStatus, RunConfig
from src.infra.config import DockerConfig, load_config


class DockerBackend:
    name = "docker"

    def __init__(self) -> None:
        self._config = load_config().docker

    def provision(self, config: RunConfig) -> Instance:
        return Instance(
            instance_id=f"docker-{uuid.uuid4().hex[:8]}",
            provider="docker",
            host="localhost",
        )

    def upload(self, instance: Instance, local_path: Path) -> None:
        pass  # Docker build copies files into the image

    def run(self, instance: Instance, config: RunConfig) -> JobHandle:
        handle = JobHandle(
            job_id=f"docker-{uuid.uuid4().hex[:8]}",
            instance=instance,
            config=config,
            status=JobStatus.RUNNING,
        )

        cmd = _build_docker_run_cmd(config, self._config)
        print(f"[docker] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=_project_root())

        handle.status = JobStatus.COMPLETED if result.returncode == 0 else JobStatus.FAILED
        return handle

    def stream_logs(self, handle: JobHandle) -> None:
        pass  # logs go to stdout via docker run

    def download_results(self, handle: JobHandle, local_path: Path) -> None:
        pass  # results mounted via volume

    def teardown(self, instance: Instance) -> None:
        pass

    def status(self, handle: JobHandle) -> JobStatus:
        return handle.status


def build_image(
    dockerfile: str = "Dockerfile.gpu",
    target: str = "full",
    tag: str = "",
    registry: str = "",
    image_name: str = "cei-eval",
) -> str:
    """Build a Docker image and return the full tag."""
    if not tag:
        tag = "latest"

    full_tag = f"{registry}/{image_name}:{tag}" if registry else f"{image_name}:{tag}"

    cmd = [
        "docker", "build",
        "-f", dockerfile,
        "--target", target,
        "-t", full_tag,
        ".",
    ]
    print(f"[docker] Building: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=_project_root())
    if result.returncode != 0:
        raise RuntimeError(f"Docker build failed with exit code {result.returncode}")
    return full_tag


def push_image(full_tag: str) -> None:
    """Push a Docker image to the registry."""
    cmd = ["docker", "push", full_tag]
    print(f"[docker] Pushing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Docker push failed with exit code {result.returncode}")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_docker_run_cmd(config: RunConfig, docker_config: DockerConfig) -> list[str]:
    """Build the docker run command for an eval."""
    image = docker_config.image_name
    if docker_config.registry:
        image = f"{docker_config.registry}/{image}"
    image += ":latest"

    cmd = ["docker", "run", "--rm"]

    # GPU support
    cmd += ["--gpus", "all"]

    # Mount env file
    env_path = _project_root() / config.env_file
    if env_path.exists():
        cmd += ["--env-file", str(env_path)]

    # Mount results volume
    cmd += ["-v", f"{_project_root() / 'results'}:/app/results"]

    # Mount data directory if specified
    if config.data_dir:
        cmd += ["-v", f"{config.data_dir}:/data"]

    # Mount HF cache
    hf_cache = Path.home() / ".cache" / "huggingface"
    if hf_cache.exists():
        cmd += ["-v", f"{hf_cache}:/root/.cache/huggingface"]

    cmd.append(image)

    # Eval command inside container
    eval_cmd = _container_eval_cmd(config)
    cmd.extend(eval_cmd)

    return cmd


def _container_eval_cmd(config: RunConfig) -> list[str]:
    """Build the eval command to run inside the container."""
    if config.task.endswith(".py") or "::" in config.task:
        cmd = [
            "src/inspect/run.py",
            "--tasks", config.task,
            "--model", config.model,
            "--log_dir", "/app/results/inspect/logs",
        ]
        if config.temperature is not None:
            cmd += ["--temperature", str(config.temperature)]
        if config.limit is not None:
            cmd += ["--limit", str(config.limit)]
        if config.max_connections > 1:
            cmd += ["--max_connections", str(config.max_connections)]
        if config.no_sandbox:
            cmd.append("--no_sandbox")
    else:
        cmd = [
            "src/lm-evaluation-harness/run.py",
            "--tasks", config.task,
        ]
        if config.model.startswith("hf/"):
            model_name = config.model[3:]
            cmd += ["--model", "hf", "--model_args", f"pretrained={model_name}"]
        if config.limit is not None:
            cmd += ["--limit", str(config.limit)]

    cmd += config.extra_args
    return cmd
