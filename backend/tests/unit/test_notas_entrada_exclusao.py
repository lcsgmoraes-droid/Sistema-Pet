from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from app.compras_pendencias_models import (
    CompraPendenciaFornecedor,
    CompraPendenciaFornecedorHistorico,
    CompraPendenciaFornecedorItem,
)
from app.models import Tenant
from app.notas_entrada.consulta_routes import excluir_nota
from app.produtos_models import NotaEntrada, NotaEntradaItem


def test_excluir_nota_remove_pendencia_criada_pela_conferencia(
    db_session, user_factory, tenant_context
):
    db_session.execute(text("PRAGMA foreign_keys = ON"))
    tenant = Tenant(
        id=str(uuid4()),
        name="Tenant exclusao NF",
        email=f"tenant-nf-{uuid4().hex[:8]}@test.com",
    )
    db_session.add(tenant)
    db_session.flush()
    tenant_id = UUID(tenant.id)
    tenant_context(tenant_id)
    user = user_factory(tenant.id)
    nota = NotaEntrada(
        numero_nota="901010",
        serie="1",
        chave_acesso="1" * 44,
        fornecedor_cnpj="11222333000181",
        fornecedor_nome="Distribuidora Horizonte Pet Demo LTDA",
        data_emissao=datetime(2026, 8, 13),
        data_entrada=datetime(2026, 8, 13),
        valor_produtos=2507.48,
        valor_total=2507.48,
        xml_content="<xml />",
        entrada_estoque_realizada=False,
        user_id=user.id,
        tenant_id=tenant_id,
    )
    item = NotaEntradaItem(
        numero_item=1,
        descricao="Produto demo",
        quantidade=8,
        valor_unitario=10,
        valor_total=80,
        tenant_id=tenant_id,
    )
    nota.itens.append(item)
    db_session.add(nota)
    db_session.flush()

    pendencia = CompraPendenciaFornecedor(
        status="aberta",
        fornecedor_nome=nota.fornecedor_nome,
        fornecedor_cnpj=nota.fornecedor_cnpj,
        nota_entrada_id=nota.id,
        numero_nota=nota.numero_nota,
        titulo=f"NF {nota.numero_nota}",
        user_id=user.id,
        tenant_id=tenant_id,
    )
    pendencia.itens.append(
        CompraPendenciaFornecedorItem(
            nota_entrada_item_id=item.id,
            descricao=item.descricao,
            quantidade_nf=8,
            quantidade_recebida=7,
            quantidade_faltante=1,
            valor_unitario=10,
            valor_total_divergente=10,
            tenant_id=tenant_id,
        )
    )
    pendencia.historico.append(
        CompraPendenciaFornecedorHistorico(
            tipo="criada",
            observacao="Pendencia gerada pela conferencia da NF.",
            user_id=user.id,
            tenant_id=tenant_id,
        )
    )
    db_session.add(pendencia)
    db_session.flush()
    pendencia_id = pendencia.id
    item_pendencia_id = pendencia.itens[0].id
    historico_id = pendencia.historico[0].id

    resposta = excluir_nota(
        nota.id,
        db=db_session,
        user_and_tenant=(user, tenant_id),
    )

    assert resposta["numero_nota"] == "901010"
    assert resposta["itens_excluidos"] == 1
    assert resposta["pendencias_excluidas"] == 1
    assert db_session.get(NotaEntrada, nota.id) is None
    assert db_session.get(NotaEntradaItem, item.id) is None
    assert db_session.get(CompraPendenciaFornecedor, pendencia_id) is None
    assert db_session.get(CompraPendenciaFornecedorItem, item_pendencia_id) is None
    assert db_session.get(CompraPendenciaFornecedorHistorico, historico_id) is None
