from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.evolucao_corepet import (
    ITENS_EVOLUCAO,
    STATUS_DISPONIVEIS,
    listar_evolucao_corepet,
    registrar_uso_funcionalidade,
    validar_catalogo_evolucao,
)
from app.evolucao_models import EvolucaoFuncionalidadeUso


def _session_metricas():
    engine = create_engine("sqlite:///:memory:")
    EvolucaoFuncionalidadeUso.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_catalogo_evolucao_respeita_contrato_de_publicacao():
    validar_catalogo_evolucao()

    ids = [item["id"] for item in ITENS_EVOLUCAO]
    assert len(ids) == len(set(ids))
    for item in ITENS_EVOLUCAO:
        if item["status"] in STATUS_DISPONIVEIS:
            assert item["publicado_em"]
            assert item["caminho_ajuda"]


def test_links_do_catalogo_apontam_para_artigos_existentes_na_central():
    raiz_repositorio = Path(__file__).resolve().parents[3]
    base_ajuda = (
        raiz_repositorio
        / "frontend"
        / "src"
        / "pages"
        / "centralAjuda"
        / "centralAjudaKnowledge.js"
    ).read_text(encoding="utf-8")

    for item in ITENS_EVOLUCAO:
        caminho = item.get("caminho_ajuda")
        if not caminho:
            continue
        artigo = parse_qs(urlparse(caminho).query).get("artigo", [None])[0]
        assert artigo, f"Caminho de ajuda sem artigo: {item['id']}"
        assert f'slug: "{artigo}"' in base_ajuda, (
            f"Artigo {artigo!r} do item {item['id']} não existe na Central de Ajuda"
        )


def test_catalogo_filtra_projetos_por_canal_sem_expor_item_interno():
    erp = listar_evolucao_corepet("erp")
    cliente = listar_evolucao_corepet("app_cliente")

    ids_erp = {item["id"] for item in erp["itens"]}
    ids_cliente = {item["id"] for item in cliente["itens"]}

    assert "grupos-empresas-transferencia-integrada" in ids_erp
    assert "grupos-empresas-transferencia-integrada" not in ids_cliente
    assert "avaliacao-entrega-app" in ids_cliente
    assert erp["total_disponivel"] >= 1


def test_catalogo_nao_anuncia_granel_de_farmacia_descartado():
    ids = {item["id"] for item in ITENS_EVOLUCAO}

    assert "fracionamento-produtos-farmacia" not in ids


def test_novidade_de_granel_mostra_os_caminhos_de_configuracao():
    item = next(
        item for item in ITENS_EVOLUCAO if item["id"] == "granel-bipagem-vinculada"
    )

    for trecho in (
        "Produtos / Estoque",
        "Ver movimentações de estoque",
        "Configurações → Estoque",
        "Funcionário → Lançar granel",
        "produto fechado",
    ):
        assert trecho in item["resumo"]
    assert "pacote pai" not in item["resumo"].lower()
    assert "produto pai" not in item["resumo"].lower()


def test_novidade_crediario_explica_configuracao_e_consequencias():
    item = next(
        item for item in ITENS_EVOLUCAO if item["id"] == "crediario-vencimento-alertas"
    )

    for trecho in (
        "já vem criado",
        "Cadastros → Formas de Pagamento",
        "PDV (Vendas) → Cliente → Registrar Recebimento → Crediário",
        "Funcionário → Passar venda → Comprador → Pagamento → Crediário",
        "DD-MM-AAAA",
        "Financeiro → Contas a Receber",
        "Pedidos → Crediário",
    ):
        assert trecho in item["resumo"]

    assert item["atualizado_em"] == "2026-08-25"


