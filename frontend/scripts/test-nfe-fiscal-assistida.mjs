import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(__dirname, "../src/utils/nfeFiscalAssistida.js"), "utf8");
const paymentActions = readFileSync(
  resolve(__dirname, "../src/components/modalPagamento/useModalPagamentoActions.js"),
  "utf8",
);
const notesList = readFileSync(
  resolve(__dirname, "../src/pages/centralNFSaida/NFSaidaList.jsx"),
  "utf8",
);
const fiscalModelSelector = readFileSync(
  resolve(__dirname, "../src/components/SeletorModeloDocumentoFiscal.jsx"),
  "utf8",
);
const finalizedSaleQuestion = readFileSync(
  resolve(__dirname, "../src/components/ModalPerguntaNFe.jsx"),
  "utf8",
);
const fiscalAvailability = readFileSync(
  resolve(__dirname, "../src/hooks/useFiscalDocumentAvailability.js"),
  "utf8",
);
const nfceCpfPrompt = readFileSync(
  resolve(__dirname, "../src/components/pdv/NfceCpfPrompt.jsx"),
  "utf8",
);
const finalizedSaleFlow = readFileSync(
  resolve(__dirname, "../src/hooks/usePDVVendaFinalizacao.js"),
  "utf8",
);
const paymentController = readFileSync(
  resolve(__dirname, "../src/components/modalPagamento/useModalPagamentoController.js"),
  "utf8",
);
const finalizedSaleBanner = readFileSync(
  resolve(__dirname, "../src/components/pdv/PDVModoVisualizacaoBanner.jsx"),
  "utf8",
);
const modulesContext = readFileSync(
  resolve(__dirname, "../src/contexts/ModulosContext.jsx"),
  "utf8",
);

assert.match(
  source,
  /A nota ainda nao foi criada/,
  "assistente fiscal deve avisar que a nota nao foi criada quando houver pendencia",
);

assert.match(
  source,
  /\/nfe\/vendas\/\$\{vendaId\}\/corrigir-reemitir/,
  "assistente fiscal deve chamar a recuperação segura da nota rejeitada",
);

assert.match(
  paymentActions,
  /Corrigir e tentar novamente\?/,
  "PDV deve oferecer correção e nova tentativa logo após a rejeição",
);

assert.match(
  notesList,
  /title={`Tentar novamente como \$\{Number\(nota\.modelo\) === 55 \? "NF-e" : "NFC-e"\}`}/,
  "Central de NF deve disponibilizar a recuperação para notas rejeitadas",
);

assert.match(
  source,
  /\/nfe\/vendas\/\$\{vendaId\}\/descartar-rejeicao/,
  "assistente fiscal deve permitir descartar apenas uma tentativa rejeitada",
);

assert.match(
  notesList,
  /Liberar venda para escolher outro modelo de nota/,
  "Central de NF deve permitir liberar a venda sem retransmitir o modelo errado",
);

assert.match(
  source,
  /solicitarCorrecaoFiscal/,
  "assistente fiscal deve abrir a correcao guiada antes de emitir",
);
assert.match(
  source,
  /validacaoFiscalDoErro/,
  "assistente fiscal deve aproveitar pendencias detalhadas devolvidas pelo emissor",
);
assert.match(
  source,
  /tentativaEnvio < 3/,
  "assistente fiscal deve retentar com limite depois da correcao no caixa",
);

const correctionDialog = readFileSync(
  resolve(__dirname, "../src/components/ui/FiscalCorrectionDialogHost.jsx"),
  "utf8",
);
const fiscalReferenceSearch = readFileSync(
  resolve(__dirname, "../src/components/ui/FiscalReferenceSearch.jsx"),
  "utf8",
);
assert.match(
  correctionDialog,
  /Preencher sugestões confiáveis/,
  "correcao guiada deve aplicar em lote apenas sugestoes confiaveis",
);
assert.match(
  correctionDialog,
  /Usar esta sugestão/,
  "correcao guiada deve permitir aceitar explicitamente uma sugestao incerta",
);
assert.match(
  correctionDialog,
  /Alta confiança/,
  "correcao guiada deve identificar o nivel de confianca da sugestao",
);
assert.match(correctionDialog, /Fonte:/, "correcao guiada deve informar de onde veio a sugestao");
assert.match(
  correctionDialog,
  /Contexto identificado:/,
  "correcao guiada deve mostrar o regime e a UF considerados",
);
assert.match(
  correctionDialog,
  /Salvar e tentar emitir novamente/,
  "correcao guiada deve salvar e retomar a emissao",
);
assert.match(
  fiscalReferenceSearch,
  /Base de consulta fiscal/,
  "correcao guiada deve oferecer pesquisa fiscal sem sair do fluxo",
);
assert.match(
  fiscalReferenceSearch,
  /consulta automaticamente o histórico/,
  "pesquisa fiscal deve consultar as referencias sem exigir busca manual",
);
assert.match(
  fiscalReferenceSearch,
  /NCM aplicado/,
  "pesquisa fiscal deve confirmar visualmente quando o NCM for preenchido",
);
assert.match(
  fiscalReferenceSearch,
  /preenchido.*no\s*[\r\n]*\s*formulário/,
  "pesquisa fiscal deve orientar o usuario a revisar o campo preenchido",
);
assert.match(
  correctionDialog,
  /valoresAtuais=\{fiscal\}/,
  "confirmacao da pesquisa fiscal deve refletir o valor atual do formulario",
);
assert.match(
  fiscalReferenceSearch,
  /ncm_oficial/,
  "pesquisa fiscal deve informar a versao da tabela oficial carregada",
);
assert.match(
  fiscalReferenceSearch,
  /portalunico\.siscomex\.gov\.br\/classif/,
  "pesquisa fiscal deve apontar para a classificacao oficial",
);
assert.match(
  fiscalReferenceSearch,
  /A empresa está no Simples Nacional/,
  "pesquisa fiscal deve usar o regime tributario no texto de apoio",
);

