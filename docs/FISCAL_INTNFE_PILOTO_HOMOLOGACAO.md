# IntNFe — primeiro teste de NF-e de produto

Registro: 09/09/2026. Situação atual: integrador **CorePet — Lucas Guerra**, emitente LJ ativo e A1 aceito, válido até 02/04/2027. A primeira solicitação de NF-e foi aceita e processada em **homologação**, mas a nota **1, série 001**, foi rejeitada com código `SCHEMA`. Faltam corrigir a geração do XML de ICMS-ST e PIS/COFINS e obter autorização, XML e DANFE. [Diagnóstico para a IntNFe](DIAGNOSTICO_INTNFE_NFE_HOMOLOGACAO_2026-09-09.md).

## Decisão registrada

Lucas informou que seu irmão está avançando no desenvolvimento da IntNFe e considera as dúvidas anteriores, em sua maioria, trabalho futuro orientado pelos testes preliminares. Lucas fará o teste. O objetivo imediato é conseguir acesso, cadastrar/vincular uma empresa e um destinatário de teste e tentar emitir uma NF-e simples de produto.

O [estudo do Bling e da estrutura fiscal do CorePet](ESTUDO_BLING_E_ESTRUTURA_FISCAL_COREPET.md) fica preservado como planejamento. A construção completa desse módulo não é condição para testar diretamente a IntNFe. O primeiro teste será em **homologação (`ambienteCodigo: 2`)**, sem valor fiscal.

## O que já foi verificado

