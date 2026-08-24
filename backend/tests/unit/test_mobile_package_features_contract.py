import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.estoque.granel import _produto_corresponde_barcode_granel
from app.routes.app_mobile_funcionario_pdv.schemas import (
    FuncionarioPdvClienteRapidoRequest,
    FuncionarioPdvPagamentoRequest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_cadastro_rapido_mantem_todos_os_campos_opcionais():
    payload = FuncionarioPdvClienteRapidoRequest()

    assert payload.nome is None
    assert payload.telefone is None
    assert payload.endereco is None
    assert '"/funcionario/pdv/clientes/rapido"' in read_repo(
        "backend/app/routes/app_mobile_funcionario_pdv/clientes.py"
    )
    mobile = read_repo(
        "app-mobile/src/screens/funcionario/pdv/FuncionarioPdvClienteRapidoModal.tsx"
    )
    assert "Todos os campos sao opcionais" in mobile
    assert 'name="add"' in read_repo(
        "app-mobile/src/screens/funcionario/pdv/FuncionarioPdvContent.tsx"
    )


def test_granel_confere_codigos_principal_gtin_e_alternativos():
    produto = SimpleNamespace(
        codigo="SKU-10",
        codigo_barras="7891000000010",
        gtin_ean="7891000000027",
        gtin_ean_tributario="7891000000041",
        codigos_barras_alternativos='["7891000000034"]',
    )

    assert _produto_corresponde_barcode_granel(produto, "SKU-10")
    assert _produto_corresponde_barcode_granel(produto, "7891000000010")
    assert _produto_corresponde_barcode_granel(produto, "7891000000027")
    assert _produto_corresponde_barcode_granel(produto, "7891000000034")
    assert _produto_corresponde_barcode_granel(produto, "7891000000041")
    assert not _produto_corresponde_barcode_granel(produto, "7899999999999")

    backend = read_repo("backend/app/routes/app_mobile_funcionario_pdv/granel.py")
    assert '"/funcionario/granel/config"' in backend
    assert '"/funcionario/granel/produtos/barcode/{barcode}"' in backend
    assert '"/funcionario/granel/converter"' in backend
    assert "exigir_bipagem=_config_bipagem_granel" in backend


def test_crediario_transporta_vencimento_ate_contas_a_receber():
    vencimento = date(2026, 9, 30)
    payload = FuncionarioPdvPagamentoRequest(
        forma_pagamento="crediario",
        valor=100,
        data_vencimento=vencimento,
    )

    assert payload.data_vencimento == vencimento
    vendas = read_repo("backend/app/routes/app_mobile_funcionario_pdv/vendas.py")
    persistencia = read_repo("backend/app/vendas/finalizacao_pagamentos.py")
    contas = read_repo("backend/app/financeiro/contas_receber_service.py")
    checkout = read_repo("backend/app/routes/ecommerce_checkout.py")

    assert 'forma_pagamento == "Crediário"' in vendas
    assert 'pagamento_payload["data_recebimento_prevista"]' in vendas
    assert '"data_recebimento_prevista": pag_data.get' in persistencia
    assert "data_aplicada or" in contas
    assert '@router.get("/crediario")' in checkout
    assert 'source="crediario"' in vendas


def test_crediario_e_controlado_pelo_cadastro_do_erp_em_ambas_as_interfaces():
    pagamentos = read_repo(
        "backend/app/routes/app_mobile_funcionario_pdv/pagamentos.py"
    )
    cadastro = read_repo("backend/app/financeiro/config_routes.py")
    mobile = read_repo(
        "app-mobile/src/screens/funcionario/pdv/FuncionarioPdvContent.tsx"
    )
    erp = read_repo(
        "frontend/src/components/modalPagamento/ModalPagamentoFormaPanel.jsx"
    )
    migration = read_repo(
        "backend/alembic/versions/zwz20260824a1_seed_crediario_padrao.py"
    )

    assert "FormaPagamento.ativo.is_(True)" in pagamentos
    assert 'FormaPagamento.tipo == "crediario"' in pagamentos
    assert '"boleto": "Boleto"' in pagamentos
    assert '"transferencia": "Transferência"' in pagamentos
    assert "builtin:crediario" not in pagamentos
    assert "_obter_ou_criar_forma_crediario" not in pagamentos
    assert "modalidades_cartao_adicionadas" not in pagamentos
    assert 'f.tipo = "crediario" if eh_crediario else forma.tipo' in cadastro
    assert "formasPagamentoErp" in mobile
    assert "formasPagamentoBotoes.map" in mobile
    assert "{forma.nome}" in mobile
    assert 'placeholder="DD-MM-AAAA"' in mobile
    assert 'formaPagamentoSelecionada.tipo === "crediario"' in erp
    assert 'revision = "zwz20260824a1"' in migration
    assert "'Crediário', 'crediario'" in migration


def test_avaliacao_de_entrega_exige_entrega_concluida_e_uma_nota_valida():
    checkout = read_repo("backend/app/routes/ecommerce_checkout.py")
    model = read_repo("backend/app/rotas_entrega_models.py")
    history = read_repo("backend/app/services/customer_order_history.py")
    mobile = read_repo("app-mobile/src/screens/orders/orders/OrderCard.tsx")

    assert '@router.post("/vendas/{venda_id}/avaliacao-entrega"' in checkout
    assert "nota: int = Field(ge=1, le=5)" in checkout
    assert 'str(venda.status_entrega or "").lower() != "entregue"' in checkout
    assert 'UniqueConstraint("tenant_id", "venda_id"' in model
    assert 'entry["pode_avaliar_entrega"]' in history
    assert "Avaliar entrega" in mobile


def test_migracao_do_pacote_preserva_isolamento_por_empresa():
    migration = read_repo(
        "backend/alembic/versions/zwu20260822a1_mobile_granel_entrega_crediario.py"
    )

    assert 'revision = "zwu20260822a1"' in migration
    assert 'down_revision = "zws20260821a1"' in migration
    assert '"granel_bipagem_obrigatoria"' in migration
    assert '"entrega_avaliacoes"' in migration
    assert "apply_tenant_rls" in migration
