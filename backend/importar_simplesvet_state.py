"""Estado compartilhado do importador SimplesVet."""

# Mapeamento de IDs antigos -> novos para preservar relacionamentos.
ID_MAP = {
    "pessoas": {},
    "animais": {},
    "produtos": {},
    "vendas": {},
    "especies": {},
    "racas": {},
    "marcas": {},
}

STATS = {
    "especies": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "racas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "clientes": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "marcas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "produtos": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0, "sem_sku": 0},
    "pets": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "vendas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "itens_venda": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
}

NAO_IMPORTADOS = {
    "produtos": [],
    "clientes": [],
    "pets": [],
    "vendas": [],
}

USER_ID = 1
TENANT_ID = None
