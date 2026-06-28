from pathlib import Path

from app.campaigns import scheduler as scheduler_module
from app.campaigns import scheduler_jobs, scheduler_seed


EXPECTED_JOB_IDS = {
    "campaign_daily_birthday_check",
    "campaign_weekly_inactivity_check",
    "campaign_monthly_ranking_recalc",
    "campaign_worker_tick",
    "campaign_notification_tick",
    "campaign_auto_drawings",
    "campaign_destaque_mensal",
    "campaign_cashback_expiration",
}


def test_campaign_scheduler_refactor_files_stay_below_700_lines():
    backend_root = Path(__file__).resolve().parents[2]
    targets = [
        backend_root / "app/campaigns/scheduler.py",
        backend_root / "app/campaigns/scheduler_jobs.py",
        backend_root / "app/campaigns/scheduler_seed.py",
    ]

    for path in targets:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 700, path


def test_campaign_scheduler_public_contract_and_registered_jobs():
    scheduler = scheduler_module.CampaignScheduler()

    assert {job.id for job in scheduler.scheduler.get_jobs()} == EXPECTED_JOB_IDS
    assert (
        scheduler_module.seed_campaigns_for_tenant
        is scheduler_seed.seed_campaigns_for_tenant
    )
    assert (
        scheduler_jobs.seed_campaigns_for_tenant
        is scheduler_seed.seed_campaigns_for_tenant
    )


def test_campaign_scheduler_private_methods_delegate_to_extracted_jobs(monkeypatch):
    calls = []
    fake_db_factory = object()
    fake_logger = object()

    monkeypatch.setattr(scheduler_module, "SessionLocal", fake_db_factory)
    monkeypatch.setattr(scheduler_module, "logger", fake_logger)

    def capture(name):
        def _captured(*args, **kwargs):
            calls.append((name, args, kwargs))

        return _captured

    monkeypatch.setattr(
        scheduler_module, "run_auto_execute_drawings", capture("drawings")
    )
    monkeypatch.setattr(
        scheduler_module,
        "run_auto_send_monthly_highlights",
        capture("monthly_highlights"),
    )
    monkeypatch.setattr(scheduler_module, "run_auto_seed_all_tenants", capture("seed"))
    monkeypatch.setattr(
        scheduler_module,
        "publish_scheduled_event_for_all_tenants",
        capture("publish"),
    )
    monkeypatch.setattr(
        scheduler_module,
        "run_cashback_expiration_check",
        capture("cashback_expiration"),
    )

    scheduler = object.__new__(scheduler_module.CampaignScheduler)
    scheduler._auto_execute_drawings()
    scheduler._auto_enviar_destaque_mensal()
    scheduler._auto_seed_all_tenants()
    scheduler._publish_event_for_all_tenants("daily_birthday_check")
    scheduler._cashback_expiration_check()

    assert calls == [
        (
            "drawings",
            (),
            {"db_factory": fake_db_factory, "logger": fake_logger},
        ),
        (
            "monthly_highlights",
            (),
            {"db_factory": fake_db_factory, "logger": fake_logger},
        ),
        ("seed", (), {"db_factory": fake_db_factory, "logger": fake_logger}),
        (
            "publish",
            ("daily_birthday_check",),
            {"db_factory": fake_db_factory, "logger": fake_logger},
        ),
        (
            "cashback_expiration",
            (),
            {"db_factory": fake_db_factory, "logger": fake_logger},
        ),
    ]
