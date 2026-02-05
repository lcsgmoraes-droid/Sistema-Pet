import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User

# Conectar ao banco
engine = create_engine('sqlite:///petshop.db')
Session = sessionmaker(bind=engine)
session = Session()

# Buscar usuário
user = session.query(User).filter(User.email == 'admin@test.com').first()

if user:
    print("=== ATUALIZANDO SENHA ===")
    print(f"Email: {user.email}")
    print(f"Hash antigo: {user.hashed_password[:60]}...")
    
    # Gerar novo hash correto
    nova_senha = "teste123"
    senha_bytes = nova_senha.encode('utf-8')[:72]
    novo_hash = bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode('utf-8')
    
    # Verificar antes de salvar
    if bcrypt.checkpw(senha_bytes, novo_hash.encode('utf-8')):
        print(f"\n✅ Novo hash validado com sucesso!")
        print(f"Novo hash: {novo_hash[:60]}...")
        
        # Atualizar no banco
        user.hashed_password = novo_hash
        session.commit()
        print("\n✅ Senha atualizada no banco de dados!")
        print(f"Senha correta: {nova_senha}")
    else:
        print("❌ Erro na validação do novo hash")
else:
    print("Usuario nao encontrado")

session.close()
