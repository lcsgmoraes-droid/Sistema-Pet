# Guia CorePet — configuração fiscal para NF-e e NFC-e

Atualizado em 11/09/2026. Este guia explica como preparar uma empresa para a
emissão de notas de produto pelo CorePet e pela IntNFe. As regras tributárias da
empresa e dos produtos devem ser confirmadas com a contabilidade antes da
primeira emissão em produção.

## O que será configurado

- dados fiscais da empresa;
- vínculo do CNPJ com a IntNFe;
- certificado digital A1;
- CSC da NFC-e em homologação e em produção;
- série e sequência de NF-e (modelo 55) e NFC-e (modelo 65);
- cadastros de clientes, produtos e regras tributárias;
- testes de homologação e conferência antes da primeira nota real.

## NF-e e NFC-e: qual usar

| Documento | Uso mais comum | Identificação do comprador |
|---|---|---|
| NF-e, modelo 55 | Venda de mercadoria, inclusive pedidos enviados e vendas para outro estado | Destinatário completo, conforme a operação |
| NFC-e, modelo 65 | Venda presencial ao consumidor no caixa | Pode sair sem consumidor identificado; informe CPF/CNPJ quando solicitado |

Em São Paulo, a NFC-e passou a ser obrigatória para o varejo paulista em
01/01/2026, conforme a [página oficial da NFC-e da SEFAZ-SP](https://portal.fazenda.sp.gov.br/servicos/nfce/).
A Nota Fiscal Paulista não é outro documento: quando o consumidor pede CPF ou
CNPJ, essa identificação entra na NFC-e.

## 1. Separe as informações da empresa

Antes de abrir a configuração, tenha em mãos:

- CNPJ, razão social e nome fantasia;
- inscrição estadual e regime tributário/CRT;
- endereço completo do estabelecimento;
- certificado A1 em arquivo `.pfx` ou `.p12` e a senha dele;
- CSC e ID do CSC da NFC-e, separados por ambiente;
- última NF-e e última NFC-e autorizadas no sistema anterior, separadas por
  modelo e série;
- NCM, CEST quando aplicável, origem e regras tributárias dos produtos;
- regras aprovadas pela contabilidade para venda interna, interestadual,
  consumidor final, substituição tributária e crédito do Simples.

## 2. Entenda e obtenha o certificado A1

O certificado digital ICP-Brasil identifica a empresa e permite assinar os
documentos fiscais. O A1 é um certificado armazenado como arquivo e costuma ter
validade de um ano. O A3 usa cartão, token ou nuvem e não é o formato aceito no
piloto atual do CorePet/IntNFe.

Para obter um A1:

1. Consulte a [lista de Autoridades Certificadoras da ICP-Brasil](https://www.gov.br/iti/pt-br/assuntos/repositorio/repositorio-ac-raiz).
2. Escolha uma autoridade e solicite um certificado de pessoa jurídica que
   contenha o CNPJ da empresa.
3. Faça a validação indicada pela autoridade, presencialmente ou por
   videoconferência quando disponível.
4. Baixe o arquivo A1 e crie uma senha forte.
5. Guarde uma cópia protegida e anote a data de vencimento.

O [ITI explica os tipos, a obtenção e os cuidados com o certificado](https://www.gov.br/iti/pt-br/acesso-a-informacao/perguntas-frequentes/certificacao-digital).
O arquivo e a senha dão poder de assinatura em nome da empresa: não os envie por
WhatsApp, e-mail comum ou chamados. Use apenas a tela ou o procedimento seguro
indicado pelo CorePet/IntNFe.

No piloto atual, o A1 é cadastrado no portal seguro da IntNFe. O CorePet consulta
se o certificado pertence ao CNPJ, está válido e quando vence. A tela de vínculo
não devolve o arquivo nem a senha.

## 3. Confirme o credenciamento na SEFAZ

O estabelecimento precisa estar habilitado para o modelo que emitirá. Para
NF-e em São Paulo, consulte o
[credenciamento e as orientações oficiais da SEFAZ-SP](https://portal.fazenda.sp.gov.br/servicos/nfe/Paginas/PaginaGuiaDoUsuario.aspx).
O ambiente de homologação não tem validade jurídica; o ambiente de produção tem.

Para NFC-e em São Paulo:

1. acesse o [Portal da NFC-e da SEFAZ-SP](https://portal.fazenda.sp.gov.br/servicos/nfce/);
2. entre no sistema de credenciamento com a forma de autenticação exigida pela
   SEFAZ;
3. selecione o estabelecimento correto;
4. confirme a habilitação para homologação e, quando for iniciar a operação,
   para produção;
5. depois do credenciamento, abra **Gerenciar Cód Segurança** para obter o CSC.

## 4. Obtenha o CSC da NFC-e

CSC significa Código de Segurança do Contribuinte. Ele participa do QR Code da
NFC-e. Não é a senha do certificado, não é a chave de acesso da nota e não é o
segredo da IntNFe.

A SEFAZ entrega dois dados:

- **ID do CSC:** identificador curto, por exemplo `000001`;
- **Código CSC:** token longo e secreto.

Use o par correspondente ao ambiente escolhido. O CorePet separa homologação e
produção; cadastrar o CSC de testes não prepara automaticamente a produção.

No CorePet:

1. entre em **Configurações → Integrações → IntNFe**;
2. na seção **CSC da NFC-e**, escolha **Homologação (testes)** ou **Produção**;
3. informe o ID e o código CSC daquele ambiente;
4. revise a substituição quando já existir um CSC;
5. salve e clique em **Consultar CSC** para confirmar o ID registrado.

O código secreto é enviado diretamente à IntNFe e não volta nas consultas. O
CorePet mostra somente se existe um CSC e qual é o seu ID.

## 5. Ative ou vincule o emitente no CorePet

1. Abra **Configurações → Fiscal** e confira os dados da empresa.
2. Abra **Configurações → Integrações → IntNFe**.
3. Clique em **Ativar emissão em teste** para criar o vínculo, ou use
   **Vincular cadastro existente** se a IntNFe já forneceu `clientId` e
   `clientSecret` para o CNPJ.
4. Clique em **Consultar vínculo e certificado**.
5. Só prossiga quando aparecerem o vínculo concluído e o certificado A1 válido.

Durante o piloto, essa tela é liberada somente para as empresas selecionadas
pela equipe do CorePet.

Os códigos do integrador pertencem ao CorePet e não devem ser digitados na tela
do cliente. O formulário de vínculo aceita apenas os códigos do emitente daquela
empresa.

## 6. Configure série e numeração sem duplicar notas

A sequência é independente para cada combinação de:

- CNPJ emitente;
- modelo 55 ou 65;
- série;
- ambiente de homologação ou produção.

Antes de configurar produção, abra a última nota **autorizada** no Bling ou no
emissor anterior e anote modelo, série e número. Se a última NF-e modelo 55 da
série 2 foi a 17.697, informe `17698` como próximo número para essa mesma
combinação. Repita a conferência para a NFC-e.

No CorePet:

1. na seção **Numeração fiscal**, escolha NF-e ou NFC-e;
2. escolha explicitamente homologação ou produção;
3. informe a série usada no sistema anterior;
4. informe o próximo número;
5. revise o resumo e confirme.

O ajuste só avança. Não escolha uma série aleatória para produção e não tente
voltar a sequência. Notas rejeitadas, denegadas, canceladas ou faixas
inutilizadas exigem conferência do histórico antes da decisão.

## 7. Confira clientes, produtos e regras tributárias

O vínculo técnico não substitui os cadastros fiscais. Antes de emitir, confirme:

| Área | Campos principais |
|---|---|
| Cliente | CPF/CNPJ, indicador de IE, inscrição estadual quando exigida e endereço completo |
| Produto | descrição, SKU, NCM, CEST quando aplicável, origem e unidade |
| Operação | CFOP, consumidor final, presença, finalidade e natureza da operação |
| Tributos | CSOSN/CST de ICMS, PIS, COFINS, IPI quando aplicável, ST, DIFAL, FCP e crédito do Simples |
| Valores | quantidade, preço, desconto, frete, outras despesas, total e forma de pagamento |
| Marketplace | canal, CNPJ do intermediador, identificador no intermediador e referência do pedido |
| Transporte | modalidade do frete, transportadora quando houver, volumes, pesos e rastreio |

O pedido do marketplace traz os fatos comerciais. O CorePet deve aplicar as
regras fiscais aprovadas da empresa e do produto antes de montar a nota.

## 8. Faça a homologação completa

Use sempre **ambiente de homologação** nesta etapa:

1. NF-e simples de venda interna;
2. NF-e para outro estado;
3. NF-e de cada marketplace usado pela empresa;
4. frete por conta do remetente, destinatário e marketplace, quando ocorrer;
5. descontos, múltiplos itens e diferentes formas de pagamento;
6. NFC-e sem consumidor identificado;
7. NFC-e com CPF/CNPJ para Nota Fiscal Paulista;
8. DANFE A4 e DANFE NFC-e em impressora de 80 mm;
9. cancelamento, carta de correção quando cabível e inutilização;
10. reconsulta de situações e download do XML autorizado.

Uma chave de acesso sozinha não prova que a nota foi autorizada. Confira o
estado **Autorizada**, o protocolo, o XML e os dados impressos. O XML autorizado
é o documento fiscal; o DANFE é sua representação.

## 9. Libere a produção com controle

Antes da primeira nota real:

- o A1 está válido e pertence ao CNPJ correto;
- NF-e/NFC-e estão credenciadas na SEFAZ para produção;
- o CSC de produção da NFC-e está confirmado;
- a série e o próximo número de produção foram conciliados com o Bling;
- a contabilidade aprovou as regras do cenário escolhido;
- a mesma venda não será emitida também no sistema anterior;
- os testes de autorização, impressão, reconsulta e cancelamento foram
  concluídos;
- alguém acompanhará a primeira emissão e interromperá novos envios se o
  resultado ficar inconclusivo.

Comece por uma única venda real, de baixo risco e com dados conferidos. Aguarde a
autorização, valide XML e DANFE e só então amplie o volume.

## Problemas mais comuns

| Mensagem ou situação | O que conferir |
|---|---|
| Certificado pendente/inválido | CNPJ do A1, senha, arquivo, validade e cadastro na IntNFe |
| Sem CSC | Ambiente escolhido, ID e código obtidos na SEFAZ |
| Duplicidade de número | Modelo, série, ambiente e última nota autorizada no sistema anterior |
| Rejeição de destinatário | CPF/CNPJ, IE, indicador de IE, endereço e UF |
| Rejeição tributária | CFOP, NCM/CEST, origem, CSOSN/CST e regras da operação |
| Resposta ainda processando | Consultar pelo identificador; não repetir a emissão em sequência |
| DANFE diferente do esperado | Reconsultar a nota autorizada e gerar novamente o DANFE antes de alterar a nota |

Ao pedir suporte, informe CNPJ, ambiente, modelo, série, número, horário,
situação, código da rejeição e protocolo/correlationId. Não inclua senhas,
certificado, CSC, token, segredo ou XML com dados pessoais em mensagens comuns.

## Links oficiais

- [Documentação da API IntNFe](https://intnfe.com.br/api/doc)
- [Portal da NF-e da SEFAZ-SP](https://portal.fazenda.sp.gov.br/servicos/nfe)
- [Credenciamento de NF-e em São Paulo](https://portal.fazenda.sp.gov.br/servicos/nfe/Paginas/PaginaGuiaDoUsuario.aspx)
- [Portal da NFC-e da SEFAZ-SP](https://portal.fazenda.sp.gov.br/servicos/nfce/)
- [Perguntas frequentes sobre certificado digital — ITI](https://www.gov.br/iti/pt-br/acesso-a-informacao/perguntas-frequentes/certificacao-digital)
- [Autoridades Certificadoras da ICP-Brasil](https://www.gov.br/iti/pt-br/assuntos/repositorio/repositorio-ac-raiz)
