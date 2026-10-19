# Ficha de entrega — Cashback e contatos

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Prioridade | P2 |
| Risco | Médio: saldo financeiro consultado e histórico com dados pessoais |
| Domínios | Campanhas, clientes e relacionamento |

## 1. Necessidade e requisitos

O Gestor já lista clientes ativos com saldo positivo, com limite de registros,
mas não permite acompanhar as conversas de incentivo ao uso do cashback.
A nova área `/campanhas/cashback-crm` reúne todos os clientes com saldo
disponível, inclusive cadastros inativos identificados na lista, com paginação,
busca, status e filtro de retornos pendentes.

O operador pode editar um modelo de mensagem na sessão, personalizar o texto
para cada cliente, abrir o WhatsApp e registrar status, observações e a data do
próximo contato. O histórico identifica mensagem, autor, data e saldo na ocasião.

Critérios de aceite: saldo vencido não aparece como disponível; filtros e
paginação alcançam toda a lista; cada abertura gera um registro; repetição da
mesma requisição não duplica o registro; alterações de status preservam eventos
anteriores; outra empresa não pode acessar esses dados.

O cálculo do cashback, as campanhas, os relatórios existentes e o aplicativo
mobile continuam com as regras atuais. Envio automático e leitura de conversas
do WhatsApp não fazem parte desta entrega.

## 2. Regras de negócio e dados

- Saldo disponível vem do replay oficial da carteira, respeitando vencimento,
  consumo e estorno; a tela não gera nem utiliza créditos.
- Contatos são eventos por cliente e empresa, sem edição ou exclusão pela tela.
- A abertura é registrada como conversa aberta, sem confirmar envio ou leitura.
- Status de envio, interesse e conclusão são informações manuais do operador.
- Abrir outra conversa preserva o acompanhamento já existente e sua agenda.
- O bloqueio de contato e as preferências de marketing existentes são conferidos
  novamente na API antes da abertura.
- Histórico e acompanhamento permanecem consultáveis pela API após zerar o saldo.
- Uma migration aditiva cria a tabela de contatos, índices, chave de idempotência
  e isolamento RLS no PostgreSQL.

## 3. Arquitetura e integrações

Frontend usa componentes V2 e o cliente HTTP oficial. Backend separa modelo,
serviço e rotas dentro de `backend/app/campaigns/`. A listagem carrega as carteiras
em lote e pagina o resultado calculado, evitando uma consulta de saldo por pessoa.

As rotas ficam em `/campanhas/cashback/clientes`, com consultas de lista/histórico
e gravações de abertura/acompanhamento. UUID identifica cada tentativa de gravação.
O navegador abre uma aba vazia no clique e só navega para o WhatsApp após a API
salvar o registro. Falha ao salvar fecha a aba; popup bloqueado não grava contato.

## 4. Segurança e privacidade

Autenticação, permissões de clientes, filtros explícitos de empresa e RLS
protegem consultas e gravações. Nenhuma credencial nova é necessária. Nome,
telefone, mensagem e observação são dados pessoais de relacionamento e devem
ficar na empresa correspondente; não devem ser impressos em logs de diagnóstico.
O texto aparece escapado pelo React. A retenção segue os controles existentes
de dados de clientes; não há descarte automático novo.

## 5. Desenvolvimento e qualidade

Fatias: consulta da carteira e persistência; rotas e validações; tela e navegação;
testes, revisão independente, build e documentação.

Testes previstos: vencimentos/estornos, busca/paginação, isolamento, preferências
de contato, telefone inválido, repetição de requisição, status/agenda e falhas ao
abrir o WhatsApp. Foram aprovados 17 testes novos de backend, 37 regressões e
14 testes de frontend. Ruff, ESLint, Prettier, build e revisão do diff passaram.

## 6. Ambientes e homologação

Testes automatizados usaram dados fictícios em SQLite e bancos PostgreSQL
descartáveis. Os três caminhos oficiais de migration e cinco cenários RLS com
usuário sem privilégios administrativos passaram. O ambiente DEV subiu pelo
fluxo oficial. A revisão visual no Chrome usou componentes reais e uma API
simulada isolada, incluindo edição de status, nota e histórico, sem enviar
mensagens. Depois, o sistema completo em `127.0.0.1:18080` foi reconstruído pelo
script de homologação, preservando dados anteriores e a sessão autenticada.
Três clientes fictícios CRM-DEMO permitem experimentar a tela; listagem,
histórico, mudança de status e nota foram aprovados com API/PostgreSQL reais.
O aceite de Lucas permanece pendente.

Evidências e limites: `docs/homologacoes/2026-10-19-cashback-crm.md`.

## 7. Publicação e rollback

Entrega web e backend, com migration aplicada antes do backend atualizado.
Publicação depende do fluxo oficial e de autorização de produção separada.
Após publicar: conferir a lista, saldo conhecido e histórico com cliente de teste.
Reverter o código remove a área; preservar a tabela em rollback operacional
mantém o histórico. Downgrade remove os contatos e exige preservação prévia dos
registros se já houver uso real. Nenhum saldo é alterado pelo rollback.

## 8. Observabilidade e sustentação

O histórico permite conferir quem iniciou cada contato e o acompanhamento.
Erros da API aparecem na tela, sem navegação silenciosa para o WhatsApp.
Falhas de acesso ou persistência devem ser diagnosticadas pelo identificador
da requisição e logs existentes, sem copiar mensagens ou telefones para logs.
Enquanto houver falha, a consulta de benefícios do Gestor continua disponível.

## 9. Mudança, comunicação e treinamento

Entrada no submenu de Campanhas e aba Cashback e contatos. A equipe deve
revisar o texto antes de abrir o WhatsApp, concluir o envio naquele aplicativo
e atualizar o status no CorePet. Data de retorno organiza a próxima abordagem.
O guia de Campanhas documenta esse fluxo; não exige atualização do app mobile.

## 10. Fechamento

- [x] Critérios técnicos de aceite testados.
- [x] Testes e evidências registrados.
- [x] Tenant, permissões, dados e auditoria preservados.
- [x] Guia de Campanhas atualizado.
- [x] Publicação, observabilidade e rollback definidos.
- [x] Comunicação e treinamento avaliados.
- [x] Diff revisado sem arquivos locais ou segredos.
- [ ] Aceite de negócio por Lucas e publicação autorizada.

Decisão técnica: aprovado com os limites de homologação registrados. Produção
não autorizada por esta ficha.
