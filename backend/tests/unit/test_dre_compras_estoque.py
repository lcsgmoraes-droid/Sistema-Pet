from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import dre_base_routes
from app.dre_canais import agregacao, detalhes
from app.dre_canais.contas import classificacoes_contas_pagar, eh_compra_estoque
from app.dre_canais.detalhes import _detalhes_contas_campo
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_calculos import (
    calcular_frete_notas_entrada,
    calcular_taxas_cartao,
    obter_despesas_por_categoria,
)
from app.dre_schemas import DREResponse
from app.dre_plano_contas_models import (
    DRECategoria,
    DRESubcategoria,
    EscopoRateio,
    NaturezaDRE,
    TipoCusto,
)
from app.financeiro_models import CategoriaFinanceira, ContaPagar, TipoDespesa
from app.produtos_models import NotaEntrada
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
OUTRO_TENANT_ID = UUID("22222222-2222-2222-2222-222222222222")


def _conta(
    id: int,
    descricao: str,
    valor: str,
    *,
    subcategoria_id: int,
    tipo_id: int | None = None,
    categoria_id: int | None = None,
    canal: str = "loja_fisica",
    tenant_id: UUID = TENANT_ID,
    status: str = "pendente",
    afeta_dre: bool = True,
    nota_entrada_id: int | None = None,
    fornecedor_id: int | None = None,
    conta_principal_id: int | None = None,
    numero_parcela: int | None = None,
) -> ContaPagar:
    return ContaPagar(
        id=id,
        tenant_id=tenant_id,
        user_id=1,
        descricao=descricao,
        valor_original=Decimal(valor),
        valor_final=Decimal(valor),
        data_emissao=date(2026, 10, 5),
        data_vencimento=date(2026, 10, 20),
        dre_subcategoria_id=subcategoria_id,
        tipo_despesa_id=tipo_id,
        categoria_id=categoria_id,
        canal=canal,
        status=status,
        afeta_dre=afeta_dre,
        nota_entrada_id=nota_entrada_id,
        fornecedor_id=fornecedor_id,
        eh_parcelado=conta_principal_id is not None or status == "parcelado",
        conta_principal_id=conta_principal_id,
        numero_parcela=numero_parcela,
        total_parcelas=2 if conta_principal_id or status == "parcelado" else None,
    )


def _inserir(db, model, objetos) -> None:
    """Fixture usa IDs estaveis para simular subcategorias homonimas legadas."""
    linhas = [
        {
            coluna.name: valor
            for coluna in model.__table__.columns
            if (valor := getattr(objeto, coluna.name, None)) is not None
        }
        for objeto in objetos
    ]
    for linha in linhas:
        db.execute(model.__table__.insert().values(**linha))


