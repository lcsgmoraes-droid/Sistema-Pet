from __future__ import annotations

import os
from typing import Dict, Optional


class BlingCatalogoMixin:
    """Operacoes de catalogo, estoque e pedidos do cliente Bling."""

    def listar_produtos(
        self,
        codigo: str = None,
        nome: str = None,
        sku: str = None,
        pagina: int = 1,
        limite: int = 100,
    ) -> Dict:
        """
        Lista produtos do Bling com filtros

        Args:
            codigo: Filtrar por código do produto
            nome: Filtrar por nome (busca parcial)
            sku: Filtrar por SKU
            pagina: Número da página (começa em 1)
            limite: Itens por página (máx 100)
        """
        params = {"pagina": pagina, "limite": min(limite, 100)}

        if codigo:
            params["codigo"] = codigo
        if nome:
            params["nome"] = nome
        if sku:
            params["sku"] = sku

        return self._request("GET", "/produtos", data=params)

    def consultar_produto(self, produto_id: str) -> Dict:
        """
        Consulta dados completos de um produto do Bling

        Args:
            produto_id: ID do produto no Bling
        """
        resultado = self._request("GET", f"/produtos/{produto_id}")
        return resultado.get("data", resultado)

    def criar_produto(self, payload: Dict) -> Dict:
        """Cria um produto no Bling API v3."""
        return self._request("POST", "/produtos", data=payload)

    def atualizar_estoque_produto(
        self,
        produto_id: str,
        estoque_novo: float,
        deposito_id: Optional[int] = None,
        observacao: str = "",
    ) -> Dict:
        """
        Atualiza estoque de um produto no Bling via POST /estoques (Balanço absoluto).

        Usa operação "B" (Balanço) para definir o saldo físico exato do produto.
        Endpoint correto para Bling API v3.

        Args:
            produto_id: ID do produto no Bling
            estoque_novo: Novo saldo físico de estoque (valor absoluto)
            deposito_id: ID do depósito (opcional, usa BLING_DEPOSITO_ID do .env se não informado)
            observacao: Observação para o lançamento
        """
        # Deposito: parâmetro > variável de ambiente > sem especificar (Bling usa o padrão)
        _deposito_id = deposito_id or os.getenv("BLING_DEPOSITO_ID")

        payload: Dict = {
            "produto": {"id": int(produto_id)},
            "operacao": "B",  # B = Balanço: define saldo absoluto
            "quantidade": float(estoque_novo),
            "observacoes": observacao or "Sync automatico - CorePet",
        }

        if _deposito_id:
            payload["deposito"] = {"id": int(_deposito_id)}

        return self._request("POST", "/estoques", data=payload)

    def consultar_saldo_estoque(
        self, produto_id: str, deposito_id: Optional[int] = None
    ) -> Dict:
        """
        Consulta o saldo de estoque de um produto no Bling.

        Retorna saldoFisicoTotal (estoque físico real) e saldoVirtualTotal
        (descontando reservas de pedidos online).

        Args:
            produto_id: ID do produto no Bling
            deposito_id: ID do depósito específico (opcional)

        Returns:
            dict com saldoFisicoTotal, saldoVirtualTotal e lista de depositos
        """
        _deposito_id = deposito_id or os.getenv("BLING_DEPOSITO_ID")

        params: Dict = {"idsProdutos[]": produto_id}

        if _deposito_id:
            endpoint = f"/estoques/saldos/{_deposito_id}"
        else:
            endpoint = "/estoques/saldos"

        resultado = self._request("GET", endpoint, data=params)
        itens = resultado.get("data", [])
        if itens:
            return itens[0]  # Retorna o primeiro (filtrado por produto_id)
        return {}

    def consultar_pedido(self, pedido_id: str) -> Dict:
        """
        Busca pedido de VENDA completo pelo ID (incluindo itens).
        Necessário porque o webhook order.created não inclui os itens.
        Endpoint correto: /pedidos/vendas/{id}  (não /pedidos/{id} que é compras)
        """
        resultado = self._request("GET", f"/pedidos/vendas/{pedido_id}")
        return resultado.get("data", resultado)

    def listar_naturezas_operacoes(self) -> Dict:
        """
        Lista todas as naturezas de operação cadastradas no Bling
        Use para descobrir o ID correto da natureza "Venda presencial" ou "Venda de mercadoria"

        Returns:
            Dict com lista de naturezas: [{"id": 1, "descricao": "Venda de mercadoria", ...}]
        """
        return self._request("GET", "/naturezas-operacoes")
