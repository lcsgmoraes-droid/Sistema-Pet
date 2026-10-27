"""OPS: lista e detalhe de lojas (modulos, usuarios, grupo) - contrato das rotas e consultas."""

from pathlib import Path

from app.routes import ops_lojas_routes as rotas

RAIZ = Path(__file__).resolve().parents[2]


def _caminhos():
    return [(r.path, sorted(r.methods)) for r in rotas.router.routes]


def test_rotas_da_loja_existem_e_a_fixa_vem_antes_da_variavel():
    caminhos = [c for c, _ in _caminhos()]

    assert "/admin/lojas" in caminhos
    assert "/admin/lojas/{tenant_id}" in caminhos
    assert "/admin/lojas/{tenant_id}/historico" in caminhos
    # "/historico" tem que ser registrada antes de "/{tenant_id}", senao vira id de loja.
    assert caminhos.index("/admin/lojas/historico") < caminhos.index(
        "/admin/lojas/{tenant_id}"
    )


def test_todas_as_rotas_exigem_administrador_da_plataforma():
    fonte = (RAIZ / "app/routes/ops_lojas_routes.py").read_text(encoding="utf-8")

    assert fonte.count("Depends(require_platform_admin)") >= 6


def test_lista_resume_usuarios_numa_unica_consulta():
    fonte = (RAIZ / "app/services/ops_lojas_detalhe_service.py").read_text(
        encoding="utf-8"
    )

    assert "GROUP BY ut.tenant_id" in fonte  # nada de uma consulta por loja
    assert "resumo_de_usuarios_por_loja" in (
        RAIZ / "app/services/ops_lojas_modulos_service.py"
    ).read_text(encoding="utf-8")


def test_detalhe_mostra_modulos_usuarios_grupo_e_plano():
    fonte = (RAIZ / "app/services/ops_lojas_detalhe_service.py").read_text(
        encoding="utf-8"
    )

    for campo in (
        '"usuarios"',
        '"lojas_do_grupo"',
        '"plano"',
        '"responsavel"',
        "**modulos",
    ):
        assert campo in fonte


def test_usuarios_da_loja_leem_o_perfil_dentro_do_contexto_da_loja():
    fonte = (RAIZ / "app/services/ops_lojas_detalhe_service.py").read_text(
        encoding="utf-8"
    )

    # roles tem isolamento por loja: sem o contexto o nome do perfil viria vazio.
    assert "tenant_context(tid)" in fonte and "sync_rls_tenant(db, tid)" in fonte


def test_ops_so_mostra_modulos_da_propria_plataforma():
    from app.routes.modulos_routes import MODULOS_PREMIUM

    assert "bling" in MODULOS_PREMIUM and "campanhas" in MODULOS_PREMIUM


def test_todo_modulo_tem_nome_no_catalogo_do_painel():
    from app.routes.modulos_routes import MODULOS_PREMIUM
    from app.services.ops_lojas_modulos_service import (
        CATALOGO_DE_MODULOS,
        catalogo_de_modulos,
    )

    assert set(CATALOGO_DE_MODULOS) == set(MODULOS_PREMIUM)
    assert [m["codigo"] for m in catalogo_de_modulos()] == sorted(MODULOS_PREMIUM)
    assert all(m["nome"] and m["descricao"] for m in catalogo_de_modulos())
