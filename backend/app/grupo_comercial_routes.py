from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.grupo_comercial_analise_service import GrupoComercialAnaliseService
from app.grupo_comercial_analise_detalhes_service import (
    GrupoComercialAnaliseDetalhesService,
)
from app.grupo_comercial_billing_service import GrupoComercialBillingService
from app.grupo_comercial_planejamento_service import (
    GrupoComercialPlanejamentoService,
)
from app.grupo_comercial_produto_vinculo_service import (
    GrupoComercialProdutoVinculoService,
)
from app.grupo_comercial_estoque_compartilhado_service import (
    GrupoComercialEstoqueCompartilhadoService,
)
from app.grupo_comercial_schemas import (
    GrupoComercialEstoqueAcessoCatalogoAtualizar,
    GrupoComercialCriar,
    GrupoComercialEstoqueCompartilhar,
    GrupoComercialGestorConceder,
    GrupoComercialLojaAdicionar,
    GrupoComercialProdutoVincular,
)
from app.grupo_comercial_service import GrupoComercialService
from app.grupo_comercial_models import GrupoComercialMembro
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.security.permissions_decorator import require_any_permission
from app.especie_raca_mestre_models import EspecieMestre, RacaMestre
from app.produto_mestre_models import ProdutoMestre
from app.pet_mestre_models import PetMestre
from app.pessoa_mestre_models import PessoaMestre

router = APIRouter(prefix="/grupos-comerciais", tags=["Grupos Comerciais"])
PERMISSOES_CONFIG_EMPRESA = ("configuracoes.empresa", "configuracoes.editar")
PERMISSOES_ANALISE_GRUPO = ("relatorios.gerencial", "relatorios.financeiro")


