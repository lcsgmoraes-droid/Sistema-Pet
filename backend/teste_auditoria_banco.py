"""
Teste 3 - Auditoria no Banco de Dados
Verifica se distancia_prevista está sendo salva corretamente na tabela rotas_entrega.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🔍 TESTE 3 - AUDITORIA NO BANCO DE DADOS")
print("=" * 70)
print()

# ============================================================================
# 1. CONECTAR NO BANCO
# ============================================================================
print("📋 PASSO 1: Conectar no banco de dados")
print("-" * 70)

try:
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ ERRO: DATABASE_URL não encontrada no .env")
        exit(1)
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Testar conexão
    db.execute(text("SELECT 1"))
    
    print(f"✅ Conectado: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
    print()
    
except Exception as e:
    print(f"❌ Erro ao conectar: {str(e)}")
    exit(1)

# ============================================================================
# 2. VERIFICAR ESTRUTURA DA TABELA
# ============================================================================
print("📋 PASSO 2: Verificar estrutura da tabela rotas_entrega")
print("-" * 70)

try:
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'rotas_entrega'
        AND column_name IN ('id', 'venda_id', 'distancia_prevista', 'distancia_real', 'created_at')
        ORDER BY ordinal_position
    """)
    
    columns = db.execute(query).fetchall()
    
    if columns:
        print("✅ Colunas encontradas:")
        for col in columns:
            print(f"   • {col.column_name}: {col.data_type} ({'NULL' if col.is_nullable == 'YES' else 'NOT NULL'})")
        print()
        
        # Verificar se distancia_prevista existe
        has_distancia_prevista = any(col.column_name == 'distancia_prevista' for col in columns)
        has_distancia_real = any(col.column_name == 'distancia_real' for col in columns)
        
        if has_distancia_prevista:
            print("   ✅ distancia_prevista → OK")
        else:
            print("   ❌ distancia_prevista → AUSENTE")
            
        if has_distancia_real:
            print("   ✅ distancia_real → OK")
        else:
            print("   ⚠️  distancia_real → AUSENTE (será usado na Etapa 9.5)")
        print()
    else:
        print("❌ Tabela rotas_entrega não encontrada")
        exit(1)
        
except Exception as e:
    print(f"❌ Erro ao verificar estrutura: {str(e)}")
    exit(1)

# ============================================================================
# 3. CONTAR ROTAS EXISTENTES
# ============================================================================
print("📋 PASSO 3: Verificar rotas existentes")
print("-" * 70)

try:
    # Total de rotas
    query = text("SELECT COUNT(*) FROM rotas_entrega")
    total = db.execute(query).scalar()
    
    print(f"Total de rotas: {total}")
    
    # Rotas com distancia_prevista preenchida
    query = text("SELECT COUNT(*) FROM rotas_entrega WHERE distancia_prevista IS NOT NULL")
    com_distancia = db.execute(query).scalar()
    
    print(f"Com distância prevista: {com_distancia}")
    
    # Rotas sem distancia_prevista
    sem_distancia = total - com_distancia
    print(f"Sem distância prevista: {sem_distancia}")
    
    if total > 0:
        percentual = (com_distancia / total) * 100
        print(f"Percentual preenchido: {percentual:.1f}%")
    
    print()
    
except Exception as e:
    print(f"❌ Erro ao contar: {str(e)}")
    exit(1)

# ============================================================================
# 4. ANALISAR ÚLTIMAS 5 ROTAS
# ============================================================================
print("📋 PASSO 4: Analisar últimas 5 rotas criadas")
print("-" * 70)

