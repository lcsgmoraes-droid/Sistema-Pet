from pathlib import Path

import pytest

import app.bling_sync_routes as bling_sync_routes


def test_snapshot_storage_env_candidate_uses_only_allowlisted_container_paths():
    assert bling_sync_routes._snapshot_storage_env_candidate(
        "/app/data/bling_snapshots"
    ) == Path("/app/data/bling_snapshots")
    assert bling_sync_routes._snapshot_storage_env_candidate(
        " /app/uploads/bling_snapshots "
    ) == Path("/app/uploads/bling_snapshots")


def test_snapshot_storage_env_candidate_rejects_unapproved_paths():
    assert bling_sync_routes._snapshot_storage_env_candidate("/etc") is None
    assert (
        bling_sync_routes._snapshot_storage_env_candidate("../bling_snapshots") is None
    )


def test_snapshot_file_path_rejects_path_controlled_components(monkeypatch, tmp_path):
    monkeypatch.setattr(bling_sync_routes, "_SNAPSHOT_STORAGE_BASE", tmp_path)

    assert bling_sync_routes._snapshot_file_path("catalogo", "tenant-123") == (
        tmp_path / "tenant-123" / "catalogo.json"
    )

    with pytest.raises(ValueError):
        bling_sync_routes._snapshot_file_path("../catalogo", "tenant-123")

    with pytest.raises(ValueError):
        bling_sync_routes._snapshot_file_path("catalogo", "tenant/123")
