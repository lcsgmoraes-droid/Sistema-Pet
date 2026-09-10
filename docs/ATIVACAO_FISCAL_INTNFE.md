# Ativação fiscal opcional com a IntNFe

Data: 2026-09-09. Situação: implementação para desenvolvimento; homologação real pendente.

## Fluxo para o usuário

O usuário cria a empresa no CorePet normalmente. Quando desejar preparar a
emissão, acessa **Configurações → Integrações → IntNFe** e escolhe **Ativar emissão
em teste**. O cadastro inicial da conta não depende da disponibilidade do emissor.

1. O CorePet confere CNPJ, razão social e nome fantasia nos dados da empresa.
2. Consulta os emitentes da conta do integrador e cria o cadastro quando cabível.
3. Salva as credenciais do emitente com criptografia e verifica o certificado A1.
4. Mostra a situação e as pendências. Não emite uma nota nesta etapa.

Um cadastro encontrado pelo CNPJ exige comprovação de acesso com `clientId` e
`clientSecret` **do emitente**. A tela não recebe os códigos do integrador. O
CorePet confere o cadastro na conta do integrador e autentica essas credenciais
antes de associá-las à empresa. Não há rotação automática de segredo.

## Habilitar em desenvolvimento

- Aplicar a migration `zzn20260909a1`, posterior a `zzm20260909a1`, antes de iniciar
  a versão do backend que disponibiliza a tela. Ela acrescenta somente
  `intnfe_connections`; não altera vendas, estoque ou financeiro.
- Configurar no ambiente seguro do **backend**, nunca em variável `VITE_*`:
  `INTNFE_ACTIVATION_ENABLED=true`, `INTNFE_INTEGRADOR_ID` e
  `INTNFE_INTEGRADOR_SECRET`.
- Manter `PAYMENT_CONFIG_ENCRYPTION_KEY` estável e protegida. A integração usa o
  mecanismo existente de criptografia das configurações por empresa. Produção
  exige uma chave configurada; a perda/troca sem migração torna os segredos antigos
  ilegíveis. Não substituir uma chave já utilizada por outras integrações.
- O Compose local lê o `.env.local`; o Compose de produção declara explicitamente as
  três novas variáveis, desligadas/vazias por padrão. A chave de criptografia já
  era declarada. Nenhum valor real foi versionado ou habilitado nesta entrega.
- Utilizar o fluxo local `FLUXO_UNICO.bat dev-up` e uma empresa autorizada para o
  piloto. O módulo `integracoes` e a permissão `configuracoes.editar` são exigidos.

O estado padrão é desabilitado. A liberação em produção exige a autorização e o
fluxo de publicação do repositório, além da homologação abaixo.

## Contrato interno

| Rota | Finalidade |
|---|---|
| `GET /intnfe/status` | Consulta local da situação, sem contato com a IntNFe. |
| `POST /intnfe/ativar` | Consulta o vínculo e, se seguro, cria o emitente. |
| `POST /intnfe/consultar` | Consulta o emissor/certificado; nunca cria emitente remoto. |
| `POST /intnfe/vincular` | Recebe `client_id` e `client_secret` para comprovar acesso a um cadastro existente. |

As rotas usam exclusivamente a empresa da sessão autenticada. Não aceitam um
tenant ou CNPJ arbitrário como destino. A resposta contém mensagem, etapas,
pendências e ações possíveis; nunca credenciais/tokens. `emissao_disponivel` é
sempre `false` e `ambiente` é `homologacao`. Mesmo `certificado_validado` não libera
emissão. Erros de validação do formulário não reproduzem o corpo com o segredo.

A identidade vem de `Tenant`: `cnpj`, `razao_social` e `name`. O vínculo guarda
uma fotografia desses dados e os identificadores da IntNFe. A troca posterior do
CNPJ ou da conta do integrador exige revisão de suporte; não reaproveita segredos
de outra empresa. Nomes corrigidos são considerados numa nova tentativa após uma
recusa confirmada, antes de existir vínculo.

## Falhas e recuperação

