import json

from app.scripts.seed_demo_operacional_showcase import (
    DEMO_EXISTING_PET_PHOTOS,
    DEMO_PET_PHOTO_URLS,
    DEMO_RATION_SHOWCASE_PRODUCTS,
    DEMO_REMINDER_SCENARIOS,
    DEMO_VALIDITY_SCENARIOS,
    _consumption_table,
)


def test_demo_showcase_has_local_photos_for_all_pets():
    photo_urls = [*DEMO_PET_PHOTO_URLS.values()]
    photo_urls.extend(item["photo"] for item in DEMO_EXISTING_PET_PHOTOS)

    assert len(photo_urls) == 6
    assert len(set(photo_urls)) == 6
    assert all(url.startswith("/demo/pets/") for url in photo_urls)
    assert all(url.endswith(".webp") for url in photo_urls)


def test_demo_showcase_has_complete_rations_for_detailed_comparison():
    assert len(DEMO_RATION_SHOWCASE_PRODUCTS) == 6
    assert len({item["code"] for item in DEMO_RATION_SHOWCASE_PRODUCTS}) == 6
    assert len({item["brand"] for item in DEMO_RATION_SHOWCASE_PRODUCTS}) == 3

    adult_15kg = [
        item
        for item in DEMO_RATION_SHOWCASE_PRODUCTS
        if item["weight"] == 15
        and item["phase"] == "Adulto"
        and item["size"] == "Todos"
    ]
    assert len(adult_15kg) == 3
    assert {item["classification"] for item in adult_15kg} == {
        "premium",
        "super_premium",
        "standard",
    }
    assert all(
        item["price"] > item["cost"] > 0 for item in DEMO_RATION_SHOWCASE_PRODUCTS
    )
    assert all(
        json.loads(_consumption_table(item))["dados"]
        for item in DEMO_RATION_SHOWCASE_PRODUCTS
    )


def test_demo_showcase_covers_recurring_alert_deadlines():
    deadlines = {item["days"] for item in DEMO_REMINDER_SCENARIOS}

    assert any(days < 0 for days in deadlines)
    assert any(0 <= days <= 7 for days in deadlines)
    assert any(days > 7 for days in deadlines)


def test_demo_showcase_covers_expired_and_near_expiry_lots():
    deadlines = {item["days"] for item in DEMO_VALIDITY_SCENARIOS}

    assert len(DEMO_VALIDITY_SCENARIOS) == 3
    assert any(days < 0 for days in deadlines)
    assert any(0 <= days <= 7 for days in deadlines)
    assert any(7 < days <= 15 for days in deadlines)