def test_compra_de_estoque_e_contas_parceladas_nao_duplicam_dre(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            DRECategoria.__table__,
            DRESubcategoria.__table__,
            CategoriaFinanceira.__table__,
            TipoDespesa.__table__,
            ContaPagar.__table__,
            NotaEntrada.__table__,
        ],
    )
    db = sessionmaker(bind=engine)()
    set_current_tenant(TENANT_ID)
    try:
        _inserir(
            db,
            DRECategoria,
            [
                DRECategoria(
                    id=1, tenant_id=TENANT_ID, nome="Custos", natureza=NaturezaDRE.CUSTO
                ),
                DRECategoria(
                    id=2,
                    tenant_id=TENANT_ID,
                    nome="Despesas",
                    natureza=NaturezaDRE.DESPESA,
                ),
            ],
        )
        db.flush()
        subcategorias = []
        for id, categoria_id, nome, tenant_id in (
            (1, 1, "CMV - Produtos", TENANT_ID),
            (2, 1, "Fretes sobre Compras", TENANT_ID),
            (3, 1, "Fretes sobre Compras", TENANT_ID),
            (7, 1, " Fretes sobre Compras ", TENANT_ID),
            (4, 2, "Outras despesas", TENANT_ID),
            (5, 2, "Aluguel", TENANT_ID),
        ):
            subcategorias.append(
                DRESubcategoria(
                    id=id,
                    tenant_id=tenant_id,
                    categoria_id=categoria_id,
                    nome=nome,
                    tipo_custo=TipoCusto.DIRETO,
                    escopo_rateio=EscopoRateio.AMBOS,
                )
            )
        _inserir(db, DRESubcategoria, subcategorias)
        _inserir(
            db,
            CategoriaFinanceira,
            [
                CategoriaFinanceira(
                    id=10,
                    tenant_id=TENANT_ID,
                    user_id=1,
                    nome="ENTRADA DE MERCADORIA",
                    tipo="despesa",
                ),
                CategoriaFinanceira(
                    id=11,
                    tenant_id=TENANT_ID,
                    user_id=1,
                    nome="ACESSÓRIOS PET",
                    tipo="despesa",
                    categoria_pai_id=10,
                ),
                CategoriaFinanceira(
                    id=12,
                    tenant_id=TENANT_ID,
                    user_id=1,
                    nome="Fretes sobre Compras",
                    tipo="despesa",
                ),
                CategoriaFinanceira(
                    id=13,
                    tenant_id=TENANT_ID,
                    user_id=1,
                    nome="Administrativo",
                    tipo="despesa",
                ),
            ],
        )
        _inserir(
            db,
            TipoDespesa,
            [
                TipoDespesa(
                    id=1,
                    tenant_id=TENANT_ID,
                    nome="Produto para Revenda",
                    e_custo_fixo=False,
                    dre_subcategoria_id=1,
                ),
                TipoDespesa(
                    id=2,
                    tenant_id=TENANT_ID,
                    nome="Frete de Compra",
                    e_custo_fixo=False,
                    dre_subcategoria_id=2,
                ),
                TipoDespesa(
                    id=3,
                    tenant_id=TENANT_ID,
                    nome="Embalagens",
                    e_custo_fixo=False,
                    dre_subcategoria_id=4,
                ),
            ],
        )
        _inserir(
            db,
            ContaPagar,
            [
                _conta(
                    5247,
                    "ACESSÓRIOS PET",
                    "471.40",
                    subcategoria_id=1,
                    tipo_id=1,
                    categoria_id=11,
                ),
                _conta(2, "Nova compra", "40", subcategoria_id=1, categoria_id=11),
                _conta(
                    3,
                    "Frete de compra",
                    "25",
                    subcategoria_id=2,
                    tipo_id=1,
                    categoria_id=12,
                ),
                _conta(
                    4,
                    "Frete de compra",
                    "10",
                    subcategoria_id=3,
                    tipo_id=2,
                    canal="mercado_livre",
                ),
                _conta(5, "Frete sem DRE", "300", subcategoria_id=2, afeta_dre=False),
                _conta(6, "Frete da NF", "400", subcategoria_id=3, nota_entrada_id=901),
                _conta(7, "Aluguel", "50", subcategoria_id=5, categoria_id=13),
                _conta(8, "Ajuste de embalagem", "30", subcategoria_id=1, tipo_id=3),
                _conta(11, "Frete legado", "5", subcategoria_id=7, tipo_id=2),
                _conta(
                    9, "Compra cancelada", "999", subcategoria_id=4, status="cancelado"
                ),
                _conta(
                    20, "Despesa parcelada", "60", subcategoria_id=4, status="parcelado"
                ),
                _conta(
                    21,
                    "Despesa parcelada - Parcela 1/2",
                    "30",
                    subcategoria_id=4,
                    conta_principal_id=20,
                    numero_parcela=1,
                ),
                _conta(
                    22,
                    "Despesa parcelada - Parcela 2/2",
                    "30",
                    subcategoria_id=4,
                    conta_principal_id=20,
                    numero_parcela=2,
                ),
                _conta(
                    30, "Frete parcelado", "40", subcategoria_id=2, status="parcelado"
                ),
                _conta(
                    31,
                    "Frete parcelado - Parcela 1/2",
                    "20",
                    subcategoria_id=2,
                    conta_principal_id=30,
                    numero_parcela=1,
                ),
                _conta(
                    32,
                    "Frete parcelado - Parcela 2/2",
                    "20",
                    subcategoria_id=2,
                    conta_principal_id=30,
                    numero_parcela=2,
                ),
            ],
        )
        db.commit()

        set_current_tenant(OUTRO_TENANT_ID)
        _inserir(
            db,
            DRECategoria,
            [
                DRECategoria(
                    id=3,
                    tenant_id=OUTRO_TENANT_ID,
                    nome="Custos",
                    natureza=NaturezaDRE.CUSTO,
                )
            ],
        )
        _inserir(
            db,
            DRESubcategoria,
            [
                DRESubcategoria(
                    id=6,
                    tenant_id=OUTRO_TENANT_ID,
                    categoria_id=3,
                    nome="Fretes sobre Compras",
                    tipo_custo=TipoCusto.DIRETO,
                    escopo_rateio=EscopoRateio.AMBOS,
                )
            ],
        )
        _inserir(
            db,
            ContaPagar,
            [
                _conta(
                    10,
                    "Frete outro tenant",
                    "999",
                    subcategoria_id=6,
                    tenant_id=OUTRO_TENANT_ID,
                )
            ],
        )
        db.commit()
        set_current_tenant(TENANT_ID)

        compras = db.query(ContaPagar).filter(ContaPagar.id.in_([2, 5247])).all()
        tipos, categorias = classificacoes_contas_pagar(db, TENANT_ID, compras)
        assert all(eh_compra_estoque(conta, tipos, categorias) for conta in compras)

        monkeypatch.setattr(
            agregacao,
            "calcular_resumo_folha_gerencial",
            lambda *args, **kwargs: {"ajustes_por_canal": {}},
        )
        dados = {}
        agregacao.agregar_contas_pagar_por_canal(db, 10, 2026, TENANT_ID, dados)
        agregacao.agregar_fretes_sobre_compras(db, 10, 2026, TENANT_ID, dados)
        linhas, totais = montar_linhas_dre_competencia(dados)

        assert dados["loja_fisica"]["fretes_compras"] == Decimal("70")
        assert dados["mercado_livre"]["fretes_compras"] == Decimal("10")
        assert dados["loja_fisica"]["despesas_administrativas"] == Decimal("50")
        assert dados["loja_fisica"]["outras_despesas"] == Decimal("90")
        assert totais["cmv"] == 80.0
        assert totais["despesas_operacionais"] == 140.0
        assert totais["lucro_liquido"] == -220.0

        for canal, campo in (
            ("loja_fisica", "fretes_compras"),
            ("mercado_livre", "fretes_compras"),
            ("loja_fisica", "despesas_administrativas"),
            ("loja_fisica", "outras_despesas"),
        ):
            detalhe = _detalhes_contas_campo(db, 10, 2026, TENANT_ID, canal, campo)
            linha = next(
                linha
                for linha in linhas
                if linha.campo == campo and linha.canal == canal
            )
            assert sum(item.valor for item in detalhe) == linha.valor
            assert not {"conta-pagar-5247", "conta-pagar-20", "conta-pagar-30"} & {
                item.id for item in detalhe
            }

        assert {
            item.id
            for item in _detalhes_contas_campo(
                db, 10, 2026, TENANT_ID, "loja_fisica", "fretes_compras"
            )
        } == {"conta-pagar-3", "conta-pagar-11", "conta-pagar-31", "conta-pagar-32"}
        assert {
            item.id
            for item in _detalhes_contas_campo(
                db, 10, 2026, TENANT_ID, "loja_fisica", "outras_despesas"
            )
        } == {"conta-pagar-8", "conta-pagar-21", "conta-pagar-22"}

        assert obter_despesas_por_categoria(db, 10, 2026, TENANT_ID) == {
            "Despesas com Pessoal": Decimal("0"),
            "Despesas Administrativas": Decimal("0"),
            "Despesas com Ocupação": Decimal("50"),
            "Despesas com Vendas": Decimal("80"),
            "Outras Despesas": Decimal("90"),
        }

        # O complemento de folha usa as mesmas contas no total e no detalhe.
        _inserir(
            db,
            ContaPagar,
            [
                _conta(
                    40,
                    "Folha de produtos para revenda",
                    "100",
                    subcategoria_id=1,
                    tipo_id=1,
                    categoria_id=11,
                )
            ],
        )
        db.commit()

        def resumo_folha_fake(
            _db, _mes, _ano, _tenant_id, contas, _subcategorias, **_kwargs
        ):
            lancado = sum(
                (
                    conta.valor_original
                    for conta in contas
                    if "folha" in conta.descricao.lower()
                ),
                Decimal("0"),
            )
            complemento = max(Decimal("0"), Decimal("100") - lancado)
            return {
                "ajustes_por_canal": {"loja_fisica": complemento},
                "provisoes": [],
                "complemento_loja_fisica": complemento,
                "quantidade_funcionarios": 1,
                "folha_lancada_por_canal": {"loja_fisica": lancado},
                "provisoes_por_canal": {"loja_fisica": Decimal("0")},
                "estimado": Decimal("100"),
            }

        monkeypatch.setattr(
            agregacao, "calcular_resumo_folha_gerencial", resumo_folha_fake
        )
        monkeypatch.setattr(
            detalhes, "calcular_resumo_folha_gerencial", resumo_folha_fake
        )
        dados_folha = {}
        agregacao.agregar_contas_pagar_por_canal(db, 10, 2026, TENANT_ID, dados_folha)
        detalhe_folha = _detalhes_contas_campo(
            db, 10, 2026, TENANT_ID, "loja_fisica", "despesas_pessoal"
        )
        assert dados_folha["loja_fisica"]["despesas_pessoal"] == Decimal("100")
        assert sum(item.valor for item in detalhe_folha) == 100.0

        # Taxas parceladas: somente as parcelas elegíveis entram no DRE.
        _inserir(
            db,
            DRECategoria,
            [
                DRECategoria(
                    id=7,
                    tenant_id=TENANT_ID,
                    nome="Taxas Financeiras",
                    natureza=NaturezaDRE.DESPESA,
                )
            ],
        )
        _inserir(
            db,
            DRESubcategoria,
            [
                DRESubcategoria(
                    id=8,
                    tenant_id=TENANT_ID,
                    categoria_id=7,
                    nome="Taxas de Cartão",
                    tipo_custo=TipoCusto.DIRETO,
                    escopo_rateio=EscopoRateio.AMBOS,
                )
            ],
        )
        _inserir(
            db,
            ContaPagar,
            [
                _conta(
                    60, "Taxa de cartão", "20", subcategoria_id=8, status="parcelado"
                ),
                _conta(
                    61,
                    "Taxa de cartão 1/2",
                    "10",
                    subcategoria_id=8,
                    conta_principal_id=60,
                ),
                _conta(
                    62,
                    "Taxa de cartão 2/2",
                    "10",
                    subcategoria_id=8,
                    conta_principal_id=60,
                ),
                _conta(
                    63, "Taxa fora da DRE", "50", subcategoria_id=8, afeta_dre=False
                ),
                _conta(
                    64,
                    "Taxa vinculada à NF",
                    "60",
                    subcategoria_id=8,
                    nota_entrada_id=901,
                ),
                _conta(
                    70,
                    "Material de limpeza com fornecedor",
                    "12",
                    subcategoria_id=4,
                    fornecedor_id=999,
                ),
            ],
        )
        _inserir(
            db,
            NotaEntrada,
            [
                NotaEntrada(
                    id=901,
                    tenant_id=TENANT_ID,
                    user_id=1,
                    numero_nota="901",
                    serie="1",
                    chave_acesso="9" * 44,
                    fornecedor_cnpj="00000000000000",
                    fornecedor_nome="Fornecedor teste",
                    data_emissao=datetime(2026, 10, 5),
                    valor_produtos=100,
                    valor_frete=400,
                    valor_total=500,
                    xml_content="<xml/>",
                )
            ],
        )
        db.commit()

        assert calcular_taxas_cartao(db, 10, 2026, TENANT_ID) == Decimal("20")
        assert calcular_frete_notas_entrada(db, 10, 2026, TENANT_ID) == Decimal("400")

        class ConsultaSemVendas:
            def options(self, *_args):
                return self

            def filter(self, *_args):
                return self

            def all(self):
                return []

        consulta_original = db.query
        monkeypatch.setattr(
            db,
            "query",
            lambda modelo: (
                ConsultaSemVendas() if modelo is Venda else consulta_original(modelo)
            ),
        )
        dados_dre = {campo: 0 for campo in DREResponse.model_fields}
        dados_dre.update(
            periodo="Outubro/2026",
            mes=10,
            ano=2026,
            despesas_operacionais=Decimal("252"),
        )
        monkeypatch.setattr(
            dre_base_routes,
            "_dre_para_exportacao",
            lambda **_kwargs: DREResponse(**dados_dre),
        )
        dre_detalhado = dre_base_routes.gerar_dre_detalhado(
            ano=2026, mes=10, db=db, user_and_tenant=(object(), TENANT_ID)
        )
        assert dre_detalhado.dre.despesas_operacionais == Decimal("252")
        assert any(
            item["descricao"] == "Material de limpeza com fornecedor"
            for item in dre_detalhado.detalhes_despesas
        )
        assert (
            sum(
                (
                    Decimal(str(item["valor"]))
                    for item in dre_detalhado.detalhes_despesas
                ),
                Decimal("0"),
            )
            == dre_detalhado.dre.despesas_operacionais
        )
    finally:
        clear_current_tenant()
        db.close()
        engine.dispose()
