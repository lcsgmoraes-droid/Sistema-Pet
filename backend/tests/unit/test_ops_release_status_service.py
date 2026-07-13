import json

from app.services import ops_release_status_service as service


def test_release_status_returns_healthy_safe_summary(tmp_path, monkeypatch):
    path = tmp_path / "release_status.json"
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-13T20:00:00Z",
                "status": "passed",
                "repository": "owner/repo",
                "commit_sha": "a" * 40,
                "checks_url": "https://github.com/owner/repo/commit/abc/checks",
                "required_checks": [
                    {
                        "name": "Quality Gate",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(service, "RELEASE_STATUS_PATH", str(path))

    result = service.summarize_release_status()

    assert result["status"] == "healthy"
    assert result["commit_sha"] == "a" * 40
    assert result["passed_checks"] == 1
    assert result["total_checks"] == 1


def test_release_status_fails_closed_when_required_check_did_not_pass(
    tmp_path, monkeypatch
):
    path = tmp_path / "release_status.json"
    path.write_text(
        json.dumps(
            {
                "status": "passed",
                "repository": "owner/repo",
                "commit_sha": "b" * 40,
                "required_checks": [
                    {
                        "name": "Quality Gate",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(service, "RELEASE_STATUS_PATH", str(path))

    result = service.summarize_release_status()

    assert result["status"] == "failed"
    assert result["passed_checks"] == 0


def test_release_status_is_unavailable_for_missing_or_invalid_evidence(
    tmp_path, monkeypatch
):
    path = tmp_path / "release_status.json"
    monkeypatch.setattr(service, "RELEASE_STATUS_PATH", str(path))
    assert service.summarize_release_status()["status"] == "unavailable"

    path.write_text("[]", encoding="utf-8")
    assert service.summarize_release_status()["status"] == "unavailable"