def test_central_ajuda_crediario_tem_passo_a_passo_completo():
    raiz_repositorio = Path(__file__).resolve().parents[3]
    base_ajuda = (
        raiz_repositorio
        / "frontend"
        / "src"
        / "pages"
        / "centralAjuda"
        / "centralAjudaKnowledge.js"
    ).read_text(encoding="utf-8")
    inicio = base_ajuda.index('slug: "venda-crediario-app-funcionario"')
    fim = base_ajuda.index("      {", inicio + 20)
    artigo = base_ajuda[inicio:fim]

    for trecho in (
        "Crediário já é criado automaticamente",
        "Não é necessário criar outra forma",
        "PDV (Vendas)",
        "Funcionário → Passar venda",
        "DD-MM-AAAA",
        "Financeiro → Contas a Receber",
        "Pedidos → Crediário",
        "Quando o cliente pagar",
    ):
        assert trecho in artigo


def test_novidade_relatorio_lista_espera_explica_totalizadores_e_agrupamento():
    item = next(
        item for item in ITENS_EVOLUCAO if item["id"] == "relatorio-lista-espera-sku"
    )

    assert item["status"] == "disponivel_teste"
    assert item["plataformas"] == ["ERP"]
    assert item["canais"] == ["erp"]
    for trecho in (
        "Relatório geral",
        "clientes aguardam",
        "quantidade desejada",
        "fornecedor e marca",
        "cliente × produto",
        "CSV",
    ):
        assert trecho in item["resumo"]


def test_novidade_registro_rapido_nao_venda_cobre_produto_livre_e_relatorio():
    item = next(
        item for item in ITENS_EVOLUCAO if item["id"] == "registro-rapido-nao-venda"
    )

    assert item["status"] == "disponivel_teste"
    assert item["plataformas"] == ["ERP"]
    assert item["canais"] == ["erp"]
    for trecho in (
        "cliente opcional",
        "não existem no catálogo",
        "motivos",
        "produto, marca e fornecedor",
        "cliente × produto",
        "CSV",
    ):
        assert trecho in item["resumo"]


def test_central_ajuda_registro_nao_venda_explica_diferenca_da_lista_espera():
    raiz_repositorio = Path(__file__).resolve().parents[3]
    base_ajuda = (
        raiz_repositorio
        / "frontend"
        / "src"
        / "pages"
        / "centralAjuda"
        / "centralAjudaKnowledge.js"
    ).read_text(encoding="utf-8")
    inicio = base_ajuda.index('slug: "registro-rapido-nao-venda"')
    fim = base_ajuda.index("      {", inicio + 20)
    artigo = base_ajuda[inicio:fim]

    for trecho in (
        "cliente é opcional",
        "nome e telefone",
        "Outro produto",
        "não cria automaticamente um produto",
        "produto que a loja não trabalha",
        "Também colocar na lista de espera",
        "Fornecedor → Marca → Produto/SKU",
        "Atendimento × produto",
        "Baixar CSV",
    ):
        assert trecho in artigo


def test_central_ajuda_relatorio_lista_espera_tem_passo_a_passo_completo():
    raiz_repositorio = Path(__file__).resolve().parents[3]
    base_ajuda = (
        raiz_repositorio
        / "frontend"
        / "src"
        / "pages"
        / "centralAjuda"
        / "centralAjudaKnowledge.js"
    ).read_text(encoding="utf-8")
    inicio = base_ajuda.index('slug: "relatorio-lista-espera-sku"')
    fim = base_ajuda.index("      {", inicio + 20)
    artigo = base_ajuda[inicio:fim]

    for trecho in (
        "sino da lista de espera",
        "Relatório geral",
        "Fornecedor → Marca → SKU",
        "clientes o aguardam",
        "Cliente × produto",
        "Baixar CSV",
        "pendentes",
        "notificados",
        "Sem fornecedor",
        "Atualizar",
    ):
        assert trecho in artigo


