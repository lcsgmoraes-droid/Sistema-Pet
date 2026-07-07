"""Resumo de execucao do importador SimplesVet."""

from __future__ import annotations


def exibir_resumo(stats, nao_importados):
    """Exibe resumo da importacao."""
    print("\n" + "=" * 90)
    print("RESUMO DA IMPORTACAO".center(90))
    print("=" * 90)
    print(
        f"{'ENTIDADE':<15} | {'TOTAL':>6} | {'NOVOS':>6} | {'DUPLIC':>6} | {'ERROS':>6} | {'SEM_SKU':>7} | {'TAXA':>6}"
    )
    print("-" * 90)

    for entidade, item_stats in stats.items():
        if item_stats["total"] > 0:
            taxa = (
                (item_stats["sucesso"] / item_stats["total"]) * 100
                if item_stats["total"] > 0
                else 0
            )
            sem_sku = item_stats.get("sem_sku", 0)
            print(
                f"{entidade.upper():<15} | {item_stats['total']:>6} | {item_stats['sucesso']:>6} | "
                f"{item_stats['duplicado']:>6} | {item_stats['erro']:>6} | {sem_sku:>7} | {taxa:>5.1f}%"
            )

    print("-" * 90)

    total_geral = sum(s["total"] for s in stats.values())
    novos_geral = sum(s["sucesso"] for s in stats.values())
    duplic_geral = sum(s["duplicado"] for s in stats.values())
    erros_geral = sum(s["erro"] for s in stats.values())
    sem_sku_geral = sum(s.get("sem_sku", 0) for s in stats.values())

    print(
        f"{'TOTAL GERAL':<15} | {total_geral:>6} | {novos_geral:>6} | "
        f"{duplic_geral:>6} | {erros_geral:>6} | {sem_sku_geral:>7}"
    )
    print("=" * 90)

    nao_imp_total = sum(len(items) for items in nao_importados.values())
    if nao_imp_total > 0:
        print(f"\nATENCAO: {nao_imp_total} itens NAO foram importados")
        for entidade, items in nao_importados.items():
            if items:
                print(f"  - {entidade.capitalize()}: {len(items)}")
        print(
            "\nVerifique os arquivos CSV em logs_importacao/ para detalhes dos produtos nao importados"
        )
    print("=" * 90 + "\n")
