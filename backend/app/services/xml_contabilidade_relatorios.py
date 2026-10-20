"""Snapshots de tentativas, sem XML, segredos ou consultas remotas adicionais."""

from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from urllib.parse import urlencode
from zipfile import ZipFile, BadZipFile

from sqlalchemy import func, select
from sqlalchemy.orm import load_only, noload

from app.services.xml_contabilidade_common import (
    BRASILIA,
    NS,
    UTC,
    _tenant,
    _utc,
    XmlContabilidadeError,
)
from app.services.xml_contabilidade_reconciliation import STATUS_PENDENTES
from app.vendas_models import Venda
from app.xml_contabilidade_models import (
    XmlContabilidadeEnvio,
    XmlContabilidadeTentativa,
)

_ATUAL = ContextVar("xml_contabilidade_relatorio", default=None)
ACOES_PENDENTES = "Consulte a situação na central de notas de saída. Após regularizar, solicite um novo lote do período; ele pode conter notas já enviadas."
NOMES_EVENTOS = {
    "110111": "Cancelamento",
    "110112": "Cancelamento por substituição",
    "110110": "Carta de correção",
}


def atual():
    return _ATUAL.get()


def ativar(relatorio):
    return _ATUAL.set(relatorio)


def desativar(token):
    _ATUAL.reset(token)


def valor_oficial(root):
    raw = root.findtext(".//n:infNFe/n:total/n:ICMSTot/n:vNF", namespaces=NS)
    if not isinstance(raw, str) or not re.fullmatch(
        r"[0-9]{1,15}(?:\.[0-9]{1,2})?", raw
    ):
        return None
    try:
        valor = Decimal(raw)
        return (
            format(valor.quantize(Decimal("0.01")), ".2f")
            if valor.is_finite()
            else None
        )
    except InvalidOperation:
        return None


def _iso(value):
    return _utc(value).isoformat() if value else None


def _texto(value, limite=120):
    # Metadados esperados têm tamanho limitado e nunca contêm markup/XML.
    valor = str(value or "")
    return valor[:limite] if "<" not in valor and ">" not in valor else None


def motivo_seguro(exc):
    if isinstance(exc, XmlContabilidadeError):
        mensagem = str(exc)
        if not any(
            trecho in mensagem.lower()
            for trecho in ("<", ">", "token", "senha", "password", "secret", "bearer")
        ):
            return mensagem[:500]
    return "Não foi possível preparar ou enviar os documentos. Consulte os motivos das notas e solicite novo envio após resolver."


