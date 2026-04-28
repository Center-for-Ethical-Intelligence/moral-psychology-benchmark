"""Azure VM ephemeral GPU backend."""

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


class AzureBackend:
    name = "azure"

    def __init__(self) -> None:
        self._infra = load_config()

    def provision(self, config: RunConfig) -> Instance:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.network import NetworkManagementClient
        from azure.mgmt.resource import ResourceManagementClient

        credential = DefaultAzureCredential()
        subscription_id = self._get_subscription_id()
        location = config.region or self._infra.azure.region
        vm_size = resolve_instance_type("azure", config.gpu or self._infra.azure.gpu)

        run_id = uuid.uuid4().hex[:8]
        rg_name = f"cei-eval-{run_id}"
        vm_name = f"cei-vm-{run_id}"
        ip_name = f"cei-ip-{run_id}"
        nic_name = f"cei-nic-{run_id}"
        vnet_name = f"cei-vnet-{run_id}"
        subnet_name = "default"
        nsg_name = f"cei-nsg-{run_id}"

        resource_client = ResourceManagementClient(credential, subscription_id)
        network_client = NetworkManagementClient(credential, subscription_id)
        compute_client = ComputeManagementClient(credential, subscription_id)

        # Create resource group (enables clean teardown via group deletion)
        print(f"[azure] Creating resource group {rg_name} in {location}...")
        resource_client.resource_groups.create_or_update(rg_name, {"location": location})

        # Create network infrastructure
        print("[azure] Creating network...")
        nsg = network_client.network_security_groups.begin_create_or_update(
            rg_name, nsg_name, {
                "location": location,
                "security_rules": [{
                    "name": "SSH",
                    "protocol": "Tcp",
                    "source_port_range": "*",
                    "destination_port_range": "22",
                    "source_address_prefix": "*",
                    "destination_address_prefix": "*",
                    "access": "Allow",
                    "priority": 1000,
                    "direction": "Inbound",
                }],
            },
        ).result()

        vnet = network_client.virtual_networks.begin_create_or_update(
            rg_name, vnet_name, {
                "location": location,
                "address_space": {"address_prefixes": ["10.0.0.0/16"]},
                "subnets": [{"name": subnet_name, "address_prefix": "10.0.0.0/24",
                             "network_security_group": {"id": nsg.id}}],
            },
        ).result()

        subnet_id = vnet.subnets[0].id

        public_ip = network_client.public_ip_addresses.begin_create_or_update(
            rg_name, ip_name, {
                "location": location,
                "sku": {"name": "Standard"},
                "public_ip_allocation_method": "Static",
            },
        ).result()

        nic = network_client.network_interfaces.begin_create_or_update(
            rg_name, nic_name, {
                "location": location,
                "ip_configurations": [{
                    "name": "default",
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": public_ip.id},
                }],
            },
        ).result()

        # Read SSH public key
        ssh_key_path = Path(self._infra.azure.ssh_key).expanduser()
        pub_key_path = ssh_key_path.with_suffix(".pub")
        if pub_key_path.exists():
            ssh_pub_key = pub_key_path.read_text().strip()
        else:
            raise FileNotFoundError(f"SSH public key not found: {pub_key_path}")

        # Parse image reference
        image_ref = self._parse_image_ref()

        # Create VM
        print(f"[azure] Creating {vm_size} VM {vm_name}...")
        vm_params = {
            "location": location,
            "hardware_profile": {"vm_size": vm_size},
            "storage_profile": {
                "image_reference": image_ref,
                "os_disk": {
                    "create_option": "FromImage",
                    "disk_size_gb": 200,
                    "managed_disk": {"storage_account_type": "Premium_LRS"},
                },
            },
            "os_profile": {
                "computer_name": vm_name,
                "admin_username": "ubuntu",
                "linux_configuration": {
                    "disable_password_authentication": True,
                    "ssh": {
                        "public_keys": [{
                            "path": "/home/ubuntu/.ssh/authorized_keys",
                            "key_data": ssh_pub_key,
                        }],
                    },
                },
            },
            "network_profile": {
                "network_interfaces": [{"id": nic.id}],
            },
            "tags": {"Project": "cei", "ManagedBy": "cei-cli"},
        }

        if config.spot:
            vm_params["priority"] = "Spot"
            vm_params["eviction_policy"] = "Deallocate"

        compute_client.virtual_machines.begin_create_or_update(rg_name, vm_name, vm_params).result()

        # Get public IP
        public_ip = network_client.public_ip_addresses.get(rg_name, ip_name)
        host = public_ip.ip_address
        print(f"[azure] VM {vm_name} running at {host}")

        return Instance(
            instance_id=vm_name,
            provider="azure",
            host=host,
            user="ubuntu",
            metadata={
                "resource_group": rg_name,
                "subscription_id": subscription_id,
                "location": location,
            },
        )

    def upload(self, instance: Instance, local_path: Path) -> None:
        key_path = self._infra.azure.ssh_key
        wait_for_ssh(instance.host, user=instance.user, key_path=key_path)
        ssh_exec(instance.host, "mkdir -p ~/cei", user=instance.user, key_path=key_path, stream=False)
        rsync_upload(instance.host, local_path, "~/cei", user=instance.user, key_path=key_path)

    def run(self, instance: Instance, config: RunConfig) -> JobHandle:
        key_path = self._infra.azure.ssh_key
        handle = JobHandle(
            job_id=f"azure-{uuid.uuid4().hex[:8]}",
            instance=instance,
            config=config,
            status=JobStatus.RUNNING,
        )

        print("[azure] Installing dependencies...")
        ssh_exec(instance.host, SETUP_SCRIPT, user=instance.user, key_path=key_path)

        extra_flags = _build_extra_flags(config)
        env_exports = f'set -a; source ~/cei/{config.env_file} 2>/dev/null || true; set +a' if config.env_file else ""

        eval_script = EVAL_SCRIPT_TEMPLATE.format(
            task=config.task,
            model=config.model,
            extra_flags=" \\\n    ".join(extra_flags),
            env_exports=env_exports,
        )

        print("[azure] Running eval...")
        rc = ssh_exec(instance.host, eval_script, user=instance.user, key_path=key_path)
        handle.status = JobStatus.COMPLETED if rc == 0 else JobStatus.FAILED
        return handle

    def stream_logs(self, handle: JobHandle) -> None:
        key_path = self._infra.azure.ssh_key
        ssh_exec(
            handle.instance.host,
            "tail -f ~/cei/results/inspect/logs/*.log 2>/dev/null || echo 'No logs yet'",
            user=handle.instance.user, key_path=key_path,
        )

    def download_results(self, handle: JobHandle, local_path: Path) -> None:
        key_path = self._infra.azure.ssh_key
        scp_download(handle.instance.host, "~/cei/results/", local_path,
                     user=handle.instance.user, key_path=key_path)
        print(f"[azure] Results downloaded to {local_path}")

    def teardown(self, instance: Instance) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient

        rg_name = instance.metadata["resource_group"]
        subscription_id = instance.metadata["subscription_id"]
        credential = DefaultAzureCredential()
        client = ResourceManagementClient(credential, subscription_id)

        print(f"[azure] Deleting resource group {rg_name} (this removes all resources)...")
        client.resource_groups.begin_delete(rg_name)
        print(f"[azure] Resource group {rg_name} deletion initiated.")

    def status(self, handle: JobHandle) -> JobStatus:
        return handle.status

    def _get_subscription_id(self) -> str:
        import os
        sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
        if not sub_id:
            raise RuntimeError(
                "AZURE_SUBSCRIPTION_ID not set. "
                "Run: export AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)"
            )
        return sub_id

    def _parse_image_ref(self) -> dict:
        """Parse infra.yaml image string like 'publisher:offer:sku:version'."""
        image = self._infra.azure.image
        if not image:
            return {
                "publisher": "microsoft-dsvm",
                "offer": "ubuntu-hpc",
                "sku": "2204",
                "version": "latest",
            }
        parts = image.split(":")
        if len(parts) == 4:
            return {"publisher": parts[0], "offer": parts[1], "sku": parts[2], "version": parts[3]}
        # Assume it's an image ID
        return {"id": image}


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
