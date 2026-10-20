"""Configuração e entregas de XML de saída para a contabilidade da empresa."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_action
from app.db import get_session
from app.security.permissions_decorator import require_permission_dependency
from app.services import xml_contabilidade_service as service
from app.xml_contabilidade_schemas import (
    XmlContabilidadeConfigRequest,
    XmlContabilidadeEnvioRequest,
    XmlContabilidadePeriodoRequest,
)


class XmlContabilidadeRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def tratar_erro(request):
            try:
                return await handler(request)
            except service.XmlContabilidadeError as exc:
                raise HTTPException(
                    status_code=exc.status_code, detail=str(exc)
                ) from exc

        return tratar_erro


router = APIRouter(
    prefix="/contabilidade/xml",
    tags=["XML para contabilidade"],
    route_class=XmlContabilidadeRoute,
    dependencies=[Depends(require_permission_dependency("configuracoes.editar"))],
)


@router.get("/config")
def obter_config(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return service.obter_config(db, user_and_tenant[1])


@router.put("/config")
def salvar_config(
    payload: XmlContabilidadeConfigRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    resultado = service.salvar_config(db, user_and_tenant[1], payload)
    _auditar(
        db, user_and_tenant, "configuracao_salva", dados=payload.model_dump(mode="json")
    )
    return resultado


@router.post("/lotes/download")
def baixar_lote(
    payload: XmlContabilidadePeriodoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    content, filename, quantidade = service.gerar_zip_periodo(
        db, user_and_tenant[1], payload.data_inicio, payload.data_fim
    )
    _auditar(
        db,
        user_and_tenant,
        "download",
        dados={**payload.model_dump(mode="json"), "quantidade_xml": quantidade},
    )
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Quantidade-Notas": str(quantidade),
            "X-Notas-Pendentes": str(
                len(db.info.get("xml_contabilidade_pendencias", []))
            )
            if isinstance(db.info, dict)
            else "0",
            "Access-Control-Expose-Headers": "Content-Disposition, X-Quantidade-Notas, X-Notas-Pendentes",
            "Cache-Control": "no-store",
        },
    )


@router.post("/envios", status_code=201)
def criar_envio(
    payload: XmlContabilidadeEnvioRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    resultado = service.criar_envio(
        db,
        user_and_tenant[1],
        payload.data_inicio,
        payload.data_fim,
        agendado_para=payload.agendado_para,
    )
    _auditar(
        db,
        user_and_tenant,
        "envio_criado",
        resultado["id"],
        payload.model_dump(mode="json"),
    )
    return resultado


@router.get("/envios")
def listar_envios(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    return service.listar_envios(db, user_and_tenant[1])


@router.post("/envios/{envio_id}/cancelar")
def cancelar_envio(
    envio_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    resultado = service.cancelar_envio(db, user_and_tenant[1], envio_id)
    _auditar(db, user_and_tenant, "envio_cancelado", envio_id)
    return resultado


@router.get("/envios/{envio_id}/relatorios")
def listar_relatorios(
    envio_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    from app.services import xml_contabilidade_relatorios

    return xml_contabilidade_relatorios.listar(db, user_and_tenant[1], envio_id)


@router.get("/envios/{envio_id}/relatorios/{relatorio_id}")
def obter_relatorio(
    envio_id: int,
    relatorio_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    from app.services import xml_contabilidade_relatorios

    return xml_contabilidade_relatorios.obter(
        db, user_and_tenant[1], envio_id, relatorio_id
    )


@router.post("/envios/{envio_id}/reenviar")
def reenviar_envio(
    envio_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    resultado = service.reenviar_envio(db, user_and_tenant[1], envio_id)
    _auditar(db, user_and_tenant, "envio_retentado", envio_id)
    return resultado


def _auditar(db, user_and_tenant, acao, envio_id=None, dados=None):
    usuario, tenant_id = user_and_tenant
    log_action(
        db,
        usuario.id,
        action=f"xml_contabilidade.{acao}",
        entity_type="xml_contabilidade",
        entity_id=envio_id,
        new_value=dados,
        tenant_id=tenant_id,
    )
