"""Rotas de baixa FULL de estoque por NF, PDF e XML."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
import io
import logging
import re
from typing import List, Optional
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .bling_estoque_sync import sincronizar_bling_background
from .db import get_session
from .domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual
from .models import User
from .produtos_models import EstoqueMovimentacao, Produto, ProdutoKitComponente
from .services.kit_estoque_service import KitEstoqueService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/estoque", tags=["Estoque - Saida FULL"])

try:
    import pdfplumber
except Exception:
    pdfplumber = None

_CANAL_LABELS = {
    "full": "FULL (geral)",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
    "site": "Site",
    "app": "App",
    "whatsapp": "WhatsApp",
    "bling": "Bling",
    "online": "Online",
    "loja_fisica": "Loja Fisica",
    "transferencia_parceiro": "Transferencia Parceiro",
}


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


class SaidaFullNFItemRequest(BaseModel):
    """Item para baixa de estoque por NF de saida."""

    produto_id: Optional[int] = None
    sku: Optional[str] = None
    quantidade: float = Field(gt=0)


class SaidaFullNFRequest(BaseModel):
    """Baixa em lote de estoque vinculada a uma NF de saida."""

    numero_nf: str
    plataforma: Optional[str] = None
    observacao: Optional[str] = None
    tarifa_envio: Optional[float] = 0
    categoria_tarifa_id: Optional[int] = None
    dre_subcategoria_tarifa_id: Optional[int] = None
    data_vencimento_tarifa: Optional[date] = None
    itens: List[SaidaFullNFItemRequest]


class SaidaFullNFCanalUpdateRequest(BaseModel):
    """Atualizacao do canal/origem de uma baixa FULL ja processada."""

    plataforma: str


def _resolver_produto_full_nf(
    db: Session, tenant_id: int, item: SaidaFullNFItemRequest
) -> Optional[Produto]:
    if item.produto_id:
        return (
            db.query(Produto)
            .filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

    if item.sku:
        filtros_sku = [Produto.codigo == item.sku]
        # Compatibilidade com modelos legados que ainda possam expor campo "sku".
        if hasattr(Produto, "sku"):
            filtros_sku.append(getattr(Produto, "sku") == item.sku)

        return (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                or_(*filtros_sku),
            )
            .first()
        )

    return None


def _observacao_full_nf(
    numero_nf: str, plataforma: Optional[str], observacao: Optional[str]
) -> str:
    base = f"Saida FULL por NF {numero_nf} | plataforma: {plataforma or 'full'}"
    if observacao:
        return f"{base} | {observacao}"
    return base


def _observacao_full_nf_com_canal_atualizado(
    numero_nf: str,
    observacao: Optional[str],
    plataforma: str,
) -> str:
    texto = _texto_limpo(observacao)
    if texto:
        if re.search(r"plataforma:\s*[^|]+", texto, flags=re.IGNORECASE):
            return re.sub(
                r"plataforma:\s*[^|]+",
                f"plataforma: {plataforma}",
                texto,
                count=1,
                flags=re.IGNORECASE,
            )
        return f"{texto} | plataforma: {plataforma}"
    return _observacao_full_nf(numero_nf, plataforma, None)


def _canal_saida_full_por_observacao(observacao: Optional[str]) -> Optional[str]:
    texto = _texto_limpo(observacao)
    if not texto:
        return None
    match = re.search(r"plataforma:\s*([^|]+)", texto, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().lower() or None


def _sku_produto(produto: Produto) -> Optional[str]:
    return getattr(produto, "sku", None) or getattr(produto, "codigo", None)


def _produto_usa_estoque_virtual_full_nf(produto: Produto) -> bool:
    return (
        getattr(produto, "tipo_produto", None) in ("KIT", "VARIACAO")
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    )


def _estoque_disponivel_saida_full_nf(
    db: Session, tenant_id: int, produto: Produto
) -> float:
    if _produto_usa_estoque_virtual_full_nf(produto):
        return float(
            KitEstoqueService.calcular_estoque_virtual_kit(
                db,
                produto.id,
                tenant_id=tenant_id,
            )
            or 0
        )

    return float(getattr(produto, "estoque_atual", 0) or 0)


SKU_EXPLICITO_REGEX = re.compile(
    r"(?:SKU|C[ÓO]DIGO)\s*[:#-]?\s*([A-Z0-9._/-]+)", re.IGNORECASE
)
QTD_EXPLICITA_REGEX = re.compile(
    r"(?:QTD|QUANTIDADE)\s*[:#-]?\s*(\d+(?:[\.,]\d+)?)", re.IGNORECASE
)
SKU_QTD_LINHA_REGEX = re.compile(r"^([A-Za-z0-9._\-/]{3,})\s+(\d+(?:[\.,]\d+)?)$")


def _to_float_br(value: str) -> float:
    return (
        float(value.replace(".", "").replace(",", "."))
        if "," in value
        else float(value)
    )


def _extrair_itens_full_pdf(texto: str) -> List[dict]:
    itens_por_sku = defaultdict(float)

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        if not linha:
            continue

        sku_match = SKU_EXPLICITO_REGEX.search(linha)
        qtd_match = QTD_EXPLICITA_REGEX.search(linha)
        if sku_match and qtd_match:
            sku = sku_match.group(1).strip()
            qtd = _to_float_br(qtd_match.group(1))
            if qtd > 0:
                itens_por_sku[sku] += qtd
            continue

        linha_match = SKU_QTD_LINHA_REGEX.match(linha)
        if linha_match:
            sku = linha_match.group(1).strip()
            qtd = _to_float_br(linha_match.group(2))
            if qtd > 0:
                itens_por_sku[sku] += qtd

    return [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]


def _xml_find_text(parent, path_ns: str, path_plain: str, ns: dict) -> Optional[str]:
    elem = parent.find(path_ns, ns)
    if elem is None:
        elem = parent.find(path_plain)
    if elem is None:
        return None
    return (elem.text or "").strip()


def _parse_saida_full_xml(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    inf_nfe = root.find(".//nfe:infNFe", ns)
    if inf_nfe is None:
        inf_nfe = root.find(".//infNFe")
    if inf_nfe is None:
        raise HTTPException(
            status_code=400, detail="XML invalido: tag infNFe nao encontrada"
        )

    ide = inf_nfe.find("nfe:ide", ns)
    if ide is None:
        ide = inf_nfe.find("ide")
    if ide is None:
        raise HTTPException(
            status_code=400, detail="XML invalido: tag ide nao encontrada"
        )

    numero_nf = _xml_find_text(ide, "nfe:nNF", "nNF", ns)
    if not numero_nf:
        raise HTTPException(
            status_code=400, detail="Numero da NF nao encontrado no XML"
        )

    itens_por_sku = defaultdict(float)
    det_list = inf_nfe.findall(".//nfe:det", ns)
    if not det_list:
        det_list = inf_nfe.findall(".//det")

    for det in det_list:
        prod = det.find("nfe:prod", ns)
        if prod is None:
            prod = det.find("prod")
        if prod is None:
            continue

        sku = _xml_find_text(prod, "nfe:cProd", "cProd", ns)
        qcom = _xml_find_text(prod, "nfe:qCom", "qCom", ns)
        if not sku or not qcom:
            continue

        try:
            qtd = float(qcom.replace(",", "."))
        except ValueError:
            continue

        if qtd > 0:
            itens_por_sku[sku] += qtd

    itens = [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]

    if not itens:
        raise HTTPException(
            status_code=400,
            detail="Nenhum item valido (cProd + qCom) foi encontrado no XML",
        )

    return {
        "numero_nf": numero_nf,
        "total_itens": len(itens),
        "itens": itens,
    }


def _processar_item_saida_full_nf(
    db: Session,
    tenant_id: int,
    item: SaidaFullNFItemRequest,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user: User,
):
    produto = _resolver_produto_full_nf(db, tenant_id, item)
    if not produto:
        raise HTTPException(
            status_code=400,
            detail=f"Produto nao encontrado para item (produto_id={item.produto_id}, sku={item.sku})",
        )

    if _produto_usa_estoque_virtual_full_nf(produto):
        return _processar_item_kit_virtual_saida_full_nf(
            db=db,
            tenant_id=tenant_id,
            produto=produto,
            item=item,
            numero_nf=numero_nf,
            observacao_movimentacao=observacao_movimentacao,
            current_user=current_user,
        )

    estoque_anterior = float(produto.estoque_atual or 0)
    if estoque_anterior < item.quantidade:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                f"Disponivel: {estoque_anterior}, solicitado: {item.quantidade}"
            ),
        )

    produto.estoque_atual = estoque_anterior - item.quantidade

    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="saida",
        motivo="full_nfe_saida",
        quantidade=item.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=item.quantidade * float(produto.preco_custo or 0),
        documento=numero_nf,
        observacao=observacao_movimentacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    return {
        "produto_id": produto.id,
        "sku": _sku_produto(produto),
        "nome": produto.nome,
        "quantidade": item.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_novo": float(produto.estoque_atual or 0),
    }


def _processar_item_kit_virtual_saida_full_nf(
    db: Session,
    tenant_id: int,
    produto: Produto,
    item: SaidaFullNFItemRequest,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user: User,
):
    estoque_anterior = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
    quantidade_kits = float(item.quantidade or 0)

    if estoque_anterior < quantidade_kits:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                f"Disponivel: {estoque_anterior}, solicitado: {quantidade_kits}"
            ),
        )

    componentes = (
        db.query(ProdutoKitComponente)
        .filter(ProdutoKitComponente.kit_id == produto.id)
        .all()
    )
    if not componentes:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=f"Kit virtual {produto.nome} (SKU {sku_label}) nao possui componentes cadastrados",
        )

    componentes_para_baixa = []
    for componente in componentes:
        produto_componente = (
            db.query(Produto)
            .filter(
                Produto.id == componente.produto_componente_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        if not produto_componente:
            raise HTTPException(
                status_code=400,
                detail=f"Componente #{componente.produto_componente_id} do kit {produto.nome} nao encontrado",
            )

        quantidade_componente = quantidade_kits * float(componente.quantidade or 0)
        estoque_componente = float(produto_componente.estoque_atual or 0)
        if estoque_componente < quantidade_componente:
            sku_label = _sku_produto(produto_componente) or "sem-sku"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Estoque insuficiente no componente {produto_componente.nome} (SKU {sku_label}) "
                    f"para baixar o kit {produto.nome}. Disponivel: {estoque_componente}, "
                    f"solicitado: {quantidade_componente}"
                ),
            )

        componentes_para_baixa.append(
            {
                "produto": produto_componente,
                "quantidade": quantidade_componente,
                "estoque_anterior": estoque_componente,
            }
        )

    componentes_baixados = []
    for baixa in componentes_para_baixa:
        produto_componente = baixa["produto"]
        quantidade_componente = baixa["quantidade"]
        estoque_componente_anterior = baixa["estoque_anterior"]
        estoque_componente_novo = estoque_componente_anterior - quantidade_componente
        produto_componente.estoque_atual = estoque_componente_novo

        movimentacao_componente = EstoqueMovimentacao(
            produto_id=produto_componente.id,
            tipo="saida",
            motivo="full_nfe_saida",
            quantidade=quantidade_componente,
            quantidade_anterior=estoque_componente_anterior,
            quantidade_nova=estoque_componente_novo,
            custo_unitario=produto_componente.preco_custo,
            valor_total=quantidade_componente
            * float(produto_componente.preco_custo or 0),
            documento=numero_nf,
            observacao=(
                f"{observacao_movimentacao} | componente do kit virtual "
                f"{_sku_produto(produto) or produto.nome} ({quantidade_kits:g} kit(s))"
            ),
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(movimentacao_componente)

        componentes_baixados.append(
            {
                "produto_id": produto_componente.id,
                "sku": _sku_produto(produto_componente),
                "nome": produto_componente.nome,
                "quantidade": quantidade_componente,
                "estoque_anterior": estoque_componente_anterior,
                "estoque_novo": estoque_componente_novo,
            }
        )

    estoque_novo = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
    movimentacao_kit = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="saida",
        motivo="full_nfe_saida",
        quantidade=quantidade_kits,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_novo,
        custo_unitario=0,
        valor_total=0,
        documento=numero_nf,
        observacao=f"{observacao_movimentacao} | kit virtual (baixa real nos componentes)",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao_kit)

    return {
        "produto_id": produto.id,
        "sku": _sku_produto(produto),
        "nome": produto.nome,
        "quantidade": quantidade_kits,
        "estoque_anterior": estoque_anterior,
        "estoque_novo": estoque_novo,
        "tipo_kit": "VIRTUAL",
        "componentes_baixados": componentes_baixados,
        "sync_itens": [
            {
                "produto_id": componente["produto_id"],
                "estoque_novo": componente["estoque_novo"],
            }
            for componente in componentes_baixados
        ]
        + [
            {
                "produto_id": produto.id,
                "estoque_novo": estoque_novo,
            }
        ],
    }


def _problemas_estoque_saida_full_nf(
    db: Session,
    tenant_id: int,
    itens: List[SaidaFullNFItemRequest],
) -> List[dict]:
    problemas = []

    for item in itens:
        produto = _resolver_produto_full_nf(db, tenant_id, item)
        entrada_sku = _texto_limpo(item.sku)

        if not produto:
            problemas.append(
                {
                    "tipo": "produto_nao_encontrado",
                    "produto_id": item.produto_id,
                    "entrada_sku": entrada_sku,
                    "sku": entrada_sku,
                    "nome": "Produto nao encontrado",
                    "disponivel": 0,
                    "solicitado": float(item.quantidade or 0),
                    "faltante": float(item.quantidade or 0),
                    "mensagem": f"Produto nao encontrado para SKU {entrada_sku or item.produto_id or '-'}",
                    "url_correcao": None,
                }
            )
            continue

        estoque_anterior = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
        quantidade = float(item.quantidade or 0)
        if estoque_anterior < quantidade:
            sku_label = _sku_produto(produto) or entrada_sku or "sem-sku"
            faltante = max(quantidade - estoque_anterior, 0)
            usa_estoque_virtual = _produto_usa_estoque_virtual_full_nf(produto)
            problemas.append(
                {
                    "tipo": "estoque_insuficiente_kit_virtual"
                    if usa_estoque_virtual
                    else "estoque_insuficiente",
                    "produto_id": produto.id,
                    "entrada_sku": entrada_sku,
                    "sku": sku_label,
                    "nome": produto.nome,
                    "disponivel": estoque_anterior,
                    "solicitado": quantidade,
                    "faltante": faltante,
                    "mensagem": (
                        f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                        f"Disponivel: {estoque_anterior}, solicitado: {quantidade}"
                    ),
                    "url_correcao": f"/produtos/{produto.id}/editar"
                    if usa_estoque_virtual
                    else f"/produtos/{produto.id}/movimentacoes",
                }
            )

    return problemas


def _validar_estoque_saida_full_nf(
    db: Session,
    tenant_id: int,
    itens: List[SaidaFullNFItemRequest],
) -> None:
    problemas = _problemas_estoque_saida_full_nf(db, tenant_id, itens)
    if problemas:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "estoque_insuficiente_full_nf",
                "message": (
                    "Alguns itens nao possuem estoque suficiente para baixa. "
                    "Corrija o estoque dos produtos marcados e revalide antes de confirmar."
                ),
                "itens": problemas,
            },
        )


def _resolver_classificacao_tarifa_full_nf(
    db: Session,
    tenant_id,
    *,
    categoria_tarifa_id: Optional[int],
    dre_subcategoria_tarifa_id: Optional[int],
):
    if not categoria_tarifa_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para lancar tarifa de envio no financeiro, selecione uma categoria de despesa "
                "vinculada a DRE. Sem essa classificacao a conta a pagar nao pode ser gerada."
            ),
        )

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_tarifa_id,
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.tipo == "despesa",
            CategoriaFinanceira.ativo.is_(True),
        )
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=400,
            detail="Categoria de despesa invalida ou nao pertence a este tenant.",
        )

    subcategoria_id = dre_subcategoria_tarifa_id or categoria.dre_subcategoria_id
    if not subcategoria_id:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Categoria de despesa '{categoria.nome}' nao possui vinculo com DRE. "
                "Ajuste a categoria financeira antes de baixar a NF com tarifa."
            ),
        )

    subcategoria = (
        db.query(DRESubcategoria)
        .join(DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id)
        .filter(
            DRESubcategoria.id == subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
            DRECategoria.tenant_id == tenant_id,
            DRECategoria.ativo.is_(True),
            DRECategoria.natureza == NaturezaDRE.DESPESA,
        )
        .first()
    )
    if not subcategoria:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Subcategoria DRE vinculada a '{categoria.nome}' e invalida, inativa "
                "ou nao e de despesa."
            ),
        )

    return categoria, subcategoria


def _criar_conta_pagar_tarifa_full_nf(
    db: Session,
    *,
    tenant_id,
    current_user: User,
    payload: SaidaFullNFRequest,
    categoria: CategoriaFinanceira,
    subcategoria: DRESubcategoria,
):
    valor = float(payload.tarifa_envio or 0)
    if valor <= 0:
        return None

    hoje = date.today()
    vencimento = payload.data_vencimento_tarifa or hoje
    canal = (payload.plataforma or "full").strip().lower() or "full"
    plataforma_label = _CANAL_LABELS.get(canal, payload.plataforma or "FULL")
    descricao = f"Tarifa envio FULL NF {payload.numero_nf}"
    observacoes = (
        f"Tarifa da operacao FULL ({plataforma_label}). "
        "Gerado na baixa de estoque por NF."
    )

    conta = ContaPagar(
        descricao=descricao,
        categoria_id=categoria.id,
        dre_subcategoria_id=subcategoria.id,
        canal=canal,
        valor_original=valor,
        valor_final=valor,
        data_emissao=hoje,
        data_vencimento=vencimento,
        status="pendente",
        documento=payload.numero_nf,
        observacoes=observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(conta)
    db.flush()

    lancamento = LancamentoManual(
        tipo="saida",
        valor=valor,
        descricao=descricao,
        data_lancamento=hoje,
        data_competencia=vencimento,
        categoria_id=categoria.id,
        conta_bancaria_id=None,
        status="previsto",
        documento=payload.numero_nf,
        observacoes=f"Gerado automaticamente da conta a pagar #{conta.id}",
        gerado_automaticamente=True,
        confianca_ia=None,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(lancamento)

    atualizar_dre_por_lancamento(
        db=db,
        tenant_id=tenant_id,
        dre_subcategoria_id=subcategoria.id,
        canal=canal,
        valor=Decimal(str(valor)),
        data_lancamento=vencimento,
        tipo_movimentacao="DESPESA",
    )

    return conta


def _observacao_conta_tarifa_full_nf_com_canal(
    observacoes: Optional[str],
    plataforma_label: str,
) -> str:
    texto = _texto_limpo(observacoes)
    novo_prefixo = f"Tarifa da operacao FULL ({plataforma_label})."
    if not texto:
        return f"{novo_prefixo} Gerado na baixa de estoque por NF."
    if re.search(r"Tarifa da operacao FULL \([^)]+\)\.", texto, flags=re.IGNORECASE):
        return re.sub(
            r"Tarifa da operacao FULL \([^)]+\)\.",
            novo_prefixo,
            texto,
            count=1,
            flags=re.IGNORECASE,
        )
    return f"{novo_prefixo} {texto}"


def _buscar_conta_tarifa_full_nf(db: Session, tenant_id, numero_nf: str):
    return (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.documento == numero_nf,
            ContaPagar.descricao == f"Tarifa envio FULL NF {numero_nf}",
        )
        .first()
    )


def _buscar_baixas_full_nf(db: Session, tenant_id, numero_nf: str):
    return (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.documento == numero_nf,
            EstoqueMovimentacao.motivo == "full_nfe_saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.created_at.desc(), EstoqueMovimentacao.id.desc())
        .all()
    )


@router.get("/saida-full-nf/historico")
def historico_saida_full_por_nf(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista baixas FULL por NF ja processadas, agrupadas por NF."""
    _current_user, tenant_id = user_and_tenant

    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(joinedload(EstoqueMovimentacao.produto))
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.motivo == "full_nfe_saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(
            desc(EstoqueMovimentacao.created_at),
            desc(EstoqueMovimentacao.id),
        )
        .limit(max(limit * 30, 300))
        .all()
    )

    grupos = {}
    for mov in movimentacoes:
        documento = _texto_limpo(mov.documento) or f"MOV-{mov.id}"
        canal = _canal_saida_full_por_observacao(mov.observacao) or "full"
        if documento not in grupos:
            grupos[documento] = {
                "numero_nf": documento,
                "processado_em": mov.created_at.isoformat() if mov.created_at else None,
                "plataforma": canal,
                "plataforma_label": _CANAL_LABELS.get(canal, canal),
                "observacao": mov.observacao,
                "total_itens": 0,
                "baixas_estoque": 0,
                "lancamentos_financeiros": 0,
                "valor_estoque": 0.0,
                "itens": [],
                "tarifa_envio": None,
            }

        grupo = grupos[documento]
        grupo["total_itens"] += 1
        grupo["baixas_estoque"] += 1
        grupo["valor_estoque"] += float(mov.valor_total or 0)
        grupo["itens"].append(
            {
                "movimentacao_id": mov.id,
                "produto_id": mov.produto_id,
                "sku": _sku_produto(mov.produto) if mov.produto else None,
                "nome": mov.produto.nome if mov.produto else None,
                "quantidade": float(mov.quantidade or 0),
                "estoque_anterior": float(mov.quantidade_anterior or 0),
                "estoque_novo": float(mov.quantidade_nova or 0),
            }
        )

    documentos = list(grupos.keys())
    if documentos:
        contas_tarifa = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.documento.in_(documentos),
                ContaPagar.descricao.ilike("Tarifa envio FULL NF%"),
            )
            .all()
        )

        for conta in contas_tarifa:
            documento = _texto_limpo(conta.documento)
            if not documento or documento not in grupos:
                continue
            grupo = grupos[documento]
            grupo["lancamentos_financeiros"] += 1
            canal = _texto_limpo(conta.canal)
            if canal:
                grupo["plataforma"] = canal
                grupo["plataforma_label"] = _CANAL_LABELS.get(canal, canal)
            valor = float(conta.valor_final or conta.valor_original or 0)
            if not grupo["tarifa_envio"]:
                grupo["tarifa_envio"] = {
                    "conta_pagar_id": conta.id,
                    "valor": valor,
                    "status": conta.status,
                    "data_vencimento": conta.data_vencimento.isoformat()
                    if conta.data_vencimento
                    else None,
                }

    items = list(grupos.values())[:limit]
    return {"items": items, "total": len(grupos)}