try:
    query = text("""
        SELECT 
            id,
            venda_id,
            distancia_prevista,
            distancia_real,
            status,
            created_at
        FROM rotas_entrega
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    rotas = db.execute(query).fetchall()
    
    if rotas:
        print("Últimas rotas:")
        print()
        for rota in rotas:
            print(f"   ID: {rota.id} | Venda: {rota.venda_id} | Status: {rota.status}")
            print(f"   ├─ Distância prevista: {rota.distancia_prevista} km" if rota.distancia_prevista else "   ├─ Distância prevista: (não informada)")
            print(f"   ├─ Distância real: {rota.distancia_real} km" if rota.distancia_real else "   ├─ Distância real: (não registrada)")
            print(f"   └─ Criada em: {rota.created_at}")
            print()
    else:
        print("⚠️  Nenhuma rota encontrada no banco")
        print()
        
except Exception as e:
    print(f"❌ Erro ao buscar rotas: {str(e)}")
    exit(1)

# ============================================================================
# 5. ESTATÍSTICAS DE DISTÂNCIA
# ============================================================================
print("📋 PASSO 5: Estatísticas de distância")
print("-" * 70)

try:
    query = text("""
        SELECT 
            MIN(distancia_prevista) as minima,
            MAX(distancia_prevista) as maxima,
            AVG(distancia_prevista) as media,
            COUNT(CASE WHEN distancia_prevista > 0 THEN 1 END) as rotas_validas
        FROM rotas_entrega
        WHERE distancia_prevista IS NOT NULL
    """)
    
    stats = db.execute(query).fetchone()
    
    if stats and stats.rotas_validas > 0:
        print(f"Estatísticas (rotas com distância):")
        print(f"   • Menor distância: {stats.minima:.3f} km")
        print(f"   • Maior distância: {stats.maxima:.3f} km")
        print(f"   • Média: {stats.media:.3f} km")
        print(f"   • Total válidas: {stats.rotas_validas}")
    else:
        print("⚠️  Nenhuma rota com distância prevista registrada ainda")
    
    print()
    
except Exception as e:
    print(f"❌ Erro ao calcular estatísticas: {str(e)}")
    exit(1)

# ============================================================================
# 6. VERIFICAR CONFIGURAÇÃO DE ENTREGA
# ============================================================================
print("📋 PASSO 6: Verificar configuração de entrega (ponto inicial)")
print("-" * 70)

try:
    query = text("""
        SELECT 
            id,
            tenant_id as empresa_id,
            ponto_inicial_rota,
            entregador_padrao_id
        FROM configuracoes_entrega
        LIMIT 5
    """)
    
    configs = db.execute(query).fetchall()
    
    if configs:
        print("Configurações encontradas:")
        for config in configs:
            print(f"   • Tenant {config.empresa_id}:")
            if config.ponto_inicial_rota:
                print(f"     ├─ Ponto inicial: {config.ponto_inicial_rota[:60]}...")
                print(f"     └─ Entregador padrão: {config.entregador_padrao_id if config.entregador_padrao_id else '(não configurado)'}")
            else:
                print(f"     └─ ⚠️  Sem ponto inicial configurado")
        print()
    else:
        print("⚠️  Nenhuma configuração de entrega encontrada")
        print("   Recomendação: Cadastrar ponto inicial para cálculo automático")
        print()
        
except Exception as e:
    print(f"⚠️  Tabela configuracoes_entrega pode não ter dados: {str(e)[:80]}")
    print()

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("=" * 70)
print("✅ AUDITORIA CONCLUÍDA")
print("=" * 70)
print()

# Validações
validacoes = []

if has_distancia_prevista:
    validacoes.append("✅ Campo distancia_prevista existe na tabela")
else:
    validacoes.append("❌ Campo distancia_prevista NÃO existe")

if total > 0:
    validacoes.append(f"✅ {total} rotas encontradas no banco")
    if com_distancia > 0:
        validacoes.append(f"✅ {com_distancia} rotas com distância prevista")
    else:
        validacoes.append("⚠️  Nenhuma rota com distância prevista ainda")
else:
    validacoes.append("⚠️  Banco sem rotas (aguardando primeiro teste)")

print("📊 RESUMO:")
for v in validacoes:
    print(f"   {v}")

print()
print("🔍 PRÓXIMOS PASSOS PARA VALIDAR:")
print()
print("   1. Criar uma nova rota via API")
print("   2. Verificar se distancia_prevista foi calculada")
print("   3. Conferir logs do backend:")
print("      [INFO] Calculando distância...")
print("      [SUCESSO] Distância calculada: X.XXX km")
print()
print("=" * 70)

db.close()
