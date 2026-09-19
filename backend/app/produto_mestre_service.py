"""Sugestão e vínculo de produto-mestre (+ categoria/marca/departamento
mestre) do grupo comercial. Mesmo princípio do Checkpoint 1: nunca funde
sozinho, só sugere (leitura) ou vincula quando pedido explicitamente
(escrita) — ver Documentacao/Dominio/Plano-Camada-Geral.md.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.catalogo_mestre_models import CatalogoMestreProduto
from app.produto_mestre_models import (
    CategoriaMestre,
    DepartamentoMestre,
    MarcaMestre,
    ProdutoMestre,
)
from app.produtos_catalogo_models import Categoria, Departamento, Marca, Produto


def sugerir_produto_mestre(
    db: Session, grupo_id: int, *, nome: str | None = None, gtin: str | None = None
) -> ProdutoMestre | None:
    """Prioriza GTIN (mais confiável que nome) quando informado."""
    gtin_limpo = (gtin or "").strip()
    if gtin_limpo:
        achado = (
            db.query(ProdutoMestre)
            .filter(
                ProdutoMestre.grupo_id == grupo_id,
                ProdutoMestre.ativo.is_(True),
                ProdutoMestre.gtin_ean == gtin_limpo,
            )
            .first()
        )
        if achado:
            return achado

    nome_limpo = " ".join((nome or "").split())
    if not nome_limpo:
        return None
    return (
        db.query(ProdutoMestre)
        .filter(
            ProdutoMestre.grupo_id == grupo_id,
            ProdutoMestre.ativo.is_(True),
            ProdutoMestre.nome.ilike(nome_limpo),
        )
        .first()
    )


def vincular_produto_mestre(
    db: Session,
    *,
    produto: Produto,
    grupo_id: int,
    usuario_id: int,
    produto_mestre_id: int | None,
) -> ProdutoMestre:
    if produto_mestre_id is not None:
        mestre = (
            db.query(ProdutoMestre)
            .filter(
                ProdutoMestre.id == produto_mestre_id,
                ProdutoMestre.grupo_id == grupo_id,
                ProdutoMestre.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto-mestre não encontrado neste grupo.",
            )
    else:
        nome = " ".join(produto.nome.split())
        descricao_curta = produto.descricao_curta
        descricao_completa = produto.descricao_completa
        imagem_principal = produto.imagem_principal

        gtin = (produto.gtin_ean or "").strip()
        if gtin and (not descricao_curta or not descricao_completa or not imagem_principal):
            curado = (
                db.query(CatalogoMestreProduto)
                .filter(CatalogoMestreProduto.gtin == gtin)
                .first()
            )
            if curado:
                descricao_curta = descricao_curta or curado.descricao_curta
                descricao_completa = descricao_completa or curado.descricao_completa
                # CatalogoMestreProduto não guarda uma URL única de imagem
                # (tem galeria própria, CatalogoMestreImagem) — não copiado
                # aqui de propósito, pra não acoplar os dois modelos agora.

        mestre = ProdutoMestre(
            grupo_id=grupo_id,
            nome=nome,
            descricao_curta=descricao_curta,
            descricao_completa=descricao_completa,
            tags=produto.tags,
            imagem_principal=imagem_principal,
            ncm=produto.ncm,
            cest=produto.cest,
            gtin_ean=produto.gtin_ean,
            gtin_ean_tributario=produto.gtin_ean_tributario,
            unidade=produto.unidade,
            peso_liquido=produto.peso_liquido,
            peso_bruto=produto.peso_bruto,
            largura=produto.largura,
            altura=produto.altura,
            profundidade=produto.profundidade,
            itens_por_caixa=produto.itens_por_caixa,
            criado_por_usuario_id=usuario_id,
        )
        db.add(mestre)
        db.flush()

    produto.produto_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def desvincular_produto_mestre(db: Session, *, produto: Produto) -> None:
    produto.produto_mestre_id = None
    db.commit()


def _sugerir_taxonomia_mestre(modelo, db: Session, grupo_id: int, nome: str):
    nome_limpo = " ".join((nome or "").split())
    if not nome_limpo:
        return None
    return (
        db.query(modelo)
        .filter(
            modelo.grupo_id == grupo_id,
            modelo.ativo.is_(True),
            modelo.nome.ilike(nome_limpo),
        )
        .first()
    )


def _vincular_taxonomia_mestre(
    modelo, local, db: Session, *, grupo_id: int, usuario_id: int, mestre_id: int | None
):
    if mestre_id is not None:
        mestre = (
            db.query(modelo)
            .filter(
                modelo.id == mestre_id,
                modelo.grupo_id == grupo_id,
                modelo.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro mestre não encontrado neste grupo.",
            )
    else:
        mestre = modelo(
            grupo_id=grupo_id,
            nome=" ".join(local.nome.split()),
            criado_por_usuario_id=usuario_id,
        )
        db.add(mestre)
        db.flush()
    return mestre


def sugerir_categoria_mestre(db: Session, grupo_id: int, nome: str) -> CategoriaMestre | None:
    return _sugerir_taxonomia_mestre(CategoriaMestre, db, grupo_id, nome)


def vincular_categoria_mestre(
    db: Session, *, categoria: Categoria, grupo_id: int, usuario_id: int, mestre_id: int | None
) -> CategoriaMestre:
    mestre = _vincular_taxonomia_mestre(
        CategoriaMestre, categoria, db, grupo_id=grupo_id, usuario_id=usuario_id, mestre_id=mestre_id
    )
    categoria.categoria_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def sugerir_marca_mestre(db: Session, grupo_id: int, nome: str) -> MarcaMestre | None:
    return _sugerir_taxonomia_mestre(MarcaMestre, db, grupo_id, nome)


def vincular_marca_mestre(
    db: Session, *, marca: Marca, grupo_id: int, usuario_id: int, mestre_id: int | None
) -> MarcaMestre:
    mestre = _vincular_taxonomia_mestre(
        MarcaMestre, marca, db, grupo_id=grupo_id, usuario_id=usuario_id, mestre_id=mestre_id
    )
    marca.marca_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def sugerir_departamento_mestre(db: Session, grupo_id: int, nome: str) -> DepartamentoMestre | None:
    return _sugerir_taxonomia_mestre(DepartamentoMestre, db, grupo_id, nome)


def vincular_departamento_mestre(
    db: Session, *, departamento: Departamento, grupo_id: int, usuario_id: int, mestre_id: int | None
) -> DepartamentoMestre:
    mestre = _vincular_taxonomia_mestre(
        DepartamentoMestre,
        departamento,
        db,
        grupo_id=grupo_id,
        usuario_id=usuario_id,
        mestre_id=mestre_id,
    )
    departamento.departamento_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre
