#!/usr/bin/env python3
import argparse
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_versions():
    api_source = (ROOT / "catalogue-api/src/openg2p_catalogue_service/__init__.py").read_text()
    api_version = re.search(r'__version__\s*=\s*"([^"]+)"', api_source).group(1)
    api_package_version = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (ROOT / "catalogue-api/pyproject.toml").read_text(),
        re.MULTILINE,
    ).group(1)
    # TOML is intentionally parsed without an extra runtime dependency.
    client_version = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (ROOT / "catalogue-client/pyproject.toml").read_text(),
        re.MULTILINE,
    ).group(1)
    chart = yaml.safe_load((ROOT / "deployments/charts/openg2p-catalogue/Chart.yaml").read_text())
    return {
        "api": api_version,
        "api_package": api_package_version,
        "client": client_version,
        "chart": str(chart["version"]),
        "chart_app": str(chart["appVersion"]),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate aligned Catalogue Service artifact versions.")
    parser.add_argument("--expected", help="Expected semantic version, optionally prefixed with v")
    args = parser.parse_args()
    versions = read_versions()
    expected = args.expected.removeprefix("v") if args.expected else versions["api"]
    mismatches = {name: value for name, value in versions.items() if value != expected}
    if mismatches:
        details = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise SystemExit(f"Release version mismatch; expected {expected}: {details}")
    print(f"All release artifacts use version {expected}")


if __name__ == "__main__":
    main()