assert.match(
  fiscalModelSelector,
  /Modelos disponíveis/,
  "PDV deve apresentar os modelos fiscais como escolhas visiveis",
);
assert.match(
  fiscalModelSelector,
  /Padrão do caixa/,
  "PDV deve identificar a NFC-e como modelo padrao do caixa",
);
assert.match(
  fiscalModelSelector,
  /Com pendências/,
  "card fiscal deve resumir as pendencias sem expandir os detalhes",
);
assert.match(
  fiscalModelSelector,
  /onResolvePending\?\.\(opcao\.tipo\)/,
  "resumo das pendencias deve abrir a correcao guiada",
);
assert.doesNotMatch(
  fiscalModelSelector,
  /pendencias\.slice/,
  "card fiscal nao deve listar as pendencias dentro do seletor",
);
assert.match(
  fiscalModelSelector,
  /aria-label=\{`Explicação sobre \$\{opcao\.titulo\}`\}/,
  "explicacoes dos modelos fiscais devem ficar recolhidas em um botao de ajuda",
);
assert.match(
  fiscalModelSelector,
  /ajudaAberta === opcao\.tipo/,
  "explicacao do modelo deve aparecer somente quando solicitada",
);
assert.match(
  fiscalAvailability,
  /prevalidarNotaFiscal/,
  "modal deve prevalidar NF-e e NFC-e antes de oferecer a emissao",
);
assert.match(
  finalizedSaleQuestion,
  /<span>Finalizar<\/span>/,
  "saida sem emissao fiscal deve usar um rotulo neutro",
);
assert.doesNotMatch(
  finalizedSaleQuestion,
  /Concluir sem nota fiscal/,
  "modal nao deve destacar que a finalizacao ocorreu sem nota",
);
assert.match(
  nfceCpfPrompt,
  /Quer colocar CPF na nota\?/,
  "NFC-e deve perguntar se o cliente quer incluir CPF",
);
assert.match(
  nfceCpfPrompt,
  /aria-label="Explicação sobre CPF na nota"/,
  "explicacao do CPF deve ficar recolhida em um botao de ajuda",
);
assert.match(
  nfceCpfPrompt,
  /atualizarCliente/,
  "CPF informado no caixa deve ser salvo no cadastro do cliente",
);
assert.match(
  nfceCpfPrompt,
  /placeholder="000\.000\.000-00"/,
  "campo de CPF deve aparecer diretamente na pergunta",
);
assert.match(
  nfceCpfPrompt,
  /await onContinueWithoutCpf\?\.\(\)/,
  "continuar sem CPF deve iniciar a emissao da NFC-e no mesmo clique",
);
assert.match(
  nfceCpfPrompt,
  /documentoCpfCnpjCliente\(cliente\)/,
  "campo de CPF deve continuar visivel quando o cadastro tiver apenas espacos",
);
assert.doesNotMatch(
  nfceCpfPrompt,
  /Sim, adicionar CPF/,
  "CPF nao deve exigir um clique extra antes de mostrar o campo",
);
assert.doesNotMatch(
  finalizedSaleFlow,
  /Clique OK para emitir NF-e/,
  "venda finalizada nao deve esconder a escolha do modelo em OK ou Cancelar",
);
assert.match(
  paymentController,
  /moduloAtivo\("fiscal"\)/,
  "fluxo de pagamento deve consultar a contratacao do modulo fiscal",
);
assert.match(
  paymentActions,
  /!moduloFiscalAtivo \|\| devePerguntarNotaFiscal\(resultado\)/,
  "venda sem modulo fiscal deve abrir a conclusao para permitir imprimir o recibo",
);
assert.match(
  finalizedSaleQuestion,
  /\{moduloFiscalAtivo && \([\s\S]*<SeletorModeloDocumentoFiscal/,
  "modal de conclusao deve esconder apenas as opcoes fiscais quando o modulo nao estiver ativo",
);
assert.match(
  finalizedSaleQuestion,
  /useFiscalDocumentAvailability\(moduloFiscalAtivo \? vendaId : null\)/,
  "cliente sem modulo fiscal nao deve consultar a prevalidacao de notas",
);
assert.match(
  finalizedSaleBanner,
  /moduloFiscalAtivo &&[\s\S]*Emitir NF/,
  "venda ja finalizada nao deve exibir emissao sem modulo fiscal",
);
assert.match(
  modulesContext,
  /MODULOS_FORA_DA_OFERTA_PUBLICA = \["bling", "fiscal"\]/,
  "modulo fiscal deve ser tratado como contratacao separada",
);

console.log("NFe fiscal assistant checks passed.");
