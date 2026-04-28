"""GCP Compute Engine ephemeral GPU backend."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from src.infra.backend import Instance, JobHandle, JobStatus, RunConfig
from src.infra.config import load_config
from src.infra.instance_types import resolve_instance_type
from src.infra.ssh import rsync_upload, scp_download, ssh_exec, wait_for_ssh


SETUP_SCRIPT = """\
#!/bin/bash
set -euo pipefail
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
cd ~/cei
uv sync --frozen --no-dev
echo "CEI setup complete."
"""

EVAL_SCRIPT_TEMPLATE = """\
#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd ~/cei
{env_exports}
uv run --package cei-inspect python src/inspect/run.py \\
    --tasks {task} \\
    --model {model} \\
    {extra_flags}
echo "CEI eval complete."
"""


class GCPBackend:
    name = "gcp"

    def __init__(self) -> None:
        self._infra = load_config()

    def provision(self, config: RunConfig) -> Instance:
        from google.cloud import compute_v1

        zone = config.region or self._infra.gcp.region
        project = self._get_project()
        instance_type = resolve_instance_type("gcp", config.gpu or self._infra.gcp.gpu)
        name = f"cei-eval-{uuid.uuid4().hex[:8]}"

        client = compute_v1.InstancesClient()

        # Build instance config
        instance_resource = compute_v1.Instance(
            name=name,
            machine_type=f"zones/{zone}/machineTypes/{instance_type}",
            disks=[
                compute_v1.AttachedDisk(
                    auto_delete=True,
                    boot=True,
                    initialize_params=compute_v1.AttachedDiskInitializeParams(
                        source_image=self._infra.gcp.image,
                        disk_size_gb=200,
                        disk_type=f"zones/{zone}/diskTypes/pd-ssd",
                    ),
                )
            ],
            network_interfaces=[
                compute_v1.NetworkInterface(
                    access_configs=[
                        compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT"),
                    ],
                )
            ],
            labels={"project": "cei", "managed-by": "cei-cli"},
            scheduling=compute_v1.Scheduling(
                preemptible=config.spot,
            ),
        )

        print(f"[gcp] Creating {instance_type} instance {name} in {zone}...")
        operation = client.insert(project=project, zone=zone, instance_resource=instance_resource)
        _wait_for_operation(project, zone, operation.name)

        # Get the instance to find its external IP
        instance = client.get(project=project, zone=zone, instance=name)
        host = instance.network_interfaces[0].access_configs[0].nat_i_p
        print(f"[gcp] Instance {name} running at {host}")

        return Instance(
            instance_id=name,
            provider="gcp",
            host=host,
            user="ubuntu",
            metadata={"project": project, "zone": zone},
        )

    def upload(self, instance: Instance, local_path: Path) -> None:
        key_path = self._infra.gcp.ssh_key
        wait_for_ssh(instance.host, user=instance.user, key_path=key_path)
        ssh_exec(instance.host, "mkdir -p ~/cei", user=instance.user, key_path=key_path, stream=False)
        rsync_upload(instance.host, local_path, "~/cei", user=instance.user, key_path=key_path)

    def run(self, instance: Instance, config: RunConfig) -> JobHandle:
        key_path = self._infra.gcp.ssh_key
        handle = JobHandle(
            job_id=f"gcp-{uuid.uuid4().hex[:8]}",
            instance=instance,
            config=config,
            status=JobStatus.RUNNING,
        )

        print("[gcp] Installing dependencies...")
        ssh_exec(instance.host, SETUP_SCRIPT, user=instance.user, key_path=key_path)

        extra_flags = _build_extra_flags(config)
        env_exports = f'set -a; source ~/cei/{config.env_file} 2>/dev/null || true; set +a' if config.env_file else ""

        eval_script = EVAL_SCRIPT_TEMPLATE.format(
            task=config.task,
            model=config.model,
            extra_flags=" \\\n    ".join(extra_flags),
            env_exports=env_exports,
        )

        print("[gcp] Running eval...")
        rc = ssh_exec(instance.host, eval_script, user=instance.user, key_path=key_path)
        handle.status = JobStatus.COMPLETED if rc == 0 else JobStatus.FAILED
        return handle

    def stream_logs(self, handle: JobHandle) -> None:
        key_path = self._infra.gcp.ssh_key
        ssh_exec(
            handle.instance.host,
            "tail -f ~/cei/results/inspect/logs/*.log 2>/dev/null || echo 'No logs yet'",
            user=handle.instance.user, key_path=key_path,
        )

    def download_results(self, handle: JobHandle, local_path: Path) -> None:
        key_path = self._infra.gcp.ssh_key
        scp_download(handle.instance.host, "~/cei/results/", local_path,
                     user=handle.instance.user, key_path=key_path)
        print(f"[gcp] Results downloaded to {local_path}")

    def teardown(self, instance: Instance) -> None:
        from google.cloud import compute_v1

        project = instance.metadata["project"]
        zone = instance.metadata["zone"]
        client = compute_v1.InstancesClient()

        print(f"[gcp] Deleting instance {instance.instance_id}...")
        operation = client.delete(project=project, zone=zone, instance=instance.instance_id)
        print(f"[gcp] Instance {instance.instance_id} deletion initiated.")

    def status(self, handle: JobHandle) -> JobStatus:
        return handle.status

    def _get_project(self) -> str:
        import subprocess
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True,
        )
        project = result.stdout.strip()
        if not project:
            raise RuntimeError("No GCP project set. Run: gcloud config set project <PROJECT_ID>")
        return project


def _wait_for_operation(project: str, zone: str, operation_name: str) -> None:
    from google.cloud import compute_v1
    client = compute_v1.ZoneOperationsClient()
    while True:
        op = client.get(project=project, zone=zone, operation=operation_name)
        if op.status == compute_v1.Operation.Status.DONE:
            if op.error:
                raise RuntimeError(f"GCP operation failed: {op.error}")
            return
        time.sleep(5)


def _build_extra_flags(config: RunConfig) -> list[str]:
    flags = []
    if config.temperature is not None:
        flags.append(f"--temperature {config.temperature}")
    if config.limit is not None:
        flags.append(f"--limit {config.limit}")
    if config.max_connections > 1:
        flags.append(f"--max_connections {config.max_connections}")
    if config.no_sandbox:
        flags.append("--no_sandbox")
    flags.append("--log_dir results/inspect/logs")
    return flags
