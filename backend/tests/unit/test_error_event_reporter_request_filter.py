from app.services.error_event_reporter import _filter_events


def test_filter_events_can_match_exact_request_id():
    events = [
        {
            "request_id": "req-keep",
            "tenant_id": "tenant-a",
            "path": "/vendas",
            "status_code": 500,
            "duration_ms": 120,
        },
        {
            "request_id": "req-drop",
            "tenant_id": "tenant-a",
            "path": "/vendas",
            "status_code": 500,
            "duration_ms": 120,
        },
    ]

    filtered = _filter_events(events, request_id="req-keep")

    assert [item["request_id"] for item in filtered] == ["req-keep"]


def test_filter_events_combines_request_id_with_existing_filters():
    events = [
        {
            "request_id": "req-1",
            "tenant_id": "tenant-a",
            "path": "/vendas/reabrir",
            "status_code": 500,
            "duration_ms": 120,
        },
        {
            "request_id": "req-1",
            "tenant_id": "tenant-b",
            "path": "/vendas/reabrir",
            "status_code": 500,
            "duration_ms": 120,
        },
        {
            "request_id": "req-1",
            "tenant_id": "tenant-a",
            "path": "/clientes",
            "status_code": 400,
            "duration_ms": 120,
        },
    ]

    filtered = _filter_events(
        events,
        request_id="req-1",
        tenant_id="tenant-a",
        path_contains="/vendas",
        status_min=500,
    )

    assert len(filtered) == 1
    assert filtered[0]["tenant_id"] == "tenant-a"
    assert filtered[0]["path"] == "/vendas/reabrir"
