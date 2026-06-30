"""Consulta e serializacao de opcoes para a calculadora de racao."""

from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.produtos_models import Categoria, Marca, Produto

from .core import _avaliar_aptidao_calculadora, _produto_tem_config_racao
from .schemas import RacaoCalculadoraOption


def _produto_eh_racao_expr():
    tipo_normalizado = func.lower(func.coalesce(Produto.tipo, ""))
    classificacao_normalizada = func.lower(
        func.coalesce(Produto.classificacao_racao, "")
    )
    return or_(
        tipo_normalizado.like("ra%"),
        Produto.linha_racao_id.isnot(None),
        and_(
            classificacao_normalizada != "",
            classificacao_normalizada.notin_(["nao", "não"]),
        ),
    )


def _usar_unaccent(db: Session) -> bool:
    try:
        return db.get_bind().dialect.name == "postgresql"
    except Exception:
        return False


def _busca_ilike(column, pattern: str, db: Session):
    if _usar_unaccent(db):
        texto_coluna = func.lower(func.unaccent(func.coalesce(column, "")))
        return texto_coluna.ilike(func.lower(func.unaccent(pattern)))

    return func.lower(func.coalesce(column, "")).ilike(pattern.lower())


def _busca_racao_conditions(palavra: str, db: Session):
    termo = (palavra or "").strip()
    busca_pattern = f"%{termo}%"
    return or_(
        _busca_ilike(Produto.nome, busca_pattern, db),
        _busca_ilike(Produto.codigo, busca_pattern, db),
        _busca_ilike(Produto.codigo_barras, busca_pattern, db),
        _busca_ilike(Produto.classificacao_racao, busca_pattern, db),
        _busca_ilike(Produto.categoria_racao, busca_pattern, db),
        _busca_ilike(Produto.especies_indicadas, busca_pattern, db),
        _busca_ilike(Produto.sabor_proteina, busca_pattern, db),
        _busca_ilike(Categoria.nome, busca_pattern, db),
        _busca_ilike(Marca.nome, busca_pattern, db),
    )


def _float_ou_none(valor) -> Optional[float]:
    try:
        if valor is None:
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def _serializar_opcao_racao(
    produto: Produto,
    categoria_nome: Optional[str],
    marca_nome: Optional[str],
) -> RacaoCalculadoraOption:
    faltantes = _avaliar_aptidao_calculadora(produto)
    return RacaoCalculadoraOption(
        id=produto.id,
        nome=produto.nome,
        codigo=produto.codigo,
        sku=getattr(produto, "sku", None),
        codigo_barras=produto.codigo_barras,
        categoria_nome=categoria_nome,
        marca_nome=marca_nome,
        tipo=produto.tipo,
        eh_racao=_produto_tem_config_racao(produto),
        classificacao_racao=produto.classificacao_racao,
        categoria_racao=produto.categoria_racao,
        especies_indicadas=produto.especies_indicadas,
        peso_embalagem=_float_ou_none(produto.peso_embalagem),
        preco_venda=_float_ou_none(produto.preco_venda),
        linha_racao_id=produto.linha_racao_id,
        porte_animal_id=produto.porte_animal_id,
        fase_publico_id=produto.fase_publico_id,
        tipo_tratamento_id=produto.tipo_tratamento_id,
        sabor_proteina_id=produto.sabor_proteina_id,
        apresentacao_peso_id=produto.apresentacao_peso_id,
        porte_animal=produto.porte_animal,
        fase_publico=produto.fase_publico,
        tipo_tratamento=produto.tipo_tratamento,
        sabor_proteina=produto.sabor_proteina,
        tabela_consumo=produto.tabela_consumo,
        tabela_nutricional=produto.tabela_nutricional,
        apta=not faltantes,
        faltantes=faltantes,
    )