@router.put("/saida-full-nf/{numero_nf}/canal")
def atualizar_canal_saida_full_por_nf(
    numero_nf: str,
    payload: SaidaFullNFCanalUpdateRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Corrige canal/origem de uma baixa FULL ja processada."""
    _current_user, tenant_id = user_and_tenant
    canal = (payload.plataforma or "").strip().lower()
    if not canal:
        raise HTTPException(status_code=400, detail="Selecione o novo canal/origem.")
    if canal not in _CANAL_LABELS:
        raise HTTPException(status_code=400, detail="Canal/origem invalido.")

    baixas = _buscar_baixas_full_nf(db, tenant_id, numero_nf)
    if not baixas:
        raise HTTPException(
            status_code=404, detail=f"Nenhuma baixa encontrada para a NF {numero_nf}."
        )

    canal_anterior = _canal_saida_full_por_observacao(baixas[0].observacao)
    plataforma_label = _CANAL_LABELS.get(canal, canal)
    for movimentacao in baixas:
        movimentacao.observacao = _observacao_full_nf_com_canal_atualizado(
            numero_nf,
            movimentacao.observacao,
            canal,
        )

    conta_tarifa = _buscar_conta_tarifa_full_nf(db, tenant_id, numero_nf)
    lancamentos_financeiros = 0
    if conta_tarifa:
        conta_tarifa.canal = canal
        conta_tarifa.observacoes = _observacao_conta_tarifa_full_nf_com_canal(
            conta_tarifa.observacoes,
            plataforma_label,
        )
        lancamentos_financeiros = 1

        lancamentos_manuais = (
            db.query(LancamentoManual)
            .filter(
                LancamentoManual.tenant_id == tenant_id,
                LancamentoManual.documento == numero_nf,
                LancamentoManual.descricao == f"Tarifa envio FULL NF {numero_nf}",
            )
            .all()
        )
        for lancamento in lancamentos_manuais:
            lancamento.observacoes = (
                f"Gerado automaticamente da conta a pagar #{conta_tarifa.id}. "
                f"Canal/origem corrigido para {plataforma_label}."
            )

    db.commit()

    return {
        "success": True,
        "message": f"Canal da NF {numero_nf} atualizado para {plataforma_label}.",
        "numero_nf": numero_nf,
        "plataforma": canal,
        "plataforma_label": plataforma_label,
        "plataforma_anterior": canal_anterior,
        "plataforma_anterior_label": _CANAL_LABELS.get(canal_anterior, canal_anterior)
        if canal_anterior
        else None,
        "baixas_estoque": len(baixas),
        "lancamentos_financeiros": lancamentos_financeiros,
        "total_itens": len(baixas),
        "tarifa_envio": (
            {
                "conta_pagar_id": conta_tarifa.id,
                "valor": float(
                    conta_tarifa.valor_final or conta_tarifa.valor_original or 0
                ),
            }
            if conta_tarifa
            else None
        ),
    }


@router.post("/saida-full-nf/validar-estoque")
def validar_estoque_saida_full_por_nf(
    payload: SaidaFullNFRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida se os itens da NF possuem estoque suficiente, sem gerar baixa."""
    _current_user, tenant_id = user_and_tenant
    itens_validos = [
        item for item in payload.itens if item.quantidade and item.quantidade > 0
    ]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    problemas = _problemas_estoque_saida_full_nf(db, tenant_id, itens_validos)
    return {
        "ok": len(problemas) == 0,
        "total_itens": len(itens_validos),
        "problemas": problemas,
    }


@router.post("/saida-full-nf", status_code=status.HTTP_201_CREATED)
def saida_full_por_nf(
    payload: SaidaFullNFRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Baixa estoque em lote por NF de saida (operacao FULL).

    Regras:
    - Cada item baixa apenas estoque (sem gerar financeiro).
    - Se qualquer item falhar, toda a transacao e cancelada.
    """
    current_user, tenant_id = user_and_tenant

    canal = (payload.plataforma or "").strip().lower()
    canais_validos = set(_CANAL_LABELS.keys())
    if not canal:
        raise HTTPException(
            status_code=400, detail="Selecione o canal/origem da movimentacao FULL."
        )
    if canal not in canais_validos:
        raise HTTPException(
            status_code=400, detail="Canal/origem da movimentacao FULL invalido."
        )
    payload.plataforma = canal

    itens_validos = [
        item for item in payload.itens if item.quantidade and item.quantidade > 0
    ]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    processados = []
    observacao_movimentacao = _observacao_full_nf(
        payload.numero_nf, payload.plataforma, payload.observacao
    )
    tarifa_valor = float(payload.tarifa_envio or 0)
    baixas_existentes = _buscar_baixas_full_nf(db, tenant_id, payload.numero_nf)
    classificacao_tarifa = None
    if tarifa_valor > 0:
        classificacao_tarifa = _resolver_classificacao_tarifa_full_nf(
            db,
            tenant_id,
            categoria_tarifa_id=payload.categoria_tarifa_id,
            dre_subcategoria_tarifa_id=payload.dre_subcategoria_tarifa_id,
        )

    try:
        if baixas_existentes:
            conta_tarifa_existente = _buscar_conta_tarifa_full_nf(
                db, tenant_id, payload.numero_nf
            )

            if tarifa_valor > 0 and classificacao_tarifa and not conta_tarifa_existente:
                categoria_tarifa, subcategoria_tarifa = classificacao_tarifa
                conta_tarifa = _criar_conta_pagar_tarifa_full_nf(
                    db,
                    tenant_id=tenant_id,
                    current_user=current_user,
                    payload=payload,
                    categoria=categoria_tarifa,
                    subcategoria=subcategoria_tarifa,
                )
                db.commit()
                return {
                    "success": True,
                    "message": (
                        f"NF {payload.numero_nf} ja tinha baixa de estoque. "
                        "Apenas a tarifa pendente foi lancada no financeiro."
                    ),
                    "numero_nf": payload.numero_nf,
                    "plataforma": payload.plataforma,
                    "plataforma_label": _CANAL_LABELS.get(
                        payload.plataforma, payload.plataforma
                    ),
                    "estoque_ja_baixado": True,
                    "baixas_estoque": 0,
                    "lancamentos_financeiros": 1,
                    "total_itens": len(baixas_existentes),
                    "itens": [
                        {
                            "produto_id": mov.produto_id,
                            "sku": None,
                            "nome": None,
                            "quantidade": float(mov.quantidade or 0),
                            "estoque_anterior": float(mov.quantidade_anterior or 0),
                            "estoque_novo": float(mov.quantidade_nova or 0),
                        }
                        for mov in baixas_existentes
                    ],
                    "tarifa_envio": {
                        "conta_pagar_id": conta_tarifa.id,
                        "valor": tarifa_valor,
                    },
                }

            detalhe_tarifa = (
                " A tarifa de envio ja esta lancada no financeiro."
                if conta_tarifa_existente
                else " Se ficou faltando tarifa, informe valor e categoria com DRE para lancar somente o financeiro."
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"NF {payload.numero_nf} ja possui baixa de estoque registrada. "
                    f"O sistema bloqueou o reprocessamento para evitar baixa duplicada.{detalhe_tarifa}"
                ),
            )

        _validar_estoque_saida_full_nf(db, tenant_id, itens_validos)

        for item in itens_validos:
            processados.append(
                _processar_item_saida_full_nf(
                    db=db,
                    tenant_id=tenant_id,
                    item=item,
                    numero_nf=payload.numero_nf,
                    observacao_movimentacao=observacao_movimentacao,
                    current_user=current_user,
                )
            )

        conta_tarifa = None
        if classificacao_tarifa:
            categoria_tarifa, subcategoria_tarifa = classificacao_tarifa
            conta_tarifa = _criar_conta_pagar_tarifa_full_nf(
                db,
                tenant_id=tenant_id,
                current_user=current_user,
                payload=payload,
                categoria=categoria_tarifa,
                subcategoria=subcategoria_tarifa,
            )

        db.commit()

        for item in processados:
            sync_itens = item.get("sync_itens") or [
                {
                    "produto_id": item["produto_id"],
                    "estoque_novo": item["estoque_novo"],
                }
            ]
            for sync_item in sync_itens:
                try:
                    sincronizar_bling_background(
                        sync_item["produto_id"],
                        sync_item["estoque_novo"],
                        "saida_full_nfe",
                    )
                except Exception as e_sync:
                    logger.warning(
                        f"[BLING-SYNC] Erro ao agendar sync (saida-full-nf): {e_sync}"
                    )

        return {
            "success": True,
            "message": "Baixa de estoque por NF concluida",
            "numero_nf": payload.numero_nf,
            "plataforma": payload.plataforma,
            "plataforma_label": _CANAL_LABELS.get(
                payload.plataforma, payload.plataforma
            ),
            "baixas_estoque": len(processados),
            "lancamentos_financeiros": 1 if conta_tarifa else 0,
            "total_itens": len(processados),
            "itens": processados,
            "tarifa_envio": (
                {
                    "conta_pagar_id": conta_tarifa.id,
                    "valor": tarifa_valor,
                }
                if conta_tarifa
                else None
            ),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro na baixa FULL por NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar baixa por NF: {str(e)}"
        )


@router.post("/saida-full-pdf/parse")
async def parse_saida_full_pdf(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai SKU + quantidade de um PDF para preencher a baixa FULL por NF.
    Nao baixa estoque automaticamente; apenas retorna os itens interpretados.
    """
    if pdfplumber is None:
        raise HTTPException(
            status_code=500,
            detail="Leitura de PDF indisponivel no backend (pdfplumber nao instalado)",
        )

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo PDF nao informado")

    nome = file.filename.lower()
    if not nome.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF valido")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo PDF vazio")

    try:
        texto_paginas = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                texto_paginas.append(page.extract_text() or "")

        texto = "\n".join(texto_paginas).strip()
        if not texto:
            raise HTTPException(
                status_code=400, detail="Nao foi possivel ler texto do PDF"
            )

        itens = _extrair_itens_full_pdf(texto)
        if not itens:
            raise HTTPException(
                status_code=400,
                detail="Nenhum item SKU+quantidade foi identificado no PDF",
            )

        return {
            "success": True,
            "message": "Itens extraidos do PDF com sucesso",
            "total_itens": len(itens),
            "itens": itens,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao interpretar PDF FULL NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao interpretar PDF: {str(e)}"
        )


@router.post("/saida-full-xml/parse")
async def parse_saida_full_xml(
    file: UploadFile = File(...),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Extrai numero da NF e itens (SKU + quantidade) de XML da NF-e.
    Nao baixa estoque automaticamente; apenas preenche o formulario.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo XML nao informado")

    nome = file.filename.lower()
    if not nome.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Envie um arquivo XML valido")

    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Arquivo XML vazio")

    try:
        dados = _parse_saida_full_xml(xml_bytes)
        return {
            "success": True,
            "message": "XML lido com sucesso",
            **dados,
        }
    except HTTPException:
        raise
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="XML invalido: erro de estrutura")
    except Exception as e:
        logger.error(f"Erro ao interpretar XML FULL NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao interpretar XML: {str(e)}"
        )
