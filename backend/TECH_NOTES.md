# Notas Técnicas - Backend

## Ordem de Rotas no FastAPI

⚠️ **IMPORTANTE**: Rotas específicas devem vir ANTES de rotas com parâmetros de path.

### ❌ Errado
```python
@router.get("/{cliente_id}")  # Captura TUDO, inclusive "/racas"
def get_cliente(cliente_id: int):
    pass

@router.get("/racas")  # NUNCA será chamada!
def list_racas():
    pass
```

### ✅ Correto
```python
@router.get("/racas")  # Rota específica primeiro
def list_racas():
    pass

@router.get("/{cliente_id}")  # Rota com parâmetro depois
def get_cliente(cliente_id: int):
    pass
```

**Motivo**: FastAPI usa a primeira rota que corresponder. Se `/{cliente_id}` vem primeiro, ela captura `/racas` e tenta converter "racas" em inteiro, resultando em 422 Unprocessable Entity.

## Soft Delete Pattern

### Implementação
```python
# Modelo
class Pet(Base):
    __tablename__ = "pets"
    ativo = Column(Boolean, default=True, nullable=False)

# Endpoint de Delete
@router.delete("/pets/{pet_id}")
def delete_pet(pet_id: int, db: Session):
    pet.ativo = False  # Soft delete
    db.commit()
    return None

# Filtro no Response
class ClienteResponse(BaseModel):
    pets: List[PetResponse] = []
    
    @validator('pets', pre=True)
    def filter_active_pets(cls, v):
        if isinstance(v, list):
            return [pet for pet in v if pet.ativo]
        return v
```

**Vantagens**:
- Dados nunca são perdidos
- Permite auditoria completa
- Possibilidade de "restaurar" registros
- Conformidade com LGPD

## Sistema de Auditoria

### Função log_update
```python
def log_update(
    db: Session, 
    user_id: int, 
    entity_type: str, 
    entity_id: int, 
    old_data: dict,  # ⚠️ Necessário!
    new_data: dict,  # ⚠️ Necessário!
    ip: str = None
):
    pass
```

### Uso Correto
```python
@router.put("/pets/{pet_id}")
def update_pet(pet_id: int, pet_data: PetUpdate, db: Session):
    pet = db.query(Pet).get(pet_id)
    
    # 1. Capturar dados ANTES de atualizar
    old_data = {
        "nome": pet.nome,
        "especie": pet.especie,
        # ... outros campos
    }
    
    # 2. Atualizar
    for field, value in pet_data.dict(exclude_unset=True).items():
        setattr(pet, field, value)
    
    db.commit()
    
    # 3. Log com old e new
    log_update(db, user_id, "pet", pet.id, old_data, pet_data.dict())
```

## Geração de Códigos Únicos

### Padrão: `CODIGO_CLIENTE-PET-XXXX`

```python
def generate_pet_code(cliente_codigo: str, db: Session) -> str:
    # Contar pets existentes do cliente
    count = db.query(Pet).filter(
        Pet.cliente_id == cliente_id
    ).count()
    
    # Formato: 1002-PET-0001
    return f"{cliente_codigo}-PET-{count + 1:04d}"
```

## Validadores Pydantic

### Filtrar Relações
```python
class ClienteResponse(BaseModel):
    pets: List[PetResponse] = []
    
    @validator('pets', pre=True)
    def filter_active_pets(cls, v):
        """Filtrar apenas pets ativos"""
        if isinstance(v, list):
            return [pet for pet in v if pet.ativo]
        return v
```

### Converter Tipos
```python
class PetCreate(BaseModel):
    peso: Optional[float] = None
    
    @validator('peso', pre=True)
    def convert_peso(cls, v):
        if v == '' or v is None:
            return None
        return float(v)
```

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

⚠️ **Atenção**: Em produção, especificar origins explicitamente!

## Error Handling

### Custom Validation Error Handler
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ VALIDATION ERROR: {request.url}")
    logger.error(f"   Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Dados inválidos",
            "details": exc.errors()
        }
    )
```

**Uso**: Adicionar logs detalhados para debugar erros 422.

## Queries Otimizadas

### Evitar N+1
```python
# ❌ Ruim - N+1 queries
clientes = db.query(Cliente).all()
for cliente in clientes:
    pets = cliente.pets  # Query adicional por cliente!

# ✅ Bom - Eager loading
from sqlalchemy.orm import joinedload

clientes = db.query(Cliente)\
    .options(joinedload(Cliente.pets))\
    .all()
```

### Filtros Compostos
```python
# Busca em múltiplos campos
query = db.query(Cliente).filter(
    or_(
        Cliente.nome.ilike(f"%{search}%"),
        Cliente.cpf.ilike(f"%{search}%"),
        Cliente.email.ilike(f"%{search}%")
    )
)
```

## Migrations

### Adicionar Coluna
```python
# migrate_add_codigo.py
import sqlite3

conn = sqlite3.connect('./petshop.db')
c = conn.cursor()

try:
    c.execute('ALTER TABLE pets ADD COLUMN codigo VARCHAR(50) UNIQUE')
    conn.commit()
    print("✅ Coluna 'codigo' adicionada com sucesso!")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("⚠️  Coluna já existe")
    else:
        raise
finally:
    conn.close()
```

## Testes Úteis

### Testar Endpoint no Terminal
```python
# Python REPL
import requests

# Login
r = requests.post('http://127.0.0.1:8000/auth/login', 
    json={'username': 'admin', 'password': 'senha'})
token = r.json()['access_token']

# Request autenticado
headers = {'Authorization': f'Bearer {token}'}
r = requests.get('http://127.0.0.1:8000/clientes/racas?especie=Cão', 
    headers=headers)
print(r.json())
```

### Verificar Banco de Dados
```python
import sqlite3

conn = sqlite3.connect('./petshop.db')
c = conn.cursor()

# Estrutura da tabela
c.execute('PRAGMA table_info(pets)')
print([col[1] for col in c.fetchall()])

# Dados
c.execute('SELECT * FROM pets WHERE ativo = 1')
for row in c.fetchall():
    print(row)

conn.close()
```

## Performance Tips

1. **Índices**: Criar índices em campos de busca frequente
```sql
CREATE INDEX idx_clientes_nome ON clientes(nome);
CREATE INDEX idx_pets_codigo ON pets(codigo);
```

2. **Paginação**: Sempre usar `offset` e `limit`
```python
@router.get("/clientes")
def list_clientes(skip: int = 0, limit: int = 100):
    return db.query(Cliente).offset(skip).limit(limit).all()
```

3. **Select Específico**: Buscar apenas campos necessários
```python
# Evitar trazer todos os campos
db.query(Cliente.id, Cliente.nome).all()
```

## Segurança

1. **Sempre validar ownership**
```python
@router.get("/clientes/{id}")
def get_cliente(id: int, current_user: User):
    cliente = db.query(Cliente).filter(
        Cliente.id == id,
        Cliente.user_id == current_user.id  # ⚠️ Crítico!
    ).first()
```

2. **Rate Limiting**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/endpoint")
@limiter.limit("100/hour")
def endpoint():
    pass
```

3. **Sanitização de Inputs**
```python
from bleach import clean

def sanitize_input(text: str) -> str:
    return clean(text, strip=True)
```

---

**Última atualização**: 05/01/2026
