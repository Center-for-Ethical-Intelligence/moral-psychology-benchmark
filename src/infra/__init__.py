"""CEI Infrastructure — cloud GPU provisioning and Docker build/run."""

import sys


def main() -> None:
    """Entry point for `cei` console script."""
    # Import here to avoid circular imports at package level
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Delegate to the CLI module
    sys.argv[0] = "cei"

    # Re-use the main() from the cei script
    import importlib.util

    spec = importlib.util.spec_from_file_location("cei_cli", project_root / "cei")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.exit(mod.main())
