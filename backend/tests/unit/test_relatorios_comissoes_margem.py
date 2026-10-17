"""Regressão: base comissionável não representa a receita da venda."""

import sqlite3

from app.routers import relatorios_comissoes as relatorios


class _Resultado:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


def test_margem_usa_venda_real_e_conta_cada_item_parcela_uma_vez(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE produtos (id INTEGER, tenant_id TEXT, nome TEXT, categoria_id INTEGER);
        CREATE TABLE categorias (id INTEGER, tenant_id TEXT, nome TEXT);
        CREATE TABLE comissoes_itens (
            id INTEGER, tenant_id TEXT, venda_id INTEGER, venda_item_id INTEGER,
            parcela_numero INTEGER, produto_id INTEGER, funcionario_id INTEGER,
            data_venda TEXT, status TEXT, valor_venda REAL, valor_custo REAL,
            valor_base_calculo REAL, percentual_aplicado REAL, valor_comissao_gerada REAL
        );
        INSERT INTO categorias VALUES (1, 'empresa-1', 'Rações');
        INSERT INTO produtos VALUES (1, 'empresa-1', 'Ração A', 1);
        INSERT INTO produtos VALUES (2, 'empresa-1', 'Ração B', 1);
        """
    )
    # Mesmo item com duas parcelas e dois funcionários: venda/custo entram uma
    # vez por parcela, mas as quatro comissões são despesas reais.
    rows = [
        (
            1,
            "empresa-1",
            10,
            101,
            1,
            1,
            7,
            "2026-10-01",
            "pendente",
            200,
            120,
            12.5,
            50,
            0.25,
        ),
        (
            2,
            "empresa-1",
            10,
            101,
            1,
            1,
            8,
            "2026-10-01",
            "pendente",
            200,
            120,
            12.5,
            50,
            0.25,
        ),
        (
            3,
            "empresa-1",
            10,
            101,
            2,
            1,
            7,
            "2026-10-01",
            "pendente",
            200,
            120,
            12.5,
            50,
            0.25,
        ),
        (
            4,
            "empresa-1",
            10,
            101,
            2,
            1,
            8,
            "2026-10-01",
            "pendente",
            200,
            120,
            12.5,
            50,
            0.25,
        ),
        (
            5,
            "empresa-1",
            11,
            102,
            1,
            2,
            7,
            "2026-10-02",
            "pendente",
            100,
            60,
            30,
            None,
            1,
        ),
        (
            6,
            "empresa-1",
            12,
            103,
            1,
            1,
            7,
            "2026-10-03",
            "estornado",
            500,
            50,
            450,
            100,
            5,
        ),
        (
            7,
            "empresa-2",
            13,
            104,
            1,
            1,
            7,
            "2026-10-04",
            "pendente",
            900,
            1,
            899,
            100,
            1,
        ),
    ]
    db.executemany(
        "INSERT INTO comissoes_itens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
    )

    def executar(_db, sql, params, tenant_id):
        sql = sql.replace("{tenant_filter}", "tenant_id = :__tenant_id")
        # SQLite só precisa desta adaptação de sintaxe para exercitar a
        # agregação mensal, escrita para PostgreSQL em produção.
        sql = (
            sql.replace(
                "EXTRACT(MONTH FROM ci.data_venda)::INTEGER",
                "CAST(strftime('%m', ci.data_venda) AS INTEGER)",
            )
            .replace(
                "EXTRACT(MONTH FROM ci.data_venda)",
                "CAST(strftime('%m', ci.data_venda) AS INTEGER)",
            )
            .replace(
                "EXTRACT(YEAR FROM ci.data_venda)::INTEGER",
                "CAST(strftime('%Y', ci.data_venda) AS INTEGER)",
            )
        )
        return _Resultado(
            db.execute(sql, {**params, "__tenant_id": tenant_id}).fetchall()
        )

    monkeypatch.setattr(relatorios, "execute_tenant_safe", executar)
    try:
        resultado = relatorios.relatorio_margem_produto(
            db=db, user_and_tenant=(None, "empresa-1")
        )
        por_nome = {item["produto_nome"]: item for item in resultado["dados"]}
        racao_a = por_nome["Ração A"]
        assert racao_a["quantidade_vendas"] == 1
        assert racao_a["valor_venda"] == 200
        assert racao_a["valor_custo"] == 120
        assert racao_a["valor_comissao"] == 1
        assert racao_a["margem_liquida"] == 79
        assert racao_a["percentual_margem"] == 39.5
        assert not racao_a["alerta_margem_negativa"]
        assert por_nome["Ração B"]["margem_liquida"] == 39
        assert resultado["produtos_com_alerta"] == 0

        ranking = relatorios.ranking_produtos(
            limite=10, db=db, user_and_tenant=(None, "empresa-1")
        )
        assert {
            item["produto_nome"]: item["total_venda"] for item in ranking["ranking"]
        } == {
            "Ração A": 200,
            "Ração B": 100,
        }
        categorias = relatorios.ranking_categorias(
            db=db, user_and_tenant=(None, "empresa-1")
        )
        assert categorias["ranking"][0]["total_venda"] == 300
        dre = relatorios.visao_dre(
            ano=2026,
            mes_inicio=10,
            mes_fim=10,
            db=db,
            user_and_tenant=(None, "empresa-1"),
        )
        assert dre["total_ano"]["receita_bruta"] == 300
        assert dre["total_ano"]["custo_total"] == 180
        assert dre["total_ano"]["despesa_comissao"] == 2
        assert dre["total_ano"]["margem_liquida"] == 118
    finally:
        db.close()
