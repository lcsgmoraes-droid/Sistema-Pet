---
tipo: base
atualizado: 2026-09-12
---

# Tecnologias

Mapa das tecnologias confirmadas no repositório em 2026-09-12. Ver [[Arquitetura]] para como elas se conectam e [[README]] para o índice geral.

## Backend

| Tecnologia | Versão confirmada | Evidência |
|---|---|---|
| Python | 3.11 (imagem `python:3.11-slim`) | `backend/Dockerfile` |
| FastAPI | 0.137.2 | `backend/requirements.txt` |
| Starlette | 1.3.1 | `backend/requirements.txt` |
| Uvicorn | 0.49.0 | `backend/requirements.txt` |
| Pydantic / pydantic-settings | 2.13.4 / 2.14.2 | `backend/requirements.txt` |
| SQLAlchemy | 2.0.51 | `backend/requirements.txt` |
| Alembic | 1.18.4 | `backend/requirements.txt` |
| psycopg2-binary | 2.9.12 | `backend/requirements.txt` |
| PyJWT | 2.13.0 | `backend/requirements.txt` |
| passlib[bcrypt] / bcrypt | 1.7.4 / 4.1.2 | `backend/requirements.txt` |
| cryptography (Fernet) | via `cryptography` lib | `backend/app/security/tenant_config_crypto.py:9` |
| slowapi | 0.1.10 | `backend/requirements.txt`, uso parcial — ver [[API-Security]] |
| httpx / requests | 0.28.1 / 2.34.2 | `backend/requirements.txt` |
| boto3 | 1.43.32 | `backend/requirements.txt` (storage S3-compatível opcional) |
| pycryptodome | 3.23.0 | `backend/requirements.txt` — ⚠️ instalado, **sem uso confirmado no código** (grep por `Crypto.Cipher`/`import Crypto` não retornou nenhum arquivo). Ver [[Pendencias]]. |
| openai (SDK) | 2.43.0 | `backend/requirements.txt`, ver [[Integracoes]] |
| APScheduler | presente | usado por `campaigns/scheduler.py` e `schedulers/bling_sync_scheduler.py` |
| Redis (`redis.asyncio`) | opcional | `backend/app/cache/cache_manager.py` — só ativa se `REDIS_URL` setada; senão cache em memória |
| Celery / Kombu | no `requirements.txt` | ⚠️ **não usado de fato** — todas as referências no código são comentários/TODO. Fila real é implementada em tabelas Postgres com `SELECT FOR UPDATE SKIP LOCKED`. Ver [[Arquitetura#Processamento fora da requisição]] |

## Frontend web

| Tecnologia | Versão confirmada | Evidência |
|---|---|---|
| React / React DOM | 18.2.0 | `frontend/package.json` |
| Vite | 8.0.16 | `frontend/package.json` |
| React Router | 7.18.1 | `frontend/package.json` |
| Tailwind CSS | 3.4.0 | `frontend/package.json` |
| Zustand | 5.0.11 | usado apenas em `frontend/src/stores/whatsappStore.ts` — ver [[Funcionalidades]] |
| axios | 1.16.1 | `frontend/src/api.js` |
| socket.io-client | 4.8.3 | atendimento WhatsApp em tempo real |
| recharts | 3.8.1 | dashboards/relatórios |
| ESLint / Prettier / TypeScript | 10.5.0 / 3.8.4 / 6.0.3 | qualidade de código, parcialmente TS (projeto é majoritariamente `.jsx`) |

⚠️ **Requisito de runtime**: Vite 8 exige Node `^20.19.0 || >=22.12.0`. Confirmado em execução real nesta sessão: Node 20.18.2 quebra a instalação do binário nativo do Rolldown (`Cannot find native binding`). `.nvmrc`/`.node-version` do repositório pedem Node 22.

## Aplicativo mobile

| Tecnologia | Versão confirmada | Evidência |
|---|---|---|
| React Native | 0.86.0 | `app-mobile/package.json` |
| Expo | ^57.0.4 | `app-mobile/package.json` |
| React | 19.2.3 | `app-mobile/package.json` (versão diferente da usada no frontend web, 18.2.0) |
| React Navigation | 6.x | `app-mobile/package.json` |
| Zustand | 5.0.2 | `app-mobile/package.json` |
| EAS (build/update) | via `eas.json` | pipeline de release nativo/OTA, ver [[CI-CD]] |

## Banco de dados

| Item | Confirmado | Evidência |
|---|---|---|
| SGBD | PostgreSQL 16 (dev) | `docker-compose.local-dev.yml` |
| ORM | SQLAlchemy 2.0 | ver [[Banco-de-Dados]] |
| Migrations | Alembic, 317 arquivos | `backend/alembic/versions/` |
| Isolamento multiempresa | Row Level Security + filtro automático no ORM | ver [[Banco-de-Dados#Multi-tenancy e isolamento]] e [[Autorizacao]] |

## Infraestrutura e execução

| Item | Confirmado | Evidência |
|---|---|---|
| Containerização | Docker + Docker Compose (perfis `local-dev`, `homolog`, `prod`, `whatsapp-pilot`) | arquivos `docker-compose.*.yml` na raiz |
| Proxy/HTTPS | Nginx | `nginx/`, `docker-compose.prod.yml` |
| Orquestração além de Compose | ⚠️ **Não identificado no código analisado.** Não há Kubernetes/Helm no repositório. | — |
| CI | GitHub Actions, 8 workflows | ver [[CI-CD]] |
| Hospedagem de produção | servidor único acessado via SSH (`petdeploy@corepet.com.br`) | `docs/PRODUCAO_DEPLOY_SSH.md` |

## Serviços externos (visão rápida — detalhe em [[Integracoes]])

Bling, Stone, Mercado Pago, SEFAZ/IntNFe, iFood, WhatsApp (WAHA + 360dialog + n8n), OpenAI (+ Groq/Google AI como providers alternativos), Google Maps, Asaas (billing SaaS), EcommerceAI, e-mail SMTP, Expo Push, storage S3-compatível.

## Não identificado

- ❓ Se há alguma camada de observabilidade externa (APM, Sentry, Datadog) além dos logs estruturados e painel Ops internos — necessita validação com o responsável.
- ❓ Versão exata do PostgreSQL em produção (o dev usa 16; produção não foi auditada nesta rodada).
