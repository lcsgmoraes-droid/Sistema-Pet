from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "frontend" / "src" / "components" / "ContasBancarias.jsx"


def test_contas_bancarias_renderiza_icones_textuais_com_lucide():
    source = SOURCE.read_text(encoding="utf-8")

    assert "LUCIDE_ICON_BY_NAME" in source
    assert "resolveContaIcon" in source
    assert "banknote" in source
    assert "landmark" in source
    assert "ContaIconComponent" in source
    assert "<ContaIconComponent" in source


def test_contas_bancarias_limita_textos_do_card():
    source = SOURCE.read_text(encoding="utf-8")

    assert 'className="flex min-w-0 items-start justify-between' in source
    assert 'className="flex min-w-0 items-center gap-3' in source
    assert "title={conta.nome}" in source
    assert 'className="truncate font-bold text-gray-800' in source
    assert "title={conta.banco}" in source
