"""
Seed rápido para Opções de Ração - Versão Standalone
"""

from datetime import datetime

from legacy_script_env import connect_database


def seed_opcoes_racao(tenant_id=1):
    """Popula opções de ração para um tenant"""
    conn = connect_database("RACAO_DATABASE_URL", "DATABASE_URL")
    cur = conn.cursor()

    try:
        agora = datetime.now()

        # Linhas de Ração
        linhas = [
            (
                tenant_id,
                "Super Premium",
                "Linha superior com ingredientes premium",
                1,
                True,
                agora,
            ),
            (
                tenant_id,
                "Premium Special",
                "Linha especial intermediária",
                2,
                True,
                agora,
            ),
            (tenant_id, "Premium", "Linha premium padrão", 3, True, agora),
            (tenant_id, "Standard", "Linha tradicional", 4, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM linhas_racao WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO linhas_racao (tenant_id, nome, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                linhas,
            )
            print(f"✅ Inseridas {len(linhas)} Linhas de Ração")
        else:
            print("⏭️ Linhas de Ração já existem")

        # Portes de Animal
        portes = [
            (tenant_id, "Pequeno", "Até 10kg", 1, True, agora),
            (tenant_id, "Médio", "De 10kg a 25kg", 2, True, agora),
            (tenant_id, "Médio e Grande", "De 10kg a 45kg", 3, True, agora),
            (tenant_id, "Grande", "De 25kg a 45kg", 4, True, agora),
            (tenant_id, "Gigante", "Acima de 45kg", 5, True, agora),
            (tenant_id, "Todos", "Todas as raças", 6, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM portes_animal WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO portes_animal (tenant_id, nome, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                portes,
            )
            print(f"✅ Inseridos {len(portes)} Portes de Animal")
        else:
            print("⏭️ Portes de Animal já existem")

        # Fases/Público
        fases = [
            (tenant_id, "Filhote", "Até 12 meses", 1, True, agora),
            (tenant_id, "Adulto", "De 1 a 7 anos", 2, True, agora),
            (tenant_id, "Senior", "Acima de 7 anos", 3, True, agora),
            (tenant_id, "Gestante", "Fêmeas gestantes ou lactantes", 4, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM fases_publico WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO fases_publico (tenant_id, nome, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                fases,
            )
            print(f"✅ Inseridas {len(fases)} Fases/Público")
        else:
            print("⏭️ Fases/Público já existem")

        # Tipos de Tratamento
        tratamentos = [
            (tenant_id, "Obesidade", "Para controle de peso", 1, True, agora),
            (tenant_id, "Light", "Redução calórica", 2, True, agora),
            (tenant_id, "Hipoalergênico", "Para animais com alergias", 3, True, agora),
            (tenant_id, "Sensível", "Para estômagos sensíveis", 4, True, agora),
            (tenant_id, "Digestivo", "Facilita digestão", 5, True, agora),
            (tenant_id, "Urinário", "Saúde do trato urinário", 6, True, agora),
            (tenant_id, "Renal", "Para problemas renais", 7, True, agora),
            (tenant_id, "Articular", "Saúde das articulações", 8, True, agora),
            (tenant_id, "Dermatológico", "Para problemas de pele", 9, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM tipos_tratamento WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO tipos_tratamento (tenant_id, nome, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                tratamentos,
            )
            print(f"✅ Inseridos {len(tratamentos)} Tipos de Tratamento")
        else:
            print("⏭️ Tipos de Tratamento já existem")

        # Sabores/Proteínas
        sabores = [
            (tenant_id, "Frango", "Proteína de frango", 1, True, agora),
            (tenant_id, "Carne", "Proteína bovina", 2, True, agora),
            (tenant_id, "Peixe", "Proteína de peixe", 3, True, agora),
            (tenant_id, "Salmão", "Proteína de salmão", 4, True, agora),
            (tenant_id, "Cordeiro", "Proteína de cordeiro", 5, True, agora),
            (tenant_id, "Peru", "Proteína de peru", 6, True, agora),
            (tenant_id, "Porco", "Proteína suína", 7, True, agora),
            (tenant_id, "Vegetariano", "Sem proteína animal", 8, True, agora),
            (tenant_id, "Soja", "Proteína de soja", 9, True, agora),
            (tenant_id, "Mix", "Mistura de proteínas", 10, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM sabores_proteina WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO sabores_proteina (tenant_id, nome, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                sabores,
            )
            print(f"✅ Inseridos {len(sabores)} Sabores/Proteínas")
        else:
            print("⏭️ Sabores/Proteínas já existem")

        # Apresentações (Peso)
        apresentacoes = [
            (tenant_id, 0.5, "500g", 1, True, agora),
            (tenant_id, 1.0, "1kg", 2, True, agora),
            (tenant_id, 2.0, "2kg", 3, True, agora),
            (tenant_id, 3.0, "3kg", 4, True, agora),
            (tenant_id, 5.0, "5kg", 5, True, agora),
            (tenant_id, 7.0, "7kg", 6, True, agora),
            (tenant_id, 10.0, "10kg", 7, True, agora),
            (tenant_id, 10.1, "10.1kg", 8, True, agora),
            (tenant_id, 15.0, "15kg", 9, True, agora),
            (tenant_id, 20.0, "20kg", 10, True, agora),
            (tenant_id, 25.0, "25kg", 11, True, agora),
        ]

        cur.execute(
            "SELECT COUNT(*) FROM apresentacoes_peso WHERE tenant_id = %s", (tenant_id,)
        )
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO apresentacoes_peso (tenant_id, peso_kg, descricao, ordem, ativo, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                apresentacoes,
            )
            print(f"✅ Inseridas {len(apresentacoes)} Apresentações de Peso")
        else:
            print("⏭️ Apresentações de Peso já existem")

        conn.commit()
        print(f"\n🎉 Seed concluído com sucesso para tenant {tenant_id}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao executar seed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import sys

    tenant_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"🌱 Executando seed para tenant_id={tenant_id}...")
    seed_opcoes_racao(tenant_id)
