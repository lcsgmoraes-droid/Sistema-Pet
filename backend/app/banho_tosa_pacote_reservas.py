"""Reservas por serviço: agendamento reserva, check-in confirma, cancelamento devolve.

Todas as alterações usam a transação da operação chamadora. As linhas dos
contratos são bloqueadas para impedir que dois agendamentos gastem o mesmo saldo.
"""

from decimal import Decimal

from app.banho_tosa_models import BanhoTosaPacoteCredito, BanhoTosaPacoteMovimento
from app.banho_tosa_pacotes import calcular_saldo_creditos, _decimal
from app.utils.timezone import now_brasilia


def composicao_contrato(credito):
    servicos = getattr(credito, "servicos", None)
    if servicos is not None:
        return servicos
    pacote = getattr(credito, "pacote", None)
    if pacote and pacote.servico_id:
        return [
            {
                "servico_id": pacote.servico_id,
                "quantidade_creditos": float(credito.creditos_total),
            }
        ]
    return []


def saldos_por_servico(credito):
    movimentos = getattr(credito, "movimentos", []) or []
    composicao = composicao_contrato(credito)
    # O fluxo anterior tinha um serviço por contrato e não gravava servico_id
    # nos movimentos. O snapshot único identifica consumo e estorno antigos.
    servico_legado_id = composicao[0]["servico_id"] if len(composicao) == 1 else None
    saida = []
    for item in composicao:
        usados, reservados = _somar_movimentos_servico(
            movimentos, item["servico_id"], servico_legado_id
        )
        total = _decimal(item["quantidade_creditos"])
        cancelados = (
            max(total - usados - reservados, Decimal("0"))
            if credito.status == "encerrado"
            else Decimal("0")
        )
        saida.append(
            {
                **item,
                "creditos_usados": max(usados, Decimal("0")),
                "creditos_reservados": max(reservados, Decimal("0")),
                "creditos_cancelados": cancelados,
                "saldo_creditos": calcular_saldo_creditos(
                    total, usados, cancelados, reservados
                ),
            }
        )
    return saida


def _somar_movimentos_servico(movimentos, servico_procurado_id, servico_legado_id):
    usados = reservados = Decimal("0")
    sinal_consumo = {"consumo": 1, "estorno": -1}
    sinal_reserva = {"reserva": 1, "estorno_reserva": -1}
    for movimento in movimentos:
        servico_id = movimento.servico_id
        if servico_id is None and not getattr(
            movimento, "agendamento_servico_id", None
        ):
            servico_id = servico_legado_id
        if servico_id != servico_procurado_id:
            continue
        quantidade = _decimal(movimento.quantidade)
        usados += quantidade * sinal_consumo.get(movimento.tipo, 0)
        reservados += quantidade * sinal_reserva.get(movimento.tipo, 0)
    return usados, reservados


def consumo_legado_ativo(db, tenant_id, atendimento):
    """Localiza a concessão integral registrada antes da cobertura por item.

    O movimento original é a evidência da concessão. Apenas movimentos antigos,
    vinculados ao mesmo atendimento/contrato/empresa e ainda não estornados,
    mantêm a regra anterior; consumos novos continuam cobrando itens extras.
    """
    if not getattr(atendimento, "pacote_credito_id", None) or not getattr(
        atendimento, "pacote_movimento_id", None
    ):
        return None
    movimento = (
        db.query(BanhoTosaPacoteMovimento)
        .filter(
            BanhoTosaPacoteMovimento.tenant_id == tenant_id,
            BanhoTosaPacoteMovimento.id == atendimento.pacote_movimento_id,
            BanhoTosaPacoteMovimento.credito_id == atendimento.pacote_credito_id,
            BanhoTosaPacoteMovimento.atendimento_id == atendimento.id,
            BanhoTosaPacoteMovimento.tipo == "consumo",
            BanhoTosaPacoteMovimento.agendamento_id.is_(None),
            BanhoTosaPacoteMovimento.agendamento_servico_id.is_(None),
            BanhoTosaPacoteMovimento.servico_id.is_(None),
        )
        .first()
    )
    if not movimento:
        return None
    estorno = (
        db.query(BanhoTosaPacoteMovimento.id)
        .filter(
            BanhoTosaPacoteMovimento.tenant_id == tenant_id,
            BanhoTosaPacoteMovimento.movimento_origem_id == movimento.id,
            BanhoTosaPacoteMovimento.tipo == "estorno",
        )
        .first()
    )
    return None if estorno else movimento


