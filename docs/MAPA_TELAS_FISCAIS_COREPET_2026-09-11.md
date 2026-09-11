# Mapa das telas fiscais do CorePet

Data da varredura: 11/09/2026.

## Decisão de produto

O CorePet precisa cobrir as mesmas responsabilidades fiscais observadas no
Bling, mas não precisa copiar a organização nem todos os controles do ERP. O
desenho recomendado separa:

1. preparação do emitente e dos modelos fiscais;
2. regras tributárias por natureza de operação;
3. emissão e acompanhamento dos documentos;
4. eventos posteriores, arquivos e entrega ao cliente.

A varredura foi somente de leitura na conta de teste do Bling. Nenhuma
configuração, natureza, certificado ou nota foi alterada.

## O que apareceu no Bling e como fica no CorePet

| Área observada | Função encontrada | Situação atual do CorePet | Decisão para o CorePet |
|---|---|---|---|
| Emissão de NF-e | Layout, ambiente de produção/homologação e teste de comunicação com a SEFAZ | A ativação IntNFe mostra o vínculo e o certificado, mas o fluxo ainda está apresentado como homologação | Criar um painel de prontidão por modelo e ambiente, com estado do provedor, certificado, série e pendências |
| Emissão de NFC-e | Ambiente, CSC, numeração, preenchimento e automatismos | O CSC de homologação já pode ser consultado e gravado; a numeração visível/editável ainda está limitada à NF-e modelo 55 | Incluir uma configuração própria da NFC-e modelo 65, com CSC e sequência separados por ambiente |
| Certificado digital | Tipo de certificado, validade, atualização e remoção | O vínculo IntNFe recebe A1 e informa a validade quando o provedor a devolve | Manter A1 no servidor como primeiro recorte, mostrar validade e permitir rotação segura; outros tipos só entram se o emissor escolhido os suportar |
| Controle de numeração | Série e próximo número por CNPJ/modelo | A tela IntNFe já consulta e só permite avançar a NF-e por série e ambiente | Reutilizar o componente para NF-e e NFC-e, sempre distinguindo modelo, ambiente e autoridade da sequência |
| Preenchimento padrão | Frete, volumes, rastreio, descontos, retenções, grupos especiais, destinatários autorizados do XML e informações complementares | Parte desses dados já aparece no detalhe da Central, mas não existe uma configuração de emissão equivalente | Guardar padrões realmente usados pelo CorePet e preenchê-los a partir da venda/pedido; evitar uma coleção de chaves que só reproduza o Bling |
| Naturezas de operação | Lista de naturezas, padrão por tipo, série, entrada/saída, CRT, presença, consumidor final, devolução e regras por imposto | A configuração atual da empresa guarda regime, CNAE e alguns campos fiscais, sem cadastro versionado de naturezas | Criar uma tela própria de naturezas e regras, com vigência, revisão e critérios por cenário |
| Regras por imposto | Abas de ICMS, IPI, PIS, COFINS, ISSQN, outros e retenções; critérios por destino e produto; CFOP e situação tributária | Produtos guardam parte da classificação, mas não há uma matriz completa por operação | A natureza decide a regra e o produto fornece sua classificação; a combinação final deve ser validada antes da emissão |
| Preferências operacionais | Lançar/estornar estoque e contas, emissão em lote, consulta de protocolo, travas de edição e guias | O CorePet já é a origem de estoque, caixa e financeiro para vendas próprias | A nota não deve repetir efeitos já aplicados pela venda; efeitos fiscais e comerciais ficam registrados separadamente e são reconciliados por origem |
| DANFE e distribuição | Preferências de impressão, DANFE simplificado, assunto/remetente/modelo de e-mail e cópia para transportadora | A Central baixa DANFE/XML e permite compartilhar nota; a IntNFe gera o documento novamente quando solicitado | Manter download/compartilhamento no detalhe da nota; preferências de e-mail e impressão entram depois do núcleo fiscal |
| Inutilizações | Consulta por período e histórico das faixas inutilizadas | Não há tela nem operação própria no CorePet | Criar evento fiscal de inutilização com modelo, série, faixa, justificativa, protocolo, ambiente e situação |
| Cartas de correção | Lista por série/número, texto, data e atualização de protocolo | Existe uma rota legada de CC-e para Bling, sem jornada integrada na Central atual e sem histórico próprio do CorePet | Colocar CC-e dentro do detalhe da nota e também em uma consulta de eventos; habilitar somente quando a IntNFe confirmar o contrato |

## Estrutura de navegação proposta

### 1. Configurações fiscais

A página atual de configuração da empresa continua como origem dos dados
cadastrais, regime e CNAE. Ela deve ganhar um acesso para uma área operacional
com estes blocos:

- **Emitente e provedor:** vínculo IntNFe, estado do cadastro e capacidade
  habilitada;