@router.get("/{grupo_id}/mestres")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_mestres_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Checkpoint 5 da camada geral (ver Documentacao/Dominio/
    Plano-Camada-Geral.md): visão única dos dados mestre do grupo — quem
    já tem, sem precisar entrar em cada domínio separadamente. Qualquer
    membro ativo pode ver; vincular/desvincular continua na rota de cada
    domínio (cada loja só mexe nos próprios registros locais)."""
    _usuario, empresa_id = user_and_tenant
    membro = (
        db.query(GrupoComercialMembro)
        .filter(
            GrupoComercialMembro.grupo_id == grupo_id,
            GrupoComercialMembro.empresa_id == str(empresa_id),
            GrupoComercialMembro.status == "ativo",
        )
        .first()
    )
    if membro is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua empresa não participa deste grupo.",
        )

    def _linhas(modelo):
        return [
            {"id": linha.id, "nome": linha.nome}
            for linha in (
                db.query(modelo)
                .filter(modelo.grupo_id == grupo_id, modelo.ativo.is_(True))
                .order_by(modelo.nome)
                .all()
            )
        ]

    return {
        "produtos": _linhas(ProdutoMestre),
        "pets": _linhas(PetMestre),
        "pessoas": _linhas(PessoaMestre),
        "especies": _linhas(EspecieMestre),
        "racas": _linhas(RacaMestre),
    }


@router.get("/{grupo_id}/estoque-compartilhado")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_estoque_compartilhado_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    return GrupoComercialEstoqueCompartilhadoService(db).listar(grupo_id, empresa_id)


@router.get("/{grupo_id}/estoque-compartilhado/produtos")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def buscar_produtos_para_estoque_compartilhado(
    grupo_id: int,
    empresa_consumidora_id: str = Query(...),
    busca: str = Query("", max_length=120),
    limite: int = Query(80, ge=10, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    return GrupoComercialEstoqueCompartilhadoService(db).buscar_produtos_compartilhaveis(
        grupo_id,
        empresa_id,
        empresa_consumidora_id,
        busca=busca,
        limite=limite,
    )


@router.post("/{grupo_id}/estoque-compartilhado", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def compartilhar_estoque_grupo(
    grupo_id: int,
    payload: GrupoComercialEstoqueCompartilhar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialEstoqueCompartilhadoService(db).compartilhar(
        grupo_id,
        empresa_id,
        usuario.id,
        payload.empresa_consumidora_id,
        payload.produto_ids,
        acesso_catalogo_completo=payload.acesso_catalogo_completo,
    )


@router.patch("/{grupo_id}/estoque-compartilhado/{compartilhamento_id}/catalogo")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def atualizar_acesso_catalogo_estoque_compartilhado(
    grupo_id: int,
    compartilhamento_id: int,
    payload: GrupoComercialEstoqueAcessoCatalogoAtualizar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialEstoqueCompartilhadoService(db).atualizar_acesso_catalogo(
        grupo_id,
        compartilhamento_id,
        empresa_id,
        usuario.id,
        acesso_catalogo_completo=payload.acesso_catalogo_completo,
    )


@router.delete("/{grupo_id}/estoque-compartilhado/{compartilhamento_id}")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def remover_estoque_compartilhado_grupo(
    grupo_id: int,
    compartilhamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialEstoqueCompartilhadoService(db).remover(
        grupo_id, compartilhamento_id, empresa_id, usuario.id
    )


@router.get("/resumo")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_resumo_grupos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialService(db).listar_resumo(empresa_id, usuario)


@router.get("/{grupo_id}/visao-consolidada")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def obter_visao_consolidada_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=1, le=366),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    resultado = GrupoComercialAnaliseService(db).obter(
        grupo_id,
        empresa_id,
        periodo_dias,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-visao-consolidada")
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
    resultado = GrupoComercialAnaliseDetalhesService(db).listar_pedidos(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-analises-detalhadas")
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
    resultado = GrupoComercialAnaliseDetalhesService(db).listar_produtos_vendidos(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-analises-detalhadas")
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
    resultado = GrupoComercialAnaliseDetalhesService(db).listar_pedidos_compra(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-analises-detalhadas")
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
    resultado = GrupoComercialAnaliseDetalhesService(db).listar_contas_pagar(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        situacao=situacao,
        busca=busca,
        empresa_id=empresa_id,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-analises-detalhadas")
    return resultado


@router.get("/{grupo_id}/reposicao-inteligente")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def listar_reposicao_inteligente_grupo(
    grupo_id: int,
    periodo_dias: int = Query(30, ge=7, le=366),
    dias_cobertura: int = Query(30, ge=7, le=120),
    busca: str = Query("", max_length=120),
    somente_acao: bool = Query(True),
    limite: int = Query(200, ge=20, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = GrupoComercialPlanejamentoService(db).listar_reposicao_inteligente(
        grupo_id,
        empresa_atual_id,
        periodo_dias=periodo_dias,
        dias_cobertura=dias_cobertura,
        busca=busca,
        somente_acao=somente_acao,
        limite=limite,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-planejamento-inteligente")
    return resultado


@router.get("/{grupo_id}/analise-financeira")
@require_any_permission(PERMISSOES_ANALISE_GRUPO)
def obter_analise_financeira_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_atual_id = user_and_tenant
    resultado = GrupoComercialPlanejamentoService(db).analisar_financeiro(
        grupo_id, empresa_atual_id
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-planejamento-inteligente")
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
    return GrupoComercialProdutoVinculoService(db).buscar_produtos(
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
    return GrupoComercialProdutoVinculoService(db).listar_vinculos(
        grupo_id, empresa_atual_id
    )


@router.post("/{grupo_id}/vinculos-produtos", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def vincular_produtos_grupo(
    grupo_id: int,
    payload: GrupoComercialProdutoVincular,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_atual_id = user_and_tenant
    resultado = GrupoComercialProdutoVinculoService(db).vincular_produtos(
        grupo_id,
        empresa_atual_id,
        usuario.id,
        payload.produto_a,
        payload.produto_b,
    )
    registrar_uso_funcionalidade(db, "grupos-comerciais-analises-detalhadas")
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
    return GrupoComercialProdutoVinculoService(db).remover_vinculo(
        grupo_id,
        vinculo_id,
        empresa_atual_id,
        usuario.id,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def criar_grupo_empresa(
    payload: GrupoComercialCriar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialService(db).criar_grupo(empresa_id, usuario.id, payload.nome)


@router.post("/{grupo_id}/lojas", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def adicionar_loja_ao_grupo(
    grupo_id: int,
    payload: GrupoComercialLojaAdicionar,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma loja nova (mesmo usuário logado) e já anexa ao grupo — a
    forma self-service de "crescer" um grupo, sem passar por convite/código.
    Só a empresa responsável do grupo pode chamar."""
    usuario, empresa_id = user_and_tenant
    return GrupoComercialService(db).adicionar_loja(
        grupo_id=grupo_id,
        usuario=usuario,
        nome_loja=payload.nome_loja,
        nome_acesso=payload.nome_acesso,
        plan=payload.plan,
        organization_type=payload.organization_type,
        restore_tenant_id=empresa_id,
        empresa_acionadora_id=empresa_id,
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
    return GrupoComercialService(db).remover_membro(
        empresa_id,
        usuario,
        grupo_id,
        membro_empresa_id,
    )


@router.get("/{grupo_id}/gestores")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_gestores_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _empresa_id = user_and_tenant
    return {"gestores": GrupoComercialService(db).listar_gestores(grupo_id, usuario)}


@router.post("/{grupo_id}/gestores", status_code=status.HTTP_201_CREATED)
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def conceder_gestor_grupo(
    grupo_id: int,
    payload: GrupoComercialGestorConceder,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """So o usuario master do grupo pode chamar - checagem dentro do
    servico, nao depende de permissao de tenant (ver
    GrupoComercialService.conceder_gestor)."""
    usuario, empresa_id = user_and_tenant
    return GrupoComercialService(db).conceder_gestor(
        grupo_id, empresa_id, usuario, payload.user_id
    )


@router.delete("/{grupo_id}/gestores/{user_id}")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def revogar_gestor_grupo(
    grupo_id: int,
    user_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    return GrupoComercialService(db).revogar_gestor(
        grupo_id, empresa_id, usuario, user_id
    )


@router.get("/{grupo_id}/billing")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def listar_billing_grupo(
    grupo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _empresa_id = user_and_tenant
    return GrupoComercialBillingService(db).listar(grupo_id, usuario)


@router.post("/{grupo_id}/lojas/{tenant_id}/billing/sincronizar")
@require_any_permission(PERMISSOES_CONFIG_EMPRESA)
def sincronizar_billing_loja_grupo(
    grupo_id: int,
    tenant_id: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _empresa_id = user_and_tenant
    return GrupoComercialBillingService(db).sincronizar_loja(
        grupo_id, tenant_id, usuario
    )
