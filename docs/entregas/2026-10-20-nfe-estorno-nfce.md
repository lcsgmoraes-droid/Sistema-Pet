# NF-e de estorno de operação não realizada

Data: 20/10/2026. Solicitação de Lucas: implementar emissão de NF-e de estorno
no CorePet e regularizar a NFC-e 18574, série 2, da Tecnoagro. Lucas confirmou
que a venda não aconteceu e a mercadoria não saiu.

## Comportamento

A Central de NF de Saída oferece prévia de NF-e modelo 55, entrada, finalidade
de ajuste, referenciando a NFC-e original. A emissão exige administrador,
declaração explícita de operação não realizada e justificativa. Os documentos
originais são preservados; a venda continua cancelada e nenhum ajuste de estoque
ou financeiro é executado novamente.

O primeiro escopo fiscal aceita inversão integral de NFC-e interna, emitente
CRT1, CFOP 5102 para 1102, CSOSN 102 e PIS/COFINS 49 zerados, sem frete ou
acréscimos. Outros cenários são bloqueados antes da transmissão e exigem revisão
fiscal. Pagamento é 90 (sem pagamento), valor zero.

O estorno tem registro próprio por empresa, venda e ambiente. Payload, hash,
referência original, declaração e tentativa são persistidos antes do POST.
Uma tentativa existente não dispara nova nota. Respostas incertas exigem
consulta ou conferência pelo suporte; a janela de idempotência da API não
substitui a proteção permanente no banco.

A confirmação depende do XML autorizado: empresa, ambiente, chave, modelo 55,
entrada, ajuste, referência original, destinatário, itens, tributos, valores e
protocolo. HTTP 202 significa apenas recebimento para processamento. Rejeições
e divergências mantêm a pendência e mostram código/motivo.

O PDV apresenta a regularização separadamente: a NFC-e original continua
autorizada, vinculada ao estorno, e a venda permanece cancelada. XML e DANFE
do novo documento são disponibilizados após confirmação. A contabilidade inclui
estornos próprios validados com identidade `estorno:{id}`, sem misturá-los com
entradas de fornecedores nem substituir a nota original.

## Contrato e orientação fiscal