- **Certificado A1:** situação, validade, atualização e pendências;
- **NF-e:** ambiente, série, próximo número, situação de homologação e teste de
  comunicação;
- **NFC-e:** ambiente, CSC, série, próximo número e situação de homologação;
- **Naturezas de operação:** regras revisadas por cenário, sem alíquotas
  genéricas aplicadas silenciosamente;
- **Pendências fiscais:** atalhos para dados da empresa, cliente, produto,
  certificado, CSC, natureza e numeração.

Homologação e produção devem aparecer como contextos claramente distintos. Uma
configuração válida em homologação não libera produção automaticamente.

### 2. Naturezas de operação

A lista deve mostrar nome, finalidade, direção, modelo, série padrão, vigência,
situção e onde a natureza é usada. O primeiro recorte precisa permitir definir
critérios e resultados para os cenários que forem aprovados com a contabilidade.

Critérios possíveis:

- NF-e ou NFC-e;
- venda, devolução, complemento ou ajuste;
- PDV ou canal de marketplace;
- operação interna ou interestadual;
- consumidor final e condição de contribuinte;
- grupos ou características fiscais do produto.

Resultados da regra:

- CFOP;
- CRT e CSOSN/CST aplicável;
- parâmetros de ICMS, crédito do Simples, ST, DIFAL e FCP;
- CST e parâmetros de PIS/COFINS/IPI quando aplicáveis;
- informações complementares e de interesse do fisco.

Cada mudança precisa de versão, data de vigência, autor e indicação de revisão
contábil. A nota guarda uma fotografia da versão utilizada.

### 3. Central fiscal

A `CentralNFSaida` existente é a base. Ela já oferece filtros, canal, detalhe,
reconciliação, cancelamento, DANFE, XML e compartilhamento. A evolução deve:

- tornar a lista independente do Bling e identificar o provedor de cada nota;
- filtrar também por modelo, ambiente, série e tipo de evento;
- mostrar tentativas, retorno da SEFAZ, chave, protocolo e documentos arquivados;
- reunir cancelamento, CC-e, inutilização e consultas de protocolo em um
  histórico cronológico;
- preservar o vínculo com PDV, pedido do marketplace e EcommerceAI;
- impedir emissão duplicada quando uma resposta externa for inconclusiva.

### 4. Preferências de saída

Depois do fluxo fiscal básico, uma tela menor pode reunir:

- compartilhamento e modelo de e-mail;
- cópia para destinatário ou transportadora;
- formato de impressão do DANFE/NFC-e;
- rastreio e informações complementares;
- pessoas autorizadas a acessar o XML.

Controles raros de segmentos como combustíveis, armamentos, veículos e bebidas
devem ficar condicionados à atividade da empresa. Eles não precisam aparecer no
primeiro recorte do CorePet para pet shops.

## Ordem de implementação

| Prioridade | Entrega | Critério prático |
|---|---|---|
| P0 | Painel de prontidão fiscal para NF-e/NFC-e | O usuário entende o que está pronto e o que bloqueia cada modelo em homologação ou produção |
| P0 | Numeração também para NFC-e | Série e próximo número do modelo 65 podem ser consultados e avançados com as mesmas proteções do modelo 55 |
| P0 | Naturezas de operação versionadas | PDV, venda interna e venda interestadual usam regras explícitas aprovadas para o piloto |
| P0 | Documento fiscal próprio e adaptador IntNFe | A Central não depende do cache do Bling para registrar a emissão, o retorno e os arquivos |
| P0 | Cancelamento e reconsulta | O resultado é conciliado por protocolo sem repetir estoque, caixa ou emissão |
| P1 | CC-e e inutilização | Eventos possuem justificativa, protocolo, XML, situação e histórico auditável |
| P1 | Logística e pagamentos completos | Frete, transportadora, volumes, rastreio e pagamentos do marketplace chegam ao XML sem perder dados |
| P1 | Impressão física e compartilhamento | DANFE A4 e NFC-e 80 mm são validados visualmente e na impressora; envio usa documentos autorizados |
| P2 | Configurações de segmentos e guias | Só entram conforme a atividade e as UFs atendidas exigirem |

## Pendências externas que continuam abertas

- confirmar com a IntNFe a separação do CSC entre homologação e produção;
- corrigir ou expor o rateio do frete nos itens para eliminar a rejeição 535;
- confirmar os endpoints e contratos de cancelamento, CC-e, inutilização e XML
  dos eventos;
- definir com a contabilidade as naturezas e regras dos cenários reais, incluindo
  vendas internas, interestaduais, consumidor final e substituição tributária;
- concluir o contrato de entrada de pedidos do EcommerceAI com canal,
  intermediador, destinatário, logística, pagamentos e referências do pedido.
