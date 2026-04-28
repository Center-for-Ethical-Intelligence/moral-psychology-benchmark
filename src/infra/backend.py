"""Abstract backend protocol and shared dataclasses for CEI eval runs."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


class JobStatus(enum.Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class RunConfig:
    """Configuration for a single eval run."""

    task: str  # e.g. "evals/unimoral.py" or "evals/ethics.py::commonsense"
    model: str  # e.g. "hf/Qwen/Qwen3-8B" or "openrouter/qwen/qwen3-8b"
    backend: str  # "local", "docker", "aws", "gcp", "azure"
    gpu: str = ""  # instance type override (e.g. "g5.xlarge")
    region: str = ""  # region override
    temperature: float | None = None
    limit: int | None = None
    max_connections: int = 1
    max_runtime_hours: float = 4.0
    spot: bool = False  # use spot/preemptible instances
    no_sandbox: bool = True
    extra_args: list[str] = field(default_factory=list)
    data_dir: str = ""  # path to benchmark data on local machine
    env_file: str = ".env"


@dataclass
class Instance:
    """Represents a provisioned compute instance."""

    instance_id: str
    provider: str  # "aws", "gcp", "azure", "docker", "local"
    host: str = ""  # SSH-reachable hostname or IP
    port: int = 22
    user: str = "ubuntu"
    status: JobStatus = JobStatus.PENDING
    metadata: dict = field(default_factory=dict)


@dataclass
class JobHandle:
    """Handle to a running or completed eval job."""

    job_id: str
    instance: Instance
    config: RunConfig
    status: JobStatus = JobStatus.PENDING
    log_path: str = ""
    results_path: str = ""
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class Backend(Protocol):
    """Protocol that all compute backends must implement."""

    name: str

    def provision(self, config: RunConfig) -> Instance:
        """Provision a compute instance (no-op for local/docker)."""
        ...

    def upload(self, instance: Instance, local_path: Path) -> None:
        """Upload project files to the instance."""
        ...

    def run(self, instance: Instance, config: RunConfig) -> JobHandle:
        """Execute the eval command on the instance."""
        ...

    def stream_logs(self, handle: JobHandle) -> None:
        """Stream logs from a running job to stdout."""
        ...

    def download_results(self, handle: JobHandle, local_path: Path) -> None:
        """Download results from the instance to local."""
        ...

    def teardown(self, instance: Instance) -> None:
        """Terminate and clean up the instance."""
        ...

    def status(self, handle: JobHandle) -> JobStatus:
        """Check the current status of a job."""
        ...


def get_backend(name: str) -> Backend:
    """Factory: return a Backend instance by name."""
    if name == "local":
        from src.infra.local_backend import LocalBackend

        return LocalBackend()
    if name == "docker":
        from src.infra.docker_backend import DockerBackend

        return DockerBackend()
    if name == "aws":
        from src.infra.aws import AWSBackend

        return AWSBackend()
    if name == "gcp":
        from src.infra.gcp import GCPBackend

        return GCPBackend()
    if name == "azure":
        from src.infra.azure import AzureBackend

        return AzureBackend()
    raise ValueError(f"Unknown backend: {name!r}. Choose from: local, docker, aws, gcp, azure")
