# 🐾 Sistema Pet Shop Pro v1.0.0 Enterprise

Sistema ERP completo para Pet Shops com PDV, estoque, produtos com variações, comissões, financeiro, IA integrada e muito mais.

## 🚀 Quick Start - 2 Ambientes Organizados

### 🔵 DESENVOLVIMENTO (Recomendado para programar)
**Use quando:** Desenvolver features, testar código, debug  
**Banco:** SQLite local (rápido, sem Docker)  
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

## 📋 Configuração de Ambientes

### Arquivos de Configuração
- **`.env.development`** - Desenvolvimento local (SQLite)
- **`.env.production`** - Produção com Docker (PostgreSQL + Backups)

### Docker Compose
- **`docker-compose.production.yml`** - Produção (dados reais)
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