class RelatorioTentativa:
    def __init__(self, db, tenant_id, envio, *, inventariar=True):
        self.tenant_id, self.envio_id = _tenant(tenant_id), envio.id
        self.iniciado_em = datetime.now(UTC)
        self.origem, self.email = envio.origem, envio.email_destino
        self.inicio, self.fim = envio.data_inicio, envio.data_fim
        self.chave_envio = envio.idempotency_key or ""
        self.documentos, self.validados, self.anexos = {}, {}, []
        self.fontes = {}
        self.smtp_aceitou = False
        self.smtp_iniciado = False
        self.contagens_verificadas = inventariar
        if inventariar:
            self._inventario(db, envio)

    def _inventario(self, db, envio):
        query = (
            db.query(Venda)
            .options(
                noload("*"),
                load_only(
                    Venda.id,
                    Venda.nfe_chave,
                    Venda.nfe_numero,
                    Venda.nfe_modelo,
                    Venda.nfe_status,
                    Venda.nfe_data_emissao,
                ),
            )
            .filter(
                Venda.tenant_id == self.tenant_id,
                Venda.nfe_provider == "intnfe",
                Venda.nfe_ambiente == 1,
                Venda.nfe_status.in_(
                    ("autorizada", "cancelada", "cancelado", *STATUS_PENDENTES)
                ),
            )
        )
        if envio.origem == "automatico":
            if (
                envio.provider != "intnfe"
                or not str(envio.documento_id or "").isdigit()
            ):
                return
            query = query.filter(Venda.id == int(envio.documento_id))
        else:
            query = query.filter(
                Venda.nfe_data_emissao >= datetime.combine(self.inicio, time.min),
                Venda.nfe_data_emissao
                < datetime.combine(self.fim + timedelta(days=1), time.min),
            )
        for venda in query.order_by(Venda.id).limit(10001).all():
            self._venda(
                venda, considerar_nota=not self.chave_envio.startswith("evento:")
            )

    def _venda(self, venda, *, considerar_nota=True):
        ref = str(venda.id)
        doc = self.documentos.get(ref)
        if doc is None:
            numero, chave = _texto(venda.nfe_numero), _texto(venda.nfe_chave, 44)
            parametros = {"venda_id": venda.id, "abrir": "1"}
            if numero or chave:
                parametros["busca"] = numero or chave
            doc = {
                "documento_id": ref,
                "venda_id": venda.id,
                "provider": "intnfe",
                "numero": numero,
                "chave": chave,
                "modelo": _texto(venda.nfe_modelo, 2),
                "data_emissao": venda.nfe_data_emissao.isoformat()
                if venda.nfe_data_emissao
                else None,
                "status_fiscal": _texto(venda.nfe_status, 30),
                "estado": "nao_preparada",
                "enviada": False,
                "valor_nf": None,
                "motivo": None,
                "acao_recomendada": None,
                "eventos": [],
                "link_corepet": "/notas-fiscais/saida?" + urlencode(parametros),
                "_considerar_nota": considerar_nota,
                "_preparada": False,
            }
            self.documentos[ref] = doc
        doc["status_fiscal"] = _texto(venda.nfe_status, 30)
        if doc["status_fiscal"] in STATUS_PENDENTES:
            doc["estado"] = "pendente"
            doc["motivo"] = (
                "Emissão ainda sem confirmação fiscal. Não foi incluída nos anexos."
            )
            doc["acao_recomendada"] = ACOES_PENDENTES
        elif doc["estado"] == "pendente":
            doc["estado"] = "nao_preparada"
            doc["motivo"] = (
                f"A consulta fiscal retornou a situação {doc['status_fiscal']}; esta nota ainda não tem XML preparado nesta tentativa."
            )
            doc["acao_recomendada"] = (
                "Confira a situação e os motivos na central de notas de saída antes de solicitar um novo lote."
            )
        return doc

    def nota_validada(self, doc, root, data_real):
        if doc.provider != "intnfe" or doc.venda is None:
            return
        ref = str(doc.documento_id)
        self.fontes[ref] = doc
        self.validados[ref] = {
            "valor_nf": valor_oficial(root),
            "numero": root.findtext(".//n:infNFe/n:ide/n:nNF", namespaces=NS),
            "chave": doc.chave,
            "data_emissao": data_real.isoformat(),
        }
        considerar = (
            self.inicio <= data_real <= self.fim
            and not self.chave_envio.startswith("evento:")
        )
        if considerar or ref in self.documentos:
            registro = self._venda(doc.venda, considerar_nota=considerar)
            registro["_considerar_nota"] = considerar
            if not considerar:
                registro.update(
                    estado="excluida",
                    motivo="A data oficial de emissão do XML está fora do período de notas desta tentativa.",
                )
            self._aplicar_validados(registro)

    def _aplicar_validados(self, registro):
        dados = self.validados.get(registro["documento_id"], {})
        for campo in ("valor_nf", "chave", "data_emissao"):
            if campo in dados:
                registro[campo] = dados[campo]
        if dados.get("numero"):
            registro["numero"] = _texto(dados["numero"])

    def coleta(self, doc, nota):
        if doc.provider != "intnfe" or doc.venda is None:
            return
        considerar = self.inicio.isoformat() <= nota[
            "data_emissao"
        ] <= self.fim.isoformat() and not self.chave_envio.startswith("evento:")
        eventos = [
            e
            for e in nota.get("eventos", [])
            if considerar
            or self.inicio.isoformat() <= e["data_registro"] <= self.fim.isoformat()
        ]
        if not considerar and not eventos:
            return
        registro = self._venda(doc.venda, considerar_nota=considerar)
        registro["_considerar_nota"] = considerar
        registro["status_fiscal"] = nota["status"]
        registro["estado"] = "preparada" if considerar else "somente_eventos"
        registro["_preparada"] = considerar
        registro["motivo"], registro["acao_recomendada"] = None, None
        self._aplicar_validados(registro)
        unicos = {e["identidade"]: e for e in registro["eventos"]}
        for evento in eventos:
            unicos[evento["identidade"]] = {
                "identidade": evento["identidade"],
                "tipo": evento["tipo"],
                "nome": NOMES_EVENTOS.get(evento["tipo"], f"Evento {evento['tipo']}"),
                "sequencia": evento["sequencia"],
                "protocolo": evento["protocolo"],
                "data_registro": evento["data_registro"],
                "preparado": True,
                "enviado": False,
            }
        registro["eventos"] = list(unicos.values())

    def evento_encontrado(self, chave, evento):
        for ref, dados in self.validados.items():
            if dados["chave"] != chave:
                continue
            considerar = self.inicio.isoformat() <= dados[
                "data_emissao"
            ] <= self.fim.isoformat() and not self.chave_envio.startswith("evento:")
            if (
                not considerar
                and not self.inicio.isoformat() <= evento.data <= self.fim.isoformat()
            ):
                continue
            doc = self.fontes[ref]
            registro = self._venda(doc.venda, considerar_nota=considerar)
            registro["_considerar_nota"] = considerar
            self._aplicar_validados(registro)
            unicos = {e["identidade"]: e for e in registro["eventos"]}
            if evento.identidade not in unicos:
                unicos[evento.identidade] = {
                    "identidade": evento.identidade,
                    "tipo": evento.tipo,
                    "nome": NOMES_EVENTOS.get(evento.tipo, f"Evento {evento.tipo}"),
                    "sequencia": evento.sequencia,
                    "protocolo": evento.protocolo,
                    "data_registro": evento.data,
                    "preparado": False,
                    "enviado": False,
                }
            registro["eventos"] = list(unicos.values())

    def pendentes(self, vendas):
        for venda in vendas:
            self._venda(venda)

    def excluir(self, doc, motivo):
        registro = self.documentos.get(str(doc.documento_id))
        if registro:
            registro.update(
                _considerar_nota=False,
                estado="excluida",
                motivo=motivo,
                acao_recomendada="Confira a identificação fiscal na central de notas de saída.",
            )

    def falha_documento(self, doc, exc):
        if doc.provider != "intnfe" or doc.venda is None:
            return
        registro = self._venda(doc.venda)
        mensagem = str(exc).lower() if isinstance(exc, XmlContabilidadeError) else ""
        motivo = (
            "Não foi possível obter ou confirmar o XML e todos os eventos desta nota."
        )
        if "cancelamento" in mensagem:
            motivo = (
                "O comprovante XML oficial do cancelamento está ausente ou inválido."
            )
        elif "correção" in mensagem or "sequência" in mensagem:
            motivo = "Uma sequência de carta de correção está ausente ou inválida."
        elif "referência fiscal" in mensagem:
            motivo = "A referência da emissão CorePet está ausente ou inválida."
        elif "protocolo" in mensagem:
            motivo = "O XML não possui protocolo fiscal válido."
        elif "xml" in mensagem and (
            "inválid" in mensagem or "não corresponde" in mensagem
        ):
            motivo = "O XML retornado não corresponde à nota ou não é válido."
        registro.update(
            motivo=motivo_seguro(exc)
            if isinstance(exc, XmlContabilidadeError)
            else motivo,
            acao_recomendada="Consulte a nota na central de saída e confirme os documentos no emissor antes de solicitar novo lote.",
        )

    def evento_individual(self, doc, evento):
        registro = self._venda(doc.venda, considerar_nota=False)
        registro.update(_considerar_nota=False, estado="somente_eventos")
        registro["eventos"] = [
            {
                "identidade": evento.identidade,
                "tipo": evento.tipo,
                "nome": NOMES_EVENTOS.get(evento.tipo, f"Evento {evento.tipo}"),
                "sequencia": evento.sequencia,
                "protocolo": evento.protocolo,
                "data_registro": _utc(evento.registrado_em)
                .astimezone(BRASILIA)
                .date()
                .isoformat(),
                "preparado": True,
                "enviado": False,
            }
        ]

    def anexos_prontos(self, anexos):
        self.anexos = [
            {
                "nome_arquivo": a["filename"],
                "tipo_documento": a["filename"].split("-20", 1)[0]
                if a["filename"].endswith(".zip")
                else "xml",
                "bytes": len(a["content"]),
            }
            for a in anexos
        ]
        for resumo, anexo in zip(self.anexos, anexos):
            if anexo["filename"].endswith(".zip"):
                try:
                    with ZipFile(BytesIO(anexo["content"])) as arquivo:
                        resumo["quantidade_xml"] = sum(
                            n.endswith(".xml") for n in arquivo.namelist()
                        )
                except BadZipFile:
                    resumo["quantidade_xml"] = None
            else:
                resumo["quantidade_xml"] = 1

    def snapshot(self, resultado, motivo=None):
        docs = list(deepcopy(self.documentos).values())
        eventos = {}
        for doc in docs:
            doc["enviada"] = bool(self.smtp_aceitou and doc["_preparada"])
            for ev in doc["eventos"]:
                ev["enviado"] = bool(self.smtp_aceitou and ev["preparado"])
                eventos[ev["identidade"]] = ev
            if not self.smtp_aceitou and doc["estado"] != "pendente":
                doc["motivo"] = (
                    doc["motivo"]
                    or motivo
                    or "O envio não foi concluído nesta tentativa."
                )
                doc["acao_recomendada"] = (
                    doc["acao_recomendada"]
                    or "Confira o motivo da tentativa e solicite um novo envio após resolver."
                )
        unicas = {}
        for doc in docs:
            if not doc["_considerar_nota"]:
                continue
            chave = doc["chave"] or doc["documento_id"]
            anterior = unicas.get(chave)
            if anterior is None or (doc["_preparada"], doc["valor_nf"] is not None) > (
                anterior["_preparada"],
                anterior["valor_nf"] is not None,
            ):
                unicas[chave] = doc
        notas = list(unicas.values())
        pendentes = [d for d in notas if d["estado"] == "pendente"]
        if resultado == "enviado" and self.smtp_aceitou and pendentes:
            resultado = "enviado_com_pendencias"
        elif resultado == "sem_notas" and pendentes:
            resultado = "pendencias"
        grupos = {}
        for ev in eventos.values():
            grupo = grupos.setdefault(
                ev["tipo"],
                {
                    "tipo": ev["tipo"],
                    "nome": ev["nome"],
                    "encontrados": 0,
                    "preparados": 0,
                    "enviados": 0,
                },
            )
            grupo["encontrados"] += 1
            grupo["preparados"] += int(ev["preparado"])
            grupo["enviados"] += int(ev["enviado"])
        canceladas = [
            d for d in notas if d["status_fiscal"] in {"cancelada", "cancelado"}
        ]
        enviadas = [d for d in notas if d["enviada"]]
        valores = self._valores(notas, canceladas, enviadas)
        resumo = {
            "envio_id": self.envio_id,
            "iniciado_em": _iso(self.iniciado_em),
            "concluido_em": _iso(datetime.now(UTC)),
            "resultado": resultado,
            "contagens_verificadas": self.contagens_verificadas,
            "origem": self.origem,
            "email_destino": self.email,
            "data_inicio": self.inicio.isoformat(),
            "data_fim": self.fim.isoformat(),
            "motivo": motivo,
            "acao_recomendada": ACOES_PENDENTES
            if pendentes
            else (
                "Confira o motivo e solicite um novo envio após resolver."
                if motivo
                else None
            ),
            "contagens": {
                "notas_encontradas": len(notas),
                "notas_preparadas": sum(d["_preparada"] for d in notas),
                "notas_enviadas": len(enviadas),
                "notas_nao_enviadas": len(notas) - len(enviadas),
                "notas_pendentes": len(pendentes),
                "notas_canceladas": len(canceladas),
                "eventos_encontrados": len(eventos),
                "eventos_preparados": sum(e["preparado"] for e in eventos.values()),
                "eventos_enviados": sum(e["enviado"] for e in eventos.values()),
                "eventos_por_tipo": sorted(grupos.values(), key=lambda g: g["tipo"]),
            },
            "valores": valores,
            "confirmacao_envio": "aceito_smtp"
            if self.smtp_aceitou
            else ("indeterminada" if resultado == "interrompido" else "nao_enviado"),
        }
        if resultado == "interrompido":
            resumo["acao_recomendada"] = (
                "Confira com o contador se recebeu antes de tentar novamente manualmente."
            )
        elif resultado == "falha_smtp":
            resumo["acao_recomendada"] = (
                "Verifique a configuração e a disponibilidade do e-mail e tente novamente. "
                "Se o resultado for indeterminado, confirme o recebimento com o contador antes de reenviar."
            )
        elif resultado in {"bloqueado", "falhou"}:
            resumo["acao_recomendada"] = (
                "Confira o motivo principal desta tentativa e os documentos indicados. "
                "Resolva a falha antes de solicitar um novo envio."
            )
        if not self.contagens_verificadas:
            resumo["contagens"] = {
                k: [] if k == "eventos_por_tipo" else None for k in resumo["contagens"]
            }
            resumo["valores"] = {
                "moeda": "BRL",
                "total_notas": None,
                "total_canceladas": None,
                "total_liquido": None,
                "total_enviadas": None,
                "total_canceladas_enviadas": None,
                "total_nao_enviadas": None,
                "notas_com_valor": None,
                "notas_sem_valor": None,
                "cobertura": {},
            }
        for doc in docs:
            doc.pop("_considerar_nota", None)
            doc.pop("_preparada", None)
        return {
            **resumo,
            "documentos": docs,
            "pendencias": [
                {
                    "codigo": "emissao_sem_confirmacao",
                    "documento_id": d["documento_id"],
                    "motivo": d["motivo"],
                    "acao_recomendada": d["acao_recomendada"],
                }
                for d in pendentes
            ],
            "anexos": self.anexos,
            "versao": 1,
        }

    @staticmethod
    def _valores(notas, canceladas, enviadas):
        grupos = {
            "encontradas": notas,
            "canceladas": canceladas,
            "enviadas": enviadas,
            "canceladas_enviadas": [d for d in canceladas if d["enviada"]],
            "nao_enviadas": [d for d in notas if not d["enviada"]],
        }
        cobertura, totais = {}, {}
        for nome, docs in grupos.items():
            conhecidos = [
                Decimal(d["valor_nf"]) for d in docs if d["valor_nf"] is not None
            ]
            cobertura[nome] = {
                "com_valor": len(conhecidos),
                "sem_valor": len(docs) - len(conhecidos),
            }
            totais[nome] = (
                format(sum(conhecidos, Decimal("0.00")), ".2f")
                if len(conhecidos) == len(docs)
                else None
            )
        liquido = (
            format(
                Decimal(totais["encontradas"]) - Decimal(totais["canceladas"]), ".2f"
            )
            if totais["encontradas"] is not None and totais["canceladas"] is not None
            else None
        )
        return {
            "moeda": "BRL",
            "total_notas": totais["encontradas"],
            "total_canceladas": totais["canceladas"],
            "total_liquido": liquido,
            "total_enviadas": totais["enviadas"],
            "total_canceladas_enviadas": totais["canceladas_enviadas"],
            "total_nao_enviadas": totais["nao_enviadas"],
            "notas_com_valor": cobertura["encontradas"]["com_valor"],
            "notas_sem_valor": cobertura["encontradas"]["sem_valor"],
            "cobertura": cobertura,
        }


