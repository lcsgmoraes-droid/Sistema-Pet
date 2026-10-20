"""Busca fiscal completa do período no Bling, com paginação e limite explícito."""

from app.bling_integration import BlingAPI
from app.nfe.listagem_normalizacao import _normalizar_nota_bling
from app.services.bling_connection_service import get_bling_connection
from app.services.bling_tenant_guard import tenant_pode_usar_bling_global
from app.services.nfe_cache_service import upsert_nota_cache


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
        quantidade = 0
        for modelo, endpoint in ((55, "/nfe"), (65, "/nfce")):
            pagina, vistos = 1, set()
            while True:
                resposta = api._request(
                    "GET",
                    endpoint,
                    data={
                        "dataEmissaoInicial": f"{data_inicio.isoformat()} 00:00:00",
                        "dataEmissaoFinal": f"{data_fim.isoformat()} 23:59:59",
                        "pagina": pagina,
                        "limite": 100,
                    },
                )
                rows = resposta.get("data")
                if not isinstance(rows, list):
                    raise XmlContabilidadeError(
                        "O Bling não confirmou a lista completa do período. Tente novamente.",
                        503,
                    )
                if not rows:
                    break
                ids = {str(row.get("id") or "") for row in rows}
                if not ids or "" in ids or ids & vistos:
                    raise XmlContabilidadeError(
                        "A paginação do Bling não confirmou todas as notas. Divida o período.",
                        409,
                    )
                vistos.update(ids)
                quantidade += len(rows)
                if quantidade > MAX_DOCUMENTOS:
                    raise XmlContabilidadeError(
                        f"O período no Bling excede {MAX_DOCUMENTOS} notas. Divida-o em períodos menores."
                    )
                for row in rows:
                    nota = _normalizar_nota_bling(row, modelo=modelo)
                    upsert_nota_cache(
                        db, tenant_id, nota, source="bling_api", resumo_payload=nota
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
