"""
Popular tabela de raças com raças comuns

⚠️ LEGADO - NÃO USAR
Este arquivo usa SQLite. O sistema atual usa PostgreSQL.
Use SessionLocal() do app.db para acessar o banco.
"""
import sqlite3

print("⚠️ Script LEGADO bloqueado! Use PostgreSQL via SessionLocal()")
raise SystemExit("Este script usa SQLite legado")

DB_PATH = "./petshop.db"

# Raças comuns por espécie
RACAS = {
    "Cão": [
        "SRD (Sem Raça Definida)",
        "Labrador Retriever",
        "Golden Retriever",
        "Pastor Alemão",
        "Bulldog Francês",
        "Bulldog Inglês",
        "Poodle",
        "Beagle",
        "Rottweiler",
        "Yorkshire Terrier",
        "Boxer",
        "Dachshund (Salsicha)",
        "Shih Tzu",
        "Husky Siberiano",
        "Pit Bull",
        "Chihuahua",
        "Pug",
        "Lhasa Apso",
        "Maltês",
        "Border Collie",
        "Schnauzer",
        "Doberman",
        "Akita",
        "Basset Hound",
        "Cocker Spaniel",
        "Dálmata",
        "São Bernardo",
        "Bull Terrier",
        "Staffordshire Bull Terrier",
        "Weimaraner"
    ],
    "Gato": [
        "SRD (Sem Raça Definida)",
        "Siamês",
        "Persa",
        "Maine Coon",
        "Bengal",
        "Ragdoll",
        "British Shorthair",
        "Sphynx",
        "Angorá",
        "Himalaio",
        "Abissínio",
        "Scottish Fold",
        "Exótico",
        "Birmanês",
        "Munchkin",
        "Somali",
        "Cornish Rex"
    ],
    "Ave": [
        "Calopsita",
        "Periquito Australiano",
        "Papagaio",
        "Canário",
        "Agapornis",
        "Cacatua",
        "Arara",
        "Piriquito",
        "Manon",
        "Diamante de Gould"
    ],
    "Roedor": [
        "Hamster Sírio",
        "Hamster Anão Russo",
        "Porquinho da Índia",
        "Chinchila",
        "Gerbil",
        "Rato Twister",
        "Camundongo"
    ],
    "Réptil": [
        "Iguana Verde",
        "Pogona",
        "Cobra do Milho",
        "Jabuti Piranga",
        "Tigre d'Água",
        "Gecko Leopardo",
        "Teiú"
    ]
}

def populate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        total = 0
        for especie, racas in RACAS.items():
            for raca in racas:
                # Verificar se já existe
                cursor.execute(
                    "SELECT id FROM racas WHERE nome = ? AND especie = ?",
                    (raca, especie)
                )
                if cursor.fetchone():
                    print(f"  ⏭️  {especie} - {raca} (já existe)")
                    continue
                
                # Inserir
                cursor.execute(
                    "INSERT INTO racas (nome, especie, ativo) VALUES (?, ?, 1)",
                    (raca, especie)
                )
                print(f"  ✅ {especie} - {raca}")
                total += 1
        
        conn.commit()
        print(f"\n🎉 {total} raças cadastradas com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("🐾 Populando tabela de raças...\n")
    populate()
