# -*- coding: utf-8 -*-
"""
Seed de dados padrão para Opções de Ração
Popula tabelas com valores iniciais para novos tenants
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.opcoes_racao_models import (
    LinhaRacao,
    PorteAnimal,
    FasePublico,
    TipoTratamento,
    SaborProteina,
    ApresentacaoPeso,
)

# Dados padrão para seed
DADOS_PADRAO = {
    "linhas_racao": [
        {
            "nome": "Super Premium",
            "descricao": "Linha superior com ingredientes premium",
            "ordem": 1,
        },
        {
            "nome": "Premium Special",
            "descricao": "Linha especial intermediária",
            "ordem": 2,
        },
        {"nome": "Premium", "descricao": "Linha premium padrão", "ordem": 3},
        {"nome": "Standard", "descricao": "Linha tradicional", "ordem": 4},
    ],
    "portes_animal": [
        {"nome": "Pequeno", "descricao": "Até 10kg", "ordem": 1},
        {"nome": "Médio", "descricao": "De 10kg a 25kg", "ordem": 2},
        {"nome": "Médio e Grande", "descricao": "De 10kg a 45kg", "ordem": 3},
        {"nome": "Grande", "descricao": "De 25kg a 45kg", "ordem": 4},
        {"nome": "Gigante", "descricao": "Acima de 45kg", "ordem": 5},
        {"nome": "Todos", "descricao": "Todas as raças", "ordem": 6},
    ],
    "fases_publico": [
        {"nome": "Filhote", "descricao": "Até 12 meses", "ordem": 1},
        {"nome": "Adulto", "descricao": "De 1 a 7 anos", "ordem": 2},
        {"nome": "Senior", "descricao": "Acima de 7 anos", "ordem": 3},
        {"nome": "Gestante", "descricao": "Fêmeas gestantes ou lactantes", "ordem": 4},
    ],
    "tipos_tratamento": [
        {"nome": "Obesidade", "descricao": "Para controle de peso", "ordem": 1},
        {"nome": "Light", "descricao": "Redução calórica", "ordem": 2},
        {
            "nome": "Hipoalergênico",
            "descricao": "Para animais com alergias",
            "ordem": 3,
        },
        {"nome": "Sensível", "descricao": "Para estômagos sensíveis", "ordem": 4},
        {"nome": "Digestivo", "descricao": "Facilita digestão", "ordem": 5},
        {"nome": "Urinário", "descricao": "Saúde do trato urinário", "ordem": 6},
        {"nome": "Renal", "descricao": "Para problemas renais", "ordem": 7},
        {"nome": "Articular", "descricao": "Saúde das articulações", "ordem": 8},
        {"nome": "Dermatológico", "descricao": "Para problemas de pele", "ordem": 9},
    ],
    "sabores_proteina": [
        {"nome": "Frango", "descricao": "Proteína de frango", "ordem": 1},
        {"nome": "Carne", "descricao": "Proteína de carne bovina", "ordem": 2},
        {"nome": "Peixe", "descricao": "Proteína de peixe", "ordem": 3},
        {"nome": "Salmão", "descricao": "Proteína de salmão", "ordem": 4},
        {"nome": "Cordeiro", "descricao": "Proteína de cordeiro", "ordem": 5},
        {"nome": "Peru", "descricao": "Proteína de peru", "ordem": 6},
        {"nome": "Porco", "descricao": "Proteína de porco", "ordem": 7},
        {"nome": "Vegetariano", "descricao": "Sem proteína animal", "ordem": 8},
        {"nome": "Soja", "descricao": "Proteína de soja", "ordem": 9},
        {"nome": "Mix", "descricao": "Mix de proteínas", "ordem": 10},
    ],
    "apresentacoes_peso": [
        {"peso_kg": 0.5, "descricao": "500g", "ordem": 1},
        {"peso_kg": 1.0, "descricao": "1kg", "ordem": 2},
        {"peso_kg": 2.0, "descricao": "2kg", "ordem": 3},
        {"peso_kg": 3.0, "descricao": "3kg", "ordem": 4},
        {"peso_kg": 5.0, "descricao": "5kg", "ordem": 5},
        {"peso_kg": 7.0, "descricao": "7kg", "ordem": 6},
        {"peso_kg": 10.0, "descricao": "10kg", "ordem": 7},
        {"peso_kg": 10.1, "descricao": "10.1kg", "ordem": 8},
        {"peso_kg": 15.0, "descricao": "15kg", "ordem": 9},
        {"peso_kg": 20.0, "descricao": "20kg", "ordem": 10},
        {"peso_kg": 25.0, "descricao": "25kg", "ordem": 11},
    ],
}


def seed_opcoes_racao_para_tenant(db: Session, tenant_id: str):
    """
    Popula opções de ração para um tenant específico

    Args:
        db: Sessão do banco
        tenant_id: UUID do tenant
    """
    print(f"\n🌱 Iniciando seed de opções de ração para tenant {tenant_id}...")

    # Linhas de Ração
    print("  📦 Criando Linhas de Ração...")
    for item in DADOS_PADRAO["linhas_racao"]:
        existe = (
            db.query(LinhaRacao)
            .filter(LinhaRacao.tenant_id == tenant_id, LinhaRacao.nome == item["nome"])
            .first()
        )

        if not existe:
            linha = LinhaRacao(tenant_id=tenant_id, **item)
            db.add(linha)
            print(f"    ✅ {item['nome']}")
        else:
            print(f"    ⏭️  {item['nome']} (já existe)")

    # Portes de Animal
    print("  🐕 Criando Portes de Animal...")
    for item in DADOS_PADRAO["portes_animal"]:
        existe = (
            db.query(PorteAnimal)
            .filter(
                PorteAnimal.tenant_id == tenant_id, PorteAnimal.nome == item["nome"]
            )
            .first()
        )

        if not existe:
            porte = PorteAnimal(tenant_id=tenant_id, **item)
            db.add(porte)
            print(f"    ✅ {item['nome']}")
        else:
            print(f"    ⏭️  {item['nome']} (já existe)")

    # Fases/Público
    print("  👶 Criando Fases/Público...")
    for item in DADOS_PADRAO["fases_publico"]:
        existe = (
            db.query(FasePublico)
            .filter(
                FasePublico.tenant_id == tenant_id, FasePublico.nome == item["nome"]
            )
            .first()
        )

        if not existe:
            fase = FasePublico(tenant_id=tenant_id, **item)
            db.add(fase)
            print(f"    ✅ {item['nome']}")
        else:
            print(f"    ⏭️  {item['nome']} (já existe)")

    # Tipos de Tratamento
    print("  💊 Criando Tipos de Tratamento...")
    for item in DADOS_PADRAO["tipos_tratamento"]:
        existe = (
            db.query(TipoTratamento)
            .filter(
                TipoTratamento.tenant_id == tenant_id,
                TipoTratamento.nome == item["nome"],
            )
            .first()
        )

        if not existe:
            tratamento = TipoTratamento(tenant_id=tenant_id, **item)
            db.add(tratamento)
            print(f"    ✅ {item['nome']}")
        else:
            print(f"    ⏭️  {item['nome']} (já existe)")

    # Sabores/Proteínas
    print("  🍖 Criando Sabores/Proteínas...")
    for item in DADOS_PADRAO["sabores_proteina"]:
        existe = (
            db.query(SaborProteina)
            .filter(
                SaborProteina.tenant_id == tenant_id, SaborProteina.nome == item["nome"]
            )
            .first()
        )

        if not existe:
            sabor = SaborProteina(tenant_id=tenant_id, **item)
            db.add(sabor)
            print(f"    ✅ {item['nome']}")
        else:
            print(f"    ⏭️  {item['nome']} (já existe)")

    # Apresentações de Peso
    print("  ⚖️  Criando Apresentações de Peso...")
    for item in DADOS_PADRAO["apresentacoes_peso"]:
        existe = (
            db.query(ApresentacaoPeso)
            .filter(
                ApresentacaoPeso.tenant_id == tenant_id,
                ApresentacaoPeso.peso_kg == item["peso_kg"],
            )
            .first()
        )

        if not existe:
            apresentacao = ApresentacaoPeso(tenant_id=tenant_id, **item)
            db.add(apresentacao)
            print(f"    ✅ {item['descricao']}")
        else:
            print(f"    ⏭️  {item['descricao']} (já existe)")

    db.commit()
    print(f"✅ Seed concluído para tenant {tenant_id}!\n")


def seed_todos_tenants():
    """Popula opções de ração para todos os tenants existentes"""
    db = SessionLocal()

    try:
        # Buscar todos os tenants
        from app.models import Tenant

        tenants = db.query(Tenant).all()

        if not tenants:
            print("⚠️  Nenhum tenant encontrado!")
            return

        print(f"🌱 Encontrados {len(tenants)} tenant(s)")

        for tenant in tenants:
            seed_opcoes_racao_para_tenant(db, tenant.id)

        print("✅ Seed concluído para todos os tenants!")

    except Exception as e:
        print(f"❌ Erro ao executar seed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Seed para tenant específico
        tenant_id = sys.argv[1]
        db = SessionLocal()
        try:
            seed_opcoes_racao_para_tenant(db, tenant_id)
        finally:
            db.close()
    else:
        # Seed para todos os tenants
        seed_todos_tenants()
