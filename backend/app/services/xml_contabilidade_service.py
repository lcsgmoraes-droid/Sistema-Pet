"""XMLs por documento/evento, lotes manuais e envio mensal do mês anterior.

Datas do usuário são dias civis em São Paulo. O XML oficial confirma ambiente,
direção, autorização, chave e data; o cache apenas localiza os documentos.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from html import escape

from sqlalchemy import and_, func, or_, select

from app.services import email_service
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeTentativa,
)
from app.xml_contabilidade_schemas import XmlContabilidadeConfigRequest

from app.services.xml_contabilidade_common import (
    BRASILIA,
    UTC,
    MAX_TENTATIVAS,
    _tenant,
    _utc,
    _validar_periodo,
    MAX_DOCUMENTOS as MAX_DOCUMENTOS,
    XmlContabilidadeError as XmlContabilidadeError,
)
from app.services.xml_contabilidade_documentos import (
    Documento as Documento,
    _cnpj_empresa,
    _coletar_arquivos as _coletar_arquivos,
    gerar_zip_periodo as gerar_zip_periodo,
    gerar_anexos_periodo,
)

logger = logging.getLogger(__name__)
ORIGENS_LEGADAS = ("agendado",)
ORIGENS_ATIVAS = ("manual", "mensal", "automatico")
AVISO_FLUXO_LEGADO = (
    "Este fluxo antigo foi desativado. Use o envio mensal do mês anterior "
    "completo ou prepare um lote manual."
)
AVISO_ORIGEM_COREPET = (
    "Somente notas e eventos emitidos no CorePet em produção podem ser enviados."
)


class EntregaIndeterminadaError(XmlContabilidadeError):
    """Impede retry automático quando o SMTP já aceitou a mensagem."""

    def __init__(self):
        super().__init__(
            "O SMTP aceitou a mensagem, mas o histórico não foi concluído. Confira com o contador se recebeu antes de tentar novamente manualmente.",
            409,
        )


def _agora():
    return datetime.now(UTC)


def _iso(value):
    return _utc(value).isoformat() if value else None


def _config(db, tenant_id):
    return (
        db.query(XmlContabilidadeConfig)
        .filter(XmlContabilidadeConfig.tenant_id == _tenant(tenant_id))
        .first()
    )


def _data_mensal(ano, mes, dia, hora):
    h, m = map(int, hora.split(":"))
    return datetime(
        ano, mes, min(dia, calendar.monthrange(ano, mes)[1]), h, m, tzinfo=BRASILIA
    )


def proxima_data_mensal(dia, hora, depois=None):
    local = _utc(depois or _agora()).astimezone(BRASILIA)
    alvo = _data_mensal(local.year, local.month, dia, hora)
    if alvo <= local:
        ano, mes = (
            (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
        )
        alvo = _data_mensal(ano, mes, dia, hora)
    return alvo.astimezone(UTC)


def obter_config(db, tenant_id):
    config = _config(db, tenant_id)
    return {
        "email_contador": config.email_contador if config else None,
        "envio_automatico": bool(config and config.envio_automatico),
        "envio_mensal": bool(config and config.envio_mensal),
        "dia_envio_mensal": config.dia_envio_mensal if config else 1,
        "hora_envio_mensal": config.hora_envio_mensal if config else "08:00",
        "proximo_envio_mensal": _iso(config.proximo_envio_mensal) if config else None,
        "smtp_configurado": email_service.is_email_configured(),
        "fuso_horario": "America/Sao_Paulo",
    }


def salvar_config(db, tenant_id, dados):
    dados = (
        dados
        if isinstance(dados, XmlContabilidadeConfigRequest)
        else XmlContabilidadeConfigRequest.model_validate(dados)
    )
    config = _config(db, tenant_id)
    if not config:
        config = XmlContabilidadeConfig(tenant_id=_tenant(tenant_id))
        db.add(config)
    anterior_automatico = bool(config.envio_automatico)
    mensal_alterado = (
        not config.envio_mensal
        or config.dia_envio_mensal != dados.dia_envio_mensal
        or config.hora_envio_mensal != dados.hora_envio_mensal
    )
    config.email_contador = str(dados.email_contador) if dados.email_contador else None
    config.envio_automatico = dados.envio_automatico
    if dados.envio_automatico and not anterior_automatico:
        # Só fatos novos a partir daqui: os eventos têm data oficial própria,
        # mesmo se a nota original tiver sido emitida antes da ativação.
        config.envio_automatico_desde = _agora()
    elif not dados.envio_automatico:
        config.envio_automatico_desde = None
    config.envio_mensal = dados.envio_mensal
    config.dia_envio_mensal = dados.dia_envio_mensal
    config.hora_envio_mensal = dados.hora_envio_mensal
    if not dados.envio_mensal:
        config.proximo_envio_mensal = None
    elif mensal_alterado or not config.proximo_envio_mensal:
        config.proximo_envio_mensal = proxima_data_mensal(
            dados.dia_envio_mensal, dados.hora_envio_mensal
        )
    origens_desativadas = list(ORIGENS_LEGADAS)
    if not dados.envio_automatico:
        origens_desativadas.append("automatico")
    if not dados.envio_mensal:
        origens_desativadas.append("mensal")
    if origens_desativadas:
        for envio in (
            db.query(XmlContabilidadeEnvio)
            .filter(
                XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
                XmlContabilidadeEnvio.origem.in_(origens_desativadas),
                XmlContabilidadeEnvio.status.in_(("pendente", "agendado")),
            )
            .with_for_update()
            .all()
        ):
            envio.status = "cancelado"
            if envio.origem in ORIGENS_LEGADAS:
                envio.ultimo_erro = AVISO_FLUXO_LEGADO
    db.commit()
    return obter_config(db, tenant_id)


def serializar_envio(envio):
    return {
        "id": envio.id,
        "origem": envio.origem,
        "status": envio.status,
        "email_destino": envio.email_destino,
        "data_inicio": envio.data_inicio.isoformat(),
        "data_fim": envio.data_fim.isoformat(),
        "agendado_para": _iso(envio.agendado_para),
        "created_at": _iso(envio.created_at),
        "enviado_em": _iso(envio.enviado_em),
        "proxima_tentativa_em": _iso(envio.proxima_tentativa_em),
        "tentativas": envio.tentativas,
        "quantidade_xml": envio.quantidade_xml,
        "ultimo_erro": envio.ultimo_erro,
        "nome_arquivo": envio.nome_arquivo,
    }


def listar_envios(db, tenant_id, limite=100):
    rows = (
        db.query(XmlContabilidadeEnvio)
        .filter(XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id))
        .order_by(XmlContabilidadeEnvio.id.desc())
        .limit(min(max(limite, 1), 200))
        .all()
    )
    ids = [row.id for row in rows]
    ultimos = {}
    if ids:
        recentes = (
            select(func.max(XmlContabilidadeTentativa.id))
            .where(
                XmlContabilidadeTentativa.tenant_id == _tenant(tenant_id),
                XmlContabilidadeTentativa.envio_id.in_(ids),
            )
            .group_by(XmlContabilidadeTentativa.envio_id)
        )
        for row in db.execute(
            select(
                XmlContabilidadeTentativa.id,
                XmlContabilidadeTentativa.envio_id,
                XmlContabilidadeTentativa.numero_tentativa,
                XmlContabilidadeTentativa.resumo,
            ).where(
                XmlContabilidadeTentativa.tenant_id == _tenant(tenant_id),
                XmlContabilidadeTentativa.id.in_(recentes),
            )
        ).all():
            ultimos[row.envio_id] = {
                **row.resumo,
                "id": row.id,
                "numero_tentativa": row.numero_tentativa,
            }
    return [
        {**serializar_envio(row), "ultimo_relatorio": ultimos.get(row.id)}
        for row in rows
    ]


def _exigir_email(db, tenant_id):
    config = _config(db, tenant_id)
    if not config or not config.email_contador:
        raise XmlContabilidadeError(
            "Cadastre o e-mail do contador nas configurações antes de enviar."
        )
    return config.email_contador


def criar_envio(db, tenant_id, data_inicio, data_fim, agendado_para=None):
    _validar_periodo(data_inicio, data_fim)
    agora = _agora()
    if agendado_para is not None:
        raise XmlContabilidadeError(AVISO_FLUXO_LEGADO)
    if data_fim > agora.astimezone(BRASILIA).date():
        raise XmlContabilidadeError("O período não pode terminar em uma data futura.")
    pendentes = (
        db.query(func.count(XmlContabilidadeEnvio.id))
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.origem == "manual",
            XmlContabilidadeEnvio.status.in_(("pendente", "agendado", "processando")),
        )
        .scalar()
    )
    if pendentes >= 20:
        raise XmlContabilidadeError(
            "Há 20 envios aguardando. Aguarde ou cancele um envio antes de criar outro.",
            409,
        )
    envio = XmlContabilidadeEnvio(
        tenant_id=_tenant(tenant_id),
        origem="manual",
        status="pendente",
        email_destino=_exigir_email(db, tenant_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        agendado_para=None,
        proxima_tentativa_em=agora,
    )
    db.add(envio)
    db.commit()
    return serializar_envio(envio)


def _buscar_envio_bloqueado(db, tenant_id, envio_id):
    envio = (
        db.query(XmlContabilidadeEnvio)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.id == envio_id,
        )
        .with_for_update()
        .first()
    )
    if not envio:
        raise XmlContabilidadeError("Envio não encontrado nesta empresa.", 404)
    return envio


def cancelar_envio(db, tenant_id, envio_id):
    envio = _buscar_envio_bloqueado(db, tenant_id, envio_id)
    if envio.status not in {"pendente", "agendado"}:
        raise XmlContabilidadeError(
            "Somente um envio aguardando pode ser cancelado.", 409
        )
    envio.status = "cancelado"
    db.commit()
    return serializar_envio(envio)


def reenviar_envio(db, tenant_id, envio_id):
    envio = _buscar_envio_bloqueado(db, tenant_id, envio_id)
    if envio.origem == "automatico" and envio.provider != "intnfe":
        raise XmlContabilidadeError(AVISO_ORIGEM_COREPET, 409)
    if envio.origem in ORIGENS_LEGADAS or (
        envio.origem == "automatico"
        and not (envio.idempotency_key or "").startswith(("nota:", "evento:"))
    ):
        raise XmlContabilidadeError(AVISO_FLUXO_LEGADO, 409)
    if envio.status not in {"falhou", "pendencias"}:
        raise XmlContabilidadeError(
            "Somente um envio com falha pode ser tentado novamente.", 409
        )
    envio.email_destino = _exigir_email(db, tenant_id)
    envio.status, envio.tentativas, envio.ultimo_erro = "pendente", 0, None
    envio.proxima_tentativa_em = _agora()
    envio.processamento_iniciado_em = None
    db.commit()
    return serializar_envio(envio)


def enfileirar_documento(db, tenant_id, provider, documento_id):
    """Chamado sob savepoint; emissão não aguarda consulta externa nem e-mail."""
    if provider != "intnfe":
        return None
    from app.services.xml_contabilidade_individual import enfileirar_nota

    return enfileirar_nota(db, tenant_id, provider, documento_id, _agora())


def _criar_mensal_devido(db, tenant_id, agora):
    config = (
        db.query(XmlContabilidadeConfig)
        .filter(XmlContabilidadeConfig.tenant_id == _tenant(tenant_id))
        .with_for_update()
        .first()
    )
    if (
        not config
        or not config.envio_mensal
        or not config.email_contador
        or not config.proximo_envio_mensal
        or _utc(config.proximo_envio_mensal) > agora
    ):
        return
    referencia = _utc(config.proximo_envio_mensal).astimezone(BRASILIA)
    fim = date(referencia.year, referencia.month, 1) - timedelta(days=1)
    inicio = fim.replace(day=1)
    key = f"mensal:{inicio:%Y-%m}"
    existente = (
        db.query(XmlContabilidadeEnvio.id)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.idempotency_key == key,
        )
        .first()
    )
    if not existente:
        db.add(
            XmlContabilidadeEnvio(
                tenant_id=_tenant(tenant_id),
                origem="mensal",
                status="pendente",
                email_destino=config.email_contador,
                data_inicio=inicio,
                data_fim=fim,
                agendado_para=config.proximo_envio_mensal,
                proxima_tentativa_em=agora,
                idempotency_key=key,
            )
        )
    # Se o serviço ficou parado, gera os meses devidos um por ciclo, sem pular
    # períodos nem criar um envio por cada execução do worker.
    config.proximo_envio_mensal = proxima_data_mensal(
        config.dia_envio_mensal,
        config.hora_envio_mensal,
        depois=_utc(config.proximo_envio_mensal) + timedelta(seconds=1),
    )
    db.commit()


def _processar_envio(db, tenant_id, envio):
    from app.services import xml_contabilidade_relatorios as relatorios

    # Operações sem registro persistido não possuem histórico de tentativas.
    if not isinstance(getattr(envio, "id", None), int):
        return _executar_envio(db, tenant_id, envio)
    relatorio = relatorios.RelatorioTentativa(db, tenant_id, envio)
    token = relatorios.ativar(relatorio)
    try:
        _executar_envio(db, tenant_id, envio)
        relatorios.persistir(db, relatorio, "enviado")
        db.commit()
    except Exception as exc:
        if relatorio.smtp_aceitou:
            try:
                db.rollback()
                sync_rls_tenant(db, tenant_id)
                relatorios.persistir(
                    db,
                    relatorio,
                    "interrompido",
                    "O SMTP aceitou a mensagem, mas o histórico não foi concluído. Confira com o contador antes de repetir manualmente.",
                )
                db.commit()
            except Exception:
                # O claim já foi persistido antes do SMTP. Se o banco também
                # estiver indisponível, a recuperação continua conservadora.
                try:
                    db.rollback()
                except Exception:
                    pass
            raise EntregaIndeterminadaError() from None
        db.rollback()
        sync_rls_tenant(db, tenant_id)
        if relatorio.smtp_iniciado:
            resultado, motivo = (
                "falha_smtp",
                "O servidor SMTP não confirmou a aceitação da mensagem. Nenhum envio foi confirmado nesta tentativa.",
            )
        elif isinstance(exc, XmlContabilidadeError) and str(exc).startswith(
            "Há notas pendentes"
        ):
            resultado, motivo = (
                "pendencias",
                "Há emissões pendentes de confirmação e nenhum documento pronto para envio.",
            )
        elif isinstance(exc, XmlContabilidadeError) and exc.status_code == 404:
            resultado, motivo = (
                "sem_notas",
                "Nenhuma nota ou evento CorePet elegível foi encontrado no período.",
            )
        else:
            resultado, motivo = (
                ("bloqueado" if isinstance(exc, XmlContabilidadeError) else "falhou"),
                "Não foi possível preparar ou enviar todos os documentos. Confira as informações das notas e tente novamente após resolver.",
            )
        if isinstance(exc, XmlContabilidadeError) and resultado not in {
            "pendencias",
            "sem_notas",
        }:
            motivo = relatorios.motivo_seguro(exc)
        relatorios.persistir(db, relatorio, resultado, motivo)
        db.commit()  # O rollback do chamador não apaga esta evidência.
        raise
    finally:
        relatorios.desativar(token)


def _executar_envio(db, tenant_id, envio):
    if envio.origem == "automatico" and envio.provider != "intnfe":
        raise XmlContabilidadeError(AVISO_ORIGEM_COREPET, 409)
    if envio.origem not in ORIGENS_ATIVAS or (
        envio.origem == "automatico"
        and not (getattr(envio, "idempotency_key", None) or "").startswith(
            ("nota:", "evento:")
        )
    ):
        raise XmlContabilidadeError(AVISO_FLUXO_LEGADO, 409)
    if not email_service.is_email_configured():
        raise XmlContabilidadeError(
            "O envio de e-mail do sistema não está configurado. Contate o administrador.",
            503,
        )
    from app.models import Tenant

    empresa = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    identificacao = (
        f"{empresa.razao_social or empresa.name} — CNPJ {_cnpj_empresa(db, tenant_id)}"
        if empresa
        else ""
    )
    if envio.origem == "automatico":
        from app.services.xml_contabilidade_individual import preparar_anexos_individual

        anexos, nome, quantidade = preparar_anexos_individual(db, tenant_id, envio)
        assunto = "XML fiscal de saída — nota ou evento registrado"
        texto = "Segue o XML oficial da nota fiscal ou do evento registrado. Cada nota e cada novo evento são enviados separadamente, sem alterar o XML original."
    else:
        anexos, nome, quantidade = gerar_anexos_periodo(
            db, tenant_id, envio.data_inicio, envio.data_fim
        )
        assunto = f"XMLs fiscais de saída — {envio.data_inicio:%d/%m/%Y} a {envio.data_fim:%d/%m/%Y}"
        texto = f"Seguem os XMLs de {quantidade} notas fiscais de saída e seus eventos no período de {envio.data_inicio:%d/%m/%Y} a {envio.data_fim:%d/%m/%Y}. Cada tipo de documento está organizado em seu próprio ZIP, com manifesto para conferência."
    assunto = f"{identificacao} | {assunto}"
    texto = f"Empresa emitente: {identificacao}\n\n{texto}"
    from app.services.xml_contabilidade_relatorios import atual

    relatorio = atual()
    if relatorio:
        relatorio.anexos_prontos(anexos)
        resumo_preparacao = relatorio.snapshot("preparacao")["contagens"]
        texto = (
            f"Empresa emitente: {identificacao}\n\n"
            f"Este lote contém {resumo_preparacao['notas_preparadas']} XML(s) de notas e "
            f"{resumo_preparacao['eventos_preparados']} evento(s) oficiais preparados. "
            f"{resumo_preparacao['notas_pendentes']} nota(s) pendente(s) de confirmação não foram incluídas. "
            "Cada tipo de documento está organizado em seu próprio anexo."
        )
        if resumo_preparacao["notas_pendentes"]:
            texto += " Consulte as pendências em relatorio.json nos ZIPs."
        relatorio.smtp_iniciado = True
    confirmado = email_service.send_email(
        to=envio.email_destino,
        subject=assunto,
        html_body=f"<p>{escape(texto).replace(chr(10), '<br>')}</p>",
        text_body=texto,
        attachments=anexos,
        simulate_if_unconfigured=False,
    )
    if relatorio:
        relatorio.smtp_aceitou = bool(confirmado)
    if not confirmado:
        raise XmlContabilidadeError(
            "O servidor de e-mail não confirmou o envio. Verifique a configuração e tente novamente.",
            503,
        )
    envio.status, envio.enviado_em = "enviado", _agora()
    envio.quantidade_xml, envio.nome_arquivo, envio.ultimo_erro = quantidade, nome, None


def processar_fila_tenant(db, tenant_id, limite=5):
    agora = _agora()
    # Agendamentos de período avulso continuam desativados.
    legados = (
        db.query(XmlContabilidadeEnvio)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            or_(
                XmlContabilidadeEnvio.origem.in_(ORIGENS_LEGADAS),
                and_(
                    XmlContabilidadeEnvio.origem == "automatico",
                    or_(
                        XmlContabilidadeEnvio.provider.is_(None),
                        XmlContabilidadeEnvio.provider != "intnfe",
                        XmlContabilidadeEnvio.idempotency_key.is_(None),
                        and_(
                            ~XmlContabilidadeEnvio.idempotency_key.like("nota:%"),
                            ~XmlContabilidadeEnvio.idempotency_key.like("evento:%"),
                        ),
                    ),
                ),
            ),
            XmlContabilidadeEnvio.status.in_(("pendente", "agendado")),
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for envio in legados:
        envio.status = "cancelado"
        envio.ultimo_erro = (
            AVISO_ORIGEM_COREPET
            if envio.origem == "automatico" and envio.provider != "intnfe"
            else AVISO_FLUXO_LEGADO
        )
    db.commit()
    _criar_mensal_devido(db, tenant_id, agora)
    config = _config(db, tenant_id)
    if config and config.envio_automatico and config.envio_automatico_desde:
        from app.services.xml_contabilidade_individual import capturar_novos_eventos

        capturar_novos_eventos(db, tenant_id, agora)
    # Recuperação conservadora: após queda durante SMTP não se pode afirmar se o
    # destinatário recebeu. Mantém histórico e exige tentativa manual explícita.
    interrompidos = (
        db.query(XmlContabilidadeEnvio)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.status == "processando",
            XmlContabilidadeEnvio.processamento_iniciado_em
            < agora - timedelta(minutes=30),
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for envio in interrompidos:
        envio.status = "falhou"
        envio.ultimo_erro = "O processamento foi interrompido. Confira com o contador se recebeu antes de tentar novamente."
        from app.services import xml_contabilidade_relatorios as relatorios

        relatorios.persistir(
            db,
            relatorios.RelatorioTentativa(db, tenant_id, envio, inventariar=False),
            "interrompido",
            "Processamento interrompido; o resultado SMTP é indeterminado. Confira o destinatário antes de repetir.",
        )
    db.commit()
    total = 0
    for _ in range(min(max(limite, 1), 20)):
        sync_rls_tenant(db, tenant_id)
        envio = (
            db.query(XmlContabilidadeEnvio)
            .filter(
                XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
                XmlContabilidadeEnvio.origem.in_(ORIGENS_ATIVAS),
                XmlContabilidadeEnvio.status.in_(("pendente", "agendado")),
                XmlContabilidadeEnvio.proxima_tentativa_em <= agora,
            )
            .order_by(
                XmlContabilidadeEnvio.proxima_tentativa_em, XmlContabilidadeEnvio.id
            )
            .with_for_update(skip_locked=True)
            .first()
        )
        if not envio:
            db.rollback()
            break
        envio.status, envio.processamento_iniciado_em = "processando", _agora()
        envio.tentativas += 1
        db.commit()  # claim durável antes de rede/SMTP; outro worker não repete.
        try:
            _processar_envio(db, tenant_id, envio)
        except Exception as exc:
            db.rollback()
            envio = _buscar_envio_bloqueado(db, tenant_id, envio.id)
            mensagem = (
                str(exc)
                if isinstance(exc, XmlContabilidadeError)
                else "Não foi possível preparar ou enviar os XMLs. Tente novamente."
            )
            envio.ultimo_erro = mensagem[:500]
            if isinstance(exc, EntregaIndeterminadaError):
                envio.status = "falhou"
            elif isinstance(exc, XmlContabilidadeError) and str(exc).startswith(
                "Há notas pendentes"
            ):
                envio.status, envio.quantidade_xml = "pendencias", 0
            elif isinstance(exc, XmlContabilidadeError) and exc.status_code == 404:
                envio.status, envio.quantidade_xml = "sem_notas", 0
            elif envio.tentativas >= MAX_TENTATIVAS:
                envio.status = "falhou"
            else:
                envio.status = "pendente"
                envio.proxima_tentativa_em = _agora() + timedelta(
                    minutes=5 if envio.tentativas == 1 else 30
                )
            logger.warning(
                "Falha no envio XML contábil id=%s tipo=%s",
                envio.id,
                type(exc).__name__,
            )
        db.commit()
        total += 1
    return total


def executar_rotina_xml_contabilidade(session_factory=None):
    """Descobre só tenants no diretório global e abre uma sessão isolada por empresa."""
    from app.db import SessionLocal
    from app.models import Tenant
    from app.security.module_access import _load_active_modules

    factory = session_factory or SessionLocal
    with factory() as discovery:
        tenant_ids = [
            row[0]
            for row in discovery.query(Tenant.id)
            .filter(Tenant.status == "active")
            .all()
        ]
    total = 0
    for tenant_id in tenant_ids:
        try:
            with tenant_context(tenant_id), factory() as db:
                sync_rls_tenant(db, tenant_id)
                if "fiscal" not in _load_active_modules(db, str(tenant_id)):
                    continue
                total += processar_fila_tenant(db, tenant_id)
        except Exception as exc:
            logger.warning(
                "Rotina de XML contábil falhou tenant=%s tipo=%s",
                tenant_id,
                type(exc).__name__,
            )
    return total
