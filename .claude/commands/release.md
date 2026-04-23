# Build Release Artifacts

Rebuild the release package: CSVs, SVG charts, reports, and manifest.

## Instructions

1. Run the release build:
   ```bash
   make release
   ```
2. If `make` fails (e.g., `uv` not installed), fall back to:
   ```bash
   python scripts/build_release_artifacts.py
   ```
3. Verify the outputs exist:
   - `results/release/2026-04-19-option1/` — CSVs, reports, manifest
   - `figures/release/` — SVG charts
4. Run the audit:
   ```bash
   make audit
   ```
5. Report which artifacts were generated and whether audit passed
