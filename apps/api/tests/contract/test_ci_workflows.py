from __future__ import annotations

import re
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_DIRECTORY = REPOSITORY_ROOT / ".github" / "workflows"
ACTION_SHA_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[0-9a-f]{40}$"
)


def _read_workflow(filename: str) -> dict[str, object]:
    document = yaml.safe_load((WORKFLOW_DIRECTORY / filename).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_ci_workflows_cover_backend_wear_and_security_without_provider_secrets() -> None:
    filenames = {"backend-ci.yml", "wear-ci.yml", "security.yml"}
    assert filenames.issubset({path.name for path in WORKFLOW_DIRECTORY.glob("*.yml")})

    workflows = {filename: _read_workflow(filename) for filename in filenames}
    for workflow in workflows.values():
        assert workflow["permissions"]["contents"] == "read"
        assert set(workflow["permissions"].values()) == {"read"}
        assert set(workflow[True]) == {"push", "pull_request", "workflow_dispatch"}
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    assert ACTION_SHA_PATTERN.fullmatch(step["uses"]), step["uses"]

    backend = str(workflows["backend-ci.yml"])
    assert "uv sync --locked --all-groups" in backend
    assert "uv run pytest -q --cov=app" in backend
    assert "uv run ruff check ." in backend
    assert "uv run mypy app" in backend

    wear = str(workflows["wear-ci.yml"])
    assert "testDebugUnitTest" in wear
    assert "assembleDebug" in wear
    assert "compileDebugAndroidTestKotlin" in wear
    assert "upload-artifact" in wear

    security = str(workflows["security.yml"])
    assert "pip-audit" in security
    assert "--no-emit-project" in security
    assert "--disable-pip --require-hashes" in security
    assert "gitleaks/gitleaks-action" in security
    assert "OPENROUTER_API_KEY" not in security
    assert "WAHA_API_KEY" not in security


def test_wear_ci_installs_the_stable_sdk_selected_by_the_app() -> None:
    app_gradle = (REPOSITORY_ROOT / "apps" / "wear" / "app" / "build.gradle.kts").read_text(
        encoding="utf-8"
    )
    wear_workflow = (WORKFLOW_DIRECTORY / "wear-ci.yml").read_text(encoding="utf-8")

    assert "compileSdk = 36" in app_gradle
    assert 'platforms;android-36 build-tools;36.0.0' in wear_workflow


def test_agp_9_uses_builtin_kotlin_and_the_compose_compiler_plugin() -> None:
    root_gradle = (REPOSITORY_ROOT / "apps" / "wear" / "build.gradle.kts").read_text(
        encoding="utf-8"
    )
    app_gradle = (REPOSITORY_ROOT / "apps" / "wear" / "app" / "build.gradle.kts").read_text(
        encoding="utf-8"
    )

    assert "org.jetbrains.kotlin.android" not in root_gradle + app_gradle
    assert "kotlinOptions" not in app_gradle
    assert 'id("org.jetbrains.kotlin.plugin.compose")' in app_gradle
