"""Regulariza vendas importadas pagas antes da migracao, sem caixa/estoque.

Uso no ambiente correto:
  python regularizar_vendas_importadas_pagamento_historico.py \
    --tenant-email LOGIN --tenant-name EMPRESA \
    --client-code CODIGO --client-name NOME \
    --sale NUMERO:VALOR --sale NUMERO:VALOR
  # Acrescente --apply apenas depois de revisar o plano impresso.

O modo padrao apenas valida e mostra o plano. A aplicacao exige que TODOS os
vinculos ainda correspondam ao estado esperado; qualquer divergencia aborta.
"""

import argparse
from decimal import Decimal

import app.db.base  # noqa: F401 - registra modelos e filtros de tenant
from app.audit_log import log_action
from app.caixa_models import MovimentacaoCaixa
from app.db import SessionLocal
from app.financeiro.models_caixa import MovimentacaoFinanceira
from app.financeiro_models import ContaReceber, Recebimento
from app.models import Cliente, Tenant, User
from app.tenancy.context import tenant_context
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda, VendaBaixa, VendaPagamento


OBSERVACAO = (
    "Pagamento PIX realizado no sistema anterior e informado pelo titular. "
    "Data efetiva do PIX nao informada; data deste registro e a da regularizacao. "
    "Nao gerar nova entrada de caixa nem movimentar estoque."
)