def reservar_creditos_agendamento(db, tenant_id, agendamento, user_id=None):
    """Aplica automaticamente o contrato elegível que vence primeiro.

    Cada item pode ser parcialmente coberto; a parte restante continua cobrável.
    Contratos antigos sem pet específico não são usados automaticamente.
    """
    data_servico = agendamento.data_hora_inicio.date()
    creditos = (
        db.query(BanhoTosaPacoteCredito)
        .filter(
            BanhoTosaPacoteCredito.tenant_id == tenant_id,
            BanhoTosaPacoteCredito.cliente_id == agendamento.cliente_id,
            BanhoTosaPacoteCredito.pet_id == agendamento.pet_id,
            BanhoTosaPacoteCredito.status == "ativo",
            BanhoTosaPacoteCredito.data_inicio <= data_servico,
            BanhoTosaPacoteCredito.data_validade >= data_servico,
            BanhoTosaPacoteCredito.data_validade >= now_brasilia().date(),
        )
        .order_by(BanhoTosaPacoteCredito.id)
        .with_for_update(of=BanhoTosaPacoteCredito)
        .populate_existing()
        .all()
    )
    creditos.sort(key=lambda c: (c.data_validade, c.id))
    for servico in agendamento.servicos or []:
        if not servico.servico_id or getattr(servico, "pacote_credito_id", None):
            continue
        _reservar_servico(db, tenant_id, agendamento, servico, creditos, user_id)


def _reservar_servico(db, tenant_id, agendamento, servico, creditos, user_id):
    restante = _decimal(servico.quantidade)
    for credito in creditos:
        saldo_geral = calcular_saldo_creditos(
            credito.creditos_total,
            credito.creditos_usados,
            credito.creditos_cancelados,
            credito.creditos_reservados,
        )
        # Atualiza a coleção após cada reserva da mesma transação.
        db.flush()
        db.expire(credito, ["movimentos"])
        item = next(
            (
                i
                for i in saldos_por_servico(credito)
                if i["servico_id"] == servico.servico_id
            ),
            None,
        )
        if not item:
            continue
        quantidade = min(restante, saldo_geral, item["saldo_creditos"])
        if quantidade <= 0:
            continue
        credito.creditos_reservados = _decimal(credito.creditos_reservados) + quantidade
        servico.pacote_credito_id = servico.pacote_credito_id or credito.id
        servico.pacote_quantidade = _decimal(servico.pacote_quantidade) + quantidade
        db.add(
            BanhoTosaPacoteMovimento(
                tenant_id=tenant_id,
                credito_id=credito.id,
                agendamento_id=agendamento.id,
                agendamento_servico_id=servico.id,
                servico_id=servico.servico_id,
                tipo="reserva",
                quantidade=quantidade,
                saldo_apos=saldo_geral - quantidade,
                created_by=user_id,
                observacoes="Reserva automática no agendamento.",
            )
        )
        restante -= quantidade
        if restante <= 0:
            break


def confirmar_reservas_checkin(db, tenant_id, agendamento, atendimento, user_id=None):
    if consumo_legado_ativo(db, tenant_id, atendimento):
        # Check-in repetido não pode gastar novamente o pacote já concedido.
        return
    # Também cobre agendamentos criados antes da contratação do pacote.
    reservar_creditos_agendamento(db, tenant_id, agendamento, user_id)
    db.flush()
    movimentos = (
        db.query(BanhoTosaPacoteMovimento)
        .filter(
            BanhoTosaPacoteMovimento.tenant_id == tenant_id,
            BanhoTosaPacoteMovimento.agendamento_id == agendamento.id,
            BanhoTosaPacoteMovimento.tipo == "reserva",
        )
        .order_by(BanhoTosaPacoteMovimento.credito_id, BanhoTosaPacoteMovimento.id)
        .all()
    )
    for movimento in movimentos:
        credito = _bloquear_credito(db, tenant_id, movimento.credito_id)
        quantidade = _decimal(movimento.quantidade)
        credito.creditos_reservados = max(
            _decimal(credito.creditos_reservados) - quantidade, Decimal("0")
        )
        credito.creditos_usados = _decimal(credito.creditos_usados) + quantidade
        movimento.tipo = "consumo"
        movimento.atendimento_id = atendimento.id
        movimento.observacoes = (
            movimento.observacoes or ""
        ) + " Confirmada no check-in."
        db.add(
            BanhoTosaPacoteMovimento(
                tenant_id=tenant_id,
                credito_id=credito.id,
                agendamento_id=agendamento.id,
                atendimento_id=atendimento.id,
                movimento_origem_id=movimento.id,
                servico_id=movimento.servico_id,
                tipo="confirmacao",
                quantidade=0,
                saldo_apos=calcular_saldo_creditos(
                    credito.creditos_total,
                    credito.creditos_usados,
                    credito.creditos_cancelados,
                    credito.creditos_reservados,
                ),
                created_by=user_id,
                observacoes="Confirmação da reserva no check-in.",
            )
        )
        if not atendimento.pacote_credito_id:
            atendimento.pacote_credito_id = credito.id
            atendimento.pacote_movimento_id = movimento.id
        if (
            calcular_saldo_creditos(
                credito.creditos_total,
                credito.creditos_usados,
                credito.creditos_cancelados,
            )
            <= 0
        ):
            credito.status = "esgotado"
        # O SessionLocal usa autoflush=False. Outro serviço pode recarregar o
        # mesmo contrato; persiste o delta antes desse próximo populate_existing.
        db.flush()


