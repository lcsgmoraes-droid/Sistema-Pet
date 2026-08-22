from __future__ import annotations

import json
from pathlib import Path

from app.services.tenant_onboarding_template_contracts import template_item


CATALOG_TEMPLATE_ITEMS = [
    template_item(
        "bank_account",
        "bank_cash_register",
        "Caixa",
        {
            "nome": "Caixa",
            "tipo": "caixa_fisico",
            "banco": None,
            "agencia": None,
            "conta": None,
            "saldo_inicial": 0,
            "saldo_atual": 0,
            "cor": "#22C55E",
            "icone": "banknote",
            "instituicao_bancaria": False,
            "ativa": True,
            "observacoes": "Conta padrao para recebimentos em dinheiro.",
        },
        45,
    ),
    template_item(
        "bank_account",
        "bank_main_account",
        "Conta Bancaria Principal",
        {
            "nome": "Conta Bancaria Principal",
            "tipo": "corrente",
            "banco": None,
            "agencia": None,
            "conta": None,
            "saldo_inicial": 0,
            "saldo_atual": 0,
            "cor": "#2563EB",
            "icone": "landmark",
            "instituicao_bancaria": True,
            "ativa": True,
            "observacoes": "Conta bancaria inicial para configurar depois.",
        },
        46,
    ),
    template_item(
        "pet_species",
        "species_dog",
        "Cao",
        {"nome": "Cao", "ativo": True},
        50,
    ),
    template_item(
        "pet_species",
        "species_cat",
        "Gato",
        {"nome": "Gato", "ativo": True},
        51,
    ),
    template_item(
        "pet_breed",
        "breed_dog_srd",
        "SRD - Cao",
        {
            "nome": "SRD",
            "species_code": "species_dog",
            "especie": "Cao",
            "ativo": True,
        },
        60,
    ),
    template_item(
        "pet_breed",
        "breed_cat_srd",
        "SRD - Gato",
        {
            "nome": "SRD",
            "species_code": "species_cat",
            "especie": "Gato",
            "ativo": True,
        },
        61,
    ),
]

for index, name in enumerate(
    ("Super Premium", "Premium Special", "Premium", "Standard"),
    start=1,
):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "ration_line",
            f"ration_line_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            600 + index,
        )
    )

for index, name in enumerate(
    ("Pequeno", "Medio", "Medio e Grande", "Grande", "Gigante", "Todos"),
    start=1,
):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "animal_size",
            f"animal_size_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            620 + index,
        )
    )

for index, name in enumerate(("Filhote", "Adulto", "Senior", "Gestante"), start=1):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "life_stage",
            f"life_stage_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            640 + index,
        )
    )

for index, name in enumerate(
    (
        "Obesidade",
        "Light",
        "Hipoalergenico",
        "Sensivel",
        "Digestivo",
        "Urinario",
        "Renal",
        "Articular",
        "Dermatologico",
    ),
    start=1,
):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "treatment_type",
            f"treatment_type_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            660 + index,
        )
    )

for index, name in enumerate(
    (
        "Frango",
        "Carne",
        "Peixe",
        "Salmao",
        "Cordeiro",
        "Peru",
        "Porco",
        "Vegetariano",
        "Soja",
        "Mix",
    ),
    start=1,
):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "protein_flavor",
            f"protein_flavor_{index}",
            name,
            {"nome": name, "descricao": None, "ordem": index, "ativo": True},
            680 + index,
        )
    )

for index, weight in enumerate((0.5, 1, 2, 3, 5, 7, 10, 10.1, 15, 20, 25), start=1):
    label = f"{weight:g}kg"
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "package_weight",
            f"package_weight_{index}",
            label,
            {"peso_kg": weight, "descricao": label, "ordem": index, "ativo": True},
            700 + index,
        )
    )


_VET_PROCEDURES_PATH = (
    Path(__file__).resolve().parents[1] / "catalogos" / "vet_procedimentos_v1.json"
)
with _VET_PROCEDURES_PATH.open("r", encoding="utf-8") as _vet_procedures_file:
    _VET_PROCEDURES = json.load(_vet_procedures_file)

for index, procedure in enumerate(_VET_PROCEDURES, start=1):
    CATALOG_TEMPLATE_ITEMS.append(
        template_item(
            "vet_procedure",
            procedure["code"],
            procedure["name"],
            {
                "nome": procedure["name"],
                "descricao": procedure.get("descricao"),
                "categoria": procedure.get("categoria"),
                "duracao_minutos": procedure.get("duracao_minutos"),
                "requer_anestesia": bool(procedure.get("requer_anestesia", False)),
            },
            1000 + index,
        )
    )
