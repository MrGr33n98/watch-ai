from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_image_contains_alembic_migration_assets() -> None:
    dockerfile = (API_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose_file = (API_ROOT.parents[1] / "infra" / "docker-compose.yml").read_text(
        encoding="utf-8"
    )

    assert "COPY --chown=watchai:watchai alembic ./alembic" in dockerfile
    assert "COPY --chown=watchai:watchai alembic.ini ./alembic.ini" in dockerfile
    assert "MONTHLY_MODEL_BUDGET_USD:" in compose_file
