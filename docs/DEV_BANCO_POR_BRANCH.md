# Desenvolvimento local: um banco por linha de migrações

Branches diferentes podem ter migrações Alembic diferentes. O backend recusa subir quando o banco
está numa versão que o código não conhece ("Database migrations pending"). Por isso, em
desenvolvimento, cada linha de migrações usa o seu banco no mesmo Postgres do Docker:

| Branch | Banco | Como subir |
|---|---|---|
| `main` / `adm` | `petshop_adm` | `docker compose -f docker-compose.local-dev.yml -f docker-compose.adm.yml up -d backend` |
| `notificacoes` (CRM) | `petshop_dev` | `docker compose -f docker-compose.local-dev.yml up -d backend` |

`docker-compose.adm.yml` é local (não versionado): só troca o `DATABASE_URL` do backend para
`petshop_adm`. Para criar o banco a partir de outro: parar o backend e
`CREATE DATABASE petshop_adm TEMPLATE petshop_dev;` (depois ajustar as migrações com o código de
cada branch). Depois de trocar de branch, **reconstrua a imagem se o `requirements.txt` mudou** e
reinicie o backend: ele não recarrega sozinho.