def preparar(
    db,
    *,
    aplicar: bool,
    email: str,
    nome_tenant: str,
    cliente_codigo: str,
    cliente_nome: str,
    alvos: dict[str, Decimal],
) -> tuple[list[tuple[Venda, ContaReceber | None]], User]:
    usuario = db.query(User).filter(User.email == email).one()
    tenant = db.query(Tenant).filter(Tenant.id == str(usuario.tenant_id)).one()
    if tenant.name.casefold() != nome_tenant.casefold():
        raise ValueError(f"Empresa inesperada para {email}: {tenant.name}")

    print(f"Empresa: {tenant.name} | login: {usuario.email} | tenant: {tenant.id}")
    with tenant_context(usuario.tenant_id):
        query = db.query(Venda).filter(
            Venda.tenant_id == usuario.tenant_id,
            Venda.numero_venda.in_(alvos),
        )
        if aplicar:
            query = query.with_for_update()
        vendas = {v.numero_venda: v for v in query.all()}
        if set(vendas) != set(alvos):
            raise ValueError(
                f"Vendas encontradas: {sorted(vendas)}; esperado: {sorted(alvos)}"
            )

        preparados = []
        clientes = set()
        for numero, esperado in alvos.items():
            venda = vendas[numero]
            clientes.add(venda.cliente_id)
            if venda.status != "aberta" or Decimal(venda.total) != esperado:
                raise ValueError(f"{numero}: status ou total divergiu")
            cliente = db.query(Cliente).filter_by(id=venda.cliente_id).one()
            if (
                str(cliente.codigo) != cliente_codigo
                or cliente.nome.casefold() != cliente_nome.casefold()
            ):
                raise ValueError(f"{numero}: cliente divergiu")
            if venda.data_venda.strftime("%Y%m%d") != numero[4:12]:
                raise ValueError(f"{numero}: data divergiu")
            if db.query(VendaPagamento).filter_by(venda_id=venda.id).count():
                raise ValueError(f"{numero}: ja possui pagamento")
            if db.query(VendaBaixa).filter_by(venda_id=venda.id).count():
                raise ValueError(f"{numero}: ja possui baixa")
            if db.query(MovimentacaoCaixa).filter_by(venda_id=venda.id).count():
                raise ValueError(f"{numero}: ja possui movimento de caixa")
            if (
                db.query(MovimentacaoFinanceira)
                .filter_by(origem_tipo="venda", origem_id=venda.id)
                .count()
            ):
                raise ValueError(f"{numero}: ja possui movimento bancario")

            contas = db.query(ContaReceber).filter_by(venda_id=venda.id).all()
            if len(contas) > 1:
                raise ValueError(f"{numero}: mais de uma conta a receber vinculada")
            conta = contas[0] if contas else None
            if conta is not None:
                if (
                    conta.tenant_id != usuario.tenant_id
                    or conta.cliente_id != venda.cliente_id
                    or conta.status not in {"pendente", "vencido", "vencida"}
                    or Decimal(conta.valor_final) != esperado
                    or Decimal(conta.valor_recebido or 0) != Decimal("0.00")
                    or not (conta.documento or "").startswith("SV-")
                ):
                    raise ValueError(f"{numero}: conta a receber divergiu")
                if db.query(Recebimento).filter_by(conta_receber_id=conta.id).count():
                    raise ValueError(f"{numero}: a conta ja possui recebimento")
            print(
                f"{numero}: venda_id={venda.id}, cliente_id={venda.cliente_id}, "
                f"total=R$ {esperado:.2f}, conta_id={conta.id if conta else 'nenhuma'}, "
                f"conta_status={conta.status if conta else 'nenhum'}"
            )
            preparados.append((venda, conta))
        if len(clientes) != 1 or None in clientes:
            raise ValueError("As vendas nao pertencem ao mesmo cliente identificado")
        return preparados, usuario


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-email", required=True, help="Email do login da empresa"
    )
    parser.add_argument(
        "--tenant-name", required=True, help="Nome da empresa no CorePet"
    )
    parser.add_argument(
        "--client-code", required=True, help="Codigo visivel do cliente"
    )
    parser.add_argument("--client-name", required=True, help="Nome visivel do cliente")
    parser.add_argument(
        "--sale",
        required=True,
        action="append",
        metavar="NUMERO:VALOR",
        help="Numero importado e valor exato em reais (ponto decimal)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Gravar a regularizacao validada"
    )
    args = parser.parse_args()
    if (
        len(args.sale) != 2
        or not args.client_code.strip()
        or not args.client_name.strip()
    ):
        parser.error("Informe duas vendas, codigo e nome do cliente")
    alvos = {}
    for entrada in args.sale:
        try:
            numero, valor = entrada.split(":", 1)
            quantia = Decimal(valor)
        except (ValueError, ArithmeticError) as exc:
            parser.error(f"Venda invalida: {entrada!r} ({exc})")
        if (
            not numero.startswith("IMP-")
            or quantia <= 0
            or quantia.as_tuple().exponent < -2
        ):
            parser.error(f"Venda invalida: {entrada!r}")
        alvos[numero] = quantia
    if len(alvos) != 2:
        parser.error("Os numeros das duas vendas devem ser distintos")
    db = SessionLocal()
    try:
        preparados, usuario = preparar(
            db,
            aplicar=args.apply,
            email=args.tenant_email,
            nome_tenant=args.tenant_name,
            cliente_codigo=args.client_code,
            cliente_nome=args.client_name,
            alvos=alvos,
        )
        if not args.apply:
            print(
                "SIMULACAO: nenhuma alteracao gravada. Use --apply apos revisar os dados."
            )
            db.rollback()
            return

        with tenant_context(usuario.tenant_id):
            agora = now_brasilia()
            for venda, conta in preparados:
                total = Decimal(venda.total)
                db.add(
                    VendaPagamento(
                        tenant_id=usuario.tenant_id,
                        venda_id=venda.id,
                        forma_pagamento="pix",
                        valor=total,
                        status="aprovado",
                        data_pagamento=agora,
                    )
                )
                db.add(
                    VendaBaixa(
                        tenant_id=usuario.tenant_id,
                        venda_id=venda.id,
                        valor_baixa=total,
                        valor_anterior=total,
                        valor_restante=Decimal("0.00"),
                        forma_pagamento="pix",
                        tipo="baixa_total",
                        usuario_id=usuario.id,
                        observacoes=OBSERVACAO,
                        data_baixa=agora,
                    )
                )
                venda.status = "finalizada"
                venda.data_finalizacao = agora
                if conta is not None:
                    db.delete(
                        conta
                    )  # Saldo importado indevidamente; sem recebimento vinculado.
                log_action(
                    db,
                    usuario.id,
                    action="UPDATE",
                    entity_type="vendas",
                    entity_id=venda.id,
                    details=f"Regularizacao historica PIX: {venda.numero_venda}. {OBSERVACAO}",
                    tenant_id=usuario.tenant_id,
                    commit=False,
                )
            db.flush()
            for venda, _ in preparados:
                pagamentos = db.query(VendaPagamento).filter_by(venda_id=venda.id).all()
                if (
                    venda.status != "finalizada"
                    or len(pagamentos) != 1
                    or pagamentos[0].forma_pagamento != "pix"
                    or Decimal(pagamentos[0].valor) != Decimal(venda.total)
                    or db.query(ContaReceber).filter_by(venda_id=venda.id).count()
                ):
                    raise ValueError(f"{venda.numero_venda}: validacao final falhou")
            db.commit()
            print(
                "APLICADO: duas vendas finalizadas como PIX historico; contas em aberto removidas."
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
