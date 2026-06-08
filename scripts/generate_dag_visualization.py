#!/usr/bin/env python3
"""Generate Dagster asset DAG visualization as PNG/SVG."""

from __future__ import annotations

import argparse
from pathlib import Path


def export_graphviz(
    asset_keys: list[str],
    dependencies: list[tuple[str, str]],
    output_path: Path,
    *,
    fmt: str = "png",
) -> Path:
    try:
        import graphviz
    except ImportError as exc:
        raise SystemExit(
            "graphviz Python package is required. Install with: pip install graphviz"
        ) from exc

    dot = graphviz.Digraph(
        "dagster_asset_graph",
        comment="Dagster mapping QC pipeline",
        format=fmt,
    )
    dot.attr(rankdir="LR", fontsize="12", label="Dagster Asset Graph (bioinf-hw3)")

    for key in sorted(asset_keys):
        dot.node(
            key,
            key,
            shape="box",
            style="rounded,filled",
            fillcolor="#e8f4fd",
        )

    for parent, child in dependencies:
        dot.edge(parent, child)

    rendered = dot.render(
        filename=output_path.stem,
        directory=str(output_path.parent),
        cleanup=True,
    )
    return Path(rendered)


def collect_assets_and_deps():
    from dagster_project.definitions import defs

    graph = defs.resolve_asset_graph()
    asset_keys = [key.to_user_string() for key in graph.get_all_asset_keys()]
    dependencies: list[tuple[str, str]] = []

    for key in graph.get_all_asset_keys():
        child = key.to_user_string()
        for parent_key in graph.get(key).parent_keys:
            dependencies.append((parent_key.to_user_string(), child))

    return asset_keys, dependencies


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Dagster asset DAG to image")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("results/dagster_pipeline/asset_dag.png"),
        help="Output image path",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "svg", "pdf"],
        help="Output format",
    )
    args = parser.parse_args()

    asset_keys, dependencies = collect_assets_and_deps()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = export_graphviz(asset_keys, dependencies, args.output, fmt=args.format)
    print(f"DAG visualization saved to: {result}")


if __name__ == "__main__":
    main()
