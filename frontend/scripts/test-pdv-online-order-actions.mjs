import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

const sidebarSource = readFileSync(
  resolve(__dirname, "../src/components/pdv/PDVVendasRecentesSidebar.jsx"),
  "utf8",
);

const hookSource = readFileSync(resolve(__dirname, "../src/hooks/usePDVVendasRecentes.js"), "utf8");

assert.match(
  sidebarSource,
  /function isPedidoOnlineOperacional/,
  "painel de vendas recentes deve identificar pedidos online operacionais",
);

assert.match(
  sidebarSource,
  /bg-red-50/,
  "aviso de separacao deve ficar vermelho para chamar atencao do operador",
);

assert.match(
  sidebarSource,
  /setMostrarSomentePendenciasSeparacao\(true\)/,
  "clique no aviso de separacao deve ativar filtro de pendencias online",
);

assert.match(
  sidebarSource,
  /vendasRecentes\.filter\(isPedidoOnlinePendente\)/,
  "painel deve conseguir listar somente pedidos online aguardando separacao",
);

assert.match(
  sidebarSource,
  /isPedidoOnlineOperacional\(venda\) && venda\?\.status_entrega === "pendente"/,
  "aviso de separacao deve incluir app/ecommerce com retirada ou entrega",
);

assert.match(
  sidebarSource,
  /marcarProntoRetirada\(e, venda\.id\)/,
  "PDV deve permitir marcar pedido online como pronto",
);

assert.match(
  sidebarSource,
  /Informar quem retirou/,
  "senha de retirada deve abrir o campo para informar quem retirou",
);

assert.match(
  sidebarSource,
  /podeConfirmarConclusao/,
  "PDV deve ter acao de concluir pedido online mesmo sem palavra-chave",
);

assert.match(
  sidebarSource,
  /venda\.tem_entrega \? "Entregue" : "Retirada"/,
  "acao final deve diferenciar entrega e retirada",
);

assert.match(
  hookSource,
  /\/vendas\/\$\{vendaId\}\/marcar-pronto-retirada/,
  "hook do PDV deve chamar a rota de marcar retirada pronta",
);

console.log("PDV online order action checks passed.");