def test_fluxo_granel_nao_exibe_terminologia_pai_ao_usuario():
    raiz_repositorio = Path(__file__).resolve().parents[3]
    arquivos = (
        "app-mobile/src/screens/funcionario/FuncionarioGranelScreen.tsx",
        "app-mobile/src/screens/funcionario/FuncionarioHomeScreen.tsx",
        "backend/app/estoque/granel.py",
        "backend/app/routes/app_mobile_funcionario_pdv/granel.py",
        "frontend/src/components/estoque/GranelLancamentoModal.jsx",
        "frontend/src/components/estoque/useMovimentacoesProdutoGranel.js",
        "frontend/src/pages/configuracoes/ConfiguracaoEstoque.jsx",
    )

    for caminho in arquivos:
        conteudo = (raiz_repositorio / caminho).read_text(encoding="utf-8").lower()
        assert "pacote pai" not in conteudo, caminho
        assert "produto pai" not in conteudo, caminho


def test_funcao_liberada_aparece_como_disponivel_em_fase_de_teste():
    resultado = listar_evolucao_corepet(
        "app_cliente",
        agora=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )
    avaliacao = next(
        item for item in resultado["itens"] if item["id"] == "avaliacao-entrega-app"
    )

    assert avaliacao["status"] == "disponivel"
    assert avaliacao["fase_disponibilidade"] == "teste"
    assert avaliacao["status_label"] == "Disponível — em fase de teste"


def test_central_ajuda_liberada_promove_por_tempo_sem_rastrear_leituras():
    durante_teste = listar_evolucao_corepet(
        "erp",
        agora=datetime(2026, 8, 22, 12, tzinfo=timezone.utc),
    )
    central_teste = next(
        item
        for item in durante_teste["itens"]
        if item["id"] == "expansao-central-ajuda"
    )

    assert central_teste["status_label"] == "Disponível — em fase de teste"

    depois_do_periodo = listar_evolucao_corepet(
        "erp",
        agora=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
    )
    central_implantada = next(
        item
        for item in depois_do_periodo["itens"]
        if item["id"] == "expansao-central-ajuda"
    )

    assert central_implantada["status_label"] == "Implantado"
    assert central_implantada["implantado_em"] == "2026-09-05"


def test_promove_para_implantado_depois_do_tempo_e_quantidade_de_usos():
    db = _session_metricas()
    momento_uso = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
    for _ in range(10):
        assert registrar_uso_funcionalidade(
            db, "avaliacao-entrega-app", agora=momento_uso
        )

    resultado = listar_evolucao_corepet(
        "app_cliente",
        db,
        agora=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
    )
    avaliacao = next(
        item for item in resultado["itens"] if item["id"] == "avaliacao-entrega-app"
    )

    assert avaliacao["status"] == "disponivel"
    assert avaliacao["fase_disponibilidade"] == "implantado"
    assert avaliacao["implantado_em"] == "2026-09-05"
    assert avaliacao["novidade_ate"] == "2026-10-05"


def test_novidade_some_depois_do_periodo_sem_remover_outros_projetos():
    db = _session_metricas()
    for _ in range(10):
        registrar_uso_funcionalidade(
            db,
            "avaliacao-entrega-app",
            agora=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )

    resultado = listar_evolucao_corepet(
        "erp",
        db,
        agora=datetime(2026, 10, 6, tzinfo=timezone.utc),
    )
    ids = {item["id"] for item in resultado["itens"]}

    assert "avaliacao-entrega-app" not in ids
    assert "grupos-empresas-transferencia-integrada" in ids


def test_metrica_de_uso_e_global_e_nao_guarda_empresa_cliente_ou_usuario():
    assert set(EvolucaoFuncionalidadeUso.__table__.columns.keys()) == {
        "item_id",
        "usos_total",
        "primeiro_uso_em",
        "ultimo_uso_em",
        "limiar_teste_atingido_em",
    }


def test_catalogo_rejeita_canal_desconhecido():
    try:
        listar_evolucao_corepet("canal_inexistente")
    except ValueError as exc:
        assert "Canal de evolucao invalido" in str(exc)
    else:
        raise AssertionError("Canal desconhecido deveria ser rejeitado")
