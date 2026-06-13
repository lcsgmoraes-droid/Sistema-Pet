from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_repo_declares_node_22_runtime_contract():
    assert (ROOT / ".node-version").read_text(encoding="utf-8").strip() == "22"
    assert (ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "22"


def test_frontend_dockerfiles_use_node_22():
    dev_dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    prod_dockerfile = (ROOT / "frontend" / "Dockerfile.prod").read_text(
        encoding="utf-8"
    )

    assert "FROM node:22-alpine" in dev_dockerfile
    assert "FROM node:22-alpine AS builder" in prod_dockerfile
    assert "node:18" not in dev_dockerfile
    assert "node:20" not in prod_dockerfile


def test_github_actions_use_node_22():
    smoke_ci = (ROOT / ".github" / "workflows" / "smoke-ci.yml").read_text(
        encoding="utf-8"
    )
    eas_build = (ROOT / ".github" / "workflows" / "eas-build.yml").read_text(
        encoding="utf-8"
    )

    assert "node-version: 22" in smoke_ci
    assert "node-version: 22" in eas_build
    assert "node-version: 20" not in smoke_ci
    assert "node-version: 20" not in eas_build


def test_deploy_checks_node_before_git_reset():
    deploy_script = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )

    assert "Node.js incompativel para deploy" in deploy_script

    helper_definition = deploy_script.index("require_node_runtime()")
    helper_call = deploy_script.index("\nrequire_node_runtime\n", helper_definition)
    cd_app_dir = deploy_script.index('cd "$APP_DIR"')
    git_reset = deploy_script.index('git reset --hard "$REMOTE/$BRANCH"')

    assert helper_definition < helper_call < cd_app_dir < git_reset
