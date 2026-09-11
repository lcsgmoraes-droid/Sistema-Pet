# Ativação fiscal, CSC e numeração com a IntNFe

Data: 2026-09-09. Situação: implementação para desenvolvimento; homologação do fluxo CorePet pendente.

## Fluxo para o usuário

O usuário cria a empresa no CorePet normalmente. Quando desejar preparar a
emissão, acessa **Configurações → Integrações → IntNFe** e escolhe **Ativar emissão
em teste**. O cadastro inicial da conta não depende da disponibilidade do emissor.

1. O CorePet confere CNPJ, razão social e nome fantasia nos dados da empresa.
2. Consulta os emitentes da conta do integrador e cria o cadastro quando cabível.
3. Salva as credenciais do emitente com criptografia e verifica o certificado A1.
4. Mostra a situação e as pendências. Com vínculo válido, disponibiliza CSC e
   numeração separados por modelo, série e ambiente. Não emite uma nota nesta etapa.

Um cadastro encontrado pelo CNPJ exige comprovação de acesso com `clientId` e
`clientSecret` **do emitente**. A tela não recebe os códigos do integrador. O
CorePet confere o cadastro na conta do integrador e autentica essas credenciais
antes de associá-las à empresa. Não há rotação automática de segredo.

## Habilitar em desenvolvimento

- Aplicar a migration `zzn20260909a1`, posterior a `zzm20260909a1`, antes de iniciar
  a versão do backend que disponibiliza a tela. Ela acrescenta somente
  `intnfe_connections`; não altera vendas, estoque ou financeiro.
- Configurar no ambiente seguro do **backend**, nunca em variável `VITE_*`:
  `INTNFE_ACTIVATION_ENABLED=true`, `INTNFE_ACTIVATION_TENANT_IDS` com os UUIDs
  liberados no piloto (separados por vírgula), `INTNFE_INTEGRADOR_ID` e
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
| `GET /intnfe/numeracao` | Consulta as sequências do emitente da empresa autenticada. |
| `PUT /intnfe/numeracao` | Avança uma sequência de NF-e ou NFC-e após nova consulta, auditoria e confirmação por leitura. |
| `GET /intnfe/csc` | Consulta separadamente homologação e produção, informando presença e ID; o segredo nunca retorna. |
| `PUT /intnfe/csc` | Grava o CSC do ambiente escolhido após consulta, revisão explícita e auditoria sem o segredo. |

As rotas usam exclusivamente a empresa da sessão autenticada. Não aceitam um
tenant ou CNPJ arbitrário como destino. A resposta contém mensagem, etapas,
pendências e ações possíveis; nunca credenciais/tokens. `emissao_disponivel` é
sempre `false` e `ambiente` na resposta de ativação é `homologacao`. A numeração tem
seleção explícita de ambiente independente dessa resposta. Mesmo `certificado_validado` não libera
emissão. Erros de validação do formulário não reproduzem o corpo com o segredo.

A identidade vem de `Tenant`: `cnpj`, `razao_social` e `name`. O vínculo guarda
uma fotografia desses dados e os identificadores da IntNFe. A troca posterior do
CNPJ ou da conta do integrador exige revisão de suporte; não reaproveita segredos
de outra empresa. Nomes corrigidos são considerados numa nova tentativa após uma
recusa confirmada, antes de existir vínculo.

## Numeração por modelo, série e ambiente

Em **Configurações → Integrações → IntNFe → Numeração fiscal**, o usuário consulta
o último número alcançado e o próximo número de cada série. Escolhe NF-e (55) ou
NFC-e (65), homologação (padrão) ou produção, informa a série e o **próximo número
desejado**, revisa os valores anterior/novo e confirma. Produção tem indicação
própria na revisão. Lucas autorizou os dois ambientes para esta configuração;
isso não libera emissão.

Exemplo: para continuar com a NF-e 4.501, o formulário recebe `4501` e o backend
envia `ultimoNumero: 4500`. Se uma série ainda não existe e começará no 1, não há
ajuste a enviar. A operação configura a sequência no emissor; não escolhe a série
padrão de futuras vendas e não representa consulta ao histórico completo da SEFAZ
ou sincronização automática com o Bling.

Contrato interno de escrita, sem tenant/CNPJ/credenciais no corpo:

