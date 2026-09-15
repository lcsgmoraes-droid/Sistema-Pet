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
  /Autorizar correcao fiscal e emitir a nota agora\?/,
  "assistente fiscal deve pedir autorizacao clara antes de aplicar sugestoes fiscais",
);

console.log("NFe fiscal assistant checks passed.");
