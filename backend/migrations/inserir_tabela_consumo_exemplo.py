"""
Inserir tabela de consumo de exemplo no produto Golden Fórmula Filhotes
Baseado em tabelas reais de embalagens de ração
"""
import sqlite3
import json

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Tabela de consumo exemplo (similar à imagem fornecida)
# Formato: peso_adulto e idade do filhote
tabela_consumo = {
    "peso_adulto": {
        "5": 89,
        "10": 150,
        "15": 203,
        "20": 252,
        "25": 298,
        "30": 322,
        "35": 361,
        "40": 400,
        "45": 436
    },
    "filhote_2m": {
        "5": 89,
        "10": 150,
        "15": 203,
        "20": 252,
        "25": 298,
        "30": 322,
        "35": 361,
        "40": 400,
        "45": 436
    },
    "filhote_3m": {
        "5": 112,
        "10": 188,
        "15": 254,
        "20": 316,
        "25": 373,
        "30": 424,
        "35": 476,
        "40": 526,
        "45": 574
    },
    "filhote_4m": {
        "5": 125,
        "10": 211,
        "15": 286,
        "20": 355,
        "25": 420,
        "30": 470,
        "35": 527,
        "40": 583,
        "45": 637
    },
    "filhote_6m": {
        "5": 128,
        "10": 215,
        "15": 291,
        "20": 361,
        "25": 427,
        "30": 495,
        "35": 556,
        "40": 614,
        "45": 671
    },
    "filhote_8m": {
        "5": 129,
        "10": 217,
        "15": 294,
        "20": 365,
        "25": 432,
        "30": 494,
        "35": 555,
        "40": 613,
        "45": 670
    },
    "filhote_10m": {
        "5": 126,
        "10": 213,
        "15": 288,
        "20": 358,
        "25": 423,
        "30": 484,
        "35": 544,
        "40": 601,
        "45": 657
    },
    "filhote_12m": {
        "5": 124,
        "10": 209,
        "15": 283,
        "20": 351,
        "25": 415,
        "30": 489,
        "35": 549,
        "40": 607,
        "45": 663
    }
}

# Atualizar produto ID 72 (Golden Fórmula Filhotes)
cursor.execute(
    "UPDATE produtos SET tabela_consumo = ? WHERE id = 72",
    (json.dumps(tabela_consumo),)
)

conn.commit()
print("✅ Tabela de consumo inserida no produto Golden Fórmula Filhotes (ID 72)")
print(f"\n📊 Tabela inserida:")
print(f"   • Cães adultos: {len(tabela_consumo['peso_adulto'])} faixas de peso (5-45kg)")
print(f"   • Filhotes: 8 faixas etárias (2-12 meses)")
print(f"\n💡 Exemplo: Filhote 4 meses, 15kg adulto = {tabela_consumo['filhote_4m']['15']}g/dia")
print(f"   • Com embalagem 15kg: duração = 15000g / 286g = ~52 dias")

conn.close()
