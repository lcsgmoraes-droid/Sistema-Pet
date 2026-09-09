# IntNFe — primeiro teste de NF-e de produto

Registro: 09/09/2026. Situação: acesso ao portal confirmado; cadastro pela API e envio ainda não realizados.

## Decisão registrada

Lucas informou que seu irmão está avançando no desenvolvimento da IntNFe e considera as dúvidas anteriores, em sua maioria, trabalho futuro orientado pelos testes preliminares. Lucas fará o teste. O objetivo imediato é conseguir acesso, cadastrar/vincular uma empresa e um destinatário de teste e tentar emitir uma NF-e simples de produto.

O [estudo do Bling e da estrutura fiscal do CorePet](ESTUDO_BLING_E_ESTRUTURA_FISCAL_COREPET.md) fica preservado como planejamento. A construção completa desse módulo não é condição para testar diretamente a IntNFe. O primeiro teste será em **homologação (`ambienteCodigo: 2`)**, sem valor fiscal.

## O que já foi verificado

- [Documentação oficial](https://intnfe.com.br/api/doc): NF-e modelo 55, emissão assíncrona, consulta, XML autorizado e DANFE em HTML.
- [Portal do cliente](https://app.intnfe.com.br/login): página acessível. Pede usuário e senha fornecidos pela equipe; a tela examinada não oferece cadastro público e se identifica como ambiente de homologação.
- Lucas entrou no portal. A sessão autenticada identifica a conta **PetSys (smoke test)** e mostra apenas o emitente de exemplo **Ze Pet**. O menu do integrador exibe acompanhamento de clientes e sala de situação; não apresenta cadastro de emitentes nem credenciais de API.
- Na sessão do Bling já aberta pelo Lucas, foram conferidos os dados da **LJ Comercio de Rações e Pet Shop LTDA**, empresa indicada para o teste. O corpo mínimo de cadastro foi preparado localmente em `runtime/analises/fiscal/2026-09-09/cadastro_emitente_pet.json`, fora do Git.
- O código público do portal consultado usa `/portal/auth/login`. A documentação da integração usa `/integrador/auth/token` com `integradorId` e `integradorSecret`. Não foi comprovada intercambialidade entre esses acessos; não houve tentativa de extrair ou reaproveitar o token interno da sessão. As credenciais próprias do integrador continuam pendentes.
- Os arquivos de ambiente conhecidos do projeto e as variáveis da sessão não indicaram credenciais `INTNFE_*`. Nenhum segredo foi copiado para esta documentação.
- Nenhuma empresa/destinatário foi cadastrado e nenhuma NF-e foi transmitida nesta preparação.

## Acesso, empresa e cliente são coisas diferentes

| Termo | O que significa neste teste |
|---|---|
| Login do portal | Usuário/senha liberados pela equipe da IntNFe. Não assumir que são os mesmos dados da API. |
| Credencial de integrador | `integradorId` e `integradorSecret`; permitem gerenciar as empresas vinculadas ao integrador. |
| Empresa emitente | O CNPJ que assina e emite a NF-e, com IE, regime tributário, endereço e certificado A1. A API chama essa empresa de emitente/tenant. |
| Credencial do emitente | `clientId` e `clientSecret`; servem para obter o token de emissão da empresa. |
| Destinatário da nota | O comprador/cliente informado no grupo `destinatario`. A documentação consultada não descreve um endpoint separado de cadastro de compradores; o portal autenticado examinado não mostrou essa função. |
| Chave de acesso da NF-e | Os 44 dígitos que identificam a nota; no fluxo documentado são retornados com a autorização. Não substituem a credencial de acesso à API. |

Se já houver empresa cadastrada, consultar e reutilizar seu cadastro. Não rotacionar segredos nem recriar a empresa para simplesmente testar. Caso o irmão forneça somente acesso de emitente, o cadastro dessa empresa precisa ter sido preparado por ele; o cadastro de empresas pela API exige acesso de integrador.

## Pendências imediatas para executar

| Pendência | Informação/ação necessária | Responsável sugerido |
|---|---|---|
| Acesso à API IntNFe | Portal já acessível; faltam `integradorId` e `integradorSecret` da PetSys ou um fluxo de cadastro que a equipe libere no portal | Irmão/IntNFe e Lucas |
| Cadastro da empresa piloto | LJ identificada; CNPJ e nomes necessários à criação já preenchidos no arquivo local. Antes da nota, conferir endereço/IBGE: o bairro no Bling aparece como `SP` e precisa ser esclarecido | Lucas/empresa piloto |
| Certificado | A1 válido do mesmo CNPJ, já instalado na IntNFe ou arquivo `.pfx`/`.p12` e senha para cadastro protegido | Lucas/empresa piloto |
| Habilitação e série | Confirmar que o emitente pode emitir em homologação na sua UF e qual série de teste utilizar | Irmão/empresa piloto |
| Destinatário | Dados aprovados para o teste: CPF/CNPJ, endereço, indicador de IE e IE quando aplicável | Lucas/irmão |
| Um produto simples | SKU, descrição, NCM, CFOP e tributação compatíveis com o regime escolhido | Irmão; revisão fiscal da empresa quando usar cenário real |

Solicitar credenciais por meio protegido ou entrada direta no portal; não colocar segredos/certificados em documentos, commits ou mensagens de diagnóstico. Os exemplos públicos da API não são credenciais de teste liberadas para uso.

## Roteiro pronto para execução

1. **Entrar e identificar o tipo de acesso.** Conferir a empresa selecionada e manter homologação explícita em cada envio. O rótulo de homologação do portal não substitui `ambienteCodigo: 2` no corpo da API, pois a URL da API também atende produção.
2. **Cadastrar ou localizar a empresa.** Com acesso de integrador, autenticar em `POST /integrador/auth/token`, consultar `GET /integrador/emitentes` e criar apenas se necessário em `POST /integrador/emitentes`, informando CNPJ e nomes. Webhook fica omitido neste primeiro teste. Guardar `tenantId` e as credenciais que a criação retorna uma única vez em local protegido.
3. **Autenticar o emitente.** `POST /auth/token` recebe `clientId` e `clientSecret`. As chamadas de NF-e usam o token desse emitente. Não imprimir token/segredo no relatório.
4. **Verificar o certificado.** `GET /certificados`; cadastrar se necessário em `POST /certificados` com os campos multipart `Arquivo` e `Senha`. A documentação exige A1 e-CNPJ válido, do mesmo CNPJ, até 512 KB. Não há certificado fictício universal documentado; a homologação também depende da assinatura válida.
5. **Conferir a numeração.** `GET /painel/numeracao`; usar a série combinada. A IntNFe atribui o número automaticamente por emitente/série/ambiente. Não zerar nem alterar uma sequência existente por tentativa.
6. **Preparar destinatário e produto.** Preencher o [modelo do corpo](templates/INTNFE_NOTA_SIMPLES_HOMOLOGACAO.json) com os dados definidos. Há um item de uma unidade a R$ 1,00, pagamento em dinheiro de R$ 1,00 e ausência de frete/desconto apenas como cenário proposto. Confirmar esse cenário antes do envio. O exemplo contém marcadores e não está pronto para transmissão. Os campos de impostos devem ser adaptados ao caso; não copiar uma tributação arbitrária de exemplo como regra da empresa.
7. **Revisar e registrar a tentativa.** Conferir emitente, destinatário, produto, regime, série, ambiente e totais. Omitir `destinatario.email` para evitar o envio automático de XML/DANFE a terceiros. Gerar um identificador único de teste e salvar localmente o corpo exato e a `Idempotency-Key` antes de transmitir; resultados e dados privados ficam em `runtime/analises/fiscal/`, fora do Git.
8. **Enviar uma vez.** `POST https://api.intnfe.com.br/nfe`, com token do emitente e `Idempotency-Key`. HTTP 202 e `correlationId` significam aceite para processamento, ainda não autorização fiscal.
9. **Consultar o resultado.** `GET /nfe/{correlationId}`, com intervalo de 2–5 segundos e limite de acompanhamento; respeitar `Retry-After` quando recebido. Se ainda estiver em fila, registrar como pendente. Não disparar outra nota para tentar acelerar.
10. **Guardar a evidência.** Quando autorizada, baixar `GET /nfe/{correlationId}/xml` e `/danfe`. Conferir no XML modelo 55, `tpAmb=2`, empresa, chave/protocolo, item e valor. Registrar situação, número, série, chave, protocolo e caminhos locais protegidos dos arquivos.

### Se a resposta se perder

A documentação passa a descrever `Idempotency-Key` de 8 a 128 caracteres, com escopo por emitente e cache de 24 horas. Repetir a mesma chave e rota devolve a resposta original; enquanto processa pode responder 409. Ela também informa que erros liberam a chave, de modo que não é uma garantia permanente de unicidade.

Guardar a chave com o corpo exato e o horário. Antes de qualquer repetição, consultar pelo `correlationId` se houver ou reconciliar por `GET /nfe` usando período, situação e os dados disponíveis. Não repetir automaticamente um envio inconclusivo depois da janela de 24 horas e não mudar a chave ou o conteúdo para forçar nova nota. Conflitos ou dúvidas de correspondência devem ser levados ao irmão com `X-Correlation-Id`, quando disponível, sem segredos.

## O que caracteriza sucesso

- Emitente e certificado reconhecidos.
- Solicitação aceita com identificador persistido.
- NF-e autorizada em homologação, com chave e protocolo conferidos no XML.
- XML e DANFE obtidos e correspondentes ao único item preparado.

Uma rejeição também gera um resultado útil para o desenvolvimento: guardar código, motivo, passo em que ocorreu e identificador de atendimento. Entretanto, rejeição, HTTP 202 ou a simples geração de DANFE não serão registrados como emissão autorizada. O cadastro do destinatário só será chamado de cadastro persistido se isso for efetivamente confirmado; enviá-lo dentro da nota não comprova uma agenda de clientes no portal.

## Atualização das pendências anteriores

Releitura da [documentação da IntNFe](https://intnfe.com.br/api/doc) em 09/09/2026, após o retorno do irmão. Abaixo, “documentado” não significa “testado”.

| Assunto | Situação documental atual | Tratamento |
|---|---|---|
| Reenvio seguro | Header `Idempotency-Key`, cache de 24 h e conflitos descritos | Usar desde o primeiro envio; validar repetição controlada depois da emissão inicial |
| Reconciliação | `GET /nfe` com período, situação e paginação | Recuperação documentada; comprovar correspondência de uma tentativa incerta |
| Eventos e comprovantes | `GET /nfe/{correlationId}/eventos`, XML e protocolo | Testar cancelamento/CC-e em etapa seguinte |
| ICMS e ICMS-ST | Na releitura após o login, a documentação passou a incluir CST 20/51/90, FCP, redução/diferimento, IPI e DIFAL | Passam a documentados; validar campos, cálculos e XML por cenário |
| Descontos e frete | Desconto por item e grupo de frete/transportadora descritos | Testar totais e arredondamentos em etapa seguinte |
| Referências a notas | `documentosReferenciados` descrito | Referenciar uma chave não comprova fluxo completo de devolução/finalidade e impostos |
| Webhook e recuperação | HMAC, até cinco tentativas, reenvio e reconciliação descritos | Primeiro teste pode usar consulta; validar eventos e recuperação depois |
| Retenção e arquivos | Prazos e download descritos; DANFE em HTML | Validar arquivo local; há aparente divergência entre XML “só autorizada” e menção posterior a canceladas/denegadas, a esclarecer antes de depender desse acesso |
| NFC-e e reforma tributária | Na releitura após o login, surgiram `POST /nfce` e IBS/CBS com valores calculados pelo integrador. NFC-e pede CSC e descreve DANFE provisório | Novidades documentais, ainda não testadas. O primeiro envio continua NF-e modelo 55 |
| NFS-e | Não confirmada na documentação consultada | Cobertura futura a verificar |
| Preço, suporte e operação | Não validados por este teste | Definir antes de contratar/ativar clientes em produção |

Nenhum dos assuntos futuros será usado para exigir a integração completa antes da primeira nota simples. Continuam obrigatórios os dados, o certificado e a compatibilidade do cenário que será efetivamente enviado.

## Registro de execução

| Etapa | Situação em 09/09/2026 |
|---|---|
| Estudo e decisão preservados no projeto | Registrados |
| Documentação pública e portal | Consultados |
| Corpo mínimo | Modelo com marcadores preparado e JSON validado localmente |
| Acesso ao portal | Confirmado, conta PetSys (smoke test) |
| Acesso à API do integrador | Credenciais ainda não disponibilizadas |
| Empresa | LJ identificada no Bling e corpo mínimo de cadastro preparado; ainda não criada na IntNFe |
| Certificado | Ainda não disponibilizado/consultado para a LJ na IntNFe |
| Destinatário | Não cadastrado nem transmitido |
| Nota enviada/autorizada | Não executado |
| Chave/XML/DANFE de teste | Ainda não obtidos |

O próximo passo operacional é receber as credenciais de API da PetSys ou a liberação do cadastro no portal. Com acesso, consultar os emitentes atuais novamente e criar a LJ se ela ainda não existir, guardando com segurança as credenciais retornadas. Não houve alteração de aplicação, banco, estoque, caixa ou implantação em produção.
