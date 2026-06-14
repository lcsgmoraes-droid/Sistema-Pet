from inspect import signature
from pathlib import Path

from app.ia.extrato_ia import MotorCategorizacaoIA
from app.ia.extrato_service import ServicoImportacaoExtrato


ROUTES_SOURCE = Path("app/ia/aba7_extrato_routes.py").read_text(encoding="utf-8")
SERVICE_SOURCE = Path("app/ia/extrato_service.py").read_text(encoding="utf-8")
IA_SOURCE = Path("app/ia/extrato_ia.py").read_text(encoding="utf-8")


def _parameters(callable_obj):
    return set(signature(callable_obj).parameters)


def test_servico_importacao_extrato_exige_tenant_id_nos_fluxos_publicos():
    assert "tenant_id" in _parameters(ServicoImportacaoExtrato.importar_extrato)
    assert "tenant_id" in _parameters(
        ServicoImportacaoExtrato.listar_lancamentos_pendentes
    )
    assert "tenant_id" in _parameters(ServicoImportacaoExtrato.validar_lote)
    assert "tenant_id" in _parameters(ServicoImportacaoExtrato.criar_lancamento_financeiro)
    assert "tenant_id" in _parameters(ServicoImportacaoExtrato.obter_historico_importacoes)


def test_motor_categorizacao_ia_recebe_tenant_id_no_construtor():
    assert "tenant_id" in _parameters(MotorCategorizacaoIA.__init__)


def test_rotas_de_extrato_repassam_usuario_e_tenant_explicitamente():
    assert "user_id=current_user.id" in ROUTES_SOURCE
    assert "tenant_id=tenant_id" in ROUTES_SOURCE
    assert "current_user = Depends(get_current_user)" not in ROUTES_SOURCE
    assert "MotorCategorizacaoIA(db, tenant_id=tenant_id)" in ROUTES_SOURCE


def test_servico_filtra_e_grava_importacoes_por_tenant():
    for fragment in (
        "ArquivoExtratoImportado.tenant_id == tenant_id",
        "LancamentoImportado.tenant_id == tenant_id",
        "ContaPagar.tenant_id == tenant_id",
        "ContaPagar.valor_final",
        "ContaReceber.tenant_id == tenant_id",
        "ContaReceber.valor_final",
        "tenant_id=tenant_id",
        "usuario_id=user_id",
    ):
        assert fragment in SERVICE_SOURCE


def test_motor_filtra_e_grava_padroes_por_tenant():
    for fragment in (
        "self.tenant_id = tenant_id",
        "PadraoCategoriacaoIA.tenant_id == self.tenant_id",
        "LancamentoImportado.tenant_id == self.tenant_id",
        "tenant_id=self.tenant_id",
        "usuario_id=lancamento.usuario_id",
    ):
        assert fragment in IA_SOURCE
