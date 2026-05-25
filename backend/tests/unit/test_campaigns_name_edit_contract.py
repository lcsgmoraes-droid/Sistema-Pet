from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_campaigns_parameter_editor_allows_renaming_default_campaigns():
    backend = read_repo("backend/app/campaigns/routes.py")
    hook = read_repo("frontend/src/hooks/useCampanhasGestao.js")
    main = read_repo("frontend/src/components/campanhas/CampanhasMainContent.jsx")
    list_tab = read_repo("frontend/src/components/campanhas/CampanhasListTab.jsx")

    assert "name: Optional[str] = None" in backend
    assert "campanha.name = body.name" in backend
    assert "nomeEditando" in hook
    assert "setNomeEditando(campanha.name" in hook
    assert "name: nomeCampanha" in hook
    assert "nomeEditando={gestao.nomeEditando}" in main
    assert "setNomeEditando={gestao.setNomeEditando}" in main
    assert "Nome da campanha" in list_tab
    assert "value={nomeEditando}" in list_tab
    assert "onChange={(e) => setNomeEditando(e.target.value)}" in list_tab