A documentação atualizada da [IntNFe](https://intnfe.com.br/api/doc#objetos)
descreve `tipoOperacao: "0"`, `finalidade: "3"`,
`documentosReferenciados: [chave]` e `informacoesFisco`.

A [SEFAZ/PR, pergunta 1485](https://atendimento.fazenda.pr.gov.br/sacsefa/portal/assuntosReferente/22)
orienta o estorno quando a operação não ocorreu e o prazo de cancelamento passou.
A [NPF 38/2022, artigo 1º](https://www.sefanet.pr.gov.br/dados/SEFADOCUMENTOS/103202200038.pdf)
detalha os campos do ajuste, inclusive a expressão legal em `infAdFisco`.

No caso de NFC-e sem identificação do consumidor, o sistema não inventa CPF nem
preenche automaticamente o destinatário. A opção de usar os dados do emitente
exige escolha explícita conforme orientação contábil. A norma paranaense
consultada não esclareceu esse preenchimento para o caso concreto.

## Prova real em homologação e impedimento atual

O primeiro envio de estorno em homologação foi recusado HTTP 400 por ausência de
`Emitente.NomeFantasia`. O campo foi corrigido com os dados reais do emitente.
O cliente CorePet passou também a preservar mensagens sanitizadas de
`ProblemDetails.errors`, evitando esconder a identificação do campo inválido.

O envio corrigido, em 20/10/2026 às 20:04:35 de Brasília, foi recebido e
processado como NF-e modelo 55, número 1, série 003, ambiente 2. Resultado:
**rejeição 974: CNPJ do responsável técnico diverge do cadastrado**.
Referência de emissão: `c403b31f-ecf1-4392-a7d9-5218e153c024`.

Esse é um estorno rejeitado em homologação, sem autorização fiscal. Não
regulariza a nota de produção. É necessário conferir o responsável técnico da
emissão NF-e na IntNFe/SEFAZ e concluir a definição fiscal do destinatário antes
de transmitir o estorno real. Nenhuma NF-e de estorno foi emitida em produção.

Os registros operacionais detalhados ficam em `runtime/validacoes/`, ignorados
pelo Git. Segredos, certificados e dados de desenvolvimento não são publicados.

## Ficha de entrega

Identificação conforme `docs/templates/FICHA_ENTREGA.md`: responsável de negócio
Lucas; executor técnico Codex; prioridade P1; risco alto pela transmissão de
documento fiscal e necessidade de preservar isolamento, histórico e valores.
Domínios: fiscal, vendas e envio de XMLs à contabilidade. Branch:
`codex/estorno-nfce-18574`.

### 1. Necessidade e requisitos

Administradores precisam regularizar uma operação não realizada após o prazo de
cancelamento. Aceite: prévia conferível, declaração e justificativa, um envio
persistido, resultado fiscal verdadeiro e documentos vinculados. A conclusão
do caso real permanece pendente. Fora do escopo: nova venda, reembolso no
adquirente, catálogo iFood, DRE e novos cálculos tributários genéricos.

### 2. Regras de negócio e dados

`intnfe_estornos` é responsável pelo novo documento; quatro campos nullable na
venda são apenas projeção. A migration `zzzzm20261020a1`, após `zzzzl20261020a1`,
cria a tabela com RLS e unicidade por empresa/venda/ambiente. Locks e registros
anteriores impedem transmissões concorrentes. O XML original e o histórico do
novo documento são preservados, inclusive em cancelamento externo posterior.

### 3. Arquitetura e integrações

Builder, validador XML, serviço e rotas de estorno são separados da emissão
comercial e do cancelamento da NFC-e. A API IntNFe recebe o modelo 55. Consultas
de resultado não repetem POST de emissão. Falha de rede preserva tentativa e
identificador disponíveis para reconciliação ou suporte.

### 4. Segurança e privacidade

Rotas exigem autenticação, empresa ativa e administrador. Consultas usam tenant
explícito e a tabela tem RLS. CPF/CNPJ, endereço e XML são dados fiscais de acesso
restrito. Credenciais existentes são reutilizadas sem cópia para logs ou payload.
Mensagens externas são sanitizadas. O parser rejeita entidades/DTD; o XML é
conferido contra o snapshot antes de fechar a pendência fiscal.

### 5. Desenvolvimento e qualidade

Implementação separada em persistência/contrato fiscal, projeção comercial,
interface e contabilidade. Cobertura local inclui SQLite real, permissões,
isolamento, falhas de rede, repetição, divergência XML, valores e exportação.
Na fonte final passaram 641 testes de backend. Frontend: 43 testes lógicos,
9 cenários E2E com APIs simuladas, ESLint e build de produção aprovados.
Ruff e verificação do diff passaram; os resultados ficam também na descrição
do PR.

### 6. Ambientes e homologação

Testes locais usam dados fictícios. A prova externa usa credencial e
`ambienteCodigo: 2` explícitos, sem mudar a configuração de produção.
O registro de homologação e seu resultado rejeitado 974 constam nesta ficha.
Pendências não aceitas para emissão real: responsável técnico da NF-e e
definição fiscal do destinatário no caso anônimo do Paraná.

### 7. Publicação e rollback

Entrega de backend, frontend e migration, sem versão mobile. Está em preparação
para revisão por PR; não publicada em produção. A autorização de Lucas para
implementação/publicação já foi dada; os impedimentos são os descritos acima.
Após solucioná-los: validar homologação, executar o release-check completo,
mergear o PR e usar o launcher oficial de deploy remoto. Conferir commit,
migration, health e situação fiscal. Rollback do código deve preservar tabelas,
tentativas e XMLs; não apagar histórico fiscal com downgrade de produção.

### 8. Observabilidade e sustentação

Auditoria registra tentativa, resultado, consulta, usuário, empresa, hash e
identificador remoto. Sucesso exige XML/protocolo conferidos. Erro 974 deve ser
investigado pelo responsável da integração; resultado incerto não é autorização
para nova nota. Alternativa operacional: manter venda cancelada e pendência
fiscal visível enquanto a regularização não está autorizada.

### 9. Mudança, comunicação e treinamento

A ação aparece na Central de NF de Saída, com prévia e explicação da diferença
entre nota original e estorno. O PDV apresenta a regularização sem falsear o
status da NFC-e. Antes da liberação operacional, demonstrar a Lucas a declaração,
a escolha do destinatário e a consulta separada da transmissão.

### 10. Fechamento

Decisão: implementação revisável com pendências; emissão real não concluída.
Testes locais, tenant, auditoria, documentação e rollback foram avaliados.
Homologação autorizada e regularização da NFC-e 18574 continuam pendentes dos
ajustes externos e fiscais descritos nesta ficha, sem prazo presumido.
