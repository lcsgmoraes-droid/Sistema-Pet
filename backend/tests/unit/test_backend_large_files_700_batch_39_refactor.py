from pathlib import Path

from app import models
from app import models_cadastros


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def test_models_cadastros_preserva_reexports_publicos():
    assert models.FornecedorGrupo is models_cadastros.FornecedorGrupo
    assert models.Cliente is models_cadastros.Cliente
    assert models.Especie is models_cadastros.Especie
    assert models.Raca is models_cadastros.Raca
    assert models.Pet is models_cadastros.Pet


def test_models_cadastros_compartilha_metadata_e_tabelas_legadas():
    assert models.Cliente.metadata is models.Base.metadata
    assert models.Pet.metadata is models.Base.metadata

    assert models.Cliente.__tablename__ == "clientes"
    assert models.Pet.__tablename__ == "pets"
    assert models.FornecedorGrupo.__tablename__ == "fornecedor_grupos"
    assert models.Especie.__tablename__ == "especies"
    assert models.Raca.__tablename__ == "racas"


def test_models_fatia_39_remove_cadastros_do_arquivo_agregador():
    source = _source("backend/app/models.py")
    cadastros_source = _source("backend/app/models_cadastros.py")

    assert "from app.models_cadastros import" in source
    assert "class Cliente(" not in source
    assert "class Pet(" not in source
    assert "class Cliente(" in cadastros_source
    assert "class Pet(" in cadastros_source


def test_models_fatia_39_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "backend/app/models.py": _non_empty_line_count("backend/app/models.py"),
        "backend/app/models_cadastros.py": _non_empty_line_count(
            "backend/app/models_cadastros.py"
        ),
    }

    assert counts["backend/app/models.py"] < 700
    assert all(lines < 700 for lines in counts.values())


def test_layout_fatia_39_extrai_sidebar_sem_mudar_orquestrador():
    layout_source = _source("frontend/src/components/Layout.jsx")
    sidebar_source = _source("frontend/src/components/layout/LayoutSidebar.jsx")

    assert "from \"./layout/LayoutSidebar\"" in layout_source
    assert "<LayoutSidebar" in layout_source
    assert "const COREPET_LOGO" not in layout_source
    assert "Meu Plano" not in layout_source
    assert "COREPET_LOGO" in sidebar_source
    assert "SidebarMenu" in sidebar_source
    assert "Meu Plano" in sidebar_source


def test_layout_fatia_39_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "frontend/src/components/Layout.jsx": _non_empty_line_count(
            "frontend/src/components/Layout.jsx"
        ),
        "frontend/src/components/layout/LayoutSidebar.jsx": _non_empty_line_count(
            "frontend/src/components/layout/LayoutSidebar.jsx"
        ),
    }

    assert counts["frontend/src/components/Layout.jsx"] < 700
    assert all(lines < 700 for lines in counts.values())
