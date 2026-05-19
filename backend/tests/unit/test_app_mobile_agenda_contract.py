from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENDA_SCREEN = REPO_ROOT / "app-mobile/src/screens/veterinario/VetAgendaScreen.tsx"


def _agenda_source() -> str:
    return AGENDA_SCREEN.read_text(encoding="utf-8")


def test_mobile_new_consultation_pet_search_waits_for_autocomplete_input():
    source = _agenda_source()

    assert "MIN_CARACTERES_BUSCA_PET = 2" in source
    assert "if (termo.length < MIN_CARACTERES_BUSCA_PET) return [];" in source
    assert "Digite pelo menos 2 caracteres" in source
    assert "if (!termo) return pets.slice(0, 30);" not in source


def test_mobile_new_consultation_date_uses_br_calendar_picker():
    source = _agenda_source()

    assert "formatarDataIsoParaBr(form.data)" in source
    assert 'placeholder="dd/mm/aaaa"' in source
    assert "setCalendarioAberto(true)" in source
    assert "calendarioDias" in source
    assert 'placeholder="AAAA-MM-DD"' not in source
