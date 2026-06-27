"""Regras de estoque baseadas no tipo comercial do produto."""

TIPOS_COMERCIAIS_PRODUTO = {"produto", "servico", "produto_servico"}
ALIASES_TIPO_COMERCIAL = {
    "ambos": "produto_servico",
    "servi\u00e7o": "servico",
}


def normalizar_tipo_comercial_produto(tipo) -> str:
    valor = str(tipo or "produto").strip().lower()
    valor = ALIASES_TIPO_COMERCIAL.get(valor, valor)
    if valor not in TIPOS_COMERCIAIS_PRODUTO:
        return "produto"
    return valor


def produto_eh_servico(produto) -> bool:
    return normalizar_tipo_comercial_produto(getattr(produto, "tipo", produto)) == "servico"


def mensagem_servico_sem_estoque(produto) -> str:
    nome = getattr(produto, "nome", "Servico")
    return (
        f"Servico '{nome}' nao controla estoque. "
        "Cadastre os insumos consumidos como produtos e movimente o estoque dos insumos."
    )


def validar_produto_permite_estoque(produto) -> None:
    if produto_eh_servico(produto):
        raise ValueError(mensagem_servico_sem_estoque(produto))


def aplicar_regras_servico_sem_estoque(dados: dict) -> str:
    tipo = normalizar_tipo_comercial_produto(dados.get("tipo"))
    dados["tipo"] = tipo
    if tipo == "servico":
        dados["tipo_produto"] = "SIMPLES"
        dados["tipo_kit"] = None
        dados["controle_lote"] = False
        dados["estoque_minimo"] = 0
        dados["estoque_maximo"] = None
        dados["participa_sugestao_compra"] = False
    return tipo
