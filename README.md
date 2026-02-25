# 🐾 Sistema Pet Shop Pro v1.0.0 Enterprise

Sistema ERP completo para Pet Shops com PDV, estoque, produtos com variações, comissões, financeiro, IA integrada e muito mais.

## 🚀 Quick Start - 2 Ambientes Organizados

### 🔵 DESENVOLVIMENTO (Recomendado para programar)
**Use quando:** Desenvolver features, testar código, debug  
**Banco:** PostgreSQL DEV no Docker (`petshop_dev` em `localhost:5433`)  
**Como iniciar:**
```bash
INICIAR_DEV.bat
```
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Docs: http://localhost:8000/docs

### 🟢 PRODUÇÃO (Dados reais)
**Use quando:** Operar a loja com dados reais  
**Banco:** PostgreSQL no Docker (com backup automático)  
**Como iniciar:**
```bash
INICIAR_PRODUCAO.bat
```
- Backend: http://localhost:8000
- Backups: Automáticos a cada 6h em `./backups/`
- **⚠️ CUIDADO: Dados reais!**

### 🧭 Rotina simples (sem decorar Docker)
Use sempre estes atalhos na raiz do projeto:

- `INICIAR_PRODUCAO.bat` → sobe produção sem rebuild pesado
- `REBUILD_BACKEND.bat` → só rebuild do backend (mudou API/Python)
- `REBUILD_FRONTEND.bat` → só rebuild do frontend (mudou React/PDV)
- `STATUS_PRODUCAO.bat` → mostra status dos containers + memória do host
- `PARAR_PRODUCAO.bat` → para tudo com segurança

Regra prática para ficar rápido:
1. Mudou só frontend? rode `REBUILD_FRONTEND.bat`
2. Mudou só backend? rode `REBUILD_BACKEND.bat`
3. Só reiniciar ambiente? rode `INICIAR_PRODUCAO.bat`
4. Só use rebuild total quando for realmente necessário

Observação: no primeiro uso local, o script gera automaticamente certificado em `nginx/ssl` para evitar reinício contínuo do nginx.

## ✅ Fluxo Único Oficial (DEV -> PROD sem perder nada)

Para evitar divergência entre desenvolvimento e produção, use **sempre este trilho**:

1. Rodar validação estrutural do repositório:
```bash
FLUXO_UNICO.bat check
```

2. Trabalhar e testar no DEV:
```bash
FLUXO_UNICO.bat dev-up
```

3. Antes de subir produção, validar release:
```bash
FLUXO_UNICO.bat release-check
```

4. Subir produção pelo caminho seguro:
```bash
FLUXO_UNICO.bat prod-up
```

5. Verificar status:
```bash
FLUXO_UNICO.bat status
```

Documentação detalhada do processo: `docs/FLUXO_UNICO_DEV_PROD.md`.

## 📋 Configuração de Ambientes

### Arquivos de Configuração
- **`.env.development`** - Desenvolvimento local oficial (`petshop_dev` em `localhost:5433`)
- **`.env.production`** - Produção com Docker (PostgreSQL + Backups)

### Docker Compose
- **`docker-compose.local-dev.yml`** - Desenvolvimento oficial
- **`docker-compose.prod.yml`** - Produção (dados reais)
- ~~`docker-compose.yml`~~ - Antigo (não usar)
- ~~`docker-compose.staging.yml`~~ - Antigo (não usar)
- ~~`docker-compose.local-prod.yml`~~ - Antigo (não usar)

### ⚠️ IMPORTANTE - Segurança
Antes de usar PRODUÇÃO, edite `.env.production`:
1. Mude `POSTGRES_PASSWORD` para senha forte
2. Gere novo `JWT_SECRET_KEY` com: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
3. Mude `ADMIN_TOKEN` para algo único
4. Configure suas APIs (Google Maps, OpenAI, Bling, Stone)

## 📋 Status Atual

✅ **Sprint 2 - Produtos com Variação CONCLUÍDO**
- Sistema de variações implementado
- Frontend e backend integrados
- Validações e constraints aplicadas
- Documentação completa

## 📁 Estrutura

```
Sistema Pet/
├── backend/          # FastAPI + SQLAlchemy + PostgreSQL
├── frontend/         # React 19 + Vite + TailwindCSS
├── arquivo_documentacao/  # 244 arquivos MD históricos
├── arquivo_testes/        # 5 arquivos de teste
├── arquivo_scripts/       # Scripts temporários
└── backup_sistema_YYYYMMDD_HHMMSS/  # Backups completos
```

## 🎯 Funcionalidades

- ✅ Autenticação JWT Multi-Tenant
- ✅ CRUD Produtos com Variações
- ✅ PDV (Ponto de Venda)
- ✅ Controle de Estoque
- ✅ Gestão de Clientes e Pets
- ✅ Sistema de Comissões
- ✅ Financeiro Completo
- ✅ Dashboard Gerencial
- ✅ IA Integrada (OpenAI/Groq/Gemini)
- ✅ Integração Bling
- ✅ Relatórios e Analytics

## 📚 Documentação

Toda a documentação detalhada está em:
```
backup_sistema_20260127_032250/
├── DOCUMENTACAO_COMPLETA_SISTEMA.md (LEIA PRIMEIRO!)
└── INDICE_BACKUP.md
```

## 🔧 Tecnologias

**Backend:** Python 3.11 · FastAPI · SQLAlchemy · PostgreSQL · Alembic  
**Frontend:** React 19 · Vite · TailwindCSS · Axios  
**IA:** OpenAI · Groq · Gemini  
**Infra:** Docker · Uvicorn · APScheduler

## 📦 Últimos Backups

- `backup_sistema_20260127_032250/` - Sprint 2 COMPLETO
- Todos os backups contêm documentação completa

## 🆘 Suporte

Consulte `DOCUMENTACAO_COMPLETA_SISTEMA.md` no backup mais recente para:
- Arquitetura completa
- Guia de instalação
- Troubleshooting
- Referência de API
- Próximos passos

---

**Desenvolvido por Lucas** | Janeiro 2026 | v1.0.0 Enterprise
