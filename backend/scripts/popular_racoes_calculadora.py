"""Popula campos inferiveis da calculadora de racao.

Uso dentro do container/backend:
  python scripts/popular_racoes_calculadora.py --tenant-id <uuid> --apply

Sem --apply roda em modo dry-run.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter
from typing import Iterable

from sqlalchemy.orm import joinedload

from app.classificador_racao import classificar_produto
from app.db import SessionLocal
from app.opcoes_racao_models import (
    ApresentacaoPeso,
    FasePublico,
    LinhaRacao,
    PorteAnimal,
    SaborProteina,
)
from app.produtos_models import Produto


def normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFD", str(valor or "").strip().lower())
    return "".join(char for char in texto if unicodedata.category(char) != "Mn")


def normalizar_classificacao(nome_linha: str | None) -> str | None:
    nome = normalizar(nome_linha)
    if not nome:
        return None

    if "super" in nome and "premium" in nome:
        return "super_premium"
    if "premium" in nome and ("special" in nome or "especial" in nome):
        return "premium_special"
    if "premium" in nome:
        return "premium"
    if "standard" in nome:
        return "standard"
    return nome.replace(" ", "_")


def detectar_especie(texto: str) -> str | None:
    dog = bool(
        re.search(
            r"\b(dog|dogs|cao|caes|cachorro|canino|puppy|filhote\s+cao)\b",
            texto,
        )
    )
    cat = bool(
        re.search(
            r"\b(cat|cats|gato|gatos|felino|kitten|filhote\s+gato)\b",
            texto,
        )
    )

    if dog and cat:
        return "both"
    if dog:
        return "dog"
    if cat:
        return "cat"
    return None


def parece_racao(texto: str, produto: Produto) -> bool:
    if normalizar(getattr(produto, "tipo", "")).startswith("ra"):
        return True
    if getattr(produto, "linha_racao_id", None):
        return True
    if normalizar(getattr(produto, "classificacao_racao", "")) not in {"", "nao"}:
        return True
    return bool(
        re.search(
            r"\b(racao|racoes|alimento\s+completo|alimento\s+seco|alimento\s+umido)\b",
            texto,
        )
    )


def mapa_por_nome(itens: Iterable[object]) -> dict[str, object]:
    return {normalizar(getattr(item, "nome", "")): item for item in itens}


def opcao_por_nome(opcoes: dict[str, object], nomes: Iterable[str]) -> object | None:
    for nome in nomes:
        chave = normalizar(nome)
        if chave in opcoes:
            return opcoes[chave]
    return None


def buscar_apresentacao(apresentacoes: list[ApresentacaoPeso], peso: float | None):
    if not peso:
        return None

    for apresentacao in apresentacoes:
        if abs(float(apresentacao.peso_kg or 0) - float(peso)) <= 0.01:
            return apresentacao
    return None


def categoria_racao_por_fase(nome_fase: str | None) -> str | None:
    fase = normalizar(nome_fase)
    if "filhote" in fase:
        return "filhote"
    if "senior" in fase or "idoso" in fase:
        return "senior"
    if "gestante" in fase:
        return "gestante"
    if "adulto" in fase:
        return "adulto"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    db = SessionLocal()
    stats = Counter()
    exemplos = []

    try:
        linhas = mapa_por_nome(
            db.query(LinhaRacao)
            .filter(LinhaRacao.tenant_id == args.tenant_id, LinhaRacao.ativo.is_(True))
            .all()
        )
        portes = mapa_por_nome(
            db.query(PorteAnimal)
            .filter(PorteAnimal.tenant_id == args.tenant_id, PorteAnimal.ativo.is_(True))
            .all()
        )
        fases = mapa_por_nome(
            db.query(FasePublico)
            .filter(FasePublico.tenant_id == args.tenant_id, FasePublico.ativo.is_(True))
            .all()
        )
        sabores = mapa_por_nome(
            db.query(SaborProteina)
            .filter(SaborProteina.tenant_id == args.tenant_id, SaborProteina.ativo.is_(True))
            .all()
        )
        apresentacoes = (
            db.query(ApresentacaoPeso)
            .filter(
                ApresentacaoPeso.tenant_id == args.tenant_id,
                ApresentacaoPeso.ativo.is_(True),
            )
            .all()
        )

        produtos = (
            db.query(Produto)
            .options(joinedload(Produto.categoria), joinedload(Produto.marca))
            .filter(
                Produto.tenant_id == args.tenant_id,
                Produto.ativo.is_(True),
                Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            )
            .order_by(Produto.id)
            .all()
        )

        for produto in produtos:
            texto = normalizar(
                " ".join(
                    [
                        produto.nome,
                        getattr(produto.categoria, "nome", ""),
                        getattr(produto.marca, "nome", ""),
                    ]
                )
            )

            if not parece_racao(texto, produto):
                continue

            especie = detectar_especie(texto) or produto.especies_indicadas
            if especie not in {"dog", "cat", "both"}:
                stats["ignoradas_sem_especie_cao_gato"] += 1
                continue

            resultado, _, _ = classificar_produto(produto.nome, produto.peso_embalagem)
            alteracoes = []

            if normalizar(produto.tipo) != "racao":
                produto.tipo = "ra\u00e7\u00e3o"
                alteracoes.append("tipo")

            if not produto.especies_indicadas:
                produto.especies_indicadas = especie
                alteracoes.append("especies_indicadas")

            if not produto.peso_embalagem and resultado.get("peso_embalagem"):
                produto.peso_embalagem = resultado["peso_embalagem"]
                alteracoes.append("peso_embalagem")

            linha = None
            if resultado.get("linha_racao"):
                linha = opcao_por_nome(linhas, [resultado["linha_racao"]])
            if not linha:
                linha = opcao_por_nome(linhas, ["Standard"])
            if not produto.linha_racao_id and linha:
                produto.linha_racao_id = linha.id
                alteracoes.append("linha_racao_id")
            if not produto.classificacao_racao and (linha or resultado.get("linha_racao")):
                produto.classificacao_racao = normalizar_classificacao(
                    getattr(linha, "nome", None) or resultado.get("linha_racao")
                )
                alteracoes.append("classificacao_racao")

            porte = None
            for nome_porte in resultado.get("porte_animal") or []:
                porte = opcao_por_nome(portes, [nome_porte])
                if porte:
                    break
            if not porte:
                porte = opcao_por_nome(portes, ["Todos"])
            if not produto.porte_animal_id and porte:
                produto.porte_animal_id = porte.id
                alteracoes.append("porte_animal_id")

            fase = None
            for nome_fase in resultado.get("fase_publico") or []:
                fase = opcao_por_nome(fases, [nome_fase])
                if fase:
                    break
            if not fase:
                fase = opcao_por_nome(fases, ["Adulto"])
            if not produto.fase_publico_id and fase:
                produto.fase_publico_id = fase.id
                alteracoes.append("fase_publico_id")
            if not produto.categoria_racao and fase:
                categoria = categoria_racao_por_fase(getattr(fase, "nome", None))
                if categoria:
                    produto.categoria_racao = categoria
                    alteracoes.append("categoria_racao")

            sabor = None
            if resultado.get("sabor_proteina"):
                sabor = opcao_por_nome(
                    sabores,
                    [resultado["sabor_proteina"], "Salmao" if resultado["sabor_proteina"] == "Peixe" else ""],
                )
            if not sabor:
                sabor = opcao_por_nome(sabores, ["Mix"])
            if not produto.sabor_proteina_id and sabor:
                produto.sabor_proteina_id = sabor.id
                alteracoes.append("sabor_proteina_id")

            apresentacao = buscar_apresentacao(apresentacoes, produto.peso_embalagem)
            if not produto.apresentacao_peso_id and apresentacao:
                produto.apresentacao_peso_id = apresentacao.id
                alteracoes.append("apresentacao_peso_id")

            if alteracoes:
                stats["produtos_alterados"] += 1
                for campo in alteracoes:
                    stats[f"campo_{campo}"] += 1
                if len(exemplos) < 20:
                    exemplos.append((produto.id, produto.nome, ", ".join(alteracoes)))

                if args.apply:
                    db.add(produto)

                if args.limit and stats["produtos_alterados"] >= args.limit:
                    break

        if args.apply:
            db.commit()
        else:
            db.rollback()

        print("modo:", "apply" if args.apply else "dry-run")
        for chave, valor in stats.most_common():
            print(f"{chave}: {valor}")
        if exemplos:
            print("exemplos:")
            for produto_id, nome, campos in exemplos:
                print(f"- {produto_id}: {nome} -> {campos}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
