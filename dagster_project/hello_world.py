"""Hello World test pipeline for Dagster."""

from dagster import Definitions, asset


@asset(description="Simple hello world asset for Dagster smoke test")
def hello_world_message() -> str:
    return "Hello, Dagster! Bioinformatics pipeline is ready."


@asset(deps=[hello_world_message], description="Greet using the hello world message")
def hello_world_greeting(hello_world_message: str) -> str:
    return f"{hello_world_message} Framework: Dagster. Mapper: minimap2. Platform: ONT."


defs = Definitions(assets=[hello_world_message, hello_world_greeting])
