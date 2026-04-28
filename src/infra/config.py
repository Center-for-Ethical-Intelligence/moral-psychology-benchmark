"""Load infra.yaml configuration with environment variable overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "infra.yaml"


@dataclass(frozen=True)
class DockerConfig:
    registry: str = ""
    image_name: str = "cei-eval"
    dockerfile: str = "Dockerfile.gpu"


@dataclass(frozen=True)
class ProviderDefaults:
    region: str = ""
    gpu: str = ""
    image: str = ""
    ssh_key: str = "~/.ssh/id_ed25519"


@dataclass(frozen=True)
class InfraConfig:
    aws: ProviderDefaults = field(default_factory=lambda: ProviderDefaults(
        region="us-east-1",
        gpu="g5.xlarge",
        image="",  # resolved at runtime via AWS Deep Learning AMI lookup
    ))
    gcp: ProviderDefaults = field(default_factory=lambda: ProviderDefaults(
        region="us-central1-a",
        gpu="g2-standard-4",
        image="projects/deeplearning-platform-release/global/images/family/pytorch-latest-gpu",
    ))
    azure: ProviderDefaults = field(default_factory=lambda: ProviderDefaults(
        region="eastus",
        gpu="Standard_NC4as_T4_v3",
        image="microsoft-dsvm:ubuntu-hpc:2204:latest",
    ))
    docker: DockerConfig = field(default_factory=DockerConfig)
    max_runtime_hours: float = 4.0


def _env_or(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _parse_provider(raw: dict) -> ProviderDefaults:
    return ProviderDefaults(
        region=str(raw.get("region", "")),
        gpu=str(raw.get("gpu", "")),
        image=str(raw.get("image", "")),
        ssh_key=str(raw.get("ssh_key", "~/.ssh/id_ed25519")),
    )


def load_config(path: Path | None = None) -> InfraConfig:
    """Load infra.yaml, falling back to built-in defaults."""
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        return InfraConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    defaults = raw.get("defaults", {})

    # Parse provider sections
    aws_raw = defaults.get("aws", {})
    gcp_raw = defaults.get("gcp", {})
    azure_raw = defaults.get("azure", {})
    docker_raw = defaults.get("docker", {})

    # Apply env var overrides
    aws = ProviderDefaults(
        region=_env_or("AWS_REGION", aws_raw.get("region", "us-east-1")),
        gpu=aws_raw.get("gpu", "g5.xlarge"),
        image=aws_raw.get("image", ""),
        ssh_key=_env_or("CEI_SSH_KEY", aws_raw.get("ssh_key", "~/.ssh/id_ed25519")),
    )
    gcp = ProviderDefaults(
        region=_env_or("GCP_ZONE", gcp_raw.get("region", "us-central1-a")),
        gpu=gcp_raw.get("gpu", "g2-standard-4"),
        image=gcp_raw.get("image", "projects/deeplearning-platform-release/global/images/family/pytorch-latest-gpu"),
        ssh_key=_env_or("CEI_SSH_KEY", gcp_raw.get("ssh_key", "~/.ssh/id_ed25519")),
    )
    azure = ProviderDefaults(
        region=_env_or("AZURE_REGION", azure_raw.get("region", "eastus")),
        gpu=azure_raw.get("gpu", "Standard_NC4as_T4_v3"),
        image=azure_raw.get("image", "microsoft-dsvm:ubuntu-hpc:2204:latest"),
        ssh_key=_env_or("CEI_SSH_KEY", azure_raw.get("ssh_key", "~/.ssh/id_ed25519")),
    )
    docker = DockerConfig(
        registry=_env_or("CEI_DOCKER_REGISTRY", docker_raw.get("registry", "")),
        image_name=docker_raw.get("image_name", "cei-eval"),
        dockerfile=docker_raw.get("dockerfile", "Dockerfile.gpu"),
    )

    return InfraConfig(
        aws=aws,
        gcp=gcp,
        azure=azure,
        docker=docker,
        max_runtime_hours=float(defaults.get("max_runtime_hours", 4.0)),
    )
