import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createServer } from "vite";

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
  /Abrir a tela de correção desta nota agora\?/,
  "PDV deve abrir a correção guiada logo após a rejeição",
);

assert.match(
  notesList,
  /Corrigir erro/,
  "Central de NF deve abrir a correção diretamente pela rejeição",
);

assert.match(
  notesList,
  /label: `Tentar novamente como \$\{Number\(nota\.modelo\) === 55 \? "NF-e" : "NFC-e"\}`/,
  "Central de NF deve disponibilizar a recuperação para notas rejeitadas",
);

assert.match(
  source,
  /\/nfe\/vendas\/\$\{vendaId\}\/descartar-rejeicao/,
  "assistente fiscal deve permitir descartar apenas uma tentativa rejeitada",
);

assert.match(
  notesList,
  /Escolher outro modelo de nota/,
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

const correctionDialog = ["FiscalCorrectionDialogHost.jsx", "FiscalCorrectionField.jsx"]
  .map((file) => readFileSync(resolve(__dirname, "../src/components/ui", file), "utf8"))
  .join("\n");
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
  /documentoEmitido \? "Concluir venda" : "Finalizar"/,
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

// Load the real module through the same SSR runner used by other frontend tests.
const servidor = await createServer({
  root: resolve(__dirname, ".."),
  configFile: false,
  optimizeDeps: { noDiscovery: true },
  server: { middlewareMode: true, watch: null, ws: false },
});
try {
  const { default: api } = await servidor.ssrLoadModule("/src/api.js");
  const { emitirNotaFiscalAssistida } = await servidor.ssrLoadModule(
    "/src/utils/nfeFiscalAssistida.js",
  );

  async function obterConfirmacao(resumo) {
    const chamadas = [];
    const validacao = { provedor: "intnfe", pode_emitir: true, resumo_emissao: resumo };
    const postOriginal = api.post;
    api.post = async (url, payload) => {
      chamadas.push({ url, payload });
      assert.equal(url, "/nfe/prevalidar", "cancelar a confirmação não deve emitir nota");
      return { data: validacao };
    };
    try {
      let mensagem = "";
      const resultado = await emitirNotaFiscalAssistida({
        vendaId: 123,
        tipoNota: resumo.modelo === 55 ? "nfe" : "nfce",
        revisarDadosAdicionais: async () => true,
        confirmar: (texto) => {
          mensagem = texto;
          return false;
        },
      });
      assert.equal(resultado.cancelado, true);
      assert.notEqual(mensagem, "", "o fluxo deve solicitar confirmação antes de emitir");
      assert.deepEqual(chamadas, [
        {
          url: "/nfe/prevalidar",
          payload: { venda_id: 123, tipo_nota: resumo.modelo === 55 ? "nfe" : "nfce" },
        },
      ]);
      return mensagem;
    } finally {
      api.post = postOriginal;
    }
  }

  const resumoBalcao = {
    modelo: 65,
    ambiente: "homologação",
    ambiente_codigo: 2,
    serie: 2,
    total: 28.9,
    itens: [{}],
    indicador_presenca: "1",
    destinatario: { nome: "Cliente teste" },
  };
  const enderecoEntrega = {
    logradouro: "Rua de Teste",
    numero: "123",
    complemento: "Casa 2",
    bairro: "Centro",
    municipio: "Curitiba",
    uf: "PR",
    cep: "80000000",
  };
  const resumoEntrega = {
    ...resumoBalcao,
    indicador_presenca: "4",
    destinatario: { nome: "Cliente teste", endereco: enderecoEntrega },
    frete: 5.5,
  };
  const confirmacaoEntrega = await obterConfirmacao(resumoEntrega);
  assert.match(confirmacaoEntrega, /^Entrega própria$/m);
  assert.ok(
    confirmacaoEntrega.includes(
      "Endereço de entrega: Rua de Teste, 123, Casa 2, Centro, Curitiba - PR, CEP 80000000",
    ),
    "a confirmação deve mostrar o endereço estruturado da pré-validação",
  );
  assert.ok(confirmacaoEntrega.includes("Taxa de entrega: R$ 5,50"));

  const confirmacaoEntregaGratuita = await obterConfirmacao({ ...resumoEntrega, frete: 0 });
  assert.match(confirmacaoEntregaGratuita, /^Entrega própria$/m);
  assert.ok(confirmacaoEntregaGratuita.includes("Taxa de entrega: R$ 0,00"));
  assert.ok(confirmacaoEntregaGratuita.includes("Rua de Teste, 123, Casa 2"));

  const textoManual =
    "Pedido MARKETPLACE-QA-8372 | Informações complementares conferidas antes da emissão.";
  const confirmacaoManual = await obterConfirmacao({
    ...resumoBalcao,
    modelo: 55,
    contexto_comercial: {
      canal: "amazon",
      numero_pedido: "MARKETPLACE-QA-8372",
      codigo_rastreamento: "RASTREIO-QA-2123",
    },
    informacoes_adicionais: textoManual,
  });
  assert.match(confirmacaoManual, /^Canal da operação: Amazon$/m);
  assert.match(confirmacaoManual, /^Número do pedido: MARKETPLACE-QA-8372$/m);
  assert.match(confirmacaoManual, /^Rastreamento: RASTREIO-QA-2123$/m);
  assert.ok(confirmacaoManual.includes(`Informações adicionais no DANFE:\n${textoManual}`));

  const observacaoSemVinculo = await obterConfirmacao({
    ...resumoBalcao,
    informacoes_adicionais: "Amazon citada em observação livre, sem vínculo de pedido.",
  });
  assert.match(observacaoSemVinculo, /Informações adicionais no DANFE/);
  assert.doesNotMatch(observacaoSemVinculo, /Canal da operação:|Número do pedido:/);

  const postOriginal = api.post;
  const chamadasSemRevisao = [];
  api.post = async (...args) => {
    chamadasSemRevisao.push(args);
    throw new Error("Nenhuma requisição fiscal é esperada antes de concluir a revisão.");
  };
  try {
    const resultado = await emitirNotaFiscalAssistida({
      vendaId: 123,
      tipoNota: "nfe",
      revisarDadosAdicionais: async () => false,
    });
    assert.equal(resultado.cancelado, true);
    assert.deepEqual(chamadasSemRevisao, [], "fechar a revisão impede prevalidar e emitir");
  } finally {
    api.post = postOriginal;
  }

  assert.equal(
    await obterConfirmacao(resumoBalcao),
    "NFC-e em homologação, série 2\nTotal: R$ 28,90\nItens: 1\nDestinatário: Cliente teste\n\nConfirmar a transmissão destes dados?",
    "o resumo de balcão deve manter o conteúdo atual",
  );
  assert.equal(
    await obterConfirmacao({
      ...resumoBalcao,
      modelo: 55,
      ambiente: "produção",
      ambiente_codigo: 1,
      destinatario: { razaoSocial: "Empresa teste", endereco: enderecoEntrega },
      frete: 5.5,
    }),
    "ATENÇÃO: esta confirmação transmitirá uma nota fiscal real.\n\nNF-e em produção, série 2\nTotal: R$ 28,90\nItens: 1\nDestinatário: Empresa teste\n\nConfirmar a transmissão destes dados?",
    "o resumo de NF-e e o aviso de produção devem permanecer iguais",
  );
} finally {
  await servidor.close();
}

console.log("NFe fiscal assistant checks passed.");
