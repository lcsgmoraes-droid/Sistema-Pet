# ADR-0002 — Isolamento multiempresa em camadas

- Estado: Aceito
- Data: 2026-08-27
- Responsável: plataforma CorePet

## Contexto

Empresas diferentes compartilham a aplicação e o PostgreSQL. Uma falha de
filtro não pode permitir acesso cruzado a cadastros, vendas, estoque, finanças
ou configurações. Proteger apenas a interface ou lembrar manualmente de um
`tenant_id` em cada consulta não oferece defesa suficiente.

## Decisão

Aplicar defesa em profundidade:

1. autenticação seleciona explicitamente a empresa e emite sessão com tenant;
2. dependências do backend revalidam usuário, vínculo, sessão e permissão;
3. modelos e consultas carregam `tenant_id`;
4. a sessão do PostgreSQL recebe o contexto de tenant;
5. Row Level Security protege tabelas multiempresa elegíveis;
6. exceções globais são explícitas, restritas e auditadas;
7. migrations Alembic e testes multiempresa impedem dívida silenciosa.

PostgreSQL continua compartilhado enquanto essa estratégia atender segurança,
operação e custo. Banco por empresa não é requisito automático.

## Alternativas consideradas

- **Filtro apenas no frontend:** rejeitado; o cliente não é fronteira de
  segurança.
- **Filtro apenas na aplicação:** insuficiente sozinho; uma consulta esquecida
  pode atravessar empresas.
- **Banco dedicado por empresa agora:** adiado; aumenta provisionamento,
  migrations, backup e suporte sem necessidade comprovada para a faixa atual.

## Consequências

- Toda nova tabela precisa ser classificada como multiempresa ou global.
- SQL bruto, jobs e workers devem sincronizar o contexto antes de acessar dados.
- Rotas administrativas globais exigem autorização separada de plataforma.
- RLS não substitui testes de regra e permissão; as camadas se complementam.
- Uma futura migração para bancos dedicados permanece possível, mas exigirá
  estratégia própria de particionamento e operação.

## Gatilhos para revisão

- requisito contratual ou regulatório de isolamento físico;
- volume de um tenant prejudicar de forma recorrente os demais;
- manutenção ou restore seletivo se tornar inviável no banco compartilhado;
- custo de RLS/índices superar, por medição, os benefícios operacionais.

## Evidências relacionadas

- `docs/CONTRATO_MULTITENANT_E_ONBOARDING.md`
- `backend/app/tenancy/`
- `backend/tests/multi_tenant/`
- `backend/alembic/versions/`