- [Documentação oficial](https://intnfe.com.br/api/doc): NF-e modelo 55, emissão assíncrona, consulta, XML autorizado e DANFE em HTML.
- [Portal do cliente](https://app.intnfe.com.br/login): página acessível. Pede usuário e senha fornecidos pela equipe; a tela examinada não oferece cadastro público e se identifica como ambiente de homologação.
- Lucas entrou no portal. A sessão autenticada identifica a conta **PetSys (smoke test)**. Inicialmente o menu oferecia apenas acompanhamento; depois o portal passou a exibir o ID do integrador e a geração de segredo. Lucas disponibilizou as credenciais para execução do teste.
- Na sessão do Bling já aberta pelo Lucas, foram conferidos os dados da **LJ Comercio de Rações e Pet Shop LTDA**, empresa indicada para o teste. O corpo mínimo de cadastro foi preparado localmente em `runtime/analises/fiscal/2026-09-09/cadastro_emitente_pet.json`, fora do Git.
- A autenticação própria da API em `POST /integrador/auth/token` retornou HTTP 200 e validade de 43.200 segundos. Não foi necessário extrair o token do navegador.
- Credenciais e token foram guardados localmente com proteção DPAPI do Windows, em arquivos ignorados pelo Git. Nenhum segredo foi copiado para esta documentação.
- Na primeira execução, `GET /integrador/emitentes` retornou HTTP 200 e apenas **Ze Pet**. O cadastro da LJ retornou HTTP 409 `EmitenteDuplicado`; a consulta posterior continuou sem a LJ. Após Lucas informar a exclusão do Ze Pet, a lista passou a vazia, mas uma nova tentativa continuou retornando o mesmo conflito. A API considera o CNPJ existente, mas não informa aqui a conta à qual ele pertence nem a situação desse registro.
- Após a equipe informar a remoção de todos os emitentes, o cadastro da LJ foi
  concluído e confirmado por consulta. A autenticação própria do emitente
  retornou HTTP 200. O histórico de recusas abaixo está superado para este CNPJ.
- Lucas autorizou usar os cadastros do Bling apenas em homologação. Um destinatário
  e um produto foram enviados dentro do corpo da primeira nota. Isso não confirma
  um cadastro separado de compradores na IntNFe. O envio recebeu HTTP 202 e depois
  rejeição `SCHEMA`, sem chave ou protocolo de autorização.

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
| Acesso à API IntNFe | Concluído: autenticação e consulta de emitentes funcionando | Lucas/IntNFe |
| Acesso ao emitente LJ | Concluído: emitente criado e ativo sob CorePet — Lucas Guerra; credencial própria protegida e autenticação HTTP 200 | Codex/IntNFe |
| Dados da empresa piloto | Concluído: CNPJ, IE, CRT, endereço e IBGE conferidos. Bairro usado: Vila Industrial, confirmado por consultas de CNPJ e CEP | Codex |
| Certificado | Concluído: A1 do mesmo CNPJ enviado e reconhecido, HTTP 200, não expirado, válido até 02/04/2027 | Lucas/Codex/IntNFe |
| Habilitação e série | Série 1 de homologação iniciada automaticamente pela API, sem alterar sequência. Autorização pela SEFAZ ainda não comprovada | IntNFe |
| Destinatário | Concluído para o envio: cadastro do Bling autorizado por Lucas, CPF válido e endereço/IBGE conferidos, indicador IE 9, sem e-mail | Codex |
| Um produto simples | Concluído para o envio: um item da NF-e 017697 do Bling, com NCM, CFOP, CEST, origem e tributação da referência | Codex |
| XML dos impostos | Corrigir o grupo ICMSSN500 e o tratamento do CST 49 de PIS/COFINS, rejeitados pelo schema | Equipe IntNFe |
| Nota autorizada e arquivos | Após a correção, repetir de forma controlada em homologação; conferir chave, protocolo, XML e DANFE | Lucas/Codex/IntNFe |

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
| Acesso ao portal | Confirmado; integrador renomeado de PetSys (smoke test) para CorePet — Lucas Guerra |
| Acesso à API do integrador | Autenticação HTTP 200 e consulta HTTP 200 confirmadas |
| Empresa | LJ criada e ativa; `tenantId` 4ef8812e-51da-4dd7-85dc-8b47df8c5148 |
| Autenticação do emitente | HTTP 200, credencial própria armazenada com DPAPI |
| Certificado | Upload e consulta HTTP 200; CNPJ correto, válido até 02/04/2027 |
| Destinatário | Enviado no corpo da NF-e; não foi comprovado cadastro separado de comprador |
| Nota enviada/autorizada | HTTP 202; nº 1, série 001, homologação; rejeitada com `SCHEMA`, sem autorização |
| Chave/XML/DANFE de teste | Ainda não obtidos |

### Evidência do impedimento no cadastro

- Rota: `POST /integrador/emitentes`.
- CNPJ preparado para o teste: `33590794000140`.
- Resultado: HTTP 409, código `EmitenteDuplicado`.
- Mensagem retornada: “Já existe um emitente com o CNPJ 33590794000140.”
- Identificador de diagnóstico `X-Correlation-Id`: `e88892115c064c68b697401fe1e7b79d`.
- Horário do retorno registrado: 09/09/2026 às 22:48:47 UTC (19:48:47 em Brasília).
- Duas solicitações de cadastro receberam 409; a segunda capturou a mensagem e o identificador para diagnóstico. Não houve resposta de criação nem credenciais de emitente retornadas.
- Arquivos locais de evidência: `runtime/analises/fiscal/2026-09-09/cadastro_emitente_resultado.json` e `cadastro_emitente_erro.json`. Não contêm o segredo de acesso.

### Nova tentativa após a exclusão informada pelo Lucas

- Lucas informou que Ze Pet era seu cadastro e que ele foi excluído, autorizando nova tentativa.
- A consulta autenticada confirmou **zero emitentes** visíveis na PetSys, com HTTP 200.
- Uma nova chamada de cadastro com o mesmo CNPJ da LJ retornou HTTP 409 `EmitenteDuplicado` e a mesma mensagem de CNPJ existente.
- Identificador de diagnóstico desta tentativa: `37c1b0a98cc14bd691857bb51c9a2077`.
- Início registrado: 09/09/2026 às 23:20:58 UTC (20:20:58 em Brasília).
- Evidência local: `runtime/analises/fiscal/2026-09-09/cadastro-20260909T232058Z.json`. O arquivo `cadastro_emitente_resultado.json` também aponta para esse resultado mais recente.
- Não foram criados emitente, credenciais de emissão ou nota nessa tentativa.

Naquele momento, o próximo passo era a equipe da IntNFe localizar o registro/validação que reservava o CNPJ `33590794000140`. Outro vínculo ou registro excluído eram hipóteses, não causas comprovadas. O bloqueio foi superado no cadastro confirmado às 21:19, registrado ao final. O CNPJ da empresa não foi substituído por um fictício.

Na sequência, foram conferidos certificado, dados fiscais e série de homologação, conforme o registro final. As tentativas remotas descritas acima não alteraram aplicação, banco, estoque, caixa ou produção.

### Preparação do vínculo no CorePet

Por solicitação do Lucas, foi implementada a ativação opcional em **Configurações
→ Integrações → IntNFe**, independente do cadastro inicial da conta. O CorePet
consulta/cria o emitente, protege as credenciais por empresa e mostra a situação
do certificado. Conflito de CNPJ e resposta perdida têm recuperação controlada.

O código e a nova migration estão preparados para revisão. As validações locais
usaram dados fictícios/respostas simuladas. O piloto remoto posterior resolveu
o cadastro, validou o A1 e chegou à rejeição de schema detalhada abaixo.
Não houve emissão, habilitação ou deploy em produção.

Configuração, contrato e pendências: [guia da ativação](ATIVACAO_FISCAL_INTNFE.md)
e [ficha de entrega](entregas/2026-09-09-ativacao-fiscal-intnfe.md).

### Tentativa após a atualização de "Minha conta"

- Lucas informou que o painel passou a permitir edição dos dados do integrador
  e pediu nova tentativa do vínculo como emitente.
- Na sessão PetSys, `/conta` mostra nome, contato e acesso do integrador; o CNPJ
  dessa conta continua separado do CNPJ da empresa emitente. Não foram alterados
  dados cadastrais, senha ou secret do integrador.
- Nova autenticação do integrador: HTTP 200. Consulta dos emitentes: HTTP 200,
  lista vazia. Novo POST com o CNPJ da LJ: **HTTP 409**.
- Horário: 09/09/2026 às **21:00:21 em Brasília** (10/09/2026 00:00:21 UTC).
- Protocolo `X-Correlation-Id`: `02d1de67c4eb434eb1d7c9f4e64b7bf9`.
- Evidência: `runtime/analises/fiscal/2026-09-09/cadastro-20260910T000021Z.json`.
- Nenhum emitente ou segredo de emitente foi retornado. A alteração do painel
  foi conferida; o conflito na criação pela API ainda depende de verificação
  da equipe IntNFe. Não repetir automaticamente nem usar CNPJ fictício.

### Nova versão: login pelo CNPJ

- A atualização seguinte foi confirmada no painel: o login da conta de
  integrador PetSys é `11.444.777/0001-61`; a tela agora permite trocar somente
  a senha, sem editar o login. A sessão existente permaneceu válida. Não foi
  realizado um novo login por senha nem alterada a senha.
- O CNPJ da empresa que se pretende cadastrar como emitente continua sendo
  `33.590.794/0001-40`, da LJ. Os dois papéis não foram confundidos no POST.
- Após a atualização, autenticação e consulta da API retornaram HTTP 200,
  novamente sem emitentes visíveis. Uma nova tentativa manual de criação
  retornou **HTTP 409, `EmitenteDuplicado`**.
- Horário: 09/09/2026 às **21:09:30 em Brasília** (10/09/2026 00:09:30 UTC).
- Protocolo: `fa91fa6b79e541d082ae9b6e5436f47f`.
- Evidência: `runtime/analises/fiscal/2026-09-09/cadastro-20260910T000930Z.json`.
- A alteração de login foi observada; o vínculo do emitente continua pendente
  de correção/verificação pela IntNFe. Nenhum documento fiscal foi enviado.

### Cadastro concluído após remoção dos emitentes

- Às 21:18, Lucas informou que seu irmão removeu todos os emitentes e pediu
  identificar melhor a conta de integrador.
- No site, o nome foi alterado de **PetSys (smoke test)** para
  **CorePet — Lucas Guerra**. A tela confirmou “Dados de cadastro salvos”.
  CNPJ, login e senha do integrador não foram alterados.
- Às **21:19:43 de Brasília** (10/09/2026 00:19:43 UTC), foi iniciada uma única
  criação da LJ após autenticação HTTP 200 e lista vazia. O cliente HTTP usado
  no teste recusou seguir um redirecionamento inseguro no retorno; o status/corpo
  original não foi capturado. Não foi seguida conexão HTTP sem TLS.
- Foi feita **consulta, sem repetir o POST de criação**. Ela confirmou a LJ
  ativa, e o painel mostrou **1 emitente e zero notas**. Identificador:
  `4ef8812e-51da-4dd7-85dc-8b47df8c5148`, CNPJ `33590794000140`.
- Como o segredo retornado uma única vez não foi recebido, foi recuperado o
  acesso **somente ao emitente recém-criado neste teste**: rotação controlada de
  seu `clientSecret`, HTTP 200, seguida de armazenamento local DPAPI. Essa
  recuperação pontual não muda a regra de não rotacionar contas existentes
  automaticamente, nem a implementação do CorePet. O segredo do integrador não
  foi rotacionado.
- Às **21:22:29**, a autenticação própria da LJ em `/auth/token` retornou HTTP
  200. `GET /certificados` retornou **404 `SemCertificado`**.
- `GET /painel/numeracao` retornou HTTP 200, sem registros de numeração
  identificados. Nenhuma série/numeração foi alterada.
- Evidências locais: `cadastro-20260910T001943Z.json` registra o envio iniciado;
  `emissor-lj-vinculado.json` registra a confirmação e consultas. Ambos em
  `runtime/analises/fiscal/2026-09-09/`. A credencial fica somente em
  `intnfe-emitente.dpapi`, protegida e ignorada pelo Git.
- Naquele momento, faltavam o A1 e a preparação da nota. As etapas seguintes
  foram executadas conforme o registro abaixo.

### Certificado aceito e primeira NF-e processada

- Lucas forneceu o arquivo PFX da LJ e sua senha e autorizou usar um cliente e
  um produto já cadastrados no Bling **apenas em homologação**.
- O PFX foi aberto localmente com chave efêmera, sem instalar certificado no
  Windows. CNPJ correto, chave privada presente e validade conferida. A senha
  foi protegida com DPAPI; arquivo e senha não entram no Git.
- Às **21:27:24 de Brasília**, `POST /certificados` e a consulta posterior
  retornaram HTTP 200. Validade de 02/04/2026 a **02/04/2027**, `expirado: false`.
- Cadastro fiscal: CRT Simples Nacional (`"1"`), IE `562465456112`, Avenida
  Brasil 2550, CEP 19013-002, Presidente Prudente/SP, IBGE `3541406`. O bairro
  **Vila Industrial** foi confirmado na [consulta do CNPJ](https://brasilapi.com.br/api/cnpj/v1/33590794000140)
  e na [consulta do CEP](https://viacep.com.br/ws/19013002/json/). O Bling mostrava
  `SP` no bairro; seu cadastro foi apenas consultado, sem edição.
- Referência somente para leitura: NF-e **017697, série 2**, já autorizada no
  Bling. Um item, SKU `022860.1/1`, MGZ EXT COELHOS ORNAMENTAIS 1,2 KG, quantidade
  1, valor R$ 199,00, desconto R$ 127,77, total R$ 71,23. NCM `23099010`, CFOP
  `5405`, CEST `2200100`, origem 0, CSOSN 500, PIS/COFINS CST 49 com valores
  zerados, sem IPI. Foram mantidos os códigos fiscais da referência.
- Destinatário da referência: CPF com dígitos verificadores válidos, endereço
  em Mauá/SP conferido por CEP, IBGE `3529401`, indicador IE 9. Dados pessoais
  completos ficam somente no payload local ignorado. Nome de homologação
  explícito e e-mail omitido. Não houve emissão, salvamento ou outra alteração
  na nota original do Bling.
- O primeiro pedido HTTP foi recusado com **400**, pois o teste enviou `crt`
  como número. Corrigido para string `"1"`, conforme o exemplo oficial. Uma
  consulta confirmou lista vazia antes do novo envio. Payload, chave e resposta
  da tentativa recusada foram preservados; ela não criou uma nota.
- Às **21:37:43**, a solicitação corrigida recebeu **HTTP 202**. Identificador
  `d8026b27-c1e9-441f-b8a0-8f667a901376`; ambiente enviado `2`; numeração atribuída
  **1/001**. O payload e a chave de idempotência foram gravados antes do POST.
- Às **21:37:45**, o processamento terminou com **status 4 — Rejeitada**,
  código `SCHEMA`. O XML de `ICMSSN500` apresenta `vICMSSTRet` onde o schema
  espera `pST`; os grupos gerados para PIS/COFINS também rejeitam o CST `49`.
  [Retorno e parâmetros para diagnóstico](DIAGNOSTICO_INTNFE_NFE_HOMOLOGACAO_2026-09-09.md).
- O portal confirmou **1 nota e 1 rejeição** para a LJ. Chave, protocolo e
  autorização permanecem ausentes; XML autorizado e DANFE não foram obtidos.
  A nota rejeitada não foi reenviada nem teve a tributação trocada para passar.
- Evidências privadas em `runtime/analises/fiscal/2026-09-09/`:
  `certificado-lj-validado.json`, `nota-lj-piloto-payload.json`,
  `nota-lj-piloto-controle.json`, `nota-lj-piloto-resposta.json` e
  `nota-lj-piloto-status.json`. O script de envio bloqueia nova transmissão
  depois de iniciado o pedido; uma retomada exige consultar e revisar o estado.

**Próxima ação:** equipe IntNFe corrigir/validar a montagem desses grupos de
impostos; depois executar nova tentativa controlada, ainda em homologação.
O vínculo real pelo fluxo autenticado do CorePet DEV continua separado deste
piloto direto de API e ainda precisa de validação ponta a ponta.
