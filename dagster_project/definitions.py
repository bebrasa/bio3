"""Unified Dagster Definitions for all project pipelines."""

from dagster import Definitions, load_assets_from_modules

from dagster_project import hello_world, mapping_qc_pipeline

all_assets = load_assets_from_modules([hello_world, mapping_qc_pipeline])

defs = Definitions(
    assets=all_assets,
    jobs=[],
)