def devolver_reservas_agendamento(
    db, tenant_id, agendamento, user_id=None, motivo=None
):
    return _devolver(
        db, tenant_id, agendamento_id=agendamento.id, user_id=user_id, motivo=motivo
    )


def devolver_creditos_atendimento(
    db, tenant_id, atendimento, user_id=None, motivo=None
):
    devolvidos = _devolver(
        db, tenant_id, atendimento_id=atendimento.id, user_id=user_id, motivo=motivo
    )
    atendimento.pacote_credito_id = None
    atendimento.pacote_movimento_id = None
    return bool(devolvidos)


def _devolver(
    db, tenant_id, agendamento_id=None, atendimento_id=None, user_id=None, motivo=None
):
    query = db.query(BanhoTosaPacoteMovimento).filter(
        BanhoTosaPacoteMovimento.tenant_id == tenant_id
    )
    if atendimento_id:
        query = query.filter(
            BanhoTosaPacoteMovimento.atendimento_id == atendimento_id,
            BanhoTosaPacoteMovimento.tipo == "consumo",
        )
    else:
        query = query.filter(
            BanhoTosaPacoteMovimento.agendamento_id == agendamento_id,
            BanhoTosaPacoteMovimento.tipo == "reserva",
        )
    movimentos = query.order_by(
        BanhoTosaPacoteMovimento.credito_id, BanhoTosaPacoteMovimento.id
    ).all()
    total = 0
    for movimento in movimentos:
        credito = _bloquear_credito(db, tenant_id, movimento.credito_id)
        tipo = "estorno" if movimento.tipo == "consumo" else "estorno_reserva"
        existente = (
            db.query(BanhoTosaPacoteMovimento.id)
            .filter(
                BanhoTosaPacoteMovimento.tenant_id == tenant_id,
                BanhoTosaPacoteMovimento.movimento_origem_id == movimento.id,
                BanhoTosaPacoteMovimento.tipo == tipo,
            )
            .first()
        )
        if existente:
            continue
        campo = "creditos_usados" if tipo == "estorno" else "creditos_reservados"
        setattr(
            credito,
            campo,
            max(
                _decimal(getattr(credito, campo)) - _decimal(movimento.quantidade),
                Decimal("0"),
            ),
        )
        if credito.status == "esgotado":
            credito.status = "ativo"
        db.add(
            BanhoTosaPacoteMovimento(
                tenant_id=tenant_id,
                credito_id=credito.id,
                atendimento_id=movimento.atendimento_id,
                agendamento_id=movimento.agendamento_id,
                agendamento_servico_id=movimento.agendamento_servico_id,
                servico_id=movimento.servico_id,
                movimento_origem_id=movimento.id,
                tipo=tipo,
                quantidade=movimento.quantidade,
                saldo_apos=calcular_saldo_creditos(
                    credito.creditos_total,
                    credito.creditos_usados,
                    credito.creditos_cancelados,
                    credito.creditos_reservados,
                ),
                created_by=user_id,
                observacoes=motivo or "Cancelamento devolveu o saldo ao pacote.",
            )
        )
        _limpar_cobertura_servico(db, tenant_id, movimento)
        db.flush()
        total += 1
    return total


def _limpar_cobertura_servico(db, tenant_id, movimento):
    if not movimento.agendamento_servico_id:
        return
    from app.banho_tosa_models import BanhoTosaAgendamentoServico

    servico = (
        db.query(BanhoTosaAgendamentoServico)
        .filter(
            BanhoTosaAgendamentoServico.tenant_id == tenant_id,
            BanhoTosaAgendamentoServico.id == movimento.agendamento_servico_id,
        )
        .first()
    )
    if servico:
        servico.pacote_credito_id = None
        servico.pacote_quantidade = 0


def _bloquear_credito(db, tenant_id, credito_id):
    return (
        db.query(BanhoTosaPacoteCredito)
        .filter(
            BanhoTosaPacoteCredito.tenant_id == tenant_id,
            BanhoTosaPacoteCredito.id == credito_id,
        )
        .with_for_update(of=BanhoTosaPacoteCredito)
        .populate_existing()
        .one()
    )
