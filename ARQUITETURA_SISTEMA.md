# 📋 Arquitetura do Sistema - Pet Shop ERP Multi-Tenant

> Documentação técnica completa da arquitetura, design patterns, integrações e sugestões de melhorias.

---

## 📑 Índice

1. [Visão Geral](#visão-geral)
2. [Stack Tecnológica](#stack-tecnológica)
3. [Arquitetura Backend](#arquitetura-backend)
4. [Arquitetura Frontend](#arquitetura-frontend)
5. [Banco de Dados](#banco-de-dados)
6. [Multi-Tenancy](#multi-tenancy)
7. [Autenticação e Autorização](#autenticação-e-autorização)
8. [Integrações Externas](#integrações-externas)
9. [Features Principais](#features-principais)
10. [Infraestrutura e Deploy](#infraestrutura-e-deploy)
11. [Fluxos Críticos](#fluxos-críticos)
12. [Problemas Identificados](#problemas-identificados)
13. [Sugestões de Melhorias](#sugestões-de-melhorias)

---

## 🎯 Visão Geral

**Pet Shop ERP** é um sistema de gestão empresarial (ERP) completo projetado especificamente para pet shops, com arquitetura **multi-tenant SaaS**. O sistema oferece funcionalidades de gestão financeira, estoque, vendas, PDV, nota fiscal eletrônica, CRM, e integrações com APIs externas.

### Características Principais
- **Multi-Tenant**: Isolamento completo de dados por tenant
- **API-First**: Backend REST API com FastAPI
- **Real-time**: Integrações com WhatsApp Business API
- **Fiscal**: Processamento de NF-e (XML)
- **IA**: Assistente inteligente com OpenAI GPT
- **Mobile-Ready**: Interface responsiva com Tailwind CSS

---

## 🛠️ Stack Tecnológica

### Backend
- **Framework**: FastAPI 0.104+
- **Linguagem**: Python 3.11
- **ORM**: SQLAlchemy 2.0
- **Banco de Dados**: PostgreSQL 16
- **Validação**: Pydantic v2
- **Auth**: JWT (JSON Web Tokens)
- **Tasks**: APScheduler (agendamento de tarefas)
- **Migrations**: Scripts Python personalizados

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Linguagem**: JavaScript (JSX)
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM v6
- **HTTP Client**: Axios
- **State Management**: React Hooks (useState, useEffect, useContext)
- **Notifications**: React Hot Toast
- **Icons**: Heroicons, Lucide React

### DevOps & Infraestrutura
- **Containerização**: Docker + Docker Compose
- **Proxy Reverso**: Nginx
- **CI/CD**: Scripts shell personalizados
- **Ambientes**: Development, Staging, Production, Local-Prod

### Integrações
- **ERP**: Bling API v3
- **Pagamentos**: Stone API
- **Comunicação**: WhatsApp Business API (Evolution API)
- **IA**: OpenAI GPT-4/GPT-3.5
- **Mapas**: Google Maps API

---

## 🔧 Arquitetura Backend

### Estrutura de Diretórios

```
backend/
├── app/
│   ├── main.py                      # Entry point da aplicação
│   ├── config.py                    # Configurações globais
│   ├── database.py                  # Setup SQLAlchemy
│   ├── dependencies.py              # Dependencies DI
│   │
│   ├── auth/                        # Autenticação
│   │   ├── __init__.py
│   │   ├── dependencies.py          # get_current_user, get_current_user_and_tenant
│   │   └── utils.py                 # Hash, JWT
│   │
│   ├── tenancy/                     # Multi-tenancy
│   │   ├── middleware.py            # Tenant context middleware
│   │   ├── context.py               # Tenant context vars
│   │   └── models.py                # Tenant model
│   │
│   ├── models/                      # Modelos SQLAlchemy
│   │   ├── base.py                  # Base, BaseTenantModel
│   │   ├── user.py                  # User, Role, Permission
│   │   ├── produtos_models.py       # Produto, Estoque, NotaEntrada
│   │   ├── financeiro_models.py     # ContaPagar, ContaReceber, FluxoCaixa
│   │   └── ...
│   │
│   ├── schemas/                     # Pydantic schemas (request/response)
│   │   ├── user_schemas.py
│   │   ├── produto_schemas.py
│   │   └── ...
│   │
│   ├── middlewares/                 # Middlewares customizados
│   │   ├── request_logging.py       # Log de requisições
│   │   ├── rate_limit.py            # Rate limiting
│   │   └── tenant_middleware.py     # Tenant isolation
│   │
│   ├── routes/ ou *_routes.py       # Rotas da API
│   │   ├── auth_routes.py
│   │   ├── produtos_routes.py
│   │   ├── financeiro_routes.py
│   │   ├── notas_entrada_routes.py
│   │   ├── clientes_routes.py
│   │   ├── vendas_routes.py
│   │   ├── pdv_routes.py
│   │   ├── whatsapp_routes.py
│   │   └── ...
│   │
│   ├── services/                    # Lógica de negócio
│   │   ├── bling_service.py
│   │   ├── stone_service.py
│   │   ├── whatsapp_service.py
│   │   └── ai_service.py
│   │
│   ├── utils/                       # Utilitários
│   │   ├── logger.py
│   │   ├── validators.py
│   │   └── helpers.py
│   │
│   └── schedulers/                  # Tarefas agendadas
│       └── acerto_scheduler.py
│
├── alembic/                         # Migrations (não usado ativamente)
├── migrations/                      # Scripts de migração customizados
├── tests/                           # Testes
├── uploads/                         # Arquivos temporários
├── requirements.txt
└── Dockerfile
```

### Design Patterns Utilizados

#### 1. **Dependency Injection (FastAPI)**
```python
def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/produtos")
def listar_produtos(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    ...
```

#### 2. **Repository Pattern (Implícito via SQLAlchemy)**
- Queries centralizadas em rotas
- Modelos com métodos customizados quando necessário

#### 3. **Middleware Chain**
```python
# Ordem de execução dos middlewares:
1. CORS Middleware
2. Tenancy Middleware (extração tenant_id)
3. Rate Limit Middleware
4. Request Logging Middleware
5. Error Handler Middleware
```

#### 4. **Context Variables (Multi-Tenancy)**
```python
from contextvars import ContextVar

tenant_id_var: ContextVar[Optional[UUID]] = ContextVar('tenant_id', default=None)

# Middleware injeta tenant_id no contexto
tenant_id_var.set(tenant_id)
```

### Modelos de Dados Base

#### BaseTenantModel
```python
class BaseTenantModel(Base):
    """Base class para modelos multi-tenant"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Todos os modelos principais herdam de `BaseTenantModel`, garantindo isolamento por tenant.

### Rotas Principais

| Módulo | Endpoint Base | Principais Operações |
|--------|---------------|---------------------|
| Auth | `/auth` | login, register, me, refresh-token |
| Produtos | `/produtos` | CRUD, busca, estoque, histórico preços |
| Vendas | `/vendas` | CRUD, PDV, comissões, relatórios |
| Financeiro | `/financeiro` | contas a pagar/receber, fluxo de caixa, DRE |
| Clientes | `/clientes` | CRUD, pets, histórico, timeline |
| Notas Entrada | `/notas-entrada` | upload XML, processar, vincular produtos, reverter |
| Dashboard | `/dashboard` | resumos, métricas, gráficos |
| WhatsApp | `/api/whatsapp` | enviar mensagens, webhook, configuração |
| IA | `/ia` | chat, análise DRE, extrato bancário |

### Padrão de Response

**Sucesso:**
```json
{
  "id": 1,
  "nome": "Produto X",
  "preco": 99.90,
  ...
}
```

**Erro HTTP Exception:**
```json
{
  "detail": "Produto não encontrado"
}
```

**Erro Interno (500):**
```json
{
  "error": "internal_server_error",
  "message": "Erro interno no servidor",
  "detail": "Entre em contato com o suporte"
}
```

---

## 🎨 Arquitetura Frontend

### Estrutura de Diretórios

```
frontend/
├── public/                          # Assets estáticos
├── src/
│   ├── main.jsx                     # Entry point
│   ├── App.jsx                      # Root component
│   ├── index.css                    # Tailwind imports
│   │
│   ├── api.js                       # Axios instance configurada
│   │
│   ├── components/                  # Componentes React
│   │   ├── Layout.jsx               # Layout principal
│   │   ├── ProtectedRoute.jsx       # Guard para rotas privadas
│   │   ├── Dashboard.jsx
│   │   ├── Produtos.jsx
│   │   ├── Vendas.jsx
│   │   ├── PDV.jsx
│   │   ├── EntradaXML.jsx           # Processamento NF-e
│   │   ├── ClientesNovo.jsx
│   │   ├── Financeiro.jsx
│   │   ├── DRE.jsx
│   │   ├── ChatIA.jsx
│   │   └── ...
│   │
│   ├── contexts/                    # Context API
│   │   └── AuthContext.jsx          # Autenticação global
│   │
│   ├── hooks/                       # Custom hooks
│   │   └── useAuth.js
│   │
│   └── utils/                       # Utilitários
│       └── formatters.js
│
├── package.json
├── vite.config.js
├── tailwind.config.js
└── Dockerfile
```

### Padrões de Componentes

#### Estrutura Típica de Componente
```jsx
const Produtos = () => {
  // 1. Estados
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filtros, setFiltros] = useState({});
  
  // 2. Context/Hooks
  const { user } = useAuth();
  
  // 3. Effects
  useEffect(() => {
    carregarProdutos();
  }, []);
  
  // 4. Handlers
  const carregarProdutos = async () => {
    try {
      setLoading(true);
      const response = await api.get('/produtos');
      setProdutos(response.data);
    } catch (error) {
      toast.error('Erro ao carregar produtos');
    } finally {
      setLoading(false);
    }
  };
  
  // 5. Render
  return (
    <div>...</div>
  );
};
```

### Configuração do Axios

```javascript
// src/api.js
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  }
});

// Interceptor para adicionar token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Roteamento

```jsx
<Routes>
  <Route path="/login" element={<Login />} />
  
  <Route element={<ProtectedRoute />}>
    <Route element={<Layout />}>
      <Route path="/" element={<Dashboard />} />
      <Route path="/produtos" element={<Produtos />} />
      <Route path="/vendas" element={<Vendas />} />
      <Route path="/pdv" element={<PDV />} />
      <Route path="/compras/entrada-xml" element={<EntradaXML />} />
      <Route path="/clientes" element={<ClientesNovo />} />
      <Route path="/financeiro" element={<Financeiro />} />
      ...
    </Route>
  </Route>
</Routes>
```

---

## 💾 Banco de Dados

### Schema Principal

#### Módulo: Autenticação
```sql
-- users
id SERIAL PRIMARY KEY
email VARCHAR UNIQUE NOT NULL
hashed_password VARCHAR NOT NULL
nome VARCHAR
ativo BOOLEAN DEFAULT TRUE
tenant_id UUID NOT NULL
role_id INTEGER REFERENCES roles(id)
created_at TIMESTAMP
updated_at TIMESTAMP

-- roles
id SERIAL PRIMARY KEY
nome VARCHAR NOT NULL
descricao TEXT
tenant_id UUID NOT NULL

-- permissions
id SERIAL PRIMARY KEY
nome VARCHAR NOT NULL
descricao TEXT
```

#### Módulo: Produtos
```sql
-- produto
id SERIAL PRIMARY KEY
codigo VARCHAR NOT NULL -- SKU
nome VARCHAR NOT NULL
descricao TEXT
preco_custo DECIMAL(10,2)
preco_venda DECIMAL(10,2)
estoque_atual DECIMAL(10,3)
estoque_minimo DECIMAL(10,3)
estoque_maximo DECIMAL(10,3)
ativo BOOLEAN DEFAULT TRUE
categoria_id INTEGER
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- produto_historico_precos
id SERIAL PRIMARY KEY
produto_id INTEGER REFERENCES produto(id)
preco_custo_anterior DECIMAL(10,2)
preco_custo_novo DECIMAL(10,2)
preco_venda_anterior DECIMAL(10,2)
preco_venda_novo DECIMAL(10,2)
margem_anterior DECIMAL(5,2)
margem_nova DECIMAL(5,2)
variacao_custo_percentual DECIMAL(5,2)
variacao_venda_percentual DECIMAL(5,2)
motivo VARCHAR(50) -- 'nfe_entrada', 'manual', 'ajuste'
nota_entrada_id INTEGER
referencia VARCHAR
observacoes TEXT
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP

-- estoque_movimentacoes
id SERIAL PRIMARY KEY
produto_id INTEGER REFERENCES produto(id)
tipo VARCHAR(20) -- 'entrada', 'saida', 'ajuste', 'transferencia'
quantidade DECIMAL(10,3)
estoque_anterior DECIMAL(10,3)
estoque_novo DECIMAL(10,3)
motivo VARCHAR(100)
referencia_tipo VARCHAR(50) -- 'venda', 'nota_entrada', 'ajuste_manual'
referencia_id INTEGER
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- produto_lote
id SERIAL PRIMARY KEY
produto_id INTEGER REFERENCES produto(id)
lote VARCHAR
data_fabricacao DATE
data_validade DATE
quantidade DECIMAL(10,3)
preco_custo DECIMAL(10,2)
nota_entrada_id INTEGER
tenant_id UUID NOT NULL
created_at TIMESTAMP
```

#### Módulo: Notas Fiscais
```sql
-- notas_entrada
id SERIAL PRIMARY KEY
numero_nota VARCHAR NOT NULL
serie VARCHAR
chave_acesso VARCHAR(44) UNIQUE NOT NULL
fornecedor_cnpj VARCHAR(14)
fornecedor_nome VARCHAR
fornecedor_id INTEGER REFERENCES cliente(id)
data_emissao DATE
data_entrada TIMESTAMP
valor_produtos DECIMAL(10,2)
valor_frete DECIMAL(10,2)
valor_desconto DECIMAL(10,2)
valor_total DECIMAL(10,2)
xml_content TEXT
status VARCHAR(20) DEFAULT 'pendente' -- 'pendente', 'processada', 'erro'
erro_mensagem TEXT
processada_em TIMESTAMP
produtos_vinculados INTEGER DEFAULT 0
produtos_nao_vinculados INTEGER DEFAULT 0
entrada_estoque_realizada BOOLEAN DEFAULT FALSE
tipo_rateio VARCHAR(20) DEFAULT 'loja' -- 'loja', 'online', 'parcial'
percentual_online FLOAT DEFAULT 0
percentual_loja FLOAT DEFAULT 100
valor_online FLOAT DEFAULT 0
valor_loja FLOAT DEFAULT 0
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- notas_entrada_itens
id SERIAL PRIMARY KEY
nota_entrada_id INTEGER REFERENCES notas_entrada(id) ON DELETE CASCADE
codigo_produto VARCHAR
descricao VARCHAR
ncm VARCHAR
quantidade DECIMAL(10,3)
unidade VARCHAR(10)
valor_unitario DECIMAL(10,2)
valor_total DECIMAL(10,2)
produto_id INTEGER REFERENCES produto(id)
vinculado BOOLEAN DEFAULT FALSE
quantidade_online FLOAT DEFAULT 0
valor_online FLOAT DEFAULT 0
tenant_id UUID NOT NULL
created_at TIMESTAMP
```

#### Módulo: Financeiro
```sql
-- contas_pagar
id SERIAL PRIMARY KEY
descricao VARCHAR NOT NULL
fornecedor_id INTEGER REFERENCES cliente(id)
categoria_id INTEGER
dre_subcategoria_id INTEGER -- Pode ser NULL
canal VARCHAR -- 'online', 'loja', NULL
valor_original DECIMAL(10,2)
valor_pago DECIMAL(10,2) DEFAULT 0
valor_desconto DECIMAL(10,2) DEFAULT 0
valor_juros DECIMAL(10,2) DEFAULT 0
valor_multa DECIMAL(10,2) DEFAULT 0
valor_final DECIMAL(10,2)
data_emissao DATE
data_vencimento DATE
data_pagamento DATE
status VARCHAR(20) DEFAULT 'pendente' -- 'pendente', 'pago', 'atrasado', 'cancelado'
nota_entrada_id INTEGER
nfe_numero VARCHAR
documento VARCHAR
observacoes TEXT
percentual_online FLOAT DEFAULT 0
percentual_loja FLOAT DEFAULT 100
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- contas_receber
id SERIAL PRIMARY KEY
descricao VARCHAR NOT NULL
cliente_id INTEGER REFERENCES cliente(id)
categoria_id INTEGER
valor_original DECIMAL(10,2)
valor_recebido DECIMAL(10,2) DEFAULT 0
valor_desconto DECIMAL(10,2) DEFAULT 0
valor_juros DECIMAL(10,2) DEFAULT 0
valor_final DECIMAL(10,2)
data_emissao DATE
data_vencimento DATE
data_recebimento DATE
status VARCHAR(20) DEFAULT 'pendente'
venda_id INTEGER
documento VARCHAR
observacoes TEXT
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- fluxo_caixa
id SERIAL PRIMARY KEY
tipo VARCHAR(20) -- 'entrada', 'saida'
categoria_id INTEGER
descricao VARCHAR NOT NULL
valor DECIMAL(10,2) NOT NULL
data_movimento DATE NOT NULL
conta_bancaria_id INTEGER
forma_pagamento_id INTEGER
referencia_tipo VARCHAR(50) -- 'venda', 'conta_pagar', 'conta_receber'
referencia_id INTEGER
tenant_id UUID NOT NULL
usuario_id INTEGER
created_at TIMESTAMP
```

#### Módulo: Vendas
```sql
-- venda
id SERIAL PRIMARY KEY
cliente_id INTEGER REFERENCES cliente(id)
data_venda TIMESTAMP NOT NULL
subtotal DECIMAL(10,2)
desconto DECIMAL(10,2) DEFAULT 0
acrescimo DECIMAL(10,2) DEFAULT 0
total DECIMAL(10,2) NOT NULL
status VARCHAR(20) DEFAULT 'concluida' -- 'concluida', 'cancelada'
observacoes TEXT
vendedor_id INTEGER REFERENCES users(id)
forma_pagamento VARCHAR(50)
canal VARCHAR(20) DEFAULT 'loja' -- 'loja', 'online'
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- venda_item
id SERIAL PRIMARY KEY
venda_id INTEGER REFERENCES venda(id) ON DELETE CASCADE
produto_id INTEGER REFERENCES produto(id)
quantidade DECIMAL(10,3) NOT NULL
preco_unitario DECIMAL(10,2) NOT NULL
desconto DECIMAL(10,2) DEFAULT 0
subtotal DECIMAL(10,2)
total DECIMAL(10,2)
tenant_id UUID NOT NULL
created_at TIMESTAMP
```

#### Módulo: Clientes/CRM
```sql
-- cliente
id SERIAL PRIMARY KEY
nome VARCHAR NOT NULL
cpf_cnpj VARCHAR(14)
email VARCHAR
telefone VARCHAR
whatsapp VARCHAR
endereco TEXT
cidade VARCHAR
estado VARCHAR(2)
cep VARCHAR(8)
data_nascimento DATE
tipo VARCHAR(20) DEFAULT 'cliente' -- 'cliente', 'fornecedor', 'funcionario'
ativo BOOLEAN DEFAULT TRUE
observacoes TEXT
tenant_id UUID NOT NULL
user_id INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP

-- pet
id SERIAL PRIMARY KEY
nome VARCHAR NOT NULL
cliente_id INTEGER REFERENCES cliente(id)
especie VARCHAR -- 'cachorro', 'gato', etc
raca VARCHAR
porte VARCHAR -- 'pequeno', 'medio', 'grande'
sexo VARCHAR(1) -- 'M', 'F'
data_nascimento DATE
peso DECIMAL(5,2)
cor VARCHAR
observacoes TEXT
ativo BOOLEAN DEFAULT TRUE
tenant_id UUID NOT NULL
created_at TIMESTAMP
updated_at TIMESTAMP
```

### Índices Importantes

```sql
-- Índices de tenant_id em todas as tabelas multi-tenant
CREATE INDEX idx_produto_tenant_id ON produto(tenant_id);
CREATE INDEX idx_venda_tenant_id ON venda(tenant_id);
CREATE INDEX idx_cliente_tenant_id ON cliente(tenant_id);

-- Índices compostos para queries frequentes
CREATE INDEX idx_produto_tenant_ativo ON produto(tenant_id, ativo);
CREATE INDEX idx_venda_tenant_data ON venda(tenant_id, data_venda DESC);
CREATE INDEX idx_contas_pagar_tenant_status ON contas_pagar(tenant_id, status);

-- Índices de busca
CREATE INDEX idx_produto_codigo ON produto(codigo);
CREATE INDEX idx_produto_nome ON produto(nome);
CREATE INDEX idx_cliente_nome ON cliente(nome);
CREATE INDEX idx_cliente_cpf_cnpj ON cliente(cpf_cnpj);
```

---

## 🏢 Multi-Tenancy

### Estratégia: Shared Database, Shared Schema

Todos os tenants compartilham o mesmo banco e schema, com isolamento via coluna `tenant_id`.

#### Vantagens
- ✅ Menor custo de infraestrutura
- ✅ Manutenção simplificada (uma única base)
- ✅ Backup centralizado
- ✅ Fácil migração de schema

#### Desvantagens
- ⚠️ Risco de vazamento de dados se query não filtrar por tenant
- ⚠️ Performance compartilhada entre tenants
- ⚠️ Impossível customização de schema por tenant

### Implementação

#### 1. Middleware de Extração do Tenant
```python
# app/tenancy/middleware.py
class TenancyMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extrai tenant_id do token JWT
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            tenant_id = payload.get("tenant_id")
            
            # Injeta no contexto
            tenant_id_var.set(UUID(tenant_id))
        
        response = await call_next(request)
        return response
```

#### 2. Context Variable
```python
# app/tenancy/context.py
from contextvars import ContextVar
from uuid import UUID

tenant_id_var: ContextVar[Optional[UUID]] = ContextVar('tenant_id', default=None)

def get_current_tenant_id() -> Optional[UUID]:
    return tenant_id_var.get()
```

#### 3. Dependency Injection
```python
# app/auth/dependencies.py
def get_current_user_and_tenant(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
) -> tuple[User, UUID]:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("user_id")
    tenant_id = UUID(payload.get("tenant_id"))
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user, tenant_id
```

#### 4. Query Pattern (SEMPRE filtrar por tenant_id)
```python
@router.get("/produtos")
def listar_produtos(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    user, tenant_id = user_and_tenant
    
    # ✅ CORRETO - filtra por tenant_id
    produtos = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).all()
    
    return produtos
```

**🚨 CRÍTICO**: Toda query em modelo multi-tenant DEVE filtrar por `tenant_id`. Queries sem esse filtro causam vazamento de dados entre tenants.

---

## 🔐 Autenticação e Autorização

### JWT (JSON Web Tokens)

#### Estrutura do Token
```json
{
  "user_id": 1,
  "tenant_id": "7be8dad7-8956-4758-b7bc-855a5259fe2b",
  "email": "admin@test.com",
  "role": "admin",
  "exp": 1738790400
}
```

#### Fluxo de Login
```
1. POST /auth/login
   { "email": "user@example.com", "password": "senha123" }

2. Backend valida credenciais
   - Verifica email no banco
   - Compara hash de senha (bcrypt)
   - Valida se usuário está ativo

3. Gera JWT token
   - Payload com user_id, tenant_id, email
   - Assinatura com SECRET_KEY
   - Expiration de 7 dias

4. Retorna token
   { "access_token": "eyJ...", "token_type": "bearer" }

5. Frontend armazena em localStorage
   localStorage.setItem('token', token)

6. Requests subsequentes incluem header
   Authorization: Bearer eyJ...
```

### RBAC (Role-Based Access Control)

#### Estrutura
- **User** → pertence a um **Role**
- **Role** → tem múltiplas **Permissions**
- **Permission** → define ação (ex: "produtos.criar", "vendas.visualizar")

#### Implementação (Parcial)
Sistema tem estrutura de roles/permissions no banco, mas a verificação nas rotas ainda não está completamente implementada. Atualmente usa verificação manual de `user.role` em alguns endpoints.

---

## 🔗 Integrações Externas

### 1. Bling API (ERP)

**Propósito**: Sincronização bidirecional de produtos, pedidos e estoque.

**Endpoints Principais**:
- `GET /produtos` - Importar produtos do Bling
- `POST /produtos` - Enviar produto para Bling
- `GET /pedidos` - Importar pedidos
- `PUT /produtos/{id}/estoque` - Atualizar estoque

**Autenticação**: OAuth 2.0
- Access Token + Refresh Token
- Token armazenado em `bling_token_control.json`

**Configuração**:
```bash
python configurar_bling.py
# Solicita Client ID, Client Secret, Code
# Gera access_token e refresh_token
```

### 2. Stone API (Pagamentos)

**Propósito**: Processamento de transações com cartão via máquinas Stone.

**Features**:
- Processar transações
- Consultar status de pagamentos
- Cancelar transações
- Relatórios de vendas

**Autenticação**: API Key

**Configuração**:
```bash
python configurar_stone_api.py
# Solicita Stone API Key
# Configura environment (production/staging)
```

### 3. WhatsApp Business API (Evolution API)

**Propósito**: Envio/recebimento de mensagens WhatsApp, chatbot IA.

**Endpoints**:
- `POST /api/whatsapp/enviar` - Enviar mensagem
- `POST /webhook` - Receber mensagens (webhook)
- `GET /api/whatsapp/clientes/{id}/whatsapp/ultimas` - Histórico

**Features**:
- Envio de mensagens de texto, imagem, PDF
- Recebimento via webhook
- Chatbot com IA (OpenAI)
- Execução de ferramentas (consultar produtos, criar vendas)

**Configuração**:
- Instância Evolution API externa
- Configuração por tenant em `tenant_whatsapp_config`

### 4. OpenAI API (IA)

**Propósito**: Assistente inteligente, análise de DRE, extrato bancário.

**Modelos Usados**:
- GPT-4-turbo (análises complexas)
- GPT-3.5-turbo (chat geral)

**Features**:
- Chat IA contextual
- Análise de DRE (Demonstrativo de Resultado)
- OCR de extrato bancário com IA
- Sugestões de categorização de despesas

**Configuração**:
```bash
# .env
OPENAI_API_KEY=sk-...
```

### 5. Google Maps API

**Propósito**: Geocodificação de endereços de clientes.

**Features**:
- Autocomplete de endereços
- Validação de CEP
- Coordenadas geográficas

**Configuração**:
```bash
# .env
GOOGLE_MAPS_API_KEY=AIza...
```

---

## 📦 Features Principais

### 1. Gestão de Produtos
- ✅ CRUD completo
- ✅ Controle de estoque (atual, mínimo, máximo)
- ✅ Movimentações de estoque (entrada, saída, ajuste)
- ✅ Histórico de alteração de preços
- ✅ Categorias e subcategorias
- ✅ Variações de produtos
- ✅ Controle de lotes e validade
- ✅ Sincronização com Bling

### 2. Nota Fiscal Eletrônica (NF-e)
- ✅ Upload de arquivo XML
- ✅ Parse automático de dados da nota
- ✅ Vinculação automática de produtos (por código/nome)
- ✅ Vinculação manual com busca/autocomplete
- ✅ Criação de produtos a partir da NF-e
- ✅ Entrada automática no estoque
- ✅ Geração de contas a pagar
- ✅ Atualização de preço de custo
- ✅ Rateio de custos (loja física / online)
- ✅ Reversão de entrada (rollback)
- ✅ Criação automática de fornecedores

### 3. PDV (Ponto de Venda)
- ✅ Busca rápida de produtos
- ✅ Carrinho de compras
- ✅ Desconto por item / geral
- ✅ Múltiplas formas de pagamento
- ✅ Identificação de cliente (opcional)
- ✅ Impressão de cupom
- ✅ Baixa automática no estoque
- ✅ Integração com Stone (pagamento cartão)
- ✅ Cálculo de comissões

### 4. Gestão Financeira
- ✅ Contas a Pagar (fornecedores)
- ✅ Contas a Receber (clientes)
- ✅ Fluxo de Caixa
- ✅ Conciliação bancária
- ✅ DRE (Demonstrativo Resultado Exercício)
- ✅ DRE por canal (online vs loja)
- ✅ Projeção de caixa
- ✅ Relatórios financeiros

### 5. CRM (Clientes e Pets)
- ✅ Cadastro de clientes
- ✅ Cadastro de pets por cliente
- ✅ Histórico de compras
- ✅ Timeline de interações
- ✅ WhatsApp integrado
- ✅ Aniversários e lembretes
- ✅ Ficha completa do pet (raça, porte, peso, etc)

### 6. Comissões
- ✅ Cálculo por vendedor
- ✅ Regras por produto/categoria
- ✅ Relatórios de comissões
- ✅ Demonstrativo por período

### 7. Inteligência Artificial
- ✅ Chat IA contextual
- ✅ Análise automática de DRE com insights
- ✅ OCR de extrato bancário
- ✅ Categorização inteligente de despesas
- ✅ Chatbot WhatsApp
- ✅ Execução de ferramentas (Function Calling)

### 8. Dashboards e Relatórios
- ✅ Dashboard principal (métricas gerais)
- ✅ Dashboard gerencial (análises avançadas)
- ✅ Gráficos de vendas por período
- ✅ Contas vencidas e a vencer
- ✅ Produtos mais vendidos
- ✅ Análise de margem de lucro

---

## 🐳 Infraestrutura e Deploy

### Docker Compose - Ambientes

#### 1. Development (`docker-compose.yml`)
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: petshop_db
      POSTGRES_USER: petshop_user
      POSTGRES_PASSWORD: petshop_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  backend:
    build: ./backend
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+psycopg2://petshop_user:petshop_pass@postgres:5432/petshop_db
      ENVIRONMENT: development
      DEBUG: "True"
  
  frontend:
    build: ./frontend
    command: npm run dev -- --host 0.0.0.0 --port 5173
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

**Uso**:
```bash
docker-compose up -d
```

#### 2. Staging (`docker-compose.staging.yml`)
- Build otimizado
- Nginx como proxy reverso
- Healthchecks
- Logs estruturados
- Backups automatizados

#### 3. Production (`docker-compose.production.yml`)
- HTTPS com certificados
- Nginx com cache
- Replicas de backend (múltiplas instâncias)
- PostgreSQL com replicação
- Monitoramento
- Backups criptografados

### Scripts de Inicialização

#### Development
```bash
# INICIAR_DEV.bat (Windows)
docker-compose -f docker-compose.yml up -d --build
```

#### Production
```bash
# INICIAR_PRODUCAO.bat (Windows)
docker-compose -f docker-compose.production.yml up -d --build
```

### Backup Automático

Script SQL executado periodicamente:
```bash
pg_dump -h postgres -U ${POSTGRES_USER} -d ${POSTGRES_DB} \
  -F c -f /backups/backup_${TIMESTAMP}.dump
```

---

## 🔄 Fluxos Críticos

### 1. Processamento de NF-e (Nota Fiscal de Entrada)

```
┌─────────────────────────────────────────────────┐
│  1. Upload XML                                  │
│  POST /notas-entrada/upload                     │
│  - Usuário faz upload do arquivo XML           │
│  - Backend valida extensão .xml                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  2. Parse do XML                                │
│  - Extrai dados: chave, número, fornecedor     │
│  - Extrai itens: produtos, quantidades, valores│
│  - Valida estrutura do XML                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  3. Verificação de Duplicidade                 │
│  - Busca nota pela chave de acesso             │
│  - Se existe → erro 400                        │
│  - Se não existe → continua                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  4. Busca/Criação de Fornecedor                │
│  - Busca fornecedor por CNPJ                   │
│  - Se não existe → cria automaticamente        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  5. Criação da Nota no BD                      │
│  - INSERT em notas_entrada                     │
│  - Status: 'pendente'                          │
│  - entrada_estoque_realizada: false            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  6. Vinculação Automática de Produtos          │
│  Para cada item da nota:                       │
│  - Busca produto por código                    │
│  - Se encontra → vincula (produto_id)          │
│  - Se não encontra → marca como não vinculado  │
│  - INSERT em notas_entrada_itens               │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  7. Retorno ao Frontend                        │
│  - Quantidade de itens vinculados              │
│  - Quantidade de itens não vinculados          │
│  - Se 100% vinculado → pode processar          │
│  - Se não → usuário deve vincular manualmente  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  8. Vinculação Manual (se necessário)          │
│  Frontend:                                      │
│  - Lista itens não vinculados                  │
│  - Campo de busca com autocomplete             │
│  - Vincula ou cria novo produto                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  9. Revisão de Preços (opcional)               │
│  POST /notas-entrada/{id}/preview-processamento│
│  - Calcula novos preços de custo               │
│  - Mostra comparação com preços atuais         │
│  - Usuário pode ajustar preços de venda        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  10. Processamento Final                       │
│  POST /notas-entrada/{id}/processar            │
│  - Atualiza preço de custo dos produtos        │
│  - Registra histórico de preços                │
│  - Dá entrada no estoque                       │
│  - Cria movimentação de estoque                │
│  - Cria conta a pagar                          │
│  - Atualiza status da nota: 'processada'       │
│  - entrada_estoque_realizada: true             │
└─────────────────────────────────────────────────┘
```

**Pontos de Atenção**:
- ⚠️ Rateio de custos (online/loja) pode distribuir estoque
- ⚠️ Reversão de entrada deve desfazer TUDO (estoque, preços, contas)
- ⚠️ Múltiplas contas a pagar se a nota tem prazo parcelado

### 2. Fluxo de Venda no PDV

```
1. Adicionar itens ao carrinho
2. Identificar cliente (opcional)
3. Aplicar descontos
4. Selecionar forma de pagamento
5. Confirmar venda
   ↓
   Backend:
   - INSERT em venda
   - INSERT em venda_item (para cada produto)
   - Baixa no estoque (UPDATE produto.estoque_atual)
   - INSERT em estoque_movimentacoes (tipo='saida')
   - Se pagamento à vista:
     - INSERT em fluxo_caixa (tipo='entrada')
   - Se parcelado/à prazo:
     - INSERT em contas_receber
   - Cálculo de comissões (se configurado)
6. Retornar venda_id
7. Imprimir cupom
```

### 3. Chatbot WhatsApp com IA

```
1. Cliente envia mensagem no WhatsApp
2. Webhook recebe mensagem
   POST /webhook
3. Backend identifica tipo de mensagem
4. Envia para OpenAI com:
   - Histórico da conversa
   - Ferramentas disponíveis (tools)
   - Contexto do tenant
5. OpenAI processa e retorna:
   - Resposta em texto, OU
   - Chamada de ferramenta (function call)
6. Se chamada de ferramenta:
   - Executa função (ex: consultar_produtos, criar_venda)
   - Retorna resultado para OpenAI
   - OpenAI formula resposta final
7. Envia resposta ao cliente via WhatsApp API
8. Registra conversa no banco
```

---

## ⚠️ Problemas Identificados

### 1. **Inconsistência de Nomenclatura de Variáveis**

**Problema**: Ao longo do código, há inconsistência entre:
- `current_user` vs `user`
- `current_user.id` vs `user.id`

**Localização**: Múltiplos arquivos de rotas

**Exemplo**:
```python
# ❌ Erro encontrado
def upload_xml(
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    current_user, tenant_id = user_and_tenant
    logger.info(f"Usuário: {current_user.email} (ID: {user.id})")  # user não existe!
```

**Impacto**: Causa `NameError: name 'user' is not defined` em runtime

**Correções Aplicadas**:
- `notas_entrada_routes.py` - substituído `user.id` → `current_user.id`
- `financeiro_routes.py` - substituído `current_user.id` → `user.id` (dependendo do contexto)

**Recomendação**: Padronizar em TODO o código:
```python
def minha_rota(user_and_tenant = Depends(get_current_user_and_tenant)):
    user, tenant_id = user_and_tenant
    # Usar sempre: user.id, user.email
```

### 2. **Constraints NOT NULL Desnecessárias**

**Problema**: Colunas opcionais marcadas como NOT NULL no banco, mas código tenta inserir NULL.

**Exemplos**:
- `contas_pagar.dre_subcategoria_id` - NOT NULL, mas nem sempre há subcategoria
- `contas_pagar.canal` - NOT NULL, mas nem sempre é definido

**Impacto**: Erro `psycopg2.errors.NotNullViolation` ao criar contas a pagar de NF-e

**Correções Aplicadas**:
```sql
ALTER TABLE contas_pagar ALTER COLUMN dre_subcategoria_id DROP NOT NULL;
ALTER TABLE contas_pagar ALTER COLUMN canal DROP NOT NULL;
```

**Recomendação**: Revisar todas as constraints NOT NULL e tornar NULL colunas que realmente são opcionais. Usar validação no código Python/Pydantic se necessário.

### 3. **Falta de Filtro `tenant_id` em Queries**

**Problema**: Queries sem filtro de `tenant_id` em sistema multi-tenant causam vazamento de dados.

**Localização**: Diversas rotas (notas_entrada, produtos, clientes)

**Exemplo**:
```python
# ❌ ERRADO - retorna dados de TODOS os tenants
produtos = db.query(Produto).filter(Produto.ativo == True).all()

# ✅ CORRETO - filtra por tenant
produtos = db.query(Produto).filter(
    Produto.tenant_id == tenant_id,
    Produto.ativo == True
).all()
```

**Correções Aplicadas**:
- `notas_entrada_routes.py` - função `listar_notas()`
- `notas_entrada_routes.py` - função `buscar_nota()`
- Parcialmente em `notas_entrada_routes.py` - upload e verificação de duplicidade

**Recomendação**: 
1. Criar um linter/checker customizado que valida se toda query tem filtro de tenant_id
2. Implementar um wrapper de query que adiciona automaticamente o filtro
3. Revisão completa de código procurando por `db.query(Model)` sem `.filter(Model.tenant_id ==`

### 4. **Sequência de ID Desincronizada após DELETE**

**Problema**: Ao reverter e deletar uma nota fiscal, a sequência `notas_entrada_id_seq` não é resetada, causando erro de chave primária duplicada.

**Exemplo**:
- Nota #1 inserida
- Nota #1 revertida e deletada
- Sequência ainda aponta para id=1
- Nova nota tenta inserir id=1 → erro

**Correção Aplicada**:
```sql
SELECT setval('notas_entrada_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM notas_entrada), false);
```

**Recomendação**: Usar `ON DELETE CASCADE` com cuidado e considerar soft delete (coluna `deleted_at`) ao invés de DELETE físico.

### 5. **Migrations Manuais Sem Controle de Versão**

**Problema**: Sistema usa scripts Python avulsos para migrations ao invés de framework como Alembic.

**Consequências**:
- Difícil saber qual migration foi aplicada
- Risco de aplicar migration duas vezes
- Sem rollback automático

**Exemplo de Scripts**:
- `add_tipo_rateio_notas_entrada.py`
- `add_rateio_contas_itens.py`
- `add_missing_columns.py`

**Recomendação**: 
1. Implementar Alembic adequadamente
2. Criar tabela `alembic_version` para tracking
3. Migrations com `upgrade()` e `downgrade()`

### 6. **Falta de Tratamento de Erro Consistente**

**Problema**: Alguns endpoints retornam erro detalhado, outros escondem tudo como "erro interno".

**Exemplo**:
```python
# Inconsistente
try:
    ...
except Exception as e:
    logger.error(f"Erro: {str(e)}")
    raise HTTPException(status_code=500, detail="Erro interno")  # Genérico
```

**Recomendação**:
- Criar exceções customizadas (ex: `NotaJaCadastradaError`, `ProdutoNaoEncontradoError`)
- Middleware global de error handling
- Retornar erros estruturados com código de erro único

### 7. **Chaves Duplicadas no React**

**Problema**: Componentes React usando `key={p.id}` quando há loop por item, causando duplicação se múltiplos itens renderizam o mesmo produto.

**Correção Aplicada**:
```jsx
// ❌ Errado
.map(p => <button key={p.id}>...</button>)

// ✅ Correto
.map(p => <button key={`produto-${item.id}-${p.id}`}>...</button>)
```

**Recomendação**: Sempre usar chaves compostas quando há nested loops.

### 8. **Estado Global Compartilhado Indevidamente**

**Problema**: `filtroProduto` era uma string única para TODOS os itens da nota, causando que digitar em um campo mostrava resultados em todos.

**Correção Aplicada**:
```jsx
// ❌ Errado
const [filtroProduto, setFiltroProduto] = useState('');

// ✅ Correto
const [filtroProduto, setFiltroProduto] = useState({}); // {item_id: 'filtro'}
```

**Recomendação**: Sempre pensar em escopo do estado - componente, contexto ou global.

---

## 🚀 Sugestões de Melhorias

### 🔴 ALTA PRIORIDADE

#### 1. **Implementar Alembic para Migrations**
- **O quê**: Substituir scripts Python avulsos por Alembic
- **Por quê**: Controle de versão de schema, rollback, rastreabilidade
- **Como**:
  ```bash
  alembic init alembic
  alembic revision --autogenerate -m "Initial migration"
  alembic upgrade head
  ```
- **Benefícios**: Migrations versionadas, rollback automático, menos erros

#### 2. **Auditoria de Queries Multi-Tenant**
- **O quê**: Revisar TODAS as queries e garantir filtro de `tenant_id`
- **Por quê**: Segurança - evitar vazamento de dados entre tenants
- **Como**:
  ```bash
  grep -r "db.query(" backend/app/*.py | grep -v "tenant_id"
  # Revisar cada resultado
  ```
- **Benefícios**: Isolamento de dados garantido, conformidade LGPD

#### 3. **Padronizar Nomenclatura de Variáveis**
- **O quê**: Definir padrão único: `user` e `tenant_id` após desempacotamento
- **Por quê**: Evitar `NameError` em runtime
- **Como**: Refactoring em massa com regex
  ```python
  # Padrão sugerido:
  def my_route(user_and_tenant = Depends(get_current_user_and_tenant)):
      user, tenant_id = user_and_tenant
      # Usar sempre: user.id, user.email, tenant_id
  ```

#### 4. **Implementar Health Checks**
- **O quê**: Endpoints `/health` e `/readiness`
- **Por quê**: Monitoramento de infraestrutura, alertas
- **Como**:
  ```python
  @app.get("/health")
  def health_check(db: Session = Depends(get_session)):
      try:
          db.execute("SELECT 1")
          return {"status": "healthy"}
      except:
          return {"status": "unhealthy"}, 503
  ```

#### 5. **Logging Estruturado com Correlation ID**
- **O quê**: Adicionar `trace_id` em todas as requisições
- **Por quê**: Rastrear fluxo completo de uma requisição nos logs
- **Como**:
  ```python
  import uuid
  
  @app.middleware("http")
  async def add_trace_id(request: Request, call_next):
      trace_id = str(uuid.uuid4())
      request.state.trace_id = trace_id
      
      with logger.contextualize(trace_id=trace_id):
          response = await call_next(request)
      
      response.headers["X-Trace-ID"] = trace_id
      return response
  ```

### 🟡 MÉDIA PRIORIDADE

#### 6. **Implementar Cache com Redis**
- **O quê**: Cache para queries frequentes (produtos, categorias, configurações)
- **Por quê**: Performance, reduzir carga no banco
- **Como**:
  ```python
  from redis import Redis
  
  redis_client = Redis(host='redis', port=6379)
  
  @cache(expire=300)  # 5 minutos
  def get_produtos_ativos(tenant_id):
      ...
  ```
- **Benefícios**: Resposta 10x mais rápida, menos load no PostgreSQL

#### 7. **API de Webhooks Genérica**
- **O quê**: Permitir que tenants configurem webhooks para eventos
- **Por quê**: Integração com sistemas externos
- **Eventos sugeridos**:
  - `venda.criada`
  - `produto.estoque_minimo`
  - `conta.vencida`
- **Como**: Tabela `webhooks` + worker assíncrono

#### 8. **Testes Automatizados**
- **O quê**: Implementar testes unitários e de integração
- **Por quê**: Garantir qualidade, evitar regressões
- **Framework**: Pytest
- **Estrutura**:
  ```
  tests/
  ├── unit/
  │   ├── test_models.py
  │   ├── test_services.py
  │   └── test_utils.py
  └── integration/
      ├── test_auth.py
      ├── test_produtos.py
      └── test_vendas.py
  ```

#### 9. **Rate Limiting por Tenant**
- **O quê**: Limitar número de requisições por tenant por hora
- **Por quê**: Evitar abuso, garantir fair use
- **Como**: Implementar com Redis + decorator
  ```python
  @rate_limit(max_requests=1000, window=3600)  # 1000 req/hora
  def my_endpoint():
      ...
  ```

#### 10. **Soft Delete ao invés de DELETE físico**
- **O quê**: Adicionar coluna `deleted_at` em modelos principais
- **Por quê**: Recuperação de dados, auditoria
- **Como**:
  ```python
  class Produto(BaseTenantModel):
      deleted_at = Column(DateTime, nullable=True)
      
      @property
      def ativo(self):
          return self.deleted_at is None
  ```

#### 11. **Background Jobs com Celery**
- **O quê**: Processamento assíncrono de tarefas pesadas
- **Por quê**: Não bloquear requests HTTP
- **Casos de uso**:
  - Sincronização com Bling (lenta)
  - Envio de emails em massa
  - Geração de relatórios PDF
  - Processamento de NF-e grande

#### 12. **Versionamento de API**
- **O quê**: Adicionar `/v1/`, `/v2/` nas rotas
- **Por quê**: Breaking changes sem quebrar clientes antigos
- **Como**:
  ```python
  api_v1 = APIRouter(prefix="/v1")
  api_v2 = APIRouter(prefix="/v2")
  
  app.include_router(api_v1)
  app.include_router(api_v2)
  ```

### 🟢 BAIXA PRIORIDADE (Nice to Have)

#### 13. **GraphQL API**
- **O quê**: API GraphQL paralela à REST
- **Por quê**: Queries flexíveis, reduzir over-fetching
- **Framework**: Strawberry ou Graphene

#### 14. **Server-Sent Events (SSE) para Notificações**
- **O quê**: Push de notificações em tempo real
- **Por quê**: UX melhor que polling
- **Uso**: Notificar nova venda, estoque baixo, whatsapp

#### 15. **Multiidioma (i18n)**
- **O quê**: Suporte a múltiplos idiomas
- **Por quê**: Expansão internacional
- **Framework**: i18next (frontend), Babel (backend)

#### 16. **Tema Dark Mode**
- **O quê**: Alternância entre tema claro/escuro
- **Por quê**: Conforto visual, trend de UX
- **Como**: CSS variables + context

#### 17. **PWA (Progressive Web App)**
- **O quê**: Transformar frontend em PWA instalável
- **Por quê**: Uso offline limitado, ícone na home
- **Requisitos**: Service Worker, manifest.json

#### 18. **Exportação de Dados (LGPD)**
- **O quê**: Endpoint para exportar TODOS os dados do tenant
- **Por quê**: Conformidade com LGPD (portabilidade)
- **Formato**: JSON ou CSV

#### 19. **Analytics Interno**
- **O quê**: Dashboard de métricas de uso do sistema
- **Por quê**: Entender comportamento dos usuários
- **Métricas**: Tenants ativos, endpoints mais usados, erros

#### 20. **Módulo de Agendamentos (Agenda)**
- **O quê**: Sistema de agendamento de banho e tosa
- **Por quê**: Feature comum em pet shops
- **Recursos**: Calendário, notificações, recorrência

---

## 📊 Métricas de Qualidade do Código

### Backend
- **Cobertura de Testes**: 0% (não implementado)
- **Linhas de Código**: ~50.000 linhas (estimado)
- **Número de Rotas**: ~100+ endpoints
- **Média de Complexidade**: Média-Alta
- **Tech Debt Score**: ⚠️ Médio (migrations, consistência)

### Frontend
- **Cobertura de Testes**: 0% (não implementado)
- **Linhas de Código**: ~30.000 linhas (estimado)
- **Número de Componentes**: ~40 componentes
- **Bundle Size**: Não otimizado (sem code splitting)
- **Tech Debt Score**: ⚠️ Médio (estado global, propTypes)

---

## 🎓 Conclusão

O **Pet Shop ERP Multi-Tenant** é um sistema robusto e funcional, com arquitetura bem definida e features completas para gestão de pet shops. A escolha de FastAPI + React + PostgreSQL + Docker é adequada para o propósito.

**Pontos Fortes**:
- ✅ Arquitetura multi-tenant funcional
- ✅ Ampla gama de features (fiscal, PDV, financeiro, IA)
- ✅ Integrações com APIs externas bem estruturadas
- ✅ Docker Compose para múltiplos ambientes
- ✅ Interface responsiva com Tailwind

**Pontos de Atenção**:
- ⚠️ Segurança multi-tenant precisa de auditoria completa
- ⚠️ Falta de testes automatizados
- ⚠️ Migrations sem controle de versão adequado
- ⚠️ Inconsistências de nomenclatura causando bugs em runtime

**Recomendação de Priorização**:
1. Auditoria e correção de queries multi-tenant (SEGURANÇA)
2. Implementação de Alembic (ESTABILIDADE)
3. Padronização de código (MANUTENIBILIDADE)
4. Implementação de testes (QUALIDADE)
5. Cache e otimizações (PERFORMANCE)

Com as melhorias sugeridas implementadas, o sistema estará preparado para escalar e atender centenas ou milhares de tenants com segurança e performance.

---

**Documento gerado em**: 04 de Fevereiro de 2026  
**Versão do Sistema**: vdev (development)  
**Autor**: Análise automática baseada em código-fonte e sessão de debugging
