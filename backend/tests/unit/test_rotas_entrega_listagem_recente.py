from app.api.endpoints.rotas_entrega_core_routes import (
    aplicar_filtros_ordenacao_rotas,
    listar_vendas_pendentes_entrega,
)


def test_entregas_pendentes_sao_listadas_da_mais_recente_para_a_mais_antiga():
    class Consulta:
        ordenacao = ()

        def filter(self, *_filtros):
            return self

        def order_by(self, *campos):
            self.ordenacao = campos
            return self

        def all(self):
            return []

    class Banco:
        consulta = Consulta()

        def query(self, _modelo):
            return self.consulta

    banco = Banco()
    assert listar_vendas_pendentes_entrega(db=banco, user_and_tenant=(None, 1)) == []
    assert "data_venda DESC" in str(banco.consulta.ordenacao[0])
    assert "vendas.id DESC" in str(banco.consulta.ordenacao[1])


def test_rotas_podem_ser_consultadas_por_data_de_criacao_mais_recente():
    class Consulta:
        ordenacao = ()

        def order_by(self, *campos):
            self.ordenacao = campos
            return self

    consulta = Consulta()
    aplicar_filtros_ordenacao_rotas(
        consulta, tenant_id=1, ordenar_por="criacao", direcao="desc"
    )
    assert "rotas_entrega.created_at DESC" in str(consulta.ordenacao[0])
