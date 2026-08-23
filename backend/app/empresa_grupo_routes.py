from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.empresa_grupo_analise_service import EmpresaGrupoAnaliseService
from app.empresa_grupo_analise_detalhes_service import (
    EmpresaGrupoAnaliseDetalhesService,
)
from app.empresa_grupo_produto_vinculo_service import (
    EmpresaGrupoProdutoVinculoService,
)
from app.empresa_grupo_schemas import (
    EmpresaGrupoConvidar,
    EmpresaGrupoCriar,
    EmpresaGrupoProdutoVincular,
)
from app.empresa_grupo_service import EmpresaGrupoService
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.security.permissions_decorator import require_any_permission

router = APIRouter(prefix="/grupos-empresas", tags=["Grupos de empresas"])
PERMISSOES_CONFIG_EMPRESA = ("configuracoes.empresa", "configuracoes.editar")
PERMISSOES_ANALISE_GRUPO = ("relatorios.gerencial", "relatorios.financeiro")


@router.get("/resumo")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_resumo_grupos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).listar_resumo(empresa_id, usuario.id)


@router.get("/{grupo_id}/visao-consolidada")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def obter_visao_consolidada_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    resultado = EmpresaGrupoAnaliseService(db).obter(
        grupo_id,
        empresa_id,
        periodo_dias,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-visao-consolidada")
    return resultado


@router.get("/{grupo_id}/pedidos")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_pedidos_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    busca: str = Query("", max_length=120),
    empresa_id: str | None = Query(None),
    limite: int = Query(200, ge=20, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = EmpresaGrupoAnaliseDetalhesService(db).listar_pedidos(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-analises-detalhadas")
    return resultado


@router.get("/{grupo_id}/produtos-vendidos")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_produtos_vendidos_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    busca: str = Query("", max_length=120),
    limite: int = Query(200, ge=20, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = EmpresaGrupoAnaliseDetalhesService(db).listar_produtos_vendidos(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-analises-detalhadas")
    return resultado


@router.get("/{grupo_id}/pedidos-compra")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_pedidos_compra_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    busca: str = Query("", max_length=120),
    empresa_id: str | None = Query(None),
    limite: int = Query(200, ge=20, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = EmpresaGrupoAnaliseDetalhesService(db).listar_pedidos_compra(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-analises-detalhadas")
    return resultado


@router.get("/{grupo_id}/contas-pagar")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_contas_pagar_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    situacao: str = Query("abertas", pattern="^(abertas|vencidas|pagas|todas)$"),
    busca: str = Query("", max_length=120),
    empresa_id: str | None = Query(None),
    limite: int = Query(200, ge=20, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = EmpresaGrupoAnaliseDetalhesService(db).listar_contas_pagar(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        situacao=situacao,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-analises-detalhadas")
    return resultado


@router.get("/{grupo_id}/produtos")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def buscar_produtos_grupo(
    grupo_id: int,
    busca: str = Query("", max_length=120),
    empresa_id: str | None = Query(None),
    limite: int = Query(60, ge=10, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    return EmpresaGrupoProdutoVinculoService(db).buscar_produtos(
        grupo_id,
        empresa_atual_id,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )


@router.get("/{grupo_id}/vinculos-produtos")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_vinculos_produtos_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    return EmpresaGrupoProdutoVinculoService(db).listar_vinculos(
        grupo_id, empresa_atual_id
    )


@router.post("/{grupo_id}/vinculos-produtos", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def vincular_produtos_grupo(
    grupo_id: int,
    payload: EmpresaGrupoProdutoVincular,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_atual_id = user_and_tenant
    resultado = EmpresaGrupoProdutoVinculoService(db).vincular_produtos(
        grupo_id,
        empresa_atual_id,
        usuario.id,
        payload.produto_a,
        payload.produto_b,
    )
    registrar_uso_funcionalidade(db, "grupos-empresas-analises-detalhadas")
    return resultado


@router.delete("/{grupo_id}/vinculos-produtos/{vinculo_id}")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def remover_vinculo_produtos_grupo(
    grupo_id: int,
    vinculo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_atual_id = user_and_tenant
    return EmpresaGrupoProdutoVinculoService(db).remover_vinculo(
        grupo_id,
        vinculo_id,
        empresa_atual_id,
        usuario.id,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def criar_grupo_empresa(
    payload: EmpresaGrupoCriar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).criar_grupo(empresa_id, usuario.id, payload.nome)


@router.post("/{grupo_id}/convites", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def convidar_empresa_para_grupo(
    grupo_id: int,
    payload: EmpresaGrupoConvidar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).convidar(
        empresa_id,
        usuario.id,
        grupo_id,
        payload.codigo_empresa,
    )


@router.post("/convites/{convite_id}/aceitar")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def aceitar_convite_grupo(
    convite_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).responder_convite(
        empresa_id, usuario.id, convite_id, aceitar=True
    )


@router.post("/convites/{convite_id}/recusar")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def recusar_convite_grupo(
    convite_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).responder_convite(
        empresa_id, usuario.id, convite_id, aceitar=False
    )


@router.delete("/{grupo_id}/membros/{membro_empresa_id}")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def remover_empresa_do_grupo(
    grupo_id: int,
    membro_empresa_id: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return EmpresaGrupoService(db).remover_membro(
        empresa_id,
        usuario.id,
        grupo_id,
        membro_empresa_id,
    )
