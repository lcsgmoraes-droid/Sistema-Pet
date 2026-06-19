import hashlib

import pytest

from app.bling_sync import snapshots


def test_snapshot_storage_candidates_are_internal_app_paths():
    candidates = snapshots._snapshot_storage_candidates()

    assert candidates
    assert all("tmp" not in str(candidate) for candidate in candidates)
    assert all("bling_snapshots" in str(candidate) for candidate in candidates)


def test_snapshot_file_path_hashes_tenant_component(monkeypatch, tmp_path):
    monkeypatch.setattr(snapshots, "_SNAPSHOT_STORAGE_BASE", tmp_path)

    tenant_hash = hashlib.sha256("tenant/123".encode("utf-8")).hexdigest()[:32]

    assert snapshots._snapshot_file_path("catalogo", "tenant/123") == (
        tmp_path / f"tenant_{tenant_hash}" / "catalogo.json"
    )


def test_snapshot_file_path_rejects_path_controlled_snapshot_names(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(snapshots, "_SNAPSHOT_STORAGE_BASE", tmp_path)

    with pytest.raises(ValueError):
        snapshots._snapshot_file_path("../catalogo", "tenant-123")