def persistir(db, relatorio, resultado, motivo=None):
    snapshot = relatorio.snapshot(resultado, motivo)
    db.query(XmlContabilidadeEnvio.id).filter(
        XmlContabilidadeEnvio.tenant_id == relatorio.tenant_id,
        XmlContabilidadeEnvio.id == relatorio.envio_id,
    ).with_for_update().one()
    ultimo = (
        db.query(func.max(XmlContabilidadeTentativa.numero_tentativa))
        .filter(
            XmlContabilidadeTentativa.tenant_id == relatorio.tenant_id,
            XmlContabilidadeTentativa.envio_id == relatorio.envio_id,
        )
        .scalar()
        or 0
    )
    resumo = {
        k: deepcopy(v)
        for k, v in snapshot.items()
        if k not in {"documentos", "pendencias", "anexos", "versao"}
    }
    registro = XmlContabilidadeTentativa(
        tenant_id=relatorio.tenant_id,
        envio_id=relatorio.envio_id,
        numero_tentativa=ultimo + 1,
        iniciado_em=relatorio.iniciado_em,
        concluido_em=datetime.now(UTC),
        resultado=snapshot["resultado"],
        resumo=resumo,
        snapshot=snapshot,
    )
    db.add(registro)
    db.flush()
    return registro


