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
const finalizedSaleFlow = readFileSync(
  resolve(__dirname, "../src/hooks/usePDVVendaFinalizacao.js"),
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
  /title="Corrigir e tentar novamente"/,
  "Central de NF deve disponibilizar a recuperação para notas rejeitadas",
);

assert.match(
  source,
  /solicitarCorrecaoFiscal/,
  "assistente fiscal deve abrir a correcao guiada antes de emitir",
);

const correctionDialog = readFileSync(
  resolve(__dirname, "../src/components/ui/FiscalCorrectionDialogHost.jsx"),
  "utf8",
);
assert.match(
  correctionDialog,
  /Preencher sugestões/,
  "correcao guiada deve permitir aplicar sugestoes encontradas",
);
assert.match(
  correctionDialog,
  /Salvar e tentar emitir novamente/,
  "correcao guiada deve salvar e retomar a emissao",
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
assert.doesNotMatch(
  finalizedSaleFlow,
  /Clique OK para emitir NF-e/,
  "venda finalizada nao deve esconder a escolha do modelo em OK ou Cancelar",
);

console.log("NFe fiscal assistant checks passed.");
