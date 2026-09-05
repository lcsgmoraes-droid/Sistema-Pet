# Conferência de caixa e alertas do gestor

A tela **Gestão → Alertas do gestor** (`/alertas-gestor`) reúne vendas finalizadas
ou parcialmente pagas com justificativa de margem, diferenças registradas entre
fechamento e abertura e sobras/faltas registradas no fechamento. Permite filtrar
por período (até 93 dias), tipo e operador, com paginação. O operador do fechamento
é quem o executou, mesmo quando outra pessoa abriu o caixa compartilhado.

O acesso exige `relatorios.gerencial` no frontend e no backend. Todas as consultas
são limitadas à empresa selecionada. Esta primeira versão é uma consulta para
conferência; não aprova justificativas nem altera os valores financeiros.

## Referência do fechamento

`data_fechamento`, um campo legado sem fuso, recebeu tanto horários locais como
UTC em encerramentos operacionais. Ordenar diretamente por esse campo podia
selecionar um caixa antigo. Exemplo reproduzido: um encerramento às 19h59 UTC
(16h59 em Brasília) aparecia depois de um fechamento às 17h58 de Brasília.

Os novos fechamentos gravam também `fechamento_em`, com fuso. A ordenação usa
esse instante e, nos registros antigos, `updated_at` (horário com fuso da gravação
do fechamento). O campo antigo não é reescrito. Não editar caixas fechados
legados por SQL sem considerar que `updated_at` ainda serve como referência.

Ao abrir, `conferencia_abertura` preserva caixa anterior, valor contado,
responsável, instante, abertura e diferença. Reabrir o caixa anterior não apaga
esse registro da abertura seguinte. O formulário mostra a referência consultada
e o servidor retorna 409 se ela tiver mudado antes de confirmar a abertura.

## Registros históricos

As aberturas antigas continuam mostrando a comparação gravada na observação,
com identificação de **comparação histórica**. Não se recalculam vínculos usando
a configuração atual de caixa compartilhado: ela pode ser diferente da vigente
na época. Uma referência incorreta antiga deve ser revisada como ocorrência
histórica, sem presumir falta de dinheiro do operador.

Sobras/faltas históricas mostram o saldo esperado gravado no fechamento. Os
novos resumos e fechamentos usam o mesmo cálculo do dinheiro físico: entradas e
suprimentos menos sangrias, despesas, transferências e devoluções em dinheiro.
PIX e cartão não entram na contagem física. Valores são comparados em centavos.

## Validação e entrega

- Testes de regressão em `backend/tests/unit/test_alertas_gestor_caixa.py` cobrem
  horários mistos, isolamento entre empresas, operadores, permissão, filtros,
  paginação, referência alterada e a sequência resumo → fechamento → abertura.
- Migration `zzi20260905a1` adiciona dois campos opcionais, sem alterar registros
  históricos; deve entrar antes de servir o backend atualizado.
- Aplicação em produção segue o fluxo oficial e depende da autorização do Lucas.

## Ficha de entrega — 2026-09-05

Responsável de negócio: Lucas. Executor: Codex. Prioridade P1. Risco médio:
altera a conferência financeira e adiciona campos ao banco. Domínios: caixa,
vendas e gestão. Entrega de backend e frontend pelo PR desta branch.

### 1. Necessidade e aceite

Selecionar o fechamento contado mais recente no escopo do caixa, preservar a
referência usada na abertura e oferecer consulta gerencial das três ocorrências.
Aceite: a sequência fictícia de fechamento 646,95 e abertura 647,45 resulta em
0,50, mesmo com encerramento legado gravado em UTC; filtros, paginação e
permissões funcionam. Não inclui aprovação de justificativas, notificações,
alteração retroativa de valores ou publicação mobile.

### 2. Regras e dados

Caixa é a origem da contagem; venda é a origem da justificativa. A nova referência
é imutável na abertura seguinte. O servidor rejeita referência desatualizada
com 409. A migration adiciona campos opcionais e não reescreve histórico.
Consultas mantêm o tenant explícito; o modo individual mantém o operador.

### 3. Arquitetura e integrações

Cálculo de dinheiro e referência ficam em `app/caixa/conferencia.py`; a consulta
gerencial usa os registros existentes, sem nova fila ou serviço externo. Evita-se
reconstruir vínculos antigos usando a configuração atual. A abertura mantém sua
idempotência existente. Falha de consulta impede confirmar uma referência não
carregada; o usuário pode tentar novamente.

### 4. Segurança e privacidade

Autenticação existente e permissão `relatorios.gerencial` nas duas camadas.
Exibe nomes dos operadores e valores somente para a gestão da empresa. Não cria
segredos, exportações ou nova retenção de dados pessoais. Diagnóstico operacional
deve registrar somente identificadores e valores necessários, sem tokens.

### 5. Qualidade

Em 2026-09-05, no código `5598c7097`, passaram os 17 testes de caixa/alertas e
os 7 testes de menu/contagem/listagem. `FLUXO_UNICO.bat release-check` passou:
lint, formatação, build, testes de raiz, 758 testes multiempresa, importação do
backend, auditorias de dependências e 58 testes mobile/typecheck. Sem mudanças
de dependências. A migration e a ordenação foram verificadas em PostgreSQL
local, em schema isolado com transação revertida.

### 6. Ambientes e homologação

Homologação técnica: Windows, Python da venv do projeto, SQLite nos testes e
PostgreSQL local na verificação da migration. Formulários e alertas foram
inspecionados no Chrome local com dados simulados: valores, filtros, justificativa,
vazio e erro. Configurações de teste usam banco descartável; nenhum dado de DEV
será enviado à produção. Este registro consolida a homologação técnica; não
representa teste funcional executado pelo usuário. Limitação aceita: comparações
históricas preservam a referência original e exigem revisão do gestor.

### 7. Publicação e rollback

Lucas autorizou a publicação neste atendimento. Aguardar conclusão do deploy
de estoque, integrar este PR após os checks e usar o launcher oficial, que
aplica `zzi20260905a1` antes de servir o backend novo. Validar commit público,
health, watchdog, migration e consulta somente leitura no tenant investigado.
Guardar commit anterior e backup operacional. Se necessário, reverter código
por PR e redeploy oficial, mantendo as colunas opcionais, compatíveis com o
backend anterior. Não realizar downgrade ou restauração automática do banco.

### 8. Sustentação

Auditoria e health seguem o fluxo operacional existente. Sucesso: referência
correta e consulta sem erro, com isolamento por empresa. Falha persistente de
health ou endpoint crítico impede considerar a publicação concluída. Em caso
de dúvida no histórico, conferir os valores contados sem atribuir falta ao
operador; divergência recorrente requer investigação da origem do horário.

### 9. Comunicação

Orientação ao gestor: acessar Gestão → Alertas do gestor, filtrar período e
operador e conferir o rótulo de comparação histórica. Este documento é o manual
da primeira versão. Comunicar disponibilidade a Lucas após validação em produção;
não é necessário treinamento adicional para esta consulta.

### 10. Fechamento técnico

Critérios, testes, tenant, permissões, histórico, documentação, homologação e
rollback revisados. Código aprovado tecnicamente; conclusão operacional depende
dos checks do PR e da validação após publicação. Nenhum segredo, backup, dump,
dependência local ou build é versionado.
