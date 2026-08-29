import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  addOperationalMinutes,
  buildTaxiDogWindow,
  toOperationalDateTimeInput,
} from "../src/pages/banhoTosa/taxiDogDateTimeUtils.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const fila = read("src/pages/banhoTosa/components/BanhoTosaFilaView.jsx");
const ficha = read("src/pages/banhoTosa/components/BanhoTosaAtendimentoPanel.jsx");
const transicao = read("src/pages/banhoTosa/components/BanhoTosaTransicaoPanel.jsx");
const fechamentos = read("src/pages/banhoTosa/components/BanhoTosaFechamentosView.jsx");
const relatorios = read("src/pages/banhoTosa/components/BanhoTosaRelatoriosView.jsx");
const exportacao = read("src/pages/banhoTosa/banhoTosaRelatorioExport.js");
const rotas = read("src/app/routes/BathGroomingRoutes.jsx");
const taxiDog = read("src/pages/banhoTosa/components/BanhoTosaTaxiDogList.jsx");

assert.match(
  fila,
  /className="lg:hidden"/,
  "fila deve oferecer uma visualização própria para celular",
);
assert.match(
  fila,
  /BanhoTosaTransicaoPanel/,
  "mudança de etapa deve passar pelo painel operacional",
);
assert.match(fila, /showCode=\{false\}/, "fila nao deve poluir o card com codigos");
assert.match(fila, /atendimento\.pet_nome \|\| "Pet"\} →/, "acao deve identificar o pet");
assert.match(
  transicao,
  /iniciar_timer: operacional/,
  "etapas operacionais devem iniciar o contador",
);
assert.match(ficha, /listarInsumosAtendimento/, "ficha deve carregar consumo");
assert.match(ficha, /registrarOcorrenciaAtendimento/, "ficha deve registrar ocorrências");
assert.match(ficha, /uploadFotoAtendimento/, "ficha deve permitir fotos");
assert.match(ficha, /gerarVendaAtendimento/, "ficha deve gerar cobrança no PDV");
assert.match(ficha, /observacoes_saida/, "fechamento deve salvar observações de saída");
assert.match(
  fechamentos,
  /sincronizarPendenciasFechamento/,
  "central de fechamento deve sincronizar pendências",
);
assert.match(
  rotas,
  /banhoTosaView\("fechamentos"\)/,
  "rota de fechamentos não deve redirecionar silenciosamente para a fila",
);
assert.match(relatorios, /Baixar PDF/, "relatórios devem expor geração de PDF");
assert.match(relatorios, /Exportar CSV/, "relatórios devem expor geração de CSV");
assert.match(exportacao, /new jsPDF/, "exportação deve construir um PDF real");
assert.match(taxiDog, /const statusFlows =/);
assert.match(
  taxiDog,
  /ida: \["agendado", "motorista_a_caminho", "pet_coletado", "entregue_na_clinica"\]/,
  "somente ida deve encerrar ao entregar o pet na loja",
);
assert.match(
  taxiDog,
  /volta: \["agendado", "aguardando_retorno", "retornando", "entregue_ao_tutor"\]/,
  "somente volta deve começar aguardando o retorno",
);
assert.match(taxiDog, /proximoStatus\(item\.status, item\.tipo\)/);
assert.deepEqual(buildTaxiDogWindow("2026-08-29T15:30:00Z"), {
  inicio: "2026-08-29T14:30",
  fim: "2026-08-29T15:30",
});
assert.equal(addOperationalMinutes("2026-08-30T00:15:00-03:00", -60), "2026-08-29T23:15");
assert.equal(toOperationalDateTimeInput("data-invalida"), "");

console.log("Banho & Tosa fluid flow checks passed.");
