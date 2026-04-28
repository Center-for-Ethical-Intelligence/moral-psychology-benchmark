"""AWS EC2 ephemeral GPU backend."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from src.infra.backend import Instance, JobHandle, JobStatus, RunConfig
from src.infra.config import load_config
from src.infra.instance_types import resolve_instance_type
from src.infra.ssh import rsync_upload, scp_download, ssh_exec, wait_for_ssh


# Ubuntu 22.04 Deep Learning AMI (CUDA 12.x) — updated periodically
# Users should set this in infra.yaml or pass --gpu-image for their region.
DEFAULT_AMI_NAME_PATTERN = "Deep Learning AMI (Ubuntu 22.04)*"

SETUP_SCRIPT = """\
#!/bin/bash
set -euo pipefail

# Install uv if not present
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
    --log_dir results/inspect/logs \\
    {extra_flags}

echo "CEI eval complete."
"""


class AWSBackend:
    name = "aws"

    def __init__(self) -> None:
        self._infra = load_config()

    def provision(self, config: RunConfig) -> Instance:
        import boto3

        region = config.region or self._infra.aws.region
        ec2 = boto3.resource("ec2", region_name=region)
        client = boto3.client("ec2", region_name=region)

        instance_type = resolve_instance_type("aws", config.gpu or self._infra.aws.gpu)
        ami_id = self._resolve_ami(client, config)

        # Find or create security group with SSH access
        sg_id = self._ensure_security_group(client)

        key_name = self._infra.aws.ssh_key.split("/")[-1].replace(".pub", "").replace(".pem", "")

        tag_name = f"cei-eval-{uuid.uuid4().hex[:8]}"
        instances = ec2.create_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=key_name,
            SecurityGroupIds=[sg_id],
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": tag_name},
                    {"Key": "Project", "Value": "cei"},
                    {"Key": "ManagedBy", "Value": "cei-cli"},
                ],
            }],
            InstanceMarketOptions={"MarketType": "spot"} if config.spot else {},
            BlockDeviceMappings=[{
                "DeviceName": "/dev/sda1",
                "Ebs": {"VolumeSize": 200, "VolumeType": "gp3"},
            }],
        )

        ec2_instance = instances[0]
        print(f"[aws] Provisioning {instance_type} instance {ec2_instance.id} in {region}...")
        ec2_instance.wait_until_running()
        ec2_instance.reload()

        host = ec2_instance.public_ip_address
        print(f"[aws] Instance {ec2_instance.id} running at {host}")

        return Instance(
            instance_id=ec2_instance.id,
            provider="aws",
            host=host,
            user="ubuntu",
            metadata={"region": region, "instance_type": instance_type},
        )

    def upload(self, instance: Instance, local_path: Path) -> None:
        key_path = self._infra.aws.ssh_key
        wait_for_ssh(instance.host, user=instance.user, key_path=key_path)
        ssh_exec(instance.host, "mkdir -p ~/cei", user=instance.user, key_path=key_path, stream=False)
        rsync_upload(
            instance.host, local_path, "~/cei",
            user=instance.user, key_path=key_path,
        )

    def run(self, instance: Instance, config: RunConfig) -> JobHandle:
        key_path = self._infra.aws.ssh_key
        handle = JobHandle(
            job_id=f"aws-{uuid.uuid4().hex[:8]}",
            instance=instance,
            config=config,
            status=JobStatus.RUNNING,
        )

        # Setup
        print("[aws] Installing dependencies...")
        ssh_exec(instance.host, SETUP_SCRIPT, user=instance.user, key_path=key_path)

        # Build eval command
        extra_flags = []
        if config.temperature is not None:
            extra_flags.append(f"--temperature {config.temperature}")
        if config.limit is not None:
            extra_flags.append(f"--limit {config.limit}")
        if config.max_connections > 1:
            extra_flags.append(f"--max_connections {config.max_connections}")
        if config.no_sandbox:
            extra_flags.append("--no_sandbox")

        env_exports = ""
        if config.env_file:
            env_exports = f'set -a; source ~/cei/{config.env_file} 2>/dev/null || true; set +a'

        eval_script = EVAL_SCRIPT_TEMPLATE.format(
            task=config.task,
            model=config.model,
            extra_flags=" \\\n    ".join(extra_flags),
            env_exports=env_exports,
        )

        print("[aws] Running eval...")
        rc = ssh_exec(instance.host, eval_script, user=instance.user, key_path=key_path)
        handle.status = JobStatus.COMPLETED if rc == 0 else JobStatus.FAILED
        return handle

    def stream_logs(self, handle: JobHandle) -> None:
        key_path = self._infra.aws.ssh_key
        ssh_exec(
            handle.instance.host,
            "tail -f ~/cei/results/inspect/logs/*.log 2>/dev/null || echo 'No logs yet'",
            user=handle.instance.user, key_path=key_path,
        )

    def download_results(self, handle: JobHandle, local_path: Path) -> None:
        key_path = self._infra.aws.ssh_key
        scp_download(
            handle.instance.host, "~/cei/results/",
            local_path,
            user=handle.instance.user, key_path=key_path,
        )
        print(f"[aws] Results downloaded to {local_path}")

    def teardown(self, instance: Instance) -> None:
        import boto3

        region = instance.metadata.get("region", self._infra.aws.region)
        client = boto3.client("ec2", region_name=region)
        print(f"[aws] Terminating instance {instance.instance_id}...")
        client.terminate_instances(InstanceIds=[instance.instance_id])
        print(f"[aws] Instance {instance.instance_id} terminated.")

    def status(self, handle: JobHandle) -> JobStatus:
        return handle.status

    def _resolve_ami(self, client, config: RunConfig) -> str:
        """Find the latest Deep Learning AMI for the region."""
        image_id = self._infra.aws.image
        if image_id:
            return image_id

        response = client.describe_images(
            Owners=["amazon"],
            Filters=[
                {"Name": "name", "Values": [DEFAULT_AMI_NAME_PATTERN]},
                {"Name": "state", "Values": ["available"]},
            ],
        )
        images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
        if not images:
            raise RuntimeError("No Deep Learning AMI found. Set image in infra.yaml.")
        return images[0]["ImageId"]

    def _ensure_security_group(self, client) -> str:
        """Find or create a security group allowing SSH."""
        sg_name = "cei-eval-ssh"
        try:
            response = client.describe_security_groups(GroupNames=[sg_name])
            return response["SecurityGroups"][0]["GroupId"]
        except client.exceptions.ClientError:
            pass

        response = client.create_security_group(
            GroupName=sg_name,
            Description="CEI eval — SSH access",
        )
        sg_id = response["GroupId"]
        client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH"}],
            }],
        )
        return sg_id