def serializar(registro, *, detalhado=False):
    return {
        **deepcopy(registro.snapshot if detalhado else registro.resumo),
        "id": registro.id,
        "numero_tentativa": registro.numero_tentativa,
    }


def _exigir_envio(db, tenant_id, envio_id):
    if (
        not db.query(XmlContabilidadeEnvio.id)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.id == envio_id,
        )
        .first()
    ):
        raise XmlContabilidadeError("Envio não encontrado nesta empresa.", 404)


def listar(db, tenant_id, envio_id):
    _exigir_envio(db, tenant_id, envio_id)
    registros = db.execute(
        select(
            XmlContabilidadeTentativa.id,
            XmlContabilidadeTentativa.numero_tentativa,
            XmlContabilidadeTentativa.resumo,
        )
        .where(
            XmlContabilidadeTentativa.tenant_id == _tenant(tenant_id),
            XmlContabilidadeTentativa.envio_id == envio_id,
        )
        .order_by(XmlContabilidadeTentativa.id.desc())
    ).all()
    return {
        "envio_id": envio_id,
        "disponivel": bool(registros),
        "mensagem": None
        if registros
        else "Este envio não possui relatório detalhado. Os dados das tentativas antigas não foram reconstruídos.",
        "relatorios": [
            {
                **deepcopy(row.resumo),
                "id": row.id,
                "numero_tentativa": row.numero_tentativa,
            }
            for row in registros
        ],
    }


def obter(db, tenant_id, envio_id, relatorio_id):
    _exigir_envio(db, tenant_id, envio_id)
    registro = (
        db.query(XmlContabilidadeTentativa)
        .filter(
            XmlContabilidadeTentativa.tenant_id == _tenant(tenant_id),
            XmlContabilidadeTentativa.envio_id == envio_id,
            XmlContabilidadeTentativa.id == relatorio_id,
        )
        .first()
    )
    if not registro:
        raise XmlContabilidadeError("Relatório não encontrado nesta empresa.", 404)
    return serializar(registro, detalhado=True)