| Situação | Comportamento e ação |
|---|---|
| Dados incompletos | Nenhuma criação externa; corrigir dados da empresa. |
| `cnpj_em_uso` / HTTP 409 | Mostrar conflito e protocolo; equipe IntNFe confere o registro. Depois da correção, nova tentativa manual. |
| `credenciais_pendentes` | Solicitar os códigos do emitente e verificar acesso. CNPJ sozinho não comprova posse. |
| Timeout, HTTP 5xx ou resposta de criação inválida | Marcar `conciliacao_pendente`. Consultar antes de qualquer nova criação; não repetir o POST automaticamente, mesmo que a lista esteja vazia. |
| Resultado da criação nunca confirmado | Suporte deve reconciliar com a IntNFe. Não apagar a reserva local nem zerar indicadores para forçar uma repetição. |
| `emitente_inativo` / `vinculo_inconsistente` | Revisão de suporte; não criar substituto automaticamente. |
| Falha após salvar credenciais | Consultar novamente. O segredo retornado uma única vez permanece armazenado. |
| `certificado_pendente` / `certificado_invalido` | Cadastrar/corrigir o A1 no emissor e consultar novamente. |

As chamadas têm timeout de 3 segundos para conexão e 15 segundos para leitura,
sem retry automático e sem seguir redirecionamentos. A URL externa é fixa:
`https://api.intnfe.com.br`. A criação remota não tem idempotência documentada;
não reutilizamos a garantia de idempotência das rotas de notas para esse cadastro.

A reserva local é gravada antes do POST. Bloqueio da linha da empresa,
unicidade por tenant/CNPJ/emitente e uma operação com validade de 120 segundos
protegem cliques simultâneos. Uma operação antiga não pode sobrescrever a nova.
Após expirar a reserva, uma criação sem confirmação continua bloqueada para
repetição; a expiração permite consultar/reconciliar.

## Segurança e evidências

- Filtro de tenant no ORM, filtros explícitos e RLS obrigatória na tabela do
  PostgreSQL. A aplicação deve usar o contexto de tenant e o papel sem bypass
  já previstos na infraestrutura.
- Segredos cifrados; tokens apenas durante a requisição. Auditoria registra
  usuário, empresa, ação, estado, código e protocolo, sem payload sensível.
- O cadastro envia somente CNPJ, razão social e nome fantasia à IntNFe. Não há
  envio de dados de clientes, itens, certificado ou senha do certificado nesta etapa.
- Testes de API/serviço usam dados fictícios e respostas simuladas, sem acesso
  às credenciais ou à conta real.

Validação desta entrega e limites estão na
[ficha de entrega](entregas/2026-09-09-ativacao-fiscal-intnfe.md).

## Próximas etapas do piloto

1. Vincular a conta DEV autorizada ao emitente real já criado para a LJ, sob
   **CorePet — Lucas Guerra**. O conflito de CNPJ foi superado e a autenticação
   própria do emitente foi confirmada; credenciais permanecem protegidas localmente.
2. Concluir o teste do fluxo completo na conta DEV autorizada. A migration,
   o isolamento RLS e reservas simultâneas já passaram no PostgreSQL descartável;
   as migrations também foram aplicadas no DEV local.
3. A1 já enviado e reconhecido no piloto direto de API: CNPJ correto, HTTP 200,
   válido até 02/04/2027. Conferir esse estado também no fluxo integrado DEV.
4. A primeira NF-e direta, com um item e total de R$ 71,23, recebeu HTTP 202 e
   tornou-se a nota 1/001 em homologação. O resultado foi rejeição `SCHEMA` nos
   grupos ICMS-ST e PIS/COFINS. No reteste com o mesmo JSON, a nota 2/001
   retornou 539 (duplicidade), sem repetir os erros de XML. Reconciliar a
   numeração de homologação antes de novo envio. Autorização, XML e DANFE
   seguem pendentes; a chave gerada na rejeição não comprova autorização.
   [Diagnóstico](DIAGNOSTICO_INTNFE_NFE_HOMOLOGACAO_2026-09-09.md)
   e [registro do piloto](FISCAL_INTNFE_PILOTO_HOMOLOGACAO.md).

Upload de A1 dentro do CorePet, emissão pelo PDV, cadastro/sincronização de
destinatários, eventos, webhooks, XML/DANFE e passagem para produção são etapas
posteriores. O presente vínculo não depende da implementação completa dessas etapas.

O cadastro de origem do CorePet ainda trabalha com CNPJ numérico. A documentação
atual da IntNFe também aceita CNPJ alfanumérico; ampliar o cadastro e a validação
de ponta a ponta é uma pendência para esse cenário, sem bloquear o CNPJ do piloto.

Fonte do contrato consultado: [documentação oficial IntNFe](https://intnfe.com.br/api/doc).
Os resultados do acesso real anterior continuam registrados no roteiro do piloto.
