"""GPU instance type mappings per cloud provider."""

from __future__ import annotations

# Tiered GPU instances: small (inference), medium (fine-tuning), large (multi-GPU)
GPU_INSTANCES: dict[str, dict[str, str]] = {
    "aws": {
        "small": "g5.xlarge",       # 1x A10G 24GB, 4 vCPU, 16GB RAM — ~$1.01/hr
        "medium": "g5.2xlarge",     # 1x A10G 24GB, 8 vCPU, 32GB RAM — ~$1.21/hr
        "large": "g5.12xlarge",     # 4x A10G 96GB, 48 vCPU, 192GB RAM — ~$5.67/hr
        "xlarge": "p4d.24xlarge",   # 8x A100 40GB, 96 vCPU, 1.1TB RAM — ~$32.77/hr
    },
    "gcp": {
        "small": "g2-standard-4",         # 1x L4 24GB, 4 vCPU, 16GB RAM — ~$0.70/hr
        "medium": "g2-standard-8",        # 1x L4 24GB, 8 vCPU, 32GB RAM — ~$0.91/hr
        "large": "a2-highgpu-1g",         # 1x A100 40GB, 12 vCPU, 85GB RAM — ~$3.67/hr
        "xlarge": "a2-highgpu-8g",        # 8x A100 40GB, 96 vCPU, 680GB RAM — ~$29.39/hr
    },
    "azure": {
        "small": "Standard_NC4as_T4_v3",    # 1x T4 16GB, 4 vCPU, 28GB RAM — ~$0.53/hr
        "medium": "Standard_NC8as_T4_v3",   # 1x T4 16GB, 8 vCPU, 56GB RAM — ~$0.75/hr
        "large": "Standard_NC6s_v3",        # 1x V100 16GB, 6 vCPU, 112GB RAM — ~$3.06/hr
        "xlarge": "Standard_ND96asr_v4",    # 8x A100 40GB, 96 vCPU, 900GB RAM — ~$27.20/hr
    },
}

# Spot/preemptible discount estimates (approximate)
SPOT_DISCOUNT: dict[str, float] = {
    "aws": 0.3,    # ~70% discount
    "gcp": 0.35,   # ~65% discount
    "azure": 0.4,  # ~60% discount
}


def resolve_instance_type(provider: str, gpu: str) -> str:
    """Resolve a GPU spec to a concrete instance type.

    Accepts either a tier name ("small", "medium", "large", "xlarge")
    or a literal instance type (e.g. "g5.xlarge").
    """
    provider_types = GPU_INSTANCES.get(provider, {})
    if gpu in provider_types:
        return provider_types[gpu]
    # Assume it's a literal instance type
    return gpu


def list_instance_types(provider: str) -> dict[str, str]:
    """Return available GPU tiers for a provider."""
    return dict(GPU_INSTANCES.get(provider, {}))
