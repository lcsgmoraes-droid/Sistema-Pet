# OPS — Lojas, módulos e usuários

Tela de manutenção das lojas (tenants) para a equipe da plataforma. Substitui a necessidade de
descobrir "qual módulo esta loja tem" e "quem tem acesso" olhando banco ou várias telas.

## Menu do OPS (agrupado)

| Grupo | Tela | Para quê |
|---|---|---|
| Visão geral | Cockpit | Saúde e alertas |
| Clientes | **Lojas** (`/ops/lojas`) | Módulos, usuários, agrupamento, histórico |
| Clientes | Cobrança e implantação (`/ops/tenants`) | Planos, propostas, comprovantes, catálogo base |
| Saúde da plataforma | Incidentes, Observabilidade | Erros e lentidão |
| Desenvolvimento | Style Guide | Componentes |

## Lojas (`/ops/lojas`)

- Lista por **agrupamento**, com plano, situação, **usuários ativos/total**, **módulos ativos**
  (nomes) e **último acesso**. "Cobrança com problema" aparece em texto.
- **Abrir** leva ao detalhe `/ops/lojas/:id` com abas: Resumo (quem é, plano e cobrança,
  agrupamento e outras lojas do grupo, uso), Módulos (clicar ativa/desativa), Usuários (nome,
  acesso, perfil, situação, e-mail confirmado, último acesso) e Histórico.
- Módulo que vem do plano ou do teste grátis não se desliga na tela (a tela avisa).

## Histórico de alterações

Toda mudança feita pelo OPS fica em `ops_tenant_change_log` (quem, quando, valor anterior e novo):
módulos ligados/desligados, estado comercial (status, plano, cobrança, origem da assinatura) e
acompanhamento de implantação.

## API (somente administrador da plataforma)

`GET /admin/lojas` · `GET /admin/lojas/{id}` · `GET /admin/lojas/{id}/historico` ·
`GET /admin/lojas/historico` · `POST /admin/lojas/{id}/modulos/{modulo}/ativar|desativar`.
Todo o prefixo `/admin` passa pela camada de segurança para o token de administrador da
plataforma (`tenant_middleware.py`): tela nova do OPS não precisa ser cadastrada em lista.

## Código

Backend: `app/routes/ops_lojas_routes.py`, `app/services/ops_lojas_modulos_service.py`,
`app/services/ops_lojas_detalhe_service.py`, `app/services/ops_tenant_log_service.py`.
Frontend: `frontend/src/pages/ops-lojas/`.
