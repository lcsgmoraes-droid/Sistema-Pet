"""XMLs fiscais por empresa, ZIP íntegro e caixa de saída processada fora da emissão.

Datas do usuário são dias civis em São Paulo. O XML oficial confirma ambiente,
direção, autorização, chave e data; o cache apenas localiza os documentos.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from html import escape

from sqlalchemy import func

from app.services import email_service
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.xml_contabilidade_models import XmlContabilidadeConfig, XmlContabilidadeEnvio
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
    _coletar_arquivos,
    _documento,
    gerar_zip_periodo as gerar_zip_periodo,
)

logger = logging.getLogger(__name__)


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
        # Nenhuma varredura do histórico ao ativar: só eventos de emissão novos.
        config.envio_automatico_desde = _agora()
    config.envio_mensal = dados.envio_mensal
    config.dia_envio_mensal = dados.dia_envio_mensal
    config.hora_envio_mensal = dados.hora_envio_mensal
    if not dados.envio_mensal:
        config.proximo_envio_mensal = None
    elif mensal_alterado or not config.proximo_envio_mensal:
        config.proximo_envio_mensal = proxima_data_mensal(
            dados.dia_envio_mensal, dados.hora_envio_mensal
        )
    origens_desativadas = []
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
    return [serializar_envio(row) for row in rows]


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
        if agendado_para.utcoffset() is None or _utc(agendado_para) <= agora:
            raise XmlContabilidadeError(
                "Escolha uma data e um horário futuros para o envio."
            )
        if data_fim > _utc(agendado_para).astimezone(BRASILIA).date():
            raise XmlContabilidadeError(
                "O período deve terminar até a data programada para o envio."
            )
    elif data_fim > agora.astimezone(BRASILIA).date():
        raise XmlContabilidadeError("O período não pode terminar em uma data futura.")
    pendentes = (
        db.query(func.count(XmlContabilidadeEnvio.id))
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.origem.in_(("manual", "agendado")),
            XmlContabilidadeEnvio.status.in_(("pendente", "agendado", "processando")),
        )
        .scalar()
    )
    if pendentes >= 20:
        raise XmlContabilidadeError(
            "Há 20 envios aguardando. Aguarde ou cancele um agendamento antes de criar outro.",
            409,
        )
    envio = XmlContabilidadeEnvio(
        tenant_id=_tenant(tenant_id),
        origem="agendado" if agendado_para else "manual",
        status="agendado" if agendado_para else "pendente",
        email_destino=_exigir_email(db, tenant_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        agendado_para=_utc(agendado_para) if agendado_para else None,
        proxima_tentativa_em=_utc(agendado_para) if agendado_para else agora,
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
    if envio.status != "falhou":
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
    """Chamado sob savepoint pelo hook; não faz commit, HTTP nem SMTP."""
    config = _config(db, tenant_id)
    if (
        not config
        or not config.envio_automatico
        or not config.email_contador
        or not config.envio_automatico_desde
    ):
        return None
    doc = _documento(db, tenant_id, provider, documento_id)
    if not doc:
        return None
    # O cache guarda o horário civil sem fuso. Emissão direta segue esse padrão.
    emissao = doc.data_emissao
    emissao = emissao.replace(tzinfo=BRASILIA) if emissao.tzinfo is None else emissao
    if emissao.astimezone(UTC) < _utc(config.envio_automatico_desde):
        return None
    key = f"automatico:{provider}:{documento_id}:{doc.status}"
    existente = (
        db.query(XmlContabilidadeEnvio)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.idempotency_key == key,
        )
        .first()
    )
    if existente:
        return existente
    envio = XmlContabilidadeEnvio(
        tenant_id=_tenant(tenant_id),
        origem="automatico",
        status="pendente",
        email_destino=config.email_contador,
        data_inicio=emissao.astimezone(BRASILIA).date(),
        data_fim=emissao.astimezone(BRASILIA).date(),
        provider=provider,
        documento_id=str(documento_id),
        documento_status=doc.status,
        proxima_tentativa_em=_agora(),
        idempotency_key=key,
    )
    db.add(envio)
    db.flush()
    return envio


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
        doc = _documento(db, tenant_id, envio.provider, envio.documento_id)
        if not doc:
            raise XmlContabilidadeError(
                "A nota não está disponível para envio fiscal.", 409
            )
        # XML é a fonte da data: o horário legado pode ter sido gravado em UTC.
        arquivos, notas = _coletar_arquivos(
            db,
            tenant_id,
            [doc],
            envio.data_inicio - timedelta(days=1),
            envio.data_fim + timedelta(days=1),
        )
        if not notas:
            raise XmlContabilidadeError(
                "O documento não é uma nota de saída autorizada em produção.", 404
            )
        anexos = [
            {"filename": name, "content": content, "mime_subtype": "xml"}
            for name, content in arquivos
        ]
        nome, quantidade = arquivos[0][0], 1
        assunto = f"XML fiscal de saída — {doc.chave}"
        texto = f"Segue o XML da nota fiscal de saída. Situação: {doc.status}."
        avisos = [n["aviso"] for n in notas if n.get("aviso")]
        texto += "\n" + "\n".join(avisos) if avisos else ""
    else:
        content, nome, quantidade = gerar_zip_periodo(
            db, tenant_id, envio.data_inicio, envio.data_fim
        )
        anexos = [{"filename": nome, "content": content, "mime_subtype": "zip"}]
        assunto = f"XMLs fiscais de saída — {envio.data_inicio:%d/%m/%Y} a {envio.data_fim:%d/%m/%Y}"
        texto = f"Seguem {quantidade} notas fiscais de saída no período de {envio.data_inicio:%d/%m/%Y} a {envio.data_fim:%d/%m/%Y}. O ZIP inclui manifesto com a situação das notas e disponibilidade dos eventos fiscais."
    assunto = f"{identificacao} | {assunto}"
    texto = f"Empresa emitente: {identificacao}\n\n{texto}"
    if not email_service.send_email(
        to=envio.email_destino,
        subject=assunto,
        html_body=f"<p>{escape(texto).replace(chr(10), '<br>')}</p>",
        text_body=texto,
        attachments=anexos,
        simulate_if_unconfigured=False,
    ):
        raise XmlContabilidadeError(
            "O servidor de e-mail não confirmou o envio. Verifique a configuração e tente novamente.",
            503,
        )
    envio.status, envio.enviado_em = "enviado", _agora()
    envio.quantidade_xml, envio.nome_arquivo, envio.ultimo_erro = quantidade, nome, None


def processar_fila_tenant(db, tenant_id, limite=5):
    agora = _agora()
    _criar_mensal_devido(db, tenant_id, agora)
    config = _config(db, tenant_id)
    if config and config.envio_automatico and config.envio_automatico_desde:
        from app.services.xml_contabilidade_reconciliation import reconciliar_pendentes

        reconciliar_pendentes(db, tenant_id, config.envio_automatico_desde)
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
    db.commit()
    total = 0
    for _ in range(min(max(limite, 1), 20)):
        sync_rls_tenant(db, tenant_id)
        envio = (
            db.query(XmlContabilidadeEnvio)
            .filter(
                XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
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
            if isinstance(exc, XmlContabilidadeError) and exc.status_code == 404:
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
