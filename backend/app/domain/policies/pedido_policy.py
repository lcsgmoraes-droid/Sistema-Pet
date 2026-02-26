class PedidoPolicy:
    """
    Regras invariantes do aggregate Pedido.
    PURE DOMAIN (sem HTTP).
    """

    @staticmethod
    def validar_quantidade(qtd):
        if qtd <= 0:
            raise ValueError('Quantidade deve ser > 0')

    @staticmethod
    def validar_preco(preco):
        if preco < 0:
            raise ValueError('Preço inválido')

    @staticmethod
    def validar_nome(nome):
        if not nome or len(nome.strip()) == 0:
            raise ValueError('Nome obrigatório')