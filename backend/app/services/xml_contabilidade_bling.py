"""Busca fiscal completa do período no Bling, com paginação e limite explícito."""

import re

from app.bling_integration import BlingAPI
from app.nfe.listagem_normalizacao import _normalizar_nota_bling
from app.services.bling_connection_service import get_bling_connection
from app.services.bling_tenant_guard import tenant_pode_usar_bling_global
from app.services.nfe_cache_service import upsert_nota_cache
from app.services.xml_contabilidade_documentos import _cnpj_empresa


def _possivel_saida_empresa(row, cnpj):
    # Metadados seguros eliminam notas de fornecedores antes de contar o lote.
    # Chave ausente ou malformada segue para validação oficial, sem presumir
    # que seja uma nota de outra empresa e descartá-la silenciosamente.
    if str(row.get("tipo")) == "0":
        return False
    chave = str(row.get("chaveAcesso") or row.get("chave") or "")
    return not re.fullmatch(r"\d{44}", chave) or chave[6:20] == cnpj


def sincronizar_periodo_bling(db, tenant_id, data_inicio, data_fim):
    from app.services.xml_contabilidade_service import (
        MAX_DOCUMENTOS,
        XmlContabilidadeError,
    )

    if not get_bling_connection(tenant_id, db=db) and not tenant_pode_usar_bling_global(
        tenant_id
    ):
        return
    try:
        api = BlingAPI(tenant_id=tenant_id)
        cnpj_empresa = _cnpj_empresa(db, tenant_id)
        quantidade = 0
        for modelo, endpoint in ((55, "/nfe"), (65, "/nfce")):
            importados = set()
            # GET /nfe omite canceladas quando situacao não é informada.
            # Ambos os modelos documentam situacao=2 para canceladas. A
            # consulta separada também cobre NFC-e sem depender do padrão.
            for situacao in (None, 2):
                pagina, vistos = 1, set()
                while True:
                    parametros = {
                        "dataEmissaoInicial": f"{data_inicio.isoformat()} 00:00:00",
                        "dataEmissaoFinal": f"{data_fim.isoformat()} 23:59:59",
                        "pagina": pagina,
                        "limite": 100,
                    }
                    if modelo == 55:
                        parametros["tipo"] = 1
                    if situacao is not None:
                        parametros["situacao"] = situacao
                    resposta = api._request("GET", endpoint, data=parametros)
                    rows = resposta.get("data")
                    if not isinstance(rows, list):
                        raise XmlContabilidadeError(
                            "O Bling não confirmou a lista completa do período. Tente novamente.",
                            503,
                        )
                    if not rows:
                        break
                    ids = {str(row.get("id") or "") for row in rows}
                    if not ids or "" in ids or len(ids) != len(rows) or ids & vistos:
                        raise XmlContabilidadeError(
                            "A paginação do Bling não confirmou todas as notas. Divida o período.",
                            409,
                        )
                    vistos.update(ids)
                    for row in rows:
                        documento_id = str(row["id"])
                        repetida = documento_id in importados
                        if repetida and situacao != 2:
                            continue
                        if not _possivel_saida_empresa(row, cnpj_empresa):
                            continue
                        # Pode ter sido cancelada entre as duas consultas:
                        # atualiza o cache, mas conta a mesma nota uma só vez.
                        importados.add(documento_id)
                        quantidade += int(not repetida)
                        if quantidade > MAX_DOCUMENTOS:
                            raise XmlContabilidadeError(
                                f"O período no Bling excede {MAX_DOCUMENTOS} notas. Divida-o em períodos menores."
                            )
                        nota = _normalizar_nota_bling(row, modelo=modelo)
                        if situacao == 2:
                            # O filtro oficial confirma o cancelamento. O
                            # normalizador legado interpreta alguns códigos
                            # numéricos de outra forma; manter o payload bruto
                            # e exigir o comprovante fiscal neste fluxo.
                            nota["status"] = "Cancelada"
                        upsert_nota_cache(
                            db, tenant_id, nota, source="bling_api", resumo_payload=row
                        )
                    db.flush()
                    if len(rows) < 100:
                        break
                    pagina += 1
    except XmlContabilidadeError:
        raise
    except Exception:
        raise XmlContabilidadeError(
            "Não foi possível confirmar todas as notas do período no Bling. Nenhum ZIP parcial foi gerado.",
            503,
        ) from None