```json
{
  "serie": "3",
  "ambiente_codigo": 2,
  "modelo": 55,
  "proximo_numero": 4501,
  "ultimo_numero_consultado": 1
}
```

O backend utiliza **GET e PUT `/integrador/emitentes/{tenantId}/numeracao`** com
token do integrador, após verificar o vínculo remoto pelo CNPJ e pelos IDs
armazenados para a empresa autenticada. Envia `serie`, `ultimoNumero`,
`ambienteCodigo` e `modelo` explicitamente. NF-e e NFC-e aparecem no mesmo cartão,
mas cada combinação mantém a sua própria sequência. Não há nova tabela/migration;
a IntNFe é a fonte da sequência.

- Série de 0 a 889, normalizada (`003` e `3` identificam a mesma série).
- Próximo número inteiro de 1 a 999.999.999. Bloqueia repetição e retrocesso.
- A combinação emitente/modelo/ambiente/série identifica a sequência; produção
  e homologação são independentes.
- Nova consulta antes do PUT compara o valor da tela com o atual. Divergência
  retorna `409 NumeracaoAlterada`; o usuário consulta e revisa novamente.
- A garantia monotônica da IntNFe resolve a corrida entre consulta e escrita.
  Não há compare-and-set documentado: uma emissão simultânea ainda pode avançar
  o número depois da consulta. O GET posterior exibe o valor atual, mesmo maior
  que o solicitado; não promete reservar esse número para uma venda.
- `422 NumeracaoRetrocede` e `404` exigem consultar a sequência ou o vínculo.
  Timeout, resposta de sucesso inválida ou falha na leitura posterior deixam o
  resultado incerto; não há repetição automática do PUT. Após qualquer falha de
  escrita, a tela descarta a consulta anterior e exige GET antes de nova revisão.
- Auditoria `intnfe_numeracao`: usuário/empresa, série/ambiente/modelo, último
  valor consultado, ajuste solicitado, resultado e correlação, sem segredos.
  A solicitação é gravada antes do PUT; falha de auditoria nesse ponto impede o
  envio. Se a gravação do resultado falhar, é necessário consultar para conciliar.
- A troca de empresa desmonta o formulário e descarta a revisão anterior.

No reteste de 11/09, o GET externo passou a devolver `modelo: null` em todas as
linhas, contrariando o exemplo e a separação por modelo descritos na documentação.
O CorePet recusa essa resposta em vez de exibir uma série ambígua como NF-e ou
NFC-e. Nenhum PUT real foi feito por esta tela; as escritas continuam validadas
por testes simulados até a IntNFe voltar a identificar cada linha com 55 ou 65.

## CSC da NFC-e

O CSC é obtido pelo contribuinte na SEFAZ da UF. Em São Paulo, o acesso oficial
fica em **NFC-e → Serviços → Gerenciar Código de Segurança (ambiente de testes)**
e exige o certificado digital da empresa. O CorePet consulta e grava o CSC pela
IntNFe sem persistir o segredo localmente nem incluí-lo em auditoria.

O contrato atualizado da IntNFe separa os CSCs. O PUT recebe
`ambienteCodigo: 1|2`; o GET devolve presença e ID de homologação e produção em
campos distintos. O CorePet mostra os dois estados, exige a escolha explícita do
ambiente e confirma por nova leitura que o ambiente oposto permaneceu inalterado.

No piloto da LJ, o CSC de homologação legado apareceu como ausente após a mudança
do contrato. O mesmo valor protegido foi recadastrado com `ambienteCodigo: 2`;
o PUT respondeu 204, o GET confirmou apenas homologação e uma NFC-e foi autorizada.
A equipe IntNFe precisa confirmar se os cadastros anteriores serão migrados.

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
   retornou 539 (duplicidade), sem repetir os erros de XML. Lucas sugeriu outra
   série: alterando somente para série 3, a nota 1/003 foi autorizada, com
   protocolo e XML conferidos. A reconsulta do DANFE em 10/09 às 00:02 confirmou
   produtos 199,00, desconto 127,77, total 71,23, quantidade 1, valor unitário
   199,0000 e frete 9 - Sem frete, coerentes com o XML. Visualmente o A4 cabe em
   uma folha, sem cortes internos ou sobreposições. Restam declarar A4 no CSS,
   manter margem segura para impressoras e eliminar a página em branco que surge
   quando o navegador usa papel Carta. Conciliar a série 001 antes de reutilizá-la.
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
