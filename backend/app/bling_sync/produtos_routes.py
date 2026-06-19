import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.db import get_session
from app.produtos_models import Produto
from app.services.bling_product_image_service import (
    attach_remote_image_to_product,
    extract_bling_product_image_url,
    product_has_any_image,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _sync_routes():
    from app import bling_sync_routes

    return bling_sync_routes


@router.get("/produtos-bling")
def listar_produtos_bling(
    busca: Optional[str] = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca produtos diretamente no Bling para facilitar vínculo manual."""
    try:
        sync_routes = _sync_routes()
        termo = sync_routes._normalizar_termo_busca(busca)
        bling = BlingAPI()
        itens = sync_routes._buscar_produtos_bling_por_termo(
            bling, termo, pagina, limite
        )

        # Fallback final: para termo vazio ou quando filtros específicos retornam vazio,
        # faz uma listagem padrão da página para não bloquear a tela.
        if not itens and not termo:
            itens = sync_routes._extrair_lista_produtos_bling(
                bling.listar_produtos(pagina=pagina, limite=limite)
            )

        produtos_bling = []
        for item in itens:
            produtos_bling.append(
                {
                    "id": str(item.get("id")),
                    "descricao": item.get("nome")
                    or item.get("descricao")
                    or "Sem descrição",
                    "codigo": item.get("codigo") or item.get("sku"),
                    "estoque": sync_routes._coerce_float(
                        item.get("estoque") or item.get("saldoFisicoTotal") or 0
                    ),
                }
            )
        return produtos_bling
    except Exception as e:
        mensagem = str(e)
        if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
            raise HTTPException(
                status_code=429,
                detail="Bling com limite temporário de consultas. Aguarde alguns segundos e tente novamente.",
            )
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar produtos no Bling: {mensagem}"
        )


@router.post("/importar-imagens")
def importar_imagens_dos_produtos_bling(
    limite: int = Query(default=100, ge=1, le=500),
    apenas_sem_imagem: bool = Query(default=True),
    atraso_ms: int = Query(default=900, ge=300, le=5000),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Importa imagens do Bling para produtos locais usando o vínculo salvo ou o SKU/código atual."""
    _current_user, tenant_id = user_and_tenant

    try:
        bling = BlingAPI()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Nao foi possivel iniciar a integracao com o Bling: {str(e)}",
        )

    query = (
        db.query(Produto)
        .options(
            joinedload(Produto.imagens),
            joinedload(Produto.bling_sync),
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.situacao.is_(True),
            Produto.tipo_produto != "PAI",
            Produto.codigo.isnot(None),
            Produto.codigo != "",
        )
    )

    if apenas_sem_imagem:
        query = query.filter(
            or_(
                Produto.imagem_principal.is_(None),
                Produto.imagem_principal == "",
            )
        )

    janela_busca = min(max(limite * 4, limite), 2000)
    produtos_base = query.order_by(Produto.id.asc()).limit(janela_busca).all()

    candidatos: list[Produto] = []
    for produto in produtos_base:
        if apenas_sem_imagem and product_has_any_image(produto):
            continue
        candidatos.append(produto)
        if len(candidatos) >= limite:
            break

    if not candidatos:
        return {
            "message": "Nenhum produto elegivel para importar imagem do Bling nesta rodada.",
            "total_selecionados": 0,
            "importados": 0,
            "ja_possuiam_imagem": 0,
            "sem_match_por_sku": 0,
            "sem_imagem_no_bling": 0,
            "erros": 0,
            "atraso_ms": atraso_ms,
            "items": [],
        }

    importados = 0
    ja_possuiam_imagem = 0
    sem_match_por_sku = 0
    sem_imagem_no_bling = 0
    erros = 0
    itens_resultado: list[dict] = []
    sync_routes = _sync_routes()

    for indice, produto in enumerate(candidatos, start=1):
        if indice > 1 and atraso_ms > 0:
            time.sleep(atraso_ms / 1000)

        if apenas_sem_imagem and product_has_any_image(produto):
            ja_possuiam_imagem += 1
            itens_resultado.append(
                {
                    "produto_id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "status": "skip_imagem_existente",
                    "detalhe": "O produto ja recebeu imagem antes desta rodada terminar.",
                }
            )
            continue

        bling_id = str(
            getattr(getattr(produto, "bling_sync", None), "bling_produto_id", "") or ""
        ).strip()
        item_bling = None
        detalhe_bling = None

        try:
            if bling_id:
                try:
                    detalhe_bling = sync_routes._consultar_produto_bling_com_retry(
                        bling, bling_id
                    )
                    item_bling = detalhe_bling or {"id": bling_id}
                except Exception as detail_error:
                    logger.warning(
                        "Falha ao consultar produto Bling vinculado %s para o produto %s. Tentando fallback por SKU/codigo. Erro: %s",
                        bling_id,
                        produto.id,
                        detail_error,
                    )
                    detalhe_bling = None
                    item_bling = None

            if not item_bling:
                item_bling = sync_routes._buscar_item_bling_por_codigos_com_retry(
                    bling,
                    produto.codigo,
                    codigos_extras=[produto.codigo_barras]
                    if produto.codigo_barras
                    else None,
                )
                if item_bling:
                    bling_id = str(item_bling.get("id") or "").strip()

            if not item_bling:
                sem_match_por_sku += 1
                itens_resultado.append(
                    {
                        "produto_id": produto.id,
                        "codigo": produto.codigo,
                        "nome": produto.nome,
                        "status": "sem_match_por_sku",
                        "detalhe": "Nao encontramos item correspondente no Bling usando SKU/codigo.",
                    }
                )
                continue

            image_url = extract_bling_product_image_url(detalhe_bling or item_bling)
            if not image_url and bling_id:
                detalhe_bling = sync_routes._consultar_produto_bling_com_retry(
                    bling, bling_id
                )
                image_url = extract_bling_product_image_url(detalhe_bling)

            if not image_url:
                sem_imagem_no_bling += 1
                itens_resultado.append(
                    {
                        "produto_id": produto.id,
                        "codigo": produto.codigo,
                        "nome": produto.nome,
                        "bling_produto_id": bling_id or None,
                        "status": "sem_imagem_no_bling",
                        "detalhe": "O cadastro correspondente no Bling nao trouxe URL de imagem utilizavel.",
                    }
                )
                continue

            nova_imagem = attach_remote_image_to_product(
                db,
                tenant_id=tenant_id,
                produto=produto,
                image_url=image_url,
                force_primary=not product_has_any_image(produto),
            )
            db.commit()
            db.refresh(nova_imagem)

            importados += 1
            itens_resultado.append(
                {
                    "produto_id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "bling_produto_id": bling_id or None,
                    "status": "importado",
                    "imagem_url": nova_imagem.url,
                    "detalhe": "Imagem importada e otimizada com sucesso.",
                }
            )
        except Exception as e:
            db.rollback()
            erros += 1
            itens_resultado.append(
                {
                    "produto_id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "bling_produto_id": bling_id or None,
                    "status": "erro",
                    "detalhe": str(e),
                }
            )

    return {
        "message": "Importacao de imagens do Bling concluida.",
        "total_selecionados": len(candidatos),
        "importados": importados,
        "ja_possuiam_imagem": ja_possuiam_imagem,
        "sem_match_por_sku": sem_match_por_sku,
        "sem_imagem_no_bling": sem_imagem_no_bling,
        "erros": erros,
        "atraso_ms": atraso_ms,
        "items": itens_resultado[:50],
    }
