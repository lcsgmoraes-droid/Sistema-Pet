import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DEBUG", "false")

from app import notas_entrada_routes as routes  # noqa: E402
from app.notas_entrada import conferencia_routes  # noqa: E402
from app.notas_entrada import processamento_routes  # noqa: E402
from app.notas_entrada import reversao_routes  # noqa: E402


def test_notas_entrada_routes_inclui_subrouter_de_processamento():
    rotas = {
        (getattr(route, "path", ""), tuple(sorted(getattr(route, "methods", []) or [])))
        for route in routes.router.routes
    }

    assert ("/notas-entrada/{nota_id}/preview-processamento", ("GET",)) in rotas
    assert ("/notas-entrada/{nota_id}/atualizar-precos", ("POST",)) in rotas
    assert ("/notas-entrada/{nota_id}/processar", ("POST",)) in rotas
    assert ("/notas-entrada/{nota_id}/reverter", ("POST",)) in rotas
    assert ("/notas-entrada/{nota_id}/conferencia", ("POST",)) in rotas
    assert ("/notas-entrada/{nota_id}/conferencia/desfazer", ("POST",)) in rotas
    assert ("/notas-entrada/{nota_id}/devolucao-draft", ("GET",)) in rotas


def test_notas_entrada_routes_preserva_reexports_legados_de_processamento():
    assert routes.preview_processamento is processamento_routes.preview_processamento
    assert routes.atualizar_precos_produtos is (
        processamento_routes.atualizar_precos_produtos
    )
    assert routes.processar_entrada_estoque is (
        processamento_routes.processar_entrada_estoque
    )
    assert routes.reverter_entrada_estoque is reversao_routes.reverter_entrada_estoque
    assert routes._acoes_processamento_dict is (
        processamento_routes._acoes_processamento_dict
    )
    assert routes._carregar_acoes_processamento_nota is (
        processamento_routes._carregar_acoes_processamento_nota
    )
    assert routes.salvar_conferencia_nota is conferencia_routes.salvar_conferencia_nota
    assert routes.desfazer_conferencia_nota is (
        conferencia_routes.desfazer_conferencia_nota
    )
    assert routes.gerar_rascunho_nf_devolucao is (
        conferencia_routes.gerar_rascunho_nf_devolucao
    )


def test_notas_entrada_routes_nao_reconcentra_processamento():
    source = Path(routes.__file__).read_text(encoding="utf-8")
    processamento_source = Path(processamento_routes.__file__).read_text(
        encoding="utf-8"
    )

    assert "def processar_entrada_estoque(" not in source
    assert "def reverter_entrada_estoque(" not in source
    assert "def preview_processamento(" not in source
    assert "def salvar_conferencia_nota(" not in source
    assert "def gerar_rascunho_nf_devolucao(" not in source
    assert len(source.splitlines()) < 1250
    assert len(processamento_source.splitlines()) < 1050
    assert (
        len(Path(conferencia_routes.__file__).read_text(encoding="utf-8").splitlines())
        < 300
    )
    assert (
        len(Path(reversao_routes.__file__).read_text(encoding="utf-8").splitlines())
        < 350
    )
